import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from flask import Blueprint, Response, current_app, jsonify, request

from stealthera_api.iwown.packet import PacketParseError, parse_upload
from stealthera_api.iwown.protobuf_parser import ProtobufParser
from stealthera_api.storage import utc_now


ingest_bp = Blueprint("iwown_ingest", __name__)


def raw_body():
    return request.get_data(cache=False) or b""


def ok_byte():
    return Response(response=bytes([0x00]), status=200, mimetype="text/plain")


def error_byte(value):
    return Response(response=bytes([value]), status=200, mimetype="text/plain")


def json_reply(return_code):
    return jsonify({"ReturnCode": return_code})


def parser():
    existing = getattr(current_app, "protobuf_parser", None)
    if existing is None:
        current_app.protobuf_parser = ProtobufParser(
            current_app.config["IWOWN_SAMPLE_PATH"],
            current_app.logger,
        )
    return current_app.protobuf_parser


@ingest_bp.post("/pb/upload")
@ingest_bp.post("/<path:prefix>/pb/upload")
def upload_pb(prefix=None):
    return handle_binary_upload("pb")


@ingest_bp.post("/alarm/upload")
@ingest_bp.post("/<path:prefix>/alarm/upload")
def upload_alarm(prefix=None):
    return handle_binary_upload("alarm")


def handle_binary_upload(upload_type):
    payload = raw_body()
    source_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    try:
        upload = parse_upload(payload)
    except PacketParseError as exc:
        current_app.logger.warning("iwown %s upload parse failed: %s", upload_type, exc)
        current_app.store.insert(
            "uploads",
            {
                "upload_type": upload_type,
                "payload_bytes": len(payload),
                "source_ip": source_ip,
                "parse_status": "failed",
                "error": str(exc),
                "raw_hex": payload.hex(),
            },
        )
        return error_byte(exc.reply_code)

    upload_id = current_app.store.insert(
        "uploads",
        {
            "device_id": upload.device_id,
            "upload_type": upload_type,
            "packet_count": len(upload.packets),
            "payload_bytes": len(payload),
            "source_ip": source_ip,
            "parse_status": "ok",
            "raw_hex": payload.hex(),
        },
    )
    current_app.store.upsert_device(
        upload.device_id,
        {
            "last_payload_at": utc_now(),
            "latest_seen_at": utc_now(),
        },
    )

    current_app.logger.info("iwown %s upload accepted device=%s packets=%s", upload_type, upload.device_id, len(upload.packets))
    queue_binary_fanout(upload_type, upload_id, upload)
    return ok_byte()


def queue_binary_fanout(upload_type, upload_id, upload):
    app = current_app._get_current_object()

    def worker():
        with app.app_context():
            process_binary_upload(upload_type, upload_id, upload)

    executor = getattr(app, "ingest_executor", None)
    if executor is None:
        process_binary_upload(upload_type, upload_id, upload)
        return

    try:
        executor.submit(worker)
    except Exception:
        app.logger.exception("failed to queue iwown binary upload fanout; processing inline")
        process_binary_upload(upload_type, upload_id, upload)


def process_binary_upload(upload_type, upload_id, upload):
    try:
        for packet in upload.packets:
            decoded = parse_packet(packet)
            packet_id = current_app.store.insert(
                "packets",
                {
                    "upload_id": upload_id,
                    "device_id": upload.device_id,
                    "protocol_code": packet.protocol_code,
                    "protocol_name": decoded["protocol_name"],
                    "packet_length": packet.length,
                    "crc": packet.crc,
                    "payload_hex": packet.payload.hex(),
                    "payload_json": decoded["decoded"],
                },
            )
            for metric in decoded["measurements"]:
                row = dict(metric)
                row["device_id"] = upload.device_id
                row["source_packet_id"] = packet_id
                current_app.store.insert("health_measurements", row)
            for point in decoded["locations"]:
                row = dict(point)
                row["device_id"] = upload.device_id
                row["source_packet_id"] = packet_id
                current_app.store.insert("location_points", row)
            for alarm in decoded["alarms"]:
                row = dict(alarm)
                row["device_id"] = upload.device_id
                row["source_packet_id"] = packet_id
                current_app.store.insert("alarms", row)
    except Exception:
        current_app.logger.exception("iwown %s upload fanout failed device=%s upload_id=%s", upload_type, upload.device_id, upload_id)


def parse_packet(packet):
    try:
        return parser().parse(packet)
    except Exception as exc:
        current_app.logger.exception("packet protobuf parse failed: %s", exc)
        return {
            "protocol_name": packet.protocol_name,
            "decoded": {"error": str(exc), "payload_bytes": len(packet.payload)},
            "measurements": [],
            "locations": [],
            "alarms": [],
        }


@ingest_bp.post("/call_log/upload")
@ingest_bp.post("/<path:prefix>/call_log/upload")
def upload_call_log(prefix=None):
    data = read_json_payload()
    if data is None:
        return json_reply(10002)

    device_id = data.get("deviceid") or data.get("device_id") or data.get("DeviceId")
    current_app.store.insert(
        "uploads",
        {
            "device_id": device_id,
            "upload_type": "call_log",
            "packet_count": 0,
            "payload_bytes": len(json.dumps(data, ensure_ascii=False).encode("utf-8")),
            "source_ip": request.headers.get("X-Forwarded-For", request.remote_addr),
            "parse_status": "ok",
            "raw_json": data,
        },
    )
    current_app.store.upsert_device(device_id, {"latest_seen_at": utc_now()})

    for call in data.get("normal_call_logs", []):
        current_app.store.insert(
            "call_logs",
            {
                "device_id": device_id,
                "call_type": "normal",
                "status": call.get("status"),
                "call_number": call.get("call_number"),
                "start_time": call.get("start_time"),
                "end_time": call.get("end_time"),
                "raw": call,
            },
        )

    for sos in data.get("sos", []):
        current_app.store.insert(
            "sos_events",
            {
                "device_id": device_id,
                "alarm_time": sos.get("alarm_time"),
                "latitude": sos.get("lat"),
                "longitude": sos.get("lon"),
                "call_logs": sos.get("call_logs", []),
                "raw": sos,
            },
        )
        for call in sos.get("call_logs", []):
            current_app.store.insert(
                "call_logs",
                {
                    "device_id": device_id,
                    "call_type": "sos",
                    "status": call.get("status"),
                    "call_number": call.get("call_number"),
                    "start_time": call.get("start_time"),
                    "end_time": call.get("end_time"),
                    "raw": call,
                },
            )

    current_app.logger.info("call log accepted device=%s", device_id)
    return json_reply(0)


@ingest_bp.post("/deviceinfo/upload")
@ingest_bp.post("/<path:prefix>/deviceinfo/upload")
def upload_device_info(prefix=None):
    data = read_json_payload()
    if data is None:
        return json_reply(10002)

    device_id = data.get("deviceid") or data.get("device_id") or data.get("DeviceId")
    current_app.store.insert(
        "uploads",
        {
            "device_id": device_id,
            "upload_type": "device_info",
            "packet_count": 0,
            "payload_bytes": len(json.dumps(data, ensure_ascii=False).encode("utf-8")),
            "source_ip": request.headers.get("X-Forwarded-For", request.remote_addr),
            "parse_status": "ok",
            "raw_json": data,
        },
    )
    current_app.store.upsert_device(
        device_id,
        {
            "model": data.get("model"),
            "version": data.get("version"),
            "raw_info": data,
            "latest_seen_at": utc_now(),
        },
    )
    current_app.logger.info("device info accepted device=%s", device_id)
    return json_reply(0)


@ingest_bp.post("/status/notify")
@ingest_bp.post("/<path:prefix>/status/notify")
def status_notify(prefix=None):
    data = read_json_payload()
    if data is None:
        return json_reply(10002)

    device_id = data.get("DeviceId") or data.get("deviceid") or data.get("device_id")
    status = data.get("Status") or data.get("status")
    event_time = data.get("EventTime") or data.get("event_time")
    current_app.store.insert(
        "device_status_events",
        {
            "device_id": device_id,
            "status": status,
            "event_time": event_time,
            "raw": data,
        },
    )
    current_app.store.upsert_device(
        device_id,
        {
            "status": status,
            "latest_seen_at": event_time or utc_now(),
        },
    )
    current_app.logger.info("status notify accepted device=%s status=%s", device_id, status)
    return json_reply(0)


@ingest_bp.get("/health/sleep")
@ingest_bp.get("/<path:prefix>/health/sleep")
def health_sleep(prefix=None):
    device_id = request.args.get("deviceid") or request.args.get("device_id")
    sleep_date = request.args.get("sleep_date")
    if not device_id or not valid_date(sleep_date):
        return json_reply(10002)

    day = date.fromisoformat(sleep_date)
    previous_day = day - timedelta(days=1)
    sleep = {
        "deviceid": device_id,
        "sleep_date": sleep_date,
        "start_time": f"{previous_day.isoformat()} 23:15:00",
        "end_time": f"{sleep_date} 07:00:00",
        "deep_sleep": 85,
        "light_sleep": 300,
        "weak_sleep": 30,
        "eyemove_sleep": 50,
        "score": 80,
        "osahs_risk": 0,
        "spo2_score": 0,
        "sleep_hr": 60,
    }
    current_app.store.insert(
        "sleep_results",
        {
            "device_id": device_id,
            "sleep_date": sleep_date,
            "start_time": sleep["start_time"],
            "end_time": sleep["end_time"],
            "deep_sleep": sleep["deep_sleep"],
            "light_sleep": sleep["light_sleep"],
            "weak_sleep": sleep["weak_sleep"],
            "eyemove_sleep": sleep["eyemove_sleep"],
            "score": sleep["score"],
            "osahs_risk": sleep["osahs_risk"],
            "spo2_score": sleep["spo2_score"],
            "sleep_hr": sleep["sleep_hr"],
            "raw": sleep,
        },
    )
    return jsonify({"ReturnCode": 0, "Data": sleep})


def read_json_payload():
    payload = raw_body()
    try:
        return json.loads(payload.decode("utf-8"))
    except Exception as exc:
        current_app.logger.warning("json upload parse failed: %s", exc)
        return None


def valid_date(value):
    if not value:
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False
