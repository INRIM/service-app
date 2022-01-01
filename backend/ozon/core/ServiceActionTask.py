# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import sys
import os
from os import listdir
from os.path import isfile, join
import ujson
from ozon.settings import get_settings
from .database.mongo_core import *
from collections import OrderedDict
from pathlib import Path
from fastapi import Request
from .ServiceSecurity import ServiceSecurity
from .ServiceActionProcess import ActionProcessTask
from .ModelData import ModelData
from .BaseClass import BaseClass, PluginBase
from pydantic import ValidationError
from .QueryEngine import QueryEngine

import logging
import pymongo
import requests
import httpx
import re
from urllib.parse import quote

logger = logging.getLogger(__name__)


class ActionTask(ActionProcessTask):

    @classmethod
    def create(
            cls, session: Session, service_main, action_name, rec_name, parent, iframe, execute, pwd_context,
            container_act=""):
        self = ActionTask()
        self.init(session, service_main, action_name, rec_name, parent, iframe, execute, pwd_context,
                  container_act=container_act)
        return self

    # helper
    async def eval_data(self, data={}, eval_todo=True):
        logger.info(f"{data}")
        data = await super().eval_data(data=data, eval_todo=eval_todo)
        if not self.session.is_admin and eval_todo:
            chk_dict = data.copy()
            for k, v in chk_dict.items():
                if k.startswith("todo"):
                    data[k] = True
        return data.copy()

    # helper
    async def eval_user_todo(self, data={}, eval_todo=True):
        logger.info(f"{data}")
        if eval_todo:
            if "todo" in data:
                data["todo"] = True
        return data.copy()

    # actions
    async def task_action(self, data={}):
        """
        :param data:  form data
        :return: record updated
        """
        logger.info(
            f"task_action -> model:{self.action.model} action_type:{self.action.type}, curr_ref:{self.curr_ref}")
        model_schema = await self.mdata.component_by_name(self.action.model)
        data_model = await self.mdata.gen_model(self.action.model)
        record_data = data_model(**data)
        can_edit = await self.eval_editable(model_schema, record_data)
        if not can_edit:
            logger.error(f"Accesso Negato {record_data.rec_name}")
            return self.make_error_message(f"Accesso Negato {record_data.rec_name}")
        # check if exist task method
        eval_todo = True
        if "todo" in self.action.rec_name:
            eval_todo = False
            if self.action.process_name_to_complete:
                if self.action.process_name_to_complete in data:
                    data[self.action.process_name_to_complete] = False
            else:
                if "todo" in data:
                    data["todo"] = False

        # save record
        record = await self.save_copy(data=data, eval_todo=eval_todo)
        # if is error record is dict
        if isinstance(record, dict):
            return record

        act_path = await self.compute_action_path(record)

        return {
            "status": "ok",
            "link": f"{act_path}",
            "reload": True,
            "data": record.get_dict()
        }

    async def calendar_task(self, task_name, calendar, task, execution_status):
        logger.info(f"calendar_task -> task:{task_name}")
        if task:
            execution = {
                "status": execution_status['status'],
                "name": task_name,
                "data": task.get_dict()
            }
            if execution_status.get("updates"):
                for update in execution_status.get("updates", []):
                    record = await self.mdata.by_name(update['model'], update['rec_name'])
                    for field in update.get('fields', []):
                        setattr(record, field['name'], field['value'])
                        if field.get("data_value"):
                            record.data_value[field['name']] = field.get("data_value")
                    await self.mdata.save_object(self.session, record)
            if not calendar.periodico:
                calendar.stato = execution_status['status']
                await self.mdata.save_object(self.session, calendar)
            return execution
        return {
            "status": "error",
            "name": task_name,
            "data": {}
        }
