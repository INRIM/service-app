# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import sys

#
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
from fastapi.concurrency import run_in_threadpool
from .DateEngine import DateEngine
import pymongo
import copy

logger = logging.getLogger(__name__)


class Ozon(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class OzonBase(Ozon):

    @classmethod
    def create(
            cls, pwd_contex=None, settings=None):
        self = OzonBase()
        self.init(pwd_context, settings)
        return self

    def init(self, pwd_context, settings):
        self.session = None
        self.token = ""
        self.app_code = ""
        self.settings = settings
        self.pwd_context = pwd_context
        self.mdata = ModelData.new(session=None, pwd_context=pwd_context)
        self.auth_service = None
        self.login_required = False
        self.req_id = str(uuid.uuid4())
        self.user_token = {}
        self.main_module = {}
        self.modules_done = []
        self.session_service = None
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
        self.app_code = request.headers.get('app_code', "admin")
        await self.mdata.make_settings()
        if not req_id:
            req_id = self.req_id
        logger.debug(
            f"init_request with class {self} for {request.url.path}, req_id {req_id},"
            f"object: {self} "
        )
        self.auth_service = ServiceAuth.new(
            settings=self.settings, public_endpoint=self.public_endpoint,
            parent=self, request=request,
            pwd_context=self.pwd_context, req_id=req_id
        )
        await self.auth_service.make_settings()
        self.session = await self.auth_service.handle_request(request, req_id)
        self.mdata.session = self.session

        logger.debug(f"init_request End session {type(self.session)}")
        return self.session

    async def handle_response(self, arg) -> None:
        if arg["type"] == "http.response.start":
            if self.session:
                self.session.req_id = self.req_id
                if self.session.app.get('save_session'):
                    self.session.apps[
                        self.session.app_code] = self.session.app.copy()
                    await self.save_session()
            headers = MutableHeaders(scope=arg)
            if self.session.is_api:
                headers.append("apitoken", self.session.token)
                headers.append("cookies", f"apitoken={self.session.token}")
            else:
                headers.append("authtoken", self.session.token)
                headers.append("cookies", f"authtoken={self.session.token}")
            headers.append("req_id", self.req_id)

            # headers.append("cookies", f"domain={os.environ.get('DOMAIN')}") TODO

    async def save_session(self):
        logger.info("save_session")
        self.session.last_update = datetime.now().timestamp()
        self.session.update_datetime = datetime.now().isoformat()
        await self.mdata.save_record(self.session)

    async def home_page(self, request):
        self.session.app['mode'] = "list"
        self.session.app['component'] = "form"

        resp = JSONResponse({
            "action": "redirect",
            "url": "/dashboard",
        })
        return resp

    async def handle_request(self):
        pass

    async def init_apps(self, main_module):
        self.main_module = copy.deepcopy(main_module)
        await self.check_deps()
        await self.compute_check_and_init_db(self.main_module.copy(),
                                             main=True)

    async def get_files_in_path(self, path, id_file=-1, ext=["json"]):
        res = []
        if await run_in_threadpool(lambda: os.path.exists(path)):
            if any(True for x in
                   await run_in_threadpool(lambda: os.listdir(path)) if
                   x.split(".")[-1] in ext):
                for x in await run_in_threadpool(lambda: os.listdir(path)):
                    if x.split(".")[-1] in ext:
                        res.append(x)
        if id_file >= 0:
            if res:
                return res[id_file]
            else:
                return ""
        return res

    async def check_deps(self):
        if self.main_module.get("depends"):
            for src_dep in self.main_module.get("depends"):
                mod = {
                    "module_name": src_dep.split(".")[1],
                    "module_group": src_dep.split(".")[0]
                }
                await self.compute_check_and_init_db(mod.copy())
                self.modules_done.append(mod['module_name'])

    async def _init_session(self):
        self.session = await find_session_by_token(self.settings.api_user_key)
        if not self.session:
            user = await self.mdata.user_by_token(self.settings.api_user_key)
            if user:
                uid = user.uid
                udict = user.get_dict()
            else:
                uid = 'admin'
                udict = {
                    "uid": "admin",
                    "full_name": "Admin"
                }

            dte = DateEngine()
            min, max = dte.gen_datetime_min_max_hours(
                max_hours_delata_date_to=self.settings.session_expire_hours)
            self.session = data_helper(
                Session(
                    token=self.settings.api_user_key,
                    uid=uid,
                    user=udict.copy(),
                    create_datetime=min,
                    expire_datetime=max,
                )
            )
        self.mdata.session = self.session.copy()

    async def compute_check_and_init_db(self, ini_data, main=False):
        logger.info(f"check_and_init_db {ini_data['module_name']}")
        module_name = ini_data.get("module_name", "")
        module_group = ini_data.get("module_group", "")
        base_path = f"/apps/web-client/{module_group}/{module_name}"
        pathcfg = f"{base_path}/config.json"
        if not main:
            def_data = {}
            if os.path.exists(pathcfg):
                with open(pathcfg) as f:
                    def_data = ujson.load(f)
        else:
            def_data = ini_data.copy()
        await self._init_session()

        module_type = def_data.get("module_type", "")
        auto_create_actions = def_data.get("auto_create_actions", False)
        config_menu_group = def_data.get("config_menu_group", {})
        components_file = def_data.get("schema", {})
        pre_datas = def_data.get("pre_datas", [])
        datas = def_data.get("datas", [])
        dbviews = def_data.get("dbviews", [])
        is_update = False
        no_update = def_data.get("no_update", False)
        for node in pre_datas:
            model_name = list(node.keys())[0]
            namefile = node[model_name]
            pathfile = f"{base_path}{namefile}"
            if namefile:
                await self.import_data(model_name, pathfile)

        if components_file:
            components_file_path = f"{base_path}{components_file}"

            msg, is_update = await self.import_component(
                components_file_path, False, config_menu_group,
                no_update=no_update)

        for node in datas:
            model_name = list(node.keys())[0]
            namefile = node[model_name]
            pathfile = f"{base_path}{namefile}"
            if namefile:
                await self.import_data(
                    model_name, pathfile, is_update, no_update)
        for namefile in dbviews:
            pathfile = f"{base_path}{namefile}"
            if namefile:
                await self.import_db_views(pathfile)
        if module_type in ["app", "backend"]:
            logger.info(
                f"add App {def_data['module_group']}.{def_data['module_name']}, autoaction: {auto_create_actions}")
            rec_dict = def_data.copy()
            is_app_admin = rec_dict.get("add_admin")
            if module_type == "backend":
                rec_dict['app_code'] = [def_data['app_code']]
            rec_dict['rec_name'] = rec_dict.pop('module_name')
            App = await self.mdata.gen_model("settings")
            app = App(**rec_dict)
            app.owner_uid = self.settings.admin_username
            app.admins = app.admins + self.settings.admins
            app.list_order = int(
                await self.mdata.count_by_filter(App, query={"deleted": 0}))
            try:
                await self.mdata.save_record(app)
                if is_app_admin:
                    MenuG = await self.mdata.gen_model("menu_group")
                    q = {"$and": [
                        {"apps": {"$in": ["admin"]}},
                        {"deleted": 0}
                    ]}
                    menu_groups = await search_by_filter(
                        MenuG, q
                    )
                    for action_tmp in menu_groups:
                        data = action_tmp.copy()
                        data['apps'] = [rec_dict['rec_name']]
            except pymongo.errors.DuplicateKeyError as e:
                logger.warning(
                    f" Error create app {rec_dict['rec_name']} {e.details['errmsg']} ignored")
                pass

    async def import_db_views(self, data_file):
        logger.info(f"import_db_views data_file:{data_file}")
        if ".json" in data_file and await run_in_threadpool(
                lambda: os.path.exists(data_file)):
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
            self, model_name: str, config_menu_group: dict,
            model_menu_group: BasicModel):
        res = {}
        for group_rec_name, compo_list in config_menu_group.items():
            if model_name in compo_list:
                rec = await self.mdata.by_name(model_menu_group,
                                               group_rec_name)
                if rec:
                    return {
                        "rec_name": rec.rec_name,
                        "title": rec.label
                    }
                else:
                    logger.info(
                        f" no group for {model_menu_group} and {group_rec_name}")
                    return {}
        return res

    async def import_component(
            self, components_file, auto_create_actions=False,
            config_menu_group={}, no_update=True):
        logger.info(f"import_component components_file:{components_file}")
        is_update = False
        if ".json" in components_file and await run_in_threadpool(
                lambda: os.path.exists(components_file)):
            logger.info(f"init component {components_file}")
            async with aiofiles.open(components_file,
                                     mode="rb") as jsonfile:  # type: ignore
                data_j = await jsonfile.read()
            datas = ujson.loads(data_j)
            msgs = ""
            model_menu_group = False
            action_model = await self.mdata.gen_model("action")
            if auto_create_actions:
                model_menu_group = await self.mdata.gen_model("menu_group")
            for data in datas:
                logger.info(
                    f" component data: {data['rec_name']} autoaction {auto_create_actions}")
                component = Component(**data)
                compo = await self.mdata.by_name(Component, data['rec_name'])
                if not compo or not no_update:
                    logger.info(f"import {data['rec_name']}")
                    if self.session:
                        await self.mdata.save_object(
                            self.session, component, model_name="component",
                            copy=False)
                    else:
                        component.owner_uid = self.settings.admin_username
                        component.list_order = int(
                            await self.mdata.count_by_filter(Component, query={
                                "deleted": 0}))
                        try:
                            await self.mdata.save_record(component)
                        except pymongo.errors.DuplicateKeyError as e:
                            logger.warning(
                                f" Duplicate {e.details['errmsg']} ignored")

                else:
                    is_update = True
                    msgs += f"{data['rec_name']} alredy exixst not imported"
                if auto_create_actions and not component.data_model == "no_model":
                    mnu = await self.mdata.by_name(model_menu_group,
                                                   component.rec_name)
                    actions = await self.mdata.count_by_filter(
                        action_model, {"$and": [{"model": component.rec_name},
                                                {"action_type": {
                                                    "$ne": "task"}}]})
                    menu_group = await self.compute_menu_group(
                        component.rec_name, config_menu_group.copy(),
                        model_menu_group)
                    if not actions and not component.data_model == "no_model":
                        await self.mdata.make_default_action_model(
                            self.session, component.rec_name, component,
                            menu_group=menu_group.copy()
                        )
            if not msgs:
                msgs = "Import done."
            return msgs, is_update
        else:
            msg = f"{components_file} not exist"
            logger.error(msg)
            return msg, is_update

    async def import_data(self, model_name, data_file, is_update=False,
                          no_update=False):
        logger.info(
            f"import_data model_name: {model_name}, data_file:{data_file}")
        if no_update:
            logger.info(
                f"update_data model_name: {model_name} no_update is True")
            return
        if ".json" in data_file and await run_in_threadpool(
                lambda: os.path.exists(data_file)):
            async with aiofiles.open(data_file, mode="rb") as jsonfile:
                data_j = await jsonfile.read()
            datas = ujson.loads(data_j)
            model = await self.mdata.gen_model(model_name)
            for record_data in datas:
                record = model(**record_data)
                if model_name == "user":
                    pw_hash = self.get_password_hash(record.password)
                    record.password = pw_hash
                record.owner_uid = self.settings.admin_username
                record.list_order = int(await self.mdata.count_by_filter(model,
                                                                         query={
                                                                             "deleted": 0}))
                if self.session:
                    await self.mdata.save_object(
                        self.session, record, model_name=model_name,
                        copy=False)
                else:
                    try:
                        await self.mdata.save_record(record)
                    except pymongo.errors.DuplicateKeyError as e:
                        logger.warning(
                            f" Duplicate model {model_name} {e.details['errmsg']} ignored")
                        pass
        else:
            logger.error(f"{data_file} not exist")
