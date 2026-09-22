"""
Integration test for the FastAPI server and endpoints.
Verifies HTML, /api/info, /api/ask, and media streaming using TestClient.
"""

import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from src.ui.server import app

client = TestClient(app)


class TestFastAPIServer(unittest.TestCase):

    def test_01_index_html(self):
        res = client.get("/")
        self.assertEqual(res.status_code, 200)

    def test_02_info_endpoint(self):
        res = client.get("/api/info")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["topic"], "Gradient Descent & Optimization Dynamics")
        self.assertGreater(data["total_chunks"], 0)
        self.assertIn("blob_storage_configured", data)

    def test_03_ask_in_scope(self):
        res = client.post(
            "/api/ask",
            json={"question": "What is the gradient descent parameter update rule?"}
        )
        self.assertEqual(res.status_code, 200)
        ans = res.json()
        self.assertTrue(ans["answered"])
        self.assertGreater(len(ans["citations"]), 0)
        self.assertIsNotNone(ans.get("thinking_summary"))

    def test_04_ask_empty(self):
        res = client.post(
            "/api/ask",
            json={"question": "   "}
        )
        self.assertEqual(res.status_code, 400)

    def test_06_media_pdf(self):
        res = client.get("/media/neural_networks_notes.pdf")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("content-type"), "application/pdf")


if __name__ == "__main__":
    unittest.main()

