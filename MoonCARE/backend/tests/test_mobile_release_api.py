import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


class MobileReleaseApiTests(unittest.TestCase):
    def setUp(self):
        from app.main import app

        self.client = TestClient(app)
        self.fixtures_root = BACKEND_ROOT / "tests" / "fixtures" / "mobile_releases"

    def _fixture_dir(self, name: str) -> Path:
        return self.fixtures_root / name

    def test_android_release_manifest_returns_public_shape(self):
        release_dir = self._fixture_dir("valid")

        with patch.dict(
            os.environ,
            {
                "MOBILE_RELEASES_DIR": str(release_dir),
                "MOBILE_RELEASES_PUBLIC_BASE_URL": "https://updates.mooncare.test",
            },
            clear=False,
        ):
            response = self.client.get("/api/v1/mobile/releases/android/beta")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["message"], "ok")
        self.assertEqual(body["data"]["platform"], "android")
        self.assertEqual(body["data"]["channel"], "beta")
        self.assertEqual(body["data"]["version_code"], 2)
        self.assertEqual(body["data"]["version_name"], "1.1.0")
        self.assertEqual(body["data"]["min_supported_version_code"], 1)
        self.assertFalse(body["data"]["force_update"])
        self.assertEqual(
            body["data"]["apk_url"],
            "https://updates.mooncare.test/api/v1/mobile/releases/android/beta/download",
        )
        self.assertEqual(body["data"]["sha256"], "a" * 64)
        self.assertEqual(body["data"]["size_bytes"], 9)
        self.assertEqual(body["data"]["release_notes"], ["修复聊天恢复", "新增应用更新入口"])

    def test_android_release_manifest_rejects_insecure_download_base_url(self):
        release_dir = self._fixture_dir("valid")

        with patch.dict(
            os.environ,
            {
                "MOBILE_RELEASES_DIR": str(release_dir),
                "MOBILE_RELEASES_PUBLIC_BASE_URL": "http://insecure.mooncare.test",
            },
            clear=False,
        ):
            response = self.client.get("/api/v1/mobile/releases/android/stable")

        self.assertEqual(response.status_code, 503)
        self.assertIn("https", response.json()["detail"].lower())

    def test_android_release_manifest_returns_not_found_when_missing(self):
        release_dir = self._fixture_dir("empty")

        with patch.dict(
            os.environ,
            {
                "MOBILE_RELEASES_DIR": str(release_dir),
                "MOBILE_RELEASES_PUBLIC_BASE_URL": "https://updates.mooncare.test",
            },
            clear=False,
        ):
            response = self.client.get("/api/v1/mobile/releases/android/beta")

        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"].lower())
