import json
import os
import dotenv
from dotenv import dotenv_values

dotenv_file = dotenv.find_dotenv(filename="/app/.env")
# dotenv.load_dotenv(dotenv_file)
config = dotenv_values(dotenv_file)
for item in ["ADMINS", "PLUGINS", "DEPENDS"]:
    if item in config:
        todo = False
        try:
            res = json.loads(config[item])
            if not isinstance(res, list):
                todo = True
        except ValueError as e:
            todo = True
        if todo:
            v = json.dumps([str(i).strip() for i in config[item].split(",")])
            dotenv.set_key(dotenv_file, item, v)

print("init config env complete")
