import unittest
from doctor_pro import scan
class InventoryTest(unittest.TestCase):
    def test_all_twelve_tools_are_accounted_for(self):
        x=scan()['backend_status']
        self.assertEqual(set(x),{'FFmpeg','FFprobe','RIFE','Real-ESRGAN','Blender','MLT',
                      'Auto-Editor','Whisper.cpp','PySceneDetect','OpenColorIO',
                      'OpenTimelineIO','Vid.Stab','frei0r'})
        self.assertTrue(x['FFmpeg']['available'])
