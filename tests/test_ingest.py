import tempfile
import unittest
from pathlib import Path

from stealthera_api import create_app
from stealthera_api.config import Config


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)

        class TestConfig(Config):
            TESTING = True
            STORAGE_MODE = "file"
            LOG_DIR = root / "logs"
            DATA_DIR = root / "data"
            SUPABASE_URL = ""
            SUPABASE_SECRET_KEY = ""
            SUPABASE_SERVICE_ROLE_KEY = ""
            SUPABASE_ANON_KEY = ""
            DASHBOARD_AUTH_TOKEN = ""
            IWOWN_SAMPLE_PATH = root / "missing"

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        for handler in list(self.app.logger.handlers):
            self.app.logger.removeHandler(handler)
            handler.close()
        self.tmp.cleanup()

    def test_short_binary_upload_returns_iwown_error_byte(self):
        response = self.client.post("/pb/upload", data=b"short", content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"\x02")

    def test_prefixed_binary_upload_accepts_valid_outer_packet(self):
        payload = b"984612114945605" + b"DT" + (0).to_bytes(2, "little") + (0).to_bytes(2, "little") + (0x80).to_bytes(2, "little")
        response = self.client.post("/4g/pb/upload", data=payload, content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"\x00")

    def test_call_log_upload_returns_iwown_json(self):
        response = self.client.post(
            "/call_log/upload",
            json={
                "deviceid": "966655060102203",
                "normal_call_logs": [{"status": 2, "call_number": "13312345678"}],
                "sos": [],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["ReturnCode"], 0)

    def test_sleep_endpoint_returns_dummy_shape(self):
        response = self.client.get("/health/sleep?deviceid=860132061275301&sleep_date=2024-12-13")
        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["ReturnCode"], 0)
        self.assertEqual(data["Data"]["score"], 80)


if __name__ == "__main__":
    unittest.main()
