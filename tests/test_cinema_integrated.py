"""Integration tests with generated footage; no user files or external accounts."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from cinema_integrated import render, generate_music, beats_from_track

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class CinemaIntegratedTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name)
        self.clips=[]
        for i in range(2):
            file=self.root/f'clip{i}.mp4'
            subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',
                            'testsrc2=size=160x288:rate=24','-t','3.8',
                            '-c:v','libx264','-pix_fmt','yuv420p',str(file)],check=True)
            self.clips.append(file)

    def test_generated_music_has_onsets(self):
        song=self.root/'music.wav'
        generate_music(song,3.2)
        self.assertGreaterEqual(len(beats_from_track(song,3.2)),3)

    def test_full_edit_audio_no_captions(self):
        original=[p.stat().st_size for p in self.clips]
        result=render(self.clips,self.root/'out.mp4',seconds=3.2,
                      width=160,height=288,fps=24)
        self.assertTrue(result['quality']['decoded'])
        self.assertTrue(result['quality']['no_text'])
        self.assertEqual(result['quality']['audio_codec'],'aac')
        self.assertEqual([p.stat().st_size for p in self.clips],original)

    def test_user_supplied_music_and_no_optical_flow(self):
        song=self.root/'audio.wav'
        generate_music(song,3.2)
        result=render(self.clips,self.root/'custom.mp4',music=song,seconds=3.2,
                      width=160,height=288,fps=24,style='cinematic',
                      interpolate=False)
        self.assertEqual(result['music_source'],'provided')

    def test_cannot_destroy_input_file(self):
        with self.assertRaisesRegex(ValueError,'overwrite'):
            render(self.clips,self.clips[0],seconds=3.2,width=160,height=288)
        with self.assertRaises(ValueError):
            render(self.clips,self.root/'odd.mp4',seconds=3.2,width=161,height=288)

if __name__=='__main__':
    unittest.main()
