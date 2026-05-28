# IWOWN Endpoint Coverage

## Device To Cloud Uploads

| IWOWN route | Local route | Status |
| --- | --- | --- |
| `/pb/upload` | `/pb/upload`, `/{prefix}/pb/upload` | Implemented |
| `/alarm/upload` | `/alarm/upload`, `/{prefix}/alarm/upload` | Implemented |
| `/call_log/upload` | `/call_log/upload`, `/{prefix}/call_log/upload` | Implemented |
| `/deviceinfo/upload` | `/deviceinfo/upload`, `/{prefix}/deviceinfo/upload` | Implemented |
| `/status/notify` | `/status/notify`, `/{prefix}/status/notify` | Implemented |
| `/health/sleep` | `/health/sleep`, `/{prefix}/health/sleep` | Implemented dummy |

## Device Setting Commands

| Key | IWOWN route |
| --- | --- |
| `userinfo` | `/entservice/cmd/userinfo` |
| `realtime_location` | `/entservice/cmd/realtime/location` |
| `data_sync` | `/entservice/cmd/datasync` |
| `device_status` | `/entservice/device/status` |
| `fall_check` | `/entservice/cmd/fallcheck` |
| `phonebook_sync` | `/entservice/phonebook/sync` |
| `phonebook_clear` | `/entservice/phonebook/clear` |
| `datafreq` | `/entservice/cmd/datafreq` |
| `locate_dataupload_freq` | `/entservice/cmd/locate_dataupload/freq` |
| `lcdgesture` | `/entservice/cmd/lcdgesture` |
| `hr_alarm` | `/entservice/cmd/hralarm` |
| `dynamic_hr_alarm` | `/entservice/cmd/dynamic/hralarm` |
| `spo2_alarm` | `/entservice/cmd/spo2alarm` |
| `bp_alarm` | `/entservice/cmd/bpalarm` |
| `temperature_alarm` | `/entservice/cmd/temperature/alarm` |
| `auto_af` | `/entservice/cmd/autoaf` |
| `alarm_set` | `/entservice2/clockalarm/set` |
| `alarm_clear` | `/entservice2/clockalarm/clear` |
| `sedentary_set` | `/entservice3/sedentary/set` |
| `sedentary_clear` | `/entservice3/sedentary/clear` |
| `goal` | `/entservice/cmd/goal` |
| `factory_reset` | `/entservice/cmd/factory/reset` |
| `language_set` | `/entservice/cmd/language/set` |
| `message` | `/entservice/cmd/message` |
| `fallcheck_sensitivity` | `/entservice/cmd/fallcheck/sensitivity` |
| `hr_measure_interval` | `/entservice/cmd/measure/interval/hr` |
| `other_measure_interval` | `/entservice/cmd/measure/interval/other` |
| `gps_locate` | `/entservice/cmd/gps/locate` |
| `time_format` | `/entservice/cmd/timeformat` |
| `date_format` | `/entservice/cmd/dateformat` |
| `distance_unit` | `/entservice/cmd/distanceunit` |
| `temperature_unit` | `/entservice/cmd/temperatureunit` |
| `wear_hand` | `/entservice/device/cmd/wearhand` |
| `bp_adjust` | `/entservice/cmd/bpadjust` |

## Calculation Proxies

| Key | IWOWN route |
| --- | --- |
| `sleep` | `/calculation/sleep` |
| `ecg` | `/calculation/ecg` |
| `af` | `/calculation/af` |
| `spo2` | `/calculation/spo2` |
| `parkinson_acc` | `/calculation/parkinson/acc` |
| `matress_sleep` | `/calculation/matress/sleep` |
