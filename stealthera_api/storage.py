import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock


TABLES = [
    "devices",
    "uploads",
    "packets",
    "health_measurements",
    "location_points",
    "alarms",
    "call_logs",
    "sos_events",
    "device_status_events",
    "command_logs",
    "sleep_results",
]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def create_store(config, logger):
    store = SupabaseStore(config, logger)
    if store.ready:
        return store
    return FileStore(config, logger)


class SupabaseStore:
    name = "supabase"

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.client = None
        self.ready = False
        self.connect()

    def connect(self):
        url = self.config.get("SUPABASE_URL", "")
        if not self.config.get("STORAGE_MODE") == "supabase":
            return
        keys = [
            self.config.get("SUPABASE_SERVICE_ROLE_KEY", ""),
            self.config.get("SUPABASE_SECRET_KEY", ""),
            self.config.get("SUPABASE_ANON_KEY", ""),
        ]
        keys = [key for key in keys if key and "replace-with" not in key]
        if not url or "your-project" in url or not keys:
            self.logger.warning("supabase credentials are not configured, using file storage")
            return
        try:
            from supabase import create_client

            last_error = None
            for key in keys:
                try:
                    self.client = create_client(url, key)
                    self.ready = True
                    return
                except Exception as exc:
                    last_error = exc
            raise last_error
        except Exception as exc:
            self.logger.warning("supabase client unavailable, using file storage: %s", exc)

    def insert(self, table, record):
        data = dict(record)
        data.setdefault("id", str(uuid.uuid4()))
        data.setdefault("received_at", utc_now())
        try:
            result = self.client.table(table).insert(data).execute()
            rows = getattr(result, "data", None) or []
            if rows:
                return rows[0].get("id", data["id"])
        except Exception as exc:
            self.logger.exception("supabase insert failed for %s: %s", table, exc)
        return data["id"]

    def upsert_device(self, device_id, values):
        if not device_id:
            return
        data = dict(values)
        data["device_id"] = device_id
        data.setdefault("latest_seen_at", utc_now())
        try:
            self.client.table("devices").upsert(data, on_conflict="device_id").execute()
        except Exception as exc:
            self.logger.exception("supabase device upsert failed: %s", exc)

    def recent(self, table, limit=20, order_by="received_at"):
        try:
            result = (
                self.client.table(table)
                .select("*")
                .order(order_by, desc=True)
                .limit(limit)
                .execute()
            )
            return getattr(result, "data", None) or []
        except Exception:
            return []

    def count(self, table):
        try:
            result = self.client.table(table).select("id", count="exact").limit(1).execute()
            return getattr(result, "count", 0) or 0
        except Exception:
            return 0

    def dashboard(self):
        return dashboard_payload(self)


class FileStore:
    name = "file"

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.root = Path(config["DATA_DIR"])
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        for table in TABLES:
            (self.root / f"{table}.jsonl").touch(exist_ok=True)

    def insert(self, table, record):
        data = dict(record)
        data.setdefault("id", str(uuid.uuid4()))
        data.setdefault("received_at", utc_now())
        with self._lock:
            with (self.root / f"{table}.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(data, ensure_ascii=False, default=str) + "\n")
        return data["id"]

    def upsert_device(self, device_id, values):
        if not device_id:
            return
        data = dict(values)
        data["device_id"] = device_id
        data.setdefault("latest_seen_at", utc_now())
        self.insert("devices", data)

    def all_rows(self, table):
        rows = []
        path = self.root / f"{table}.jsonl"
        if not path.exists():
            return rows
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows

    def recent(self, table, limit=20, order_by="received_at"):
        rows = self.all_rows(table)
        rows.sort(key=lambda row: row.get(order_by) or row.get("received_at") or "", reverse=True)
        if table == "devices":
            latest = {}
            for row in rows:
                latest.setdefault(row.get("device_id"), row)
            rows = list(latest.values())
        return rows[:limit]

    def count(self, table):
        return len(self.all_rows(table))

    def dashboard(self):
        return dashboard_payload(self)


def dashboard_payload(store):
    return {
        "storage": store.name,
        "counts": {table: store.count(table) for table in TABLES},
        "devices": store.recent("devices", 12, "latest_seen_at"),
        "uploads": store.recent("uploads", 16),
        "alarms": store.recent("alarms", 8),
        "status_events": store.recent("device_status_events", 8),
        "commands": store.recent("command_logs", 8),
    }
