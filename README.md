# Stealthera 4G Wearable Backend

Flask backend for IWOWN 4G watch data ingestion, Supabase storage, outbound device commands, calculation proxies, logging, and a simple operations dashboard.

## Local Setup

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Dashboard:

```text
http://localhost:8098/dashboard
```

Health check:

```text
http://localhost:8098/healthz
```

## Environment

Edit `.env` with Supabase and IWOWN credentials. Use `supabase/schema.sql` in the Supabase SQL editor before pointing production devices at the API.

The Supabase Python client uses the service-role JWT cleanly. Keep the newer secret key in `.env`, but provide the service-role key too.

## Verify

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -c "from stealthera_api import create_app; app=create_app(); print(app.store.name)"
```

The second command should print `supabase` after the database credentials are valid.

The backend accepts IWOWN uploads with or without a prefix. For production, give the wearable team one base prefix and use the same prefix for all six IWOWN routes.

```text
https://api.stealthera.com/4g/pb/upload
https://api.stealthera.com/4g/alarm/upload
https://api.stealthera.com/4g/call_log/upload
https://api.stealthera.com/4g/deviceinfo/upload
https://api.stealthera.com/4g/status/notify
https://api.stealthera.com/4g/health/sleep
```

## Watch Upload Routes

```text
POST /pb/upload
POST /alarm/upload
POST /call_log/upload
POST /deviceinfo/upload
POST /status/notify
GET  /health/sleep?deviceid={device_id}&sleep_date=YYYY-MM-DD
```

Binary upload routes return a one-byte response. Success is `0x00`, short payload is `0x02`, and invalid packet header is `0x03`.

## IWOWN Command Routes

```text
GET  /api/iwown/commands
GET  /api/iwown/commands/device_status?device_id={device_id}
POST /api/iwown/commands/{command_key}
POST /api/iwown/calculations/{calculation_key}
```

The command key list is returned by `/api/iwown/commands`. Credentials are read from `IWOWN_API_ACCOUNT` and `IWOWN_API_PASSWORD`; the password is sent as MD5 as required by IWOWN.

## Storage

Production storage is Supabase. If `.env` still has placeholder Supabase values, the app falls back to local JSONL files under `data/` so developers can test uploads without cloud credentials.
