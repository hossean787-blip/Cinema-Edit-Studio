"""Safety quotas for memory/disk-limited Render Free trials."""
import io
import tempfile
import unittest
from unittest.mock import patch
import studio_web


class UploadQuotaTests(unittest.TestCase):
    def test_per_file_limit_rejects_before_writing(self):
        with tempfile.TemporaryDirectory() as root:
            s=studio_web.Studio(root,worker=False)
            try:
                p=s.create("quota")
                with patch.object(studio_web,"MAX_UPLOAD",4):
                    with self.assertRaisesRegex(ValueError,"حجم فایل"):
                        s.upload(p["id"],io.BytesIO(b"abcdefgh"),8,"too_big.mp4")
                self.assertEqual(list((s._project_dir(p["id"])/"media").iterdir()),[])
            finally:s.close()

    def test_workspace_quota_rejects_before_writing(self):
        with tempfile.TemporaryDirectory() as root:
            s=studio_web.Studio(root,worker=False)
            try:
                p=s.create("quota")
                with patch.object(studio_web,"MAX_WORKSPACE",1):
                    with self.assertRaisesRegex(ValueError,"فضای اختصاص"):
                        s.upload(p["id"],io.BytesIO(b"123456"),6,"clip.mp4")
                self.assertEqual(list((s._project_dir(p["id"])/"media").iterdir()),[])
            finally:s.close()


if __name__=="__main__":unittest.main()
