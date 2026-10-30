import unittest
from doctor import report

class EnvironmentTests(unittest.TestCase):
    def test_diagnostic_schema(self):
        data=report()
        self.assertIn("platform",data)
        self.assertIn("ffmpeg",data["tools"])
        self.assertIn("rife-ncnn-vulkan",data["tools"])
        self.assertIsInstance(data["tools"]["ffprobe"]["available"],bool)

if __name__=="__main__":
    unittest.main()
