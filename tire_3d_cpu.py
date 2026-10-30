#!/usr/bin/env python3
"""Procedural CPU 3D wheel animation, no Blender/GPU/model assets required.
Optional: requires OpenCV + NumPy in the assistant render runtime.
"""
import argparse
import math
import cv2
import numpy as np
from pathlib import Path

def frame(t,w=400,h=700):
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    cx,cy=w*.5,h*.49
    bg=np.zeros((h,w,3),dtype=np.float32)
    bg[:]=[8,11,17]
    rd=((xx-cx)**2+(yy-cy)**2)**.5
    bg[:,:,2]+=18*np.exp(-rd**2/(w*.8)**2)
    bg[:,:,0]+=10*np.exp(-((xx-cx-w*.42)**2+(yy-cy)**2)/(w*.7)**2)
    angle=t*1.5
    ry=-.33+math.sin(angle)*.3
    rx=-.11+math.sin(angle*.7)*.08
    rz=t*1.7
    mY=np.array([[math.cos(ry),0,math.sin(ry)],[0,1,0],[-math.sin(ry),0,math.cos(ry)]],dtype=np.float32)
    mX=np.array([[1,0,0],[0,math.cos(rx),-math.sin(rx)],[0,math.sin(rx),math.cos(rx)]],dtype=np.float32)
    mZ=np.array([[math.cos(rz),-math.sin(rz),0],[math.sin(rz),math.cos(rz),0],[0,0,1]],dtype=np.float32)
    mat=mX@mY@mZ
    focal=w*1.8
    def project(v):
        transformed=v@mat.T
        z=5.2-transformed[:,2]
        return np.stack([cx+focal*transformed[:,0]/z,
                         cy-focal*transformed[:,1]/z],axis=1),transformed
    for R,r,N,M,base in [(1.34,.43,116,32,(37,42,47)),(.86,.12,100,22,(126,139,152))]:
        a,b=np.meshgrid(np.arange(N)*2*math.pi/N,np.arange(M)*2*math.pi/M,indexing='ij')
        vertices=np.stack([(R+r*np.cos(b))*np.cos(a),
                           (R+r*np.cos(b))*np.sin(a),r*np.sin(b)],axis=-1).reshape(-1,3)
        if R<1:vertices[:,2]-=.12
        coords,transformed=project(vertices)
        light=np.array([-.6,.8,.72],dtype=np.float32)
        faces=[]
        for i in range(N):
            for j in range(M):
                ids=[i*M+j,((i+1)%N)*M+j,((i+1)%N)*M+(j+1)%M,i*M+(j+1)%M]
                xyz=transformed[ids]
                normal=np.cross(xyz[1]-xyz[0],xyz[3]-xyz[0])
                normal/=max(np.linalg.norm(normal),1e-6)
                diffuse=max(0.,float(normal@light))
                spec=max(0.,float(normal@np.array([.08,-.23,.97])))**12
                if R>1:
                    tread=.86+.14*math.cos((i%14)/14*2*math.pi)
                    color=np.array(base)*(.43+.56*diffuse+.14*spec)*tread
                else:
                    color=np.array(base)*(.30+.85*diffuse+1.4*spec)
                col=tuple(int(max(0,min(255,x))) for x in color)
                faces.append((float(xyz[:,2].mean()),coords[ids].astype(np.int32),col))
        faces.sort(key=lambda x:x[0])
        for _,poly,color in faces:
            cv2.fillConvexPoly(bg,poly,color,cv2.LINE_AA)
    def pt(x):
        return tuple(int(k) for k in project(np.array([x],dtype=np.float32))[0][0])
    for a in np.linspace(0,math.tau,8,endpoint=False):
        p1=pt([.22*math.cos(a),.22*math.sin(a),-.25])
        p2=pt([.74*math.cos(a),.74*math.sin(a),-.22])
        cv2.line(bg,p1,p2,(140,145,170),12,cv2.LINE_AA)
        cv2.line(bg,p1,p2,(225,204,175),4,cv2.LINE_AA)
    center=pt([0,0,-.3])
    cv2.circle(bg,center,32,(25,31,47),-1,cv2.LINE_AA)
    cv2.circle(bg,center,22,(164,167,173),-1,cv2.LINE_AA)
    cv2.circle(bg,center,9,(34,47,62),-1,cv2.LINE_AA)
    overlay=bg.copy()
    cv2.ellipse(overlay,(int(cx),int(cy)),(int(w*.42),int(h*.29)),20,20+int(t*150)%360,215+int(t*150)%360,(18,38,245),3,cv2.LINE_AA)
    cv2.ellipse(overlay,(int(cx),int(cy)),(int(w*.45),int(h*.31)),-20,30+int(t*180)%360,155+int(t*180)%360,(240,115,36),2,cv2.LINE_AA)
    cv2.addWeighted(overlay,.24,bg,.76,0,bg)
    return np.clip(bg,0,255).astype(np.uint8)

def create(output,seconds=1.5,width=400,height=700,fps=24):
    if width<64 or height<64 or width%2 or height%2 or not 0<seconds<=12:
        raise ValueError('Invalid animation size or duration')
    output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    writer=cv2.VideoWriter(str(output),cv2.VideoWriter_fourcc(*'mp4v'),fps,(width,height))
    if not writer.isOpened():raise RuntimeError('Cannot create output')
    try:
        for i in range(int(seconds*fps)):
            writer.write(frame(i/fps,width,height))
    finally:writer.release()
    if not output.is_file() or output.stat().st_size<1000:
        raise RuntimeError('Empty animation')
    return output

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('-o','--output',required=True)
    p.add_argument('--seconds',type=float,default=1.5)
    p.add_argument('--width',type=int,default=400)
    p.add_argument('--height',type=int,default=700)
    a=p.parse_args()
    print(create(a.output,a.seconds,a.width,a.height))
