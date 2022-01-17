import os
from os.path import exists
from dotenv import dotenv_values
import httpx
import json
import subprocess
import logging
import logging.handlers
from datetime import datetime, timedelta, timezone
import pytz
import pymongo
import re

with open('../config.json', mode="r") as jf:
    data_j = jf.read()

config_system = json.loads(data_j)

run_task_logger = logging.getLogger('run_task')
run_task_logger.setLevel(logging.INFO)
handler = logging.handlers.TimedRotatingFileHandler("log/run_task.log", when='W0', backupCount=10)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s:%(message)s'))
run_task_logger.addHandler(handler)


class App:

    def __init__(self, APIKEY, default_url="http://client:8526"):
        super().__init__()
        self.default_url = default_url
        self.api_key = APIKEY

    def get_headers(self):
        return {
            "Content-Type": "application/json",
            "apitoken": self.api_key
        }

    def get_tasks(self) -> dict:
        url = f"{self.default_url}/client/polling/calendar_tasks"
        with httpx.Client(timeout=None) as client:
            res = client.get(
                url=url, headers=self.get_headers()
            )
            return res.json()


def eval_timestamp(tmsp):
    if tmsp > 0:
        tz = pytz.timezone(config_system['TZ'])
        epoch = datetime(1970, 1, 1)
        return tz.fromutc((epoch + timedelta(microseconds=tmsp))).replace(tzinfo=tz).strftime(
            config_system['server_datetime_mask'])
    return False


def get_tasks_status():
    key_value = subprocess.check_output(
        ["systemctl", "-o", "json", "list-timers"],
        universal_newlines=True)

    json_o = json.loads(key_value)
    for i in json_o:
        for k in ["next", "left", "last", "passed"]:
            i[k] = eval_timestamp(i[k] or 0)
    return json_o


class DbTask:
    def __init__(self, config_system):
        super().__init__()
        self.config_system = config_system.copy()
        self.task_status = {}
        self.task_names = []
        user = config_system['MONGO_USER']
        passw = config_system['MONGO_PASS']
        url = config_system['MONGO_URL']
        dbname = config_system['MONGO_DB']
        # TODO read APP params to set:
        # config_system['SERVER_DATETIME_MASK'] = app.params
        # config_system['UI_DATETIME_MASK'] = app.params
        # config_system['TZ']  = app.params
        self.isodate_regex = re.compile('(\d{4}-\d{2}-\d{2})[A-Z]+(\d{2}:\d{2}:\d{2})')
        conn_str = f"mongodb://{user}:{passw}@{url}/"
        self.client = pymongo.MongoClient(conn_str, serverSelectionTimeoutMS=5000)
        try:
            self.db = self.client[dbname]
        except Exception as e:
            run_task_logger.error(f"Unable to connect to the server.\n{e}", exc_info=True)

    def get_tasks(self) -> list:
        calendarcoll = self.db['calendar']
        tasks = []
        fields = {"_id": 0}
        for cal_task in calendarcoll.find({"deleted": 0, "active": True, "tipo": "task"}, fields):
            task_name = cal_task['rec_name']
            self.task_names.append(task_name)
            if cal_task['action'] == "add":
                if cal_task['stato'] == "todo":
                    tasks.append(cal_task)
                elif cal_task['stato'] == "progress" and not exists(f"/etc/systemd/system/{task_name}.timer"):
                    tasks.append(cal_task)
            else:
                tasks.append(cal_task)
            if cal_task in tasks:
                cal_task['stato'] = "progress"
                cal_task['data_value']['stato'] = "Caricato"
                calendarcoll.update_one({"rec_name": task_name}, {"$set": cal_task})

        if len(tasks) > 0:
            run_task_logger.info(f"found and computed {len(tasks)} tasks")
        return tasks

    def parse_date(self, vals):
        value_date = False
        if isinstance(vals, str) and self.isodate_regex.match(vals):
            v = self.isodate_regex.search(vals).group()
            value_date = datetime.strptime(
                v, config_system['server_datetime_mask']).strftime(
                config_system['ui_datetime_mask'])
        return value_date

    def get_tasks_status(self):
        key_value = subprocess.check_output(
            ["systemctl", "-o", "json", "list-timers"],
            universal_newlines=True)

        json_o = json.loads(key_value)
        for i in json_o:
            for k in ["next", "left", "last", "passed"]:
                i[k] = eval_timestamp(i[k] or 0)
        return json_o

    def update_status_task(self):
        calendarcoll = self.db['calendar']
        self.task_status = self.get_tasks_status().copy()
        run_task_logger.info(f"update_status_task {len(self.task_status)}")
        for stat_task in self.task_status:
            name = stat_task['activates'].replace(".service", "")
            if name in self.task_names:
                last = stat_task['last']
                next = stat_task['next']
                data = {
                    "last": last, "next": next, "data_value":
                        {
                            "last": self.parse_date(last),
                            "next": self.parse_date(next)
                        }
                }
                calendarcoll.update_one({"rec_name": name}, {"$set": data})
                run_task_logger.info(f"Upadet {name} > {stat_task['next']}")

    def close_db(self):
        self.client.close()


db = DbTask(config_system)

tasks = db.get_tasks()


def is_active(task_name) -> bool:
    res = subprocess.run(["systemctl", "status", task_name], cwd="/",
                         stdout=subprocess.PIPE).stdout.decode('utf-8')
    return "Active: active" in res


def chk_remove_task(task):
    if exists(f"/etc/systemd/system/{task['rec_name']}.timer"):
        execute = [
            "/automations/modules/calendar-task/remove-task.sh", f"{task['rec_name']}"
        ]
        try:
            res = subprocess.run(
                execute, cwd="/automations/modules/calendar-task", stdout=subprocess.PIPE).stdout.decode('utf-8')
            run_task_logger.info(f"Chk Removed task {task['title']} -> {res}")
        except Exception as e:
            run_task_logger.info(f"Error Remove task {e} :\n {execute}")


for task in tasks:
    if task['action'] == "add":
        chk_remove_task(task)
        if task['calendar'] == "now":
            task['calendar'] = (
                    datetime.now() + timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
        execute = [
            "/automations/modules/main-scheduler/make-service.sh", f"{task['title']}", f"{task['rec_name']}",
            f"{task['calendar']}"
        ]
        try:
            res = subprocess.run(
                execute, cwd="/automations/modules/main-scheduler", stdout=subprocess.PIPE).stdout.decode('utf-8')
            run_task_logger.info(f"Add task {task['title']} -> {res}")
        except Exception as e:
            run_task_logger.info(f"Error Adding task {e} :\n {execute}")
    elif task['action'] == "pause":
        if exists(f"/etc/systemd/system/{task['rec_name']}.timer") and is_active(f"{task['rec_name']}.timer"):
            execute = [
                "/automations/modules/calendar-task/pause-task.sh", f"{task['rec_name']}"
            ]
            try:
                res = subprocess.run(
                    execute, cwd="/automations/modules/calendar-task", stdout=subprocess.PIPE).stdout.decode(
                    'utf-8')
                run_task_logger.info(f"Pause task {task['title']} -> {res}")
            except Exception as e:
                run_task_logger.info(f"Error Pause task {e} :\n {execute}")
        else:
            run_task_logger.info(f"Pause task {task['title']} -> File not exist")
    elif task['action'] == "remove":
        if exists(f"/etc/systemd/system/{task['rec_name']}.timer"):
            execute = [
                "/automations/modules/calendar-task/remove-task.sh", f"{task['rec_name']}"
            ]
            try:
                res = subprocess.run(
                    execute, cwd="/automations/modules/calendar-task", stdout=subprocess.PIPE).stdout.decode(
                    'utf-8')
                run_task_logger.info(f"Removed task {task['title']} -> {res}")
            except Exception as e:
                run_task_logger.info(f"Error Remove task {e} :\n {execute}")
        else:
            run_task_logger.info(f"Remove task {task['title']} -> File not exist")
    elif task['action'] == "resume":
        if exists(f"/etc/systemd/system/{task['rec_name']}.timer") and not is_active(f"{task['rec_name']}.timer"):
            execute = [
                "/automations/modules/calendar-task/resume-task.sh", f"{task['rec_name']}"
            ]
            try:
                res = subprocess.run(
                    execute, cwd="/automations/modules/calendar-task", stdout=subprocess.PIPE).stdout.decode(
                    'utf-8')
                run_task_logger.info(f"Resumed task {task['title']} -> {res}")
            except Exception as e:
                run_task_logger.info(f"Error Resume task {e} :\n {execute}")
        else:
            run_task_logger.info(f"Resume task {task['title']} -> File not exist")

db.update_status_task()

db.close_db()
