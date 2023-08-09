import os, sys, subprocess, json
from datetime import datetime, timedelta, timezone
import pytz


def eval_timestamp(tmsp):
    if tmsp > 0:
        epoch = datetime(1970, 1, 1)
        return (epoch + timedelta(microseconds=tmsp)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
    return False


key_value = subprocess.check_output(
    ["systemctl", "-o", "json", "list-timers"], universal_newlines=True
)

json_o = json.loads(key_value)

for i in json_o:
    for k in ["next", "left", "last", "passed"]:
        i[k] = eval_timestamp(i[k])
json.dump(json_o, sys.stdout, indent=2)
