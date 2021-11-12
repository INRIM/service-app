import os
from os.path import exists
from dotenv import dotenv_values
import httpx
import json
import subprocess
import logging
import logging.handlers

config = dotenv_values("../.env")
key = config['KEY']

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


app = App(key)

tasks = app.get_tasks()


def is_active(task_name) -> bool:
    res = subprocess.run(["systemctl", "status", task_name], cwd="/",
                         stdout=subprocess.PIPE).stdout.decode('utf-8')
    return "Active: active" in res


for task in tasks:
    if task['action'] == "add":
        if not exists(f"/etc/systemd/system/{task['name']}.timer"):
            execute = [
                "/automations/modules/main-scheduler/make-service.sh", f"{task['title']}", f"{task['name']}",
                f"{task['calendar']}"
            ]
            try:
                res = subprocess.run(
                    execute, cwd="/automations/modules/main-scheduler", stdout=subprocess.PIPE).stdout.decode('utf-8')
                run_task_logger.info(f"Add task {task['title']} -> {res}")
            except Exception as e:
                run_task_logger.info(f"Error Adding task {e} :\n {execute}")
    elif task['action'] == "pause":
        if exists(f"/etc/systemd/system/{task['name']}.timer") and is_active(f"{task['name']}.timer"):
            execute = [
                "/automations/modules/calendar-task/pause-task.sh", f"{task['name']}"
            ]
            try:
                res = subprocess.run(
                    execute, cwd="/automations/modules/calendar-task", stdout=subprocess.PIPE).stdout.decode('utf-8')
                run_task_logger.info(f"Pause task {task['title']} -> {res}")
            except Exception as e:
                run_task_logger.info(f"Error Pause task {e} :\n {execute}")
        else:
            run_task_logger.info(f"Pause task {task['title']} -> File not exist")
    elif task['action'] == "remove":
        if exists(f"/etc/systemd/system/{task['name']}.timer"):
            execute = [
                "/automations/modules/calendar-task/remove-task.sh", f"{task['name']}"
            ]
            try:
                res = subprocess.run(
                    execute, cwd="/automations/modules/calendar-task", stdout=subprocess.PIPE).stdout.decode('utf-8')
                run_task_logger.info(f"Removed task {task['title']} -> {res}")
            except Exception as e:
                run_task_logger.info(f"Error Remove task {e} :\n {execute}")
        else:
            run_task_logger.info(f"Remove task {task['title']} -> File not exist")
    elif task['action'] == "resume":
        if exists(f"/etc/systemd/system/{task['name']}.timer") and not is_active(f"{task['name']}.timer"):
            execute = [
                "/automations/modules/calendar-task/resume-task.sh", f"{task['name']}"
            ]
            try:
                res = subprocess.run(
                    execute, cwd="/automations/modules/calendar-task", stdout=subprocess.PIPE).stdout.decode('utf-8')
                run_task_logger.info(f"Resumed task {task['title']} -> {res}")
            except Exception as e:
                run_task_logger.info(f"Error Resume task {e} :\n {execute}")
        else:
            run_task_logger.info(f"Resume task {task['title']} -> File not exist")
