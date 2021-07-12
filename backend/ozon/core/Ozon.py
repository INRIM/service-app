# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
import sys

sys.path.append("..")
import os
from os import listdir
from os.path import isfile, join
from pathlib import Path
import ujson
from .BaseClass import *
from .SessionMain import SessionMain, SessionBase
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
        self.mdata = ModelData.new()
        self.req_id = str(uuid.uuid4())
        self.user_token = {}
        self.session_service = None
        self.settings = get_settings()
        self.exclude_word = [
            '/login',
            '/api_routes',
            '/static',
            '/status'
            '/favicon.ico'
        ]

    def create_session_main(self, request: Request, req_id):
        self.session_service = SessionMain.new(
            token="",
            req_id=req_id,
            request=request,
            user_token={},
            uid="",
            session={},
            user={},
            app={},
            action={},
            user_preferences={},
            settings=get_settings(),
            is_admin=False,
            use_auth=True
        )

    async def init_request(self, request: Request):
        req_id = request.headers.get("req_id")
        if not req_id:
            req_id = self.req_id
        logger.info(
            f"init_request with class {self} for {request.url.path}, req_id {req_id},"
            f"object: {self} "
        )
        self.create_session_main(request, req_id)
        self.session = await self.session_service.check_login()
        logger.info("init_request End")
        return self.session

    def deserialize_header_list(self, request: Request):
        # list_data = self.request.headers.mutablecopy().__dict__['_list']
        list_data = request.headers.mutablecopy()
        res = {item[0]: item[1] for item in list_data}
        return res.copy()

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

    async def check_init_settings(self):
        logger.info("check_init_settings")
        setting = await self.mdata.by_name(settingData, "settingData")
        if not setting:
            setting = settingData(data=get_settings().dict())
            setting.sys = True
            setting.default = True
            await self.mdata.save_object(self.session, setting, model_name="settingData")
        return setting

    async def check_and_init_db(self):
        logger.info("check_and_init_db")
        model = await self.mdata.gen_model("action")
        default = False
        if model:
            default = await self.mdata.all(model)

        if not default:
            basedir = os.path.abspath(os.path.dirname(__file__))
            Path(get_settings().upload_folder).mkdir(parents=True, exist_ok=True)

            await prepare_collenctions()
            compo_dir = get_settings().default_component_folder
            onlyfiles = [f for f in listdir(compo_dir) if isfile(join(compo_dir, f))]
            datafiles = [f for f in listdir(f"{compo_dir}/data") if isfile(join(f"{compo_dir}/data", f))]
            for namefile in onlyfiles:
                logger.info(f"init component {namefile}")
                with open(f"{compo_dir}/{namefile}") as jsonfile:
                    data = ujson.load(jsonfile)
                    component = Component(**data)
                    await self.mdata.save_object(self.session, component, model_name="component")
            for namefile in datafiles:
                logger.info(f"init component {namefile}")
                with open(f"{compo_dir}/data/{namefile}") as jsonfile:
                    data = ujson.load(jsonfile)
                    model = await self.mdata.gen_model(data['model'])
                    records_data = data['data']
                    for record_data in records_data:
                        record = model(**record_data)
                        await self.mdata.save_object(self.session, record, model_name=data['model'])

        setting = await self.check_init_settings()
        new_setting = settingData(data=get_settings().dict())
        await self.mdata.save_object(
            self.session, new_setting, rec_name=setting.rec_name, model_name="settingData", copy=False)

        if not default:
            moreschemas = [f for f in listdir(f"{compo_dir}/addons") if isfile(join(f"{compo_dir}/addons", f))]
            logger.info(f"More component schema  files: {moreschemas}")
            for namefile in moreschemas:
                logger.info(f"More component {namefile}")
                with open(f"{compo_dir}/addons/{namefile}") as jsonfile:
                    data = ujson.load(jsonfile)
                    service = ServiceMain.new(session=self.session)
                    await service.service_handle_action(
                        action_name="save_edit_mode", data=data, rec_name="", parent="", iframe="", execute=True)

    def need_session(self, request):
        return False

    def login_response(self, request):
        response = JSONResponse({
            "action": "redirect",
            "url": f"/login/"
        })
        return response

    async def logout_response(self, request):
        response = JSONResponse({
            "action": "redirect",
            "url": f"/"
        })
        request.cookies.clear()
        return response

    async def login(self, request):
        response = JSONResponse({
            "action": "redirect",
            "url": f"/"
        })
        request.cookies.clear()
        return response

    async def home_page(self, request):
        # await check_and_init_db(session)
        self.session.app['mode'] = "list"
        self.session.app['component'] = "form"

        return JSONResponse({
            "action": "redirect",
            "url": "/action/list_action",
        })

    async def handle_request(self):
        pass
