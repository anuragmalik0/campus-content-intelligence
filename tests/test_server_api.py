"""
Integration test for the FastAPI server and endpoints.
Verifies HTML, /api/info, /api/ask (grounded & refusal), and media streaming.
"""

import unittest
import urllib.request
import json

BASE_URL = "http://127.0.0.1:8000"


class TestFastAPIServer(unittest.TestCase):

    def test_01_index_html(self):
        res = urllib.request.urlopen(f"{BASE_URL}/")
        self.assertEqual(res.status, 200)
        html = res.read().decode("utf-8")
        self.assertIn("Campus Content Intelligence", html)

    def test_02_info_endpoint(self):
        res = urllib.request.urlopen(f"{BASE_URL}/api/info")
        self.assertEqual(res.status, 200)
        data = json.loads(res.read().decode("utf-8"))
        self.assertEqual(data["topic"], "Gradient Descent & Optimization Dynamics")
        self.assertGreater(data["total_chunks"], 0)

    def test_03_ask_in_scope(self):
        req = urllib.request.Request(
            f"{BASE_URL}/api/ask",
            data=json.dumps({"question": "What is the gradient descent parameter update rule?"}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        res = urllib.request.urlopen(req)
        self.assertEqual(res.status, 200)
        ans = json.loads(res.read().decode("utf-8"))
        self.assertTrue(ans["answered"])
        self.assertGreater(len(ans["citations"]), 0)

    def test_04_ask_out_of_scope(self):
        req = urllib.request.Request(
            f"{BASE_URL}/api/ask",
            data=json.dumps({"question": "What is the capital of France?"}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        res = urllib.request.urlopen(req)
        self.assertEqual(res.status, 200)
        ans = json.loads(res.read().decode("utf-8"))
        self.assertFalse(ans["answered"])
        self.assertIsNotNone(ans["reason"])


    def test_06_media_pdf(self):
        res = urllib.request.urlopen(f"{BASE_URL}/media/neural_networks_notes.pdf")
        self.assertEqual(res.status, 200)
        self.assertEqual(res.headers.get("Content-Type"), "application/pdf")


if __name__ == "__main__":
    unittest.main()
