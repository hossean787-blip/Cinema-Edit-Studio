"""Regression coverage for professional optional backends with synthetic media."""
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from studio_backends import scene_intervals, export_otio, export_mlt, stabilize, bake_ocio, color_transform
from studio_pro import options_render

class ProfessionalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.src=self.root/'sample.mp4'
        subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi',
                        '-i','testsrc2=size=120x216:rate=15','-t','4',
                        '-c:v','libx264','-pix_fmt','yuv420p',str(self.src)],check=True)

    def test_scenes_and_editable_exports(self):
        intervals=scene_intervals(self.src)
        self.assertTrue(intervals and intervals[0]['end']>0)
        shots=[{'file':str(self.src),'start':0.2,'duration':1.3}]
        otio=export_otio(shots,self.root/'editable.otio')
        xml=export_mlt(shots,self.root/'editable.mlt')
        import opentimelineio as ot
        timeline=ot.adapters.read_from_file(str(otio))
        self.assertEqual(len(timeline.tracks[0]),1)
        self.assertIn(self.src.as_uri(),timeline.tracks[0][0].media_reference.target_url)
        self.assertIn(str(self.src),xml.read_text())

    def test_vidstab_and_ocio(self):
        stabilized=stabilize(self.src,self.root/'stable.mp4')
        self.assertGreater(stabilized.stat().st_size,1000)
        cube=bake_ocio(None,'raw','raw',self.root/'identity.cube')
        result=color_transform(stabilized,self.root/'corrected.mp4',cube)
        self.assertGreater(result.stat().st_size,1000)

    def test_integrated_protects_sources_and_renders(self):
        before=hashlib.sha256(self.src.read_bytes()).hexdigest()
        out=self.root/'final.mp4'
        result=options_render([self.src],out,seconds=3,width=120,height=216,
                              style='sport',detect_scenes=True,
                              stabilize_input=True,ocio_input='raw',
                              ocio_output='raw',interpolate=False)
        self.assertTrue(result['qa']['decoded'])
        self.assertTrue(result['qa']['no_text'])
        self.assertTrue(Path(result['modules']['opentimelineio']).exists())
        self.assertTrue(Path(result['modules']['mlt_xml']).exists())
        self.assertEqual(before,hashlib.sha256(self.src.read_bytes()).hexdigest())
        p=json.loads(Path(str(out)+'.json').read_text())
        self.assertIn('opencolorio',p['modules'])
        with self.assertRaises(ValueError):
            options_render([self.src],self.src,seconds=3,width=120,height=216)

if __name__=='__main__':unittest.main()
