import os, sys, subprocess, json

key_value = subprocess.check_output(
    ["systemd-analyze", "calendar", sys.argv[1]], universal_newlines=True
).split("\n")
json_dict = {}
for entry in key_value:
    kv = entry.split(":", 1)
    if len(kv) == 2:
        json_dict[kv[0].strip()] = kv[1].strip()
json.dump(json_dict, sys.stdout, indent=2)
