"""Blender 3D test-scene template for cinematic tire / oil visuals.

Run in Blender: blender -b -P blender_scene.py -- /absolute/path/intro.mp4
Requires a separately installed Blender with supported rendering drivers.
"""
import math
import os
import sys
import bpy
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
output=os.path.abspath(argv[0] if argv else "cinematic_intro.mp4")
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.render.engine="BLENDER_EEVEE_NEXT" if bpy.app.version >= (4, 2, 0) else "BLENDER_EEVEE"
scene.render.resolution_x=720
scene.render.resolution_y=1280
scene.render.resolution_percentage=100
scene.render.fps=30
scene.frame_end=90
def material(name,color,metallic=0.0,roughness=.3):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    bs=m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value=(*color,1)
    bs.inputs["Metallic"].default_value=metallic
    bs.inputs["Roughness"].default_value=roughness
    return m

rubber=material("Rubber",(0.018,.023,.029),.1,.55)
chrome=material("Polished alloy",(.46,.53,.57),.93,.18)
accent=material("Burnt orange",(.95,.18,.03),.56,.22)
bpy.ops.mesh.primitive_torus_add(major_radius=1.65,minor_radius=.52,location=(0,0,0),
                                rotation=(math.pi/2,0,0),major_segments=64,minor_segments=24)
tire=bpy.context.object
tire.name="Cinematic tire"
tire.data.materials.append(rubber)
bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=1.12,depth=.17,location=(0,0,0),
                                    rotation=(math.pi/2,0,0))
hub=bpy.context.object;hub.data.materials.append(chrome)
bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.42,depth=.2,location=(0,-.16,0),
                                    rotation=(math.pi/2,0,0))
bpy.context.object.data.materials.append(accent)
for obj in (tire,hub):
    obj.rotation_euler[1]=0
    obj.keyframe_insert(data_path="rotation_euler",frame=1)
    obj.rotation_euler[1]=math.pi*2
    obj.keyframe_insert(data_path="rotation_euler",frame=90)
def aim(obj,point):
    obj.rotation_euler=(Vector(point)-obj.location).to_track_quat("-Z","Y").to_euler()
bpy.ops.object.camera_add(location=(3,-7,3.1))
camera=bpy.context.object;aim(camera,(0,0,0));scene.camera=camera
for loc,power,color in [((4,-3,5),1400,(1,.35,.15)),((-4,1,2),950,(.18,.4,1))]:
    bpy.ops.object.light_add(type="AREA",location=loc)
    light=bpy.context.object;light.data.energy=power;light.data.color=color
    light.data.shape="DISK";light.data.size=5;aim(light,(0,0,0))
scene.world.color=(.018,.018,.028)
scene.render.image_settings.file_format="FFMPEG"
scene.render.ffmpeg.format="MPEG4"
scene.render.ffmpeg.codec="H264"
scene.render.filepath=output
bpy.ops.render.render(animation=True)
