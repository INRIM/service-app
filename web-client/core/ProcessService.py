# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import json
import sys
from typing import Optional

from fastapi import FastAPI, Request, Header, HTTPException, Depends
from fastapi.responses import RedirectResponse, FileResponse
import httpx
import logging
import ujson
from datetime import datetime, timedelta
from fastapi.concurrency import run_in_threadpool
from aiopath import AsyncPath
from .main.base.base_class import PluginBase
from .ContentService import ContentService
import aiofiles
import uuid

logger = logging.getLogger(__name__)


class ProcessService(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        if cls not in cls.plugins:
            cls.plugins.append(cls())


class ProcessServiceBase(ProcessService):

    @classmethod
    def create(cls, content_service: ContentService, process_model, process_name):
        self = ProcessServiceBase()
        self.init(content_service, process_model, process_name)
        return self

    def init(self, content_service: ContentService, process_model, process_name):
        self.content_service = content_service
        self.gateway = content_service.gateway
        self.process_model = process_model
        self.process_rec_name = process_name
        self.user_task = False
        self.process_in_progress = False
        self.cfg = {}
        self.process_instance_id = ""
        self.current_task_id = ""
        self.current_ext_task_topic = ""
        self.process_instance = {}
        self.process_data = {}
        self.process = {}
        self.process_vars = {}
        self.execution = {}
        self.execution_local_vars = {}
        self.process_tasks = {}
        self.process_ext_tasks = {}
        self.current_task = {}
        self.current_task_name = ""
        self.current_task_vars = {}
        self.form_data = {}
        self.update_data = False

    async def load_config(self):
        self.process_data = await self.gateway.get_record_data(
            self.process_model, self.process_rec_name)
        if self.process_data:
            self.cfg = await self.gateway.get_param(self.process_data.get("model"))
        else:
            self.cfg = await self.gateway.get_param(self.process_model)

    async def start(self, **kwargs):
        await self.load_config()
        self.process = {}

    async def check(self, **kwargs):
        await self.load_config()
        self.process = {}
        return self.process

    async def next(self, **kwargs):
        await self.load_config()
        self.process = {}
        return self.process

    async def complete(self, **kwargs):
        await self.load_config()
        self.process = {}
        return self.process

    async def cancel(self, **kwargs):
        await self.load_config()
        process = {}
        return process
