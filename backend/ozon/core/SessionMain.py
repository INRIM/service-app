# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import logging
import uuid
from .BaseClass import BaseClass, PluginBase
from fastapi.requests import Request
from abc import ABC, abstractmethod
from .database.mongo_core import *
from .DateEngine import DateEngine
import uuid

logger = logging.getLogger(__name__)


class SessionMain(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class SessionBase(SessionMain, BaseClass):

    @classmethod
    def create(cls, **kwargs):
        self = SessionBase(**kwargs)
        return self

    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password):
        return self.pwd_context.hash(password)

    async def init_public_session(self) -> Session:
        logger.info(f"** Session Auth Free")
        self.user['uid'] = f"user.{str(uuid.uuid4())}"
        self.user['nome'] = "public"
        self.user['full_name'] = "Public User"
        self.uid = self.user.get("uid")
        self.app_code = request.headers.get('app_code', "admin")
        dte = DateEngine()
        min, max = dte.gen_datetime_min_max_hours(
            max_hours_delata_date_to=self.settings.session_expire_hours)
        self.session = data_helper(
            Session(
                token=self.token, uid=self.uid, user=self.user.copy(),
                create_datetime=min,
                expire_datetime=max,
            )
        )
        self.session.is_admin = False
        self.session.use_auth = False
        self.session.is_public = True
        await self.reset_app()

        logger.info(f"** Session Auth Free---> uid: {self.session.uid} {type(self.session)}")
        return self.session

    async def make_session(self, token=False) -> Session:
        self.session = await self.find_session_by_token()
        if not self.session:
            if not token:
                self.token = str(uuid.uuid4())
            else:
                self.token = token
            dte = DateEngine()
            min, max = dte.gen_datetime_min_max_hours(
                max_hours_delata_date_to=self.settings.session_expire_hours)
            self.session = data_helper(
                Session(
                    token=self.token,
                    uid=self.uid,
                    user=self.user.copy(),
                    create_datetime=min,
                    expire_datetime=max,
                )
            )
        return self.session

    async def init_session(self, user: dict) -> Session:
        logger.info(f"Init Session Auth for {self.uid}")
        self.user = user
        self.session = await self.make_session()
        self.session.is_admin = self.user.get("is_admin")
        self.session.use_auth = True
        await self.reset_app()
        logger.info(f"Session Auth Done ---> uid: {self.uid}")
        return self.session

    async def init_api_session(self, user: dict, token) -> Session:
        logger.info(f"Init Api Session for {self.uid}")
        self.user = user
        self.session = await self.make_session(token)
        self.session.is_admin = self.user.get("is_admin")
        self.session.use_auth = True
        await self.reset_app()
        logger.info(f"Session Api Done ---> uid: {self.uid}")
        return self.session

    async def find_session_by_token(self):
        logger.info(f"token: {self.token} - app {self.app_code}")
        self.session = await find_session_by_token(self.token)
        if self.session:
            await self.set_current_app()
            logger.info(f"check token --> find uid {self.session.uid}")
        else:
            logger.info(f"check token --> not found | expired")
        return self.session

    async def reset_app(self):
        app_modes = ["standard"]
        if self.session.is_admin:
            app_modes = ["standard", "maintenance"]
        self.session.apps = {self.app_code: {
            "modes": app_modes,
            "mode": "standard",
            "layout": "standard",
            "action_model": "action",
            "default_fields": default_fields,
            "models_query": {},
            "model_write_access": {},
            "model_write_access_fields": {},
            "fast_search": {},
            "action_name": "",
            "component_name": "",
            "submissison_name": "",
            "can_build": self.session.use_auth,
            "builder": False,
            "save_session": False,
            "data": {},
            "breadcrumb": {}
        }}
        await self.set_current_app()

    async def set_current_app(self):
        self.session.app = self.session.apps[self.app_code].copy()

    async def check_token(self):
        return {}

    async def logout(self):
        self.session = await find_session_by_token(self.token)
        self.session.active = False
        self.session.last_update = datetime.now().timestamp()
        await save_record(self.session)
        return self.session
