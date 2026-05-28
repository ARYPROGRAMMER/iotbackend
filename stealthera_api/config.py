import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]


class Config:
    load_dotenv(BASE_DIR / ".env")

    SECRET_KEY = os.getenv("APP_SECRET_KEY", "dev")
    STORAGE_MODE = os.getenv("STORAGE_MODE", "supabase").strip().lower()
    SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
    SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
    SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "").strip()
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()
    IWOWN_REGION = os.getenv("IWOWN_REGION", "global").strip().lower()
    IWOWN_API_HOST = os.getenv("IWOWN_API_HOST", "https://euapi.iwown.com").rstrip("/")
    IWOWN_ALGO_HOST = os.getenv("IWOWN_ALGO_HOST", "https://iwap1.iwown.com/algoservice").rstrip("/")
    IWOWN_API_ACCOUNT = os.getenv("IWOWN_API_ACCOUNT", "").strip()
    IWOWN_API_PASSWORD = os.getenv("IWOWN_API_PASSWORD", "").strip()
    DASHBOARD_AUTH_TOKEN = os.getenv("DASHBOARD_AUTH_TOKEN", "").strip()
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_DIR = BASE_DIR / os.getenv("LOG_DIR", "logs")
    DATA_DIR = BASE_DIR / "data"
    UPLOAD_BASE_PATH = os.getenv("UPLOAD_BASE_PATH", "4g").strip("/")
    IWOWN_PROTO_PATH = BASE_DIR / "stealthera_api" / "vendor"
    IWOWN_SAMPLE_PATH = IWOWN_PROTO_PATH
    REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "12"))

    @staticmethod
    def load_runtime_env(app):
        app.config["BASE_DIR"] = BASE_DIR
        app.config["LOG_DIR"].mkdir(parents=True, exist_ok=True)
        app.config["DATA_DIR"].mkdir(parents=True, exist_ok=True)
