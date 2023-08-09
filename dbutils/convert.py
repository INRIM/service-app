import json
import argparse

"""
This script is usefull to convert json exported with datagrip
in json importable with insertMany
Usage 

python3 convert.py file.name.json
"""
parser = argparse.ArgumentParser()
parser.add_argument("fname")
args = parser.parse_args()

with open(args.fname, "r", encoding="utf-8") as infile:
    data = json.load(infile)
    for row in data:
        row.pop("_id")
        v = row["create_datetime"]["$date"]
        row["create_datetime"] = v
        v1 = row["update_datetime"]["$date"]
        row["update_datetime"] = v1

with open(args.fname, "w", encoding="utf-8") as outfile:
    json.dump(data, outfile, ensure_ascii=False)
