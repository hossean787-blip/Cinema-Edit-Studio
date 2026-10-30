"""Authentication regression for browser editor; no external host or source footage."""
import base64
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from studio_web import Handler, Studio, serve


class RenderAuthenticationTests(unittest.TestCase):
    def test_public_bind_fails_without_credentials(self):
        with patch.dict(os.environ, {"CINEMA_AUTH_USER": "", "CINEMA_AUTH_PASSWORD": ""}):
            with self.assertRaises(RuntimeError):
                serve(host="0.0.0.0", port=0)

    def test_public_bind_rejects_weak_password(self):
        with patch.dict(os.environ, {"CINEMA_AUTH_USER": "owner", "CINEMA_AUTH_PASSWORD": "123"}):
            with self.assertRaises(RuntimeError):
                serve(host="0.0.0.0", port=0)

    def test_all_routes_require_valid_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"CINEMA_AUTH_USER": "owner", "CINEMA_AUTH_PASSWORD": "long-unique-secret-123456789"}):
                server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
                server.studio = Studio(tmp,worker=False)
                thread = threading.Thread(target=server.serve_forever,daemon=True)
                thread.start()
                base = "http://127.0.0.1:" + str(server.server_port)
                try:
                    for path in ("/", "/api/projects", "/api/capabilities"):
                        for header in (None, "Basic YTpi"):
                            request = Request(base + path, headers={"Authorization":header} if header else {})
                            with self.assertRaises(HTTPError) as err:
                                urlopen(request, timeout=5)
                            self.assertEqual(err.exception.code, 401)
                    encoded=base64.b64encode(b"owner:long-unique-secret-123456789").decode("ascii")
                    valid={"Authorization":"Basic "+encoded}
                    with urlopen(Request(base+"/api/projects",headers=valid),timeout=5) as response:
                        self.assertEqual(response.status, 200)
                    # Render dashboard -> editor is a cross-site top-level navigation.
                    navigation=dict(valid, **{"Sec-Fetch-Site":"cross-site",
                        "Sec-Fetch-Mode":"navigate","Sec-Fetch-Dest":"document"})
                    with urlopen(Request(base+"/",headers=navigation),timeout=5) as response:
                        self.assertEqual(response.status,200)
                        self.assertIn(b"CINEMA EDIT STUDIO",response.read())
                    blocked=dict(valid, **{"Sec-Fetch-Site":"cross-site",
                        "Sec-Fetch-Mode":"cors","Sec-Fetch-Dest":"empty"})
                    with self.assertRaises(HTTPError) as err:
                        urlopen(Request(base+"/api/projects",headers=blocked),timeout=5)
                    self.assertEqual(err.exception.code,400)
                    request=Request(base+"/api/projects",data=b'{"title":"test"}',method="POST",
                                    headers={"Content-Type":"application/json"})
                    with self.assertRaises(HTTPError) as err:
                        urlopen(request,timeout=5)
                    self.assertEqual(err.exception.code,401)
                finally:
                    server.shutdown()
                    server.server_close()
                    server.studio.close()


if __name__=="__main__":
    unittest.main()
