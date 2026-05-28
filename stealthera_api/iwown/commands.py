from flask import Blueprint, current_app, jsonify, request

from stealthera_api.iwown.client import IwownClient


commands_bp = Blueprint("iwown_commands", __name__)


DEVICE_COMMANDS = {
    "userinfo": {"method": "POST", "path": "/entservice/cmd/userinfo", "label": "Deliver user setting to device"},
    "realtime_location": {"method": "POST", "path": "/entservice/cmd/realtime/location", "label": "Enable device realtime locate"},
    "data_sync": {"method": "POST", "path": "/entservice/cmd/datasync", "label": "Request device data upload"},
    "device_status": {"method": "GET", "path": "/entservice/device/status", "label": "Device online/offline status"},
    "fall_check": {"method": "POST", "path": "/entservice/cmd/fallcheck", "label": "Set device fall check option"},
    "phonebook_sync": {"method": "POST", "path": "/entservice/phonebook/sync", "label": "Set phonebook"},
    "phonebook_clear": {"method": "POST", "path": "/entservice/phonebook/clear", "label": "Clear phonebook"},
    "datafreq": {"method": "POST", "path": "/entservice/cmd/datafreq", "label": "Device data interval setting"},
    "locate_dataupload_freq": {"method": "POST", "path": "/entservice/cmd/locate_dataupload/freq", "label": "Device data upload and auto locate interval setting"},
    "lcdgesture": {"method": "POST", "path": "/entservice/cmd/lcdgesture", "label": "Set wrist turn light up"},
    "hr_alarm": {"method": "POST", "path": "/entservice/cmd/hralarm", "label": "Set heart rate warning"},
    "dynamic_hr_alarm": {"method": "POST", "path": "/entservice/cmd/dynamic/hralarm", "label": "Dynamic heart rate warning setting"},
    "spo2_alarm": {"method": "POST", "path": "/entservice/cmd/spo2alarm", "label": "Set blood oxygen alarm"},
    "bp_alarm": {"method": "POST", "path": "/entservice/cmd/bpalarm", "label": "Blood pressure warning setting"},
    "temperature_alarm": {"method": "POST", "path": "/entservice/cmd/temperature/alarm", "label": "Temperature warning setting"},
    "auto_af": {"method": "POST", "path": "/entservice/cmd/autoaf", "label": "Auto AF setting"},
    "alarm_set": {"method": "POST", "path": "/entservice2/clockalarm/set", "label": "Set alarm"},
    "alarm_clear": {"method": "POST", "path": "/entservice2/clockalarm/clear", "label": "Clear alarm"},
    "sedentary_set": {"method": "POST", "path": "/entservice3/sedentary/set", "label": "Set sedentary"},
    "sedentary_clear": {"method": "POST", "path": "/entservice3/sedentary/clear", "label": "Clear sedentary"},
    "goal": {"method": "POST", "path": "/entservice/cmd/goal", "label": "Goal setting"},
    "factory_reset": {"method": "POST", "path": "/entservice/cmd/factory/reset", "label": "Reset to factory mode"},
    "language_set": {"method": "POST", "path": "/entservice/cmd/language/set", "label": "Set device language"},
    "message": {"method": "POST", "path": "/entservice/cmd/message", "label": "Send device message"},
    "fallcheck_sensitivity": {"method": "POST", "path": "/entservice/cmd/fallcheck/sensitivity", "label": "Set fall detection sensitivity"},
    "hr_measure_interval": {"method": "POST", "path": "/entservice/cmd/measure/interval/hr", "label": "Heart rate measurement interval setting"},
    "other_measure_interval": {"method": "POST", "path": "/entservice/cmd/measure/interval/other", "label": "Other measurement interval setting"},
    "gps_locate": {"method": "POST", "path": "/entservice/cmd/gps/locate", "label": "GPS locate"},
    "time_format": {"method": "POST", "path": "/entservice/cmd/timeformat", "label": "Set time format"},
    "date_format": {"method": "POST", "path": "/entservice/cmd/dateformat", "label": "Set date format"},
    "distance_unit": {"method": "POST", "path": "/entservice/cmd/distanceunit", "label": "Set distance units"},
    "temperature_unit": {"method": "POST", "path": "/entservice/cmd/temperatureunit", "label": "Set temperature units"},
    "wear_hand": {"method": "POST", "path": "/entservice/device/cmd/wearhand", "label": "Set wear hand"},
    "bp_adjust": {"method": "POST", "path": "/entservice/cmd/bpadjust", "label": "Set blood pressure calibration"},
}


CALCULATION_COMMANDS = {
    "sleep": {"method": "POST", "path": "/calculation/sleep", "label": "Sleep calculation"},
    "ecg": {"method": "POST", "path": "/calculation/ecg", "label": "ECG analysis"},
    "af": {"method": "POST", "path": "/calculation/af", "label": "AF analysis"},
    "spo2": {"method": "POST", "path": "/calculation/spo2", "label": "Continuous blood oxygen analysis"},
    "parkinson_acc": {"method": "POST", "path": "/calculation/parkinson/acc", "label": "Parkinson ACC analysis"},
    "matress_sleep": {"method": "POST", "path": "/calculation/matress/sleep", "label": "Mattress sleep calculation"},
}


def client():
    existing = getattr(current_app, "iwown_client", None)
    if existing is None:
        current_app.iwown_client = IwownClient(current_app.config, current_app.logger)
    return current_app.iwown_client


@commands_bp.get("/api/iwown/commands")
def list_commands():
    return jsonify({"device_commands": DEVICE_COMMANDS, "calculations": CALCULATION_COMMANDS})


@commands_bp.route("/api/iwown/commands/<command_key>", methods=["GET", "POST"])
def run_device_command(command_key):
    command = DEVICE_COMMANDS.get(command_key)
    if not command:
        return jsonify({"ReturnCode": 10404, "message": "unknown command", "available": sorted(DEVICE_COMMANDS)}), 404

    method = command["method"]
    params = dict(request.args)
    body = request.get_json(silent=True) or {}
    if method == "GET":
        result = client().call_device_api(method, command["path"], params=params)
    else:
        result = client().call_device_api(method, command["path"], json_body=body, params=query_passthrough(params))

    log_command(command_key, command, body, result)
    status = result["status_code"] if not result["ok"] else 200
    return jsonify(result["body"]), status


@commands_bp.post("/api/iwown/calculations/<calculation_key>")
def run_calculation(calculation_key):
    command = CALCULATION_COMMANDS.get(calculation_key)
    if not command:
        return jsonify({"ReturnCode": 10404, "message": "unknown calculation", "available": sorted(CALCULATION_COMMANDS)}), 404

    body = calculation_body(request.get_json(silent=True) or {})
    result = client().call_algorithm_api(command["method"], command["path"], json_body=body)
    log_command(calculation_key, command, body, result)
    status = result["status_code"] if not result["ok"] else 200
    return jsonify(result["body"]), status


def query_passthrough(params):
    passthrough = {}
    if params.get("device_model"):
        passthrough["device_model"] = params["device_model"]
    return passthrough


def calculation_body(body):
    data = dict(body)
    account = current_app.config.get("IWOWN_API_ACCOUNT", "")
    password = current_app.config.get("IWOWN_API_PASSWORD", "")
    if account and "account" not in data:
        data["account"] = account
    if password and "password" not in data:
        data["password"] = password
    return data


def log_command(command_key, command, body, result):
    response = result.get("body") or {}
    current_app.store.insert(
        "command_logs",
        {
            "command_key": command_key,
            "path": command["path"],
            "method": command["method"],
            "device_id": body.get("device_id") or request.args.get("device_id"),
            "status_code": result.get("status_code"),
            "return_code": response.get("ReturnCode") or response.get("returnCode"),
            "request_body": body,
            "response_body": response,
            "error": None if result.get("ok") else response.get("message") or response.get("raw"),
        },
    )
