import importlib
import math
import sys
from datetime import datetime, timezone


INT32_MAX = 2147483647


class ProtobufParser:
    def __init__(self, sample_path, logger):
        self.sample_path = str(sample_path)
        self.logger = logger
        self.ready = False
        self.modules = {}
        self.message_to_dict = None
        self.decode_error = None
        self.prepare()

    def prepare(self):
        if self.sample_path and self.sample_path not in sys.path:
            sys.path.insert(0, self.sample_path)
        try:
            from google.protobuf import message
            from google.protobuf.json_format import MessageToDict

            self.decode_error = message.DecodeError
            self.message_to_dict = MessageToDict
            self.modules["history"] = importlib.import_module("theproto.his_data_pb2")
            self.modules["history_health"] = importlib.import_module("theproto.his_health_data_pb2")
            self.modules["oldman"] = importlib.import_module("theproto.om0_command_pb2")
            self.modules["alarm"] = importlib.import_module("theproto.Alarm_info_pb2")
            self.ready = True
        except Exception as exc:
            self.logger.warning("protobuf parser unavailable: %s", exc)

    def parse(self, packet):
        base = {
            "protocol_name": packet.protocol_name,
            "decoded": {},
            "measurements": [],
            "locations": [],
            "alarms": [],
        }
        if not self.ready:
            base["decoded"] = {"parser": "unavailable"}
            return base
        if packet.protocol_code == 0x0A:
            return self.parse_realtime(packet.payload)
        if packet.protocol_code == 0x80:
            return self.parse_history(packet.payload)
        if packet.protocol_code == 0x12:
            return self.parse_alarm(packet.payload)
        base["decoded"] = {"payload_bytes": len(packet.payload)}
        return base

    def parse_realtime(self, payload):
        module = self.modules["oldman"]
        report = module.OM0Report()
        report.ParseFromString(payload)
        measured_at = protobuf_time(report.date_time)
        decoded = self.to_dict(report)
        measurements = []
        locations = []

        if report.HasField("battery"):
            measurements.append(
                {
                    "metric_type": "battery",
                    "measured_at": measured_at,
                    "values": {"level": report.battery.level},
                }
            )

        if report.HasField("rssi"):
            rssi = report.rssi
            if rssi > INT32_MAX:
                rssi = -((rssi ^ 0xFFFFFFFF) + 1)
            measurements.append(
                {
                    "metric_type": "signal",
                    "measured_at": measured_at,
                    "values": {"rssi": rssi},
                }
            )

        if report.HasField("health"):
            measurements.append(
                {
                    "metric_type": "realtime_activity",
                    "measured_at": measured_at,
                    "values": {
                        "steps": report.health.steps,
                        "distance": report.health.distance * 0.1,
                        "calorie": report.health.calorie * 0.1,
                    },
                }
            )

        for track in report.track_data:
            locations.append(
                {
                    "measured_at": protobuf_time(track.time),
                    "latitude": safe_number(track.gnss.latitude),
                    "longitude": safe_number(track.gnss.longitude),
                    "gps_type": track.gps_type,
                    "raw": self.to_dict(track),
                }
            )

        return {
            "protocol_name": "realtime",
            "decoded": decoded,
            "measurements": measurements,
            "locations": locations,
            "alarms": [],
        }

    def parse_history(self, payload):
        history_module = self.modules["history"]
        health_module = self.modules["history_health"]
        notice = history_module.HisNotification()
        notice.ParseFromString(payload)
        decoded = self.to_dict(notice)
        measurements = []
        locations = []
        data_field = notice.WhichOneof("data")

        if data_field == "his_data":
            his_type = enum_name(history_module.HisDataType, notice.type)
            his_data = notice.his_data
            if notice.type == history_module.HisDataType.HEALTH_DATA and his_data.HasField("health"):
                values = self.history_health_values(his_data.health, health_module)
                measurements.extend(values)
            elif notice.type == history_module.HisDataType.ECG_DATA and his_data.HasField("ecg"):
                measurements.append(raw_series_metric("ecg_raw", his_data.ecg.time_stamp, his_data.ecg.raw_data))
            elif notice.type == history_module.HisDataType.RRI_DATA and his_data.HasField("rri"):
                measurements.append(raw_series_metric("rri_raw", his_data.rri.time_stamp, split_u16_words(his_data.rri.raw_data)))
            elif notice.type == history_module.HisDataType.SPO2_DATA and his_data.HasField("spo2"):
                measurements.append(raw_series_metric("continuous_spo2", his_data.spo2.time_stamp, parse_spo2_words(his_data.spo2.spo2_data)))
            elif notice.type == history_module.HisDataType.PPG_DATA and his_data.HasField("ppg"):
                measurements.append(raw_series_metric("ppg_raw", his_data.ppg.time_stamp, split_u16_words(his_data.ppg.raw_data)))
            elif notice.type == history_module.HisDataType.ACCELEROMETER_DATA and his_data.HasField("ACCelerometer_data"):
                measurements.append(self.acc_metric(his_data.ACCelerometer_data))
            elif notice.type == history_module.HisDataType.THIRDPARTY_DATA and his_data.HasField("ThirdParty_data"):
                measurements.extend(self.third_party_metrics(his_data.ThirdParty_data))
            else:
                measurements.append(
                    {
                        "metric_type": "history_unmapped",
                        "measured_at": None,
                        "values": {"history_type": his_type},
                    }
                )

        if data_field == "index_table":
            measurements.append(
                {
                    "metric_type": "history_index",
                    "measured_at": None,
                    "values": decoded.get("index_table") or decoded.get("indexTable") or {},
                }
            )

        return {
            "protocol_name": "history",
            "decoded": decoded,
            "measurements": measurements,
            "locations": locations,
            "alarms": [],
        }

    def history_health_values(self, health, health_module):
        measured_at = protobuf_time(health.time_stamp)
        measurements = []

        if health.HasField("pedo_data"):
            pedo = health.pedo_data
            measurements.append(
                {
                    "metric_type": "activity",
                    "measured_at": measured_at,
                    "values": {
                        "type": pedo.type,
                        "state": pedo.state,
                        "steps": pedo.step,
                        "distance": pedo.distance * 0.1,
                        "calorie": pedo.calorie * 0.1,
                    },
                }
            )

        if health.HasField("hr_data"):
            hr = health.hr_data
            measurements.append(
                {
                    "metric_type": "heart_rate",
                    "measured_at": measured_at,
                    "values": {"min_bpm": hr.min_bpm, "max_bpm": hr.max_bpm, "avg_bpm": hr.avg_bpm},
                }
            )

        if health.HasField("hrv_data"):
            hrv = health.hrv_data
            fatigue = int(hrv.fatigue)
            if fatigue <= 0 and hrv.RMSSD:
                fatigue = int(math.log(float(hrv.RMSSD)) * 20)
            measurements.append(
                {
                    "metric_type": "hrv",
                    "measured_at": measured_at,
                    "values": {"fatigue": fatigue, "stress": 100 - fatigue},
                }
            )

        if health.HasField("bp_data"):
            bp = health.bp_data
            measurements.append(
                {
                    "metric_type": "blood_pressure",
                    "measured_at": measured_at,
                    "values": {"sbp": bp.sbp, "dbp": bp.dbp},
                }
            )

        if health.HasField("bxoy_data"):
            spo2 = health.bxoy_data
            measurements.append(
                {
                    "metric_type": "spo2",
                    "measured_at": measured_at,
                    "values": {"min_oxy": spo2.min_oxy, "max_oxy": spo2.max_oxy, "avg_oxy": spo2.agv_oxy},
                }
            )

        if health.HasField("temperature_data"):
            temp = health.temperature_data
            measurements.append(
                {
                    "metric_type": "temperature",
                    "measured_at": measured_at,
                    "values": {
                        "available": temp.type == health_module.TPAMeasureType.TPA_MEASURE_TYPE_AUTO,
                        "axillary": (temp.esti_arm & 0x0000FFFF) / 100.0,
                        "estimated": ((temp.esti_arm >> 16) & 0x0000FFFF) / 100.0,
                        "shell": (temp.evi_body & 0x0000FFFF) / 100.0,
                        "environment": ((temp.evi_body >> 16) & 0x0000FFFF) / 100.0,
                    },
                }
            )

        if health.HasField("sleep_data"):
            sleep = health.sleep_data
            measurements.append(
                {
                    "metric_type": "sleep_raw",
                    "measured_at": measured_at,
                    "values": {
                        "charge": sleep.charge,
                        "shutdown": sleep.shut_down,
                        "count": len(sleep.sleep_data),
                        "raw": list(sleep.sleep_data)[:120],
                    },
                }
            )

        if health.HasField("bp_bpm_data"):
            measurements.append(
                {
                    "metric_type": "blood_pressure_heart_rate",
                    "measured_at": measured_at,
                    "values": {"bpm": health.bp_bpm_data.bpm},
                }
            )

        if health.HasField("bloodPotassium_data"):
            measurements.append(
                {
                    "metric_type": "blood_potassium",
                    "measured_at": measured_at,
                    "values": {"potassium": health.bloodPotassium_data.bloodPotassium},
                }
            )

        if health.HasField("bioz_data"):
            bioz = health.bioz_data
            measurements.append(
                {
                    "metric_type": "bioz",
                    "measured_at": measured_at,
                    "values": {"r": bioz.R, "x": bioz.X, "bmi": bioz.bmi, "fat": bioz.fat, "type": bioz.type},
                }
            )

        if health.HasField("Blood_sugar_data"):
            measurements.append(
                {
                    "metric_type": "blood_sugar",
                    "measured_at": measured_at,
                    "values": {"sugar": health.Blood_sugar_data.Blood_sugar},
                }
            )

        return measurements

    def parse_alarm(self, payload):
        module = self.modules["alarm"]
        notice = module.Alarm_infokConfirm()
        notice.ParseFromString(payload)
        decoded = self.to_dict(notice)
        alarms = []

        if notice.HasField("alarm"):
            alarm = notice.alarm
            alarms.extend(repeated_alarm("heart_rate", alarm.alarm_hr, "time_stamp", lambda row: {"hr": row.hr}))
            alarms.extend(repeated_alarm("spo2", alarm.alarm_spo2, "time_stamp", lambda row: {"spo2": row.spo2}))
            alarms.extend(repeated_alarm("thrombus", alarm.alarm_Thrombus, "time_stamp", lambda row: {"thrombus_alarm": getattr(row, "Thrombus_alarm", None)}))
            alarms.extend(repeated_alarm("fall", alarm.alarm_fall, "time_stamp", lambda row: {"fall_alarm": getattr(row, "fall_alarm", None)}))
            alarms.extend(repeated_alarm("temperature", alarm.alarm_Temperature, "time_stamp", lambda row: {"temperature": row.temperature}))
            alarms.extend(repeated_alarm("blood_pressure", alarm.alarm_Bp, "time_stamp", lambda row: {"sbp": row.sbp, "dbp": row.dbp}))
            alarms.extend(repeated_alarm("sedentary", alarm.alarm_Sedentary, "time_stamp", lambda row: {}))
            alarms.extend(repeated_alarm("blood_sugar", alarm.alarm_Blood_sugar, "time_stamp", lambda row: {"blood_sugar": row.Blood_sugar}))
            alarms.extend(repeated_alarm("blood_potassium", alarm.alarm_Blood_potassium, "time_stamp", lambda row: {"blood_potassium": row.Blood_potassium}))
            if alarm.HasField("SOS_Notification_time"):
                alarms.append(
                    {
                        "alarm_type": "sos",
                        "alarm_time": protobuf_time(alarm.SOS_Notification_time),
                        "values": {},
                    }
                )

        if notice.HasField("Alarminfo"):
            info = notice.Alarminfo
            alarm_time = protobuf_time(info.time_stamp)
            if info.HasField("wearstate"):
                alarms.append({"alarm_type": "not_wearing", "alarm_time": alarm_time, "values": {"wearstate": info.wearstate}})
            if info.HasField("lowpowerPercentage"):
                alarms.append({"alarm_type": "low_power", "alarm_time": alarm_time, "values": {"battery": info.lowpowerPercentage}})
            if info.HasField("poweroffPercentage"):
                alarms.append({"alarm_type": "power_off", "alarm_time": alarm_time, "values": {"battery": info.poweroffPercentage}})
            if info.HasField("intercept_number"):
                alarms.append({"alarm_type": "phone_intercept", "alarm_time": alarm_time, "values": {"number": info.intercept_number}})

        return {
            "protocol_name": "alarm",
            "decoded": decoded,
            "measurements": [],
            "locations": [],
            "alarms": alarms,
        }

    def third_party_metrics(self, third_party):
        metrics = []
        if not third_party.HasField("DataHealth"):
            return metrics
        data = third_party.DataHealth
        mac = data.mac_addr
        for field, metric_type in [
            ("bp_data", "third_party_blood_pressure"),
            ("Glu_data", "third_party_glucose"),
            ("scale_data", "third_party_scale"),
            ("Spo2_data", "third_party_spo2"),
            ("Temp_data", "third_party_temperature"),
        ]:
            if data.HasField(field):
                value = getattr(data, field)
                measured_at = protobuf_time(value.time) if value.HasField("time") else None
                metrics.append(
                    {
                        "metric_type": metric_type,
                        "measured_at": measured_at,
                        "values": {"mac_addr": mac, "data": self.to_dict(value)},
                    }
                )
        return metrics

    def acc_metric(self, acc):
        return {
            "metric_type": "accelerometer",
            "measured_at": protobuf_time(acc.time_stamp),
            "values": {
                "x": parse_u16_bytes(acc.acc_x)[:120],
                "y": parse_u16_bytes(acc.acc_y)[:120],
                "z": parse_u16_bytes(acc.acc_z)[:120],
                "count": acc.acc_data_count,
            },
        }

    def to_dict(self, message):
        try:
            return self.message_to_dict(message, preserving_proto_field_name=True)
        except TypeError:
            return self.message_to_dict(message)


def protobuf_time(container):
    try:
        seconds = container.date_time.seconds
    except Exception:
        try:
            seconds = container.seconds
        except Exception:
            return None
    return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()


def enum_name(enum_wrapper, value):
    try:
        return enum_wrapper.Name(value)
    except Exception:
        return str(value)


def safe_number(value):
    try:
        return float(value)
    except Exception:
        return None


def parse_u16_bytes(data):
    values = []
    for index in range(1, len(data), 2):
        values.append(data[index - 1] + (data[index] << 8))
    return values


def split_u16_words(words):
    values = []
    for word in words:
        value = int(word)
        values.append((value >> 16) & 0x0000FFFF)
        values.append(value & 0x0000FFFF)
    return values


def parse_spo2_words(words):
    values = []
    for raw in words:
        values.append(
            {
                "spo2": (raw >> 24) & 0xFF,
                "hr": (raw >> 16) & 0xFF,
                "perfusion": (raw >> 8) & 0xFF,
                "touch": raw & 0xFF,
            }
        )
    return values


def raw_series_metric(metric_type, timestamp, values):
    data = list(values)
    return {
        "metric_type": metric_type,
        "measured_at": protobuf_time(timestamp),
        "values": {"count": len(data), "items": data[:200]},
    }


def repeated_alarm(alarm_type, rows, time_field, value_builder):
    alarms = []
    for row in rows:
        timestamp = getattr(row, time_field)
        alarms.append(
            {
                "alarm_type": alarm_type,
                "alarm_time": protobuf_time(timestamp),
                "values": value_builder(row),
            }
        )
    return alarms
