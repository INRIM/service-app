# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import sys
import os
from os import listdir
from os.path import isfile, join
import ujson
# from ozon.settings import get_settings
from .database.mongo_core import *
from collections import OrderedDict
from pathlib import Path
from fastapi import Request
from .ServiceSecurity import ServiceSecurity
from .ServiceAction import ActionMain
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


class ActionProcessTask(ActionMain):

    @classmethod
    def create(
            cls, session: Session, service_main, action_name, rec_name, parent, iframe, execute, pwd_context,
            container_act=""):
        self = ActionProcessTask()
        self.init(session, service_main, action_name, rec_name, parent, iframe, execute, pwd_context,
                  container_act=container_act)
        return self

    async def hendle_process_action(self, data={}):
        pass

    async def hendle_process_task_action(self, data={}):
        pass
