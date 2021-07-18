# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
import sys

sys.path.append("..")
import os
import aiofiles
from os import listdir
from os.path import isfile, join
from pathlib import Path
import ujson
from .BaseClass import *
from .SessionMain import SessionMain, SessionBase
from .ServiceAuth import ServiceAuth
from .ModelData import ModelData
from fastapi.requests import Request
from fastapi import Response
from fastapi.responses import JSONResponse
import logging
from starlette.datastructures import MutableHeaders
from .database.mongo_core import *
from .ServiceMain import ServiceMain
from datetime import datetime, timedelta
import uuid
from ozon.settings import get_settings
from ozon.base.default_data import default_data
import pymongo

logger = logging.getLogger(__name__)


class Ozon(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class OzonBase(Ozon):

    @classmethod
    def create(cls):
        self = OzonBase()
        self.init_basic()
        return self

    def init_basic(self):
        self.session = None
        self.token = ""
        self.mdata = ModelData.new(session=None)
        self.auth_service = None
        self.login_required = False
        self.req_id = str(uuid.uuid4())
        self.user_token = {}
        self.session_service = None
        self.settings = get_settings()
        self.public_endpoint = [
            '/login',
            '/session',
            '/layout',
            '/api_routes',
            '/static',
            '/redoc',
            '/status',
            '/favicon.ico'
        ]

    def add_public_end_point(self, endpoint=""):
        self.public_endpoint.append(endpoint)

    async def init_request(self, request: Request):
        logger.info("init_request")
        req_id = request.headers.get("req_id")
        if not req_id:
            req_id = self.req_id
        logger.info(
            f"init_request with class {self} for {request.url.path}, req_id {req_id},"
            f"object: {self} "
        )
        self.auth_service = ServiceAuth.new(
            public_endpoint=self.public_endpoint, parent=self, request=request, req_id=req_id)
        self.session = await self.auth_service.handle_request(request, req_id)
        self.mdata.session = self.session
        logger.info(f"init_request End session")
        return self.session

    async def handle_response(self, arg) -> None:
        # for ContextMiddleware
        if arg["type"] == "http.response.start":
            if self.session:
                self.session.req_id = self.req_id
                if self.session.app.get('save_session'):
                    await self.save_session()
            headers = MutableHeaders(scope=arg)
            headers.append("apitoken", self.token)
            headers.append("req_id", self.req_id)
            headers.append("cookie", f"authtoken={self.token}")

    async def save_session(self):
        logger.info("save_session")
        self.session.last_update = datetime.now().timestamp()
        await self.mdata.save_record(self.session)

    async def home_page(self, request):
        # await check_and_init_db(session)
        self.session.app['mode'] = "list"
        self.session.app['component'] = "form"

        return JSONResponse({
            "action": "redirect",
            "url": "/dashboard",
        })

    async def handle_request(self):
        pass

    async def check_and_init_db(self):
        logger.info("check_and_init_db")
        model = await self.mdata.gen_model("action")
        if not model:
            # Path(get_settings().upload_folder).mkdir(parents=True, exist_ok=True)
            await prepare_collenctions()
        components_file = default_data.get("schema")
        await self.import_component(components_file)
        for node in default_data.get("datas"):
            model_name = list(node.keys())[0]
            namefile = node[model_name]
            await self.import_data(model_name, namefile)

    async def import_component(self, components_file):
        logger.info(f"import_component components_file:{components_file}")
        if os.path.exists(components_file):
            logger.info(f"init component {components_file}")
            async with aiofiles.open(components_file, mode="rb") as jsonfile:  # type: ignore
                data_j = await jsonfile.read()
            datas = ujson.loads(data_j)
            msgs = ""
            for data in datas:
                component = Component(**data)
                compo = await self.mdata.by_name(Component, data['rec_name'])
                if not compo:
                    if self.session:
                        await self.mdata.save_object(
                            self.session, component, model_name="component", copy=False)
                    else:
                        component.owner_uid = get_settings().base_admin_username
                        component.list_order = int(await self.mdata.count_by_filter(Component, query={"deleted": 0}))
                        try:
                            await self.mdata.save_record(component)
                        except pymongo.errors.DuplicateKeyError as e:
                            # logger.warning(f" Duplicate {e.details['errmsg']} ignored")
                            pass
                else:
                    msgs += f"{data['rec_name']} alredy exixst not imported"
            if not msgs:
                msgs = "Import done."
            return msgs
        else:
            msg = f"{components_file} not exist"
            logger.error(msg)
            return msg

    async def import_data(self, model_name, data_file):
        logger.info(f"import_data model_name: {model_name}, data_file:{data_file}")
        if os.path.exists(data_file):
            async with aiofiles.open(data_file, mode="rb") as jsonfile:
                data_j = await jsonfile.read()
            datas = ujson.loads(data_j)
            model = await self.mdata.gen_model(model_name)
            for record_data in datas:
                record = model(**record_data)
                if self.session:
                    await self.mdata.save_object(
                        self.session, record, model_name=model_name, copy=False)
                else:
                    record.owner_uid = get_settings().base_admin_username
                    record.list_order = int(await self.mdata.count_by_filter(model, query={"deleted": 0}))
                    try:
                        await self.mdata.save_record(record)
                    except pymongo.errors.DuplicateKeyError as e:
                        # logger.warning(f" Duplicate {e.details['errmsg']} ignored")
                        pass
        else:
            logger.error(f"{data_file} not exist")
