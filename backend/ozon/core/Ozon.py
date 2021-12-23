# Copyright INRIM (https://www.inrim.eu)
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
from ozon.base.plugin_config import mod_config
import pymongo

logger = logging.getLogger(__name__)


class Ozon(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class OzonBase(Ozon):

    @classmethod
    def create(cls, pwd_context):
        self = OzonBase()
        self.init(pwd_context)
        return self

    def init(self, pwd_context):
        self.session = None
        self.token = ""
        self.pwd_context = pwd_context
        self.mdata = ModelData.new(session=None, pwd_context=pwd_context)
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

    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password):
        return self.pwd_context.hash(password)

    def add_public_end_point(self, endpoint=""):
        self.public_endpoint.append(endpoint)

    async def init_request(self, request: Request):
        logger.debug("init_request")
        req_id = request.headers.get("req_id")
        if not req_id:
            req_id = self.req_id
        logger.debug(
            f"init_request with class {self} for {request.url.path}, req_id {req_id},"
            f"object: {self} "
        )
        self.auth_service = ServiceAuth.new(
            public_endpoint=self.public_endpoint, parent=self, request=request,
            pwd_context=self.pwd_context, req_id=req_id)
        self.session = await self.auth_service.handle_request(request, req_id)
        self.mdata.session = self.session
        logger.debug(f"init_request End session {type(self.session)}")
        return self.session

    async def handle_response(self, arg) -> None:
        if arg["type"] == "http.response.start":
            if self.session:
                self.session.req_id = self.req_id
                if self.session.app.get('save_session'):
                    await self.save_session()
            headers = MutableHeaders(scope=arg)
            headers.append("authtoken", self.session.token)
            headers.append("req_id", self.req_id)
            headers.append("cookie", f"authtoken={self.session.token}")
            # headers.append("cookie", f"domain={os.environ.get('DOMAIN')}") TODO

    async def save_session(self):
        logger.info("save_session")
        self.session.last_update = datetime.now().timestamp()
        await self.mdata.save_record(self.session)

    async def home_page(self, request):
        # await check_and_init_db(session)
        self.session.app['mode'] = "list"
        self.session.app['component'] = "form"

        resp = JSONResponse({
            "action": "redirect",
            "url": "/dashboard",
        })
        # resp.headers.append("authtoken", self.session.token or "")
        return resp

    async def handle_request(self):
        pass

    async def check_and_init_db(self):
        logger.info("check_and_init_db")
        await self.compute_check_and_init_db(mod_config)

    async def compute_check_and_init_db(self, def_data):
        auto_create_actions = def_data.get("auto_create_actions", True)
        config_menu_group = def_data.get("config_menu_group", {})
        components_file = def_data.get("schema", {})
        pre_datas = def_data.get("pre_datas", [])
        datas = def_data.get("datas", [])
        dbviews = def_data.get("dbviews", [])
        for node in pre_datas:
            model_name = list(node.keys())[0]
            namefile = node[model_name]
            await self.import_data(model_name, namefile)
        await self.import_component(
            components_file, auto_create_actions, config_menu_group)
        for node in datas:
            model_name = list(node.keys())[0]
            namefile = node[model_name]
            await self.import_data(model_name, namefile)
        for namefile in dbviews:
            await self.import_db_views(namefile)

    async def import_db_views(self, data_file):
        logger.info(f"import_db_views data_file:{data_file}")
        if os.path.exists(data_file):
            async with aiofiles.open(data_file, mode="rb") as jsonfile:
                data_j = await jsonfile.read()
            data = ujson.loads(data_j)
            try:
                dbviewcfg = DbViewModel(**data)
                await self.mdata.create_view(dbviewcfg)
            except Exception as e:
                logger.error(f" Error DbView {e} ", exc_info=True)
        else:
            logger.error(f"{data_file} not exist")

    async def compute_menu_group(
            self, model_name: str, model_menu_group: BasicModel):
        res = {}
        for group_rec_name, compo_list in config_menu_group.items():
            if model_name in compo_list:
                rec = await self.mdata.by_name(model_menu_group, group_rec_name)
                return {
                    "rec_name": rec.rec_name,
                    "title": rec.title
                }
        return res

    async def import_component(
            self, components_file, auto_create_actions=False, config_menu_group={}):
        logger.info(f"import_component components_file:{components_file}")
        if os.path.exists(components_file):
            logger.info(f"init component {components_file}")
            async with aiofiles.open(components_file, mode="rb") as jsonfile:  # type: ignore
                data_j = await jsonfile.read()
            datas = ujson.loads(data_j)
            msgs = ""
            model_menu_group = False
            if auto_create_actions:
                model_menu_group = await self.mdata.gen_model("menu_group")
            for data in datas:
                component = Component(**data)
                compo = await self.mdata.by_name(Component, data['rec_name'])
                if not compo:
                    logger.info(f"import {data['rec_name']}")
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
                    if auto_create_actions:
                        menu_group = self.compute_menu_group(record.rec_name, model_menu_group)
                        self.mdata.make_default_action_model(
                            self.session, component.rec_name, component, menu_group=menu_group
                        )
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
                    if model_name == "user":
                        pw_hash = self.get_password_hash(record.password)
                        record.password = pw_hash
                    record.owner_uid = get_settings().base_admin_username
                    record.list_order = int(await self.mdata.count_by_filter(model, query={"deleted": 0}))
                    try:
                        await self.mdata.save_record(record)
                    except pymongo.errors.DuplicateKeyError as e:
                        # logger.warning(f" Duplicate {e.details['errmsg']} ignored")
                        pass
        else:
            logger.error(f"{data_file} not exist")
