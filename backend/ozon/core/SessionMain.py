# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
import logging
import uuid
from .BaseClass import BaseClass, PluginBase
from fastapi.requests import Request
from abc import ABC, abstractmethod
from .database.mongo_core import *

logger = logging.getLogger(__name__)


class SessionAbc(ABC):

    @abstractmethod
    async def init_session(self) -> Session:
        logger.info(f"** Session Auth Free")
        self.session = await self.find_session_by_token()
        if not self.session:
            self.user['uid'] = f"user.{str(uuid.uuid4())}"
            self.user['name'] = "public"
            self.user['full_name'] = "Public User"
            self.uid = self.user.get("uid")
            self.session = data_helper(
                Session(
                    token=self.token, uid=self.uid, user=self.user.copy(),
                    server_settings=self.settings.dict().copy()
                )
            )
            self.session.is_admin = True
            self.session.use_auth = False
            self.reset_app()

        logger.info(f"** Session Auth Free---> uid: {self.uid}")
        return self.session

    @abstractmethod
    async def find_session_by_token(self):
        # return await find_session_by_token_req_id(self.token, self.req_id)
        return await find_session_by_token(self.token)

    @abstractmethod
    async def find_session_by_uid(self):
        # return await find_session_by_uid_req_id(self.uid, self.req_id)
        return await find_session_by_uid(self.uid)

    @abstractmethod
    def reset_app(self):
        app_modes = ["standard"]
        if self.session.is_admin:
            app_modes = ["standard", "maintenance"]
        self.session.app = {
            "modes": app_modes,
            "mode": "standard",
            "layout": "standard",
            "action_model": "action",
            "default_fields": default_fields,
            "models_query": {},
            "action_name": "",
            "component_name": "",
            "submissison_name": "",
            "can_build": self.session.use_auth,
            "builder": False,
            "data": {},
            "breadcrumb": {}
        }

    @abstractmethod
    async def check_token(self):
        return {}

    @abstractmethod
    async def check_login(self):
        self.token = self.request.cookies.get("authtoken", "")
        if self.token == "":
            self.token = str(uuid.uuid4())
        return await self.init_session()


class SessionMain(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class SessionBase(SessionMain, SessionAbc, BaseClass):

    @classmethod
    def create(cls, **kwargs):
        self = SessionBase(**kwargs)
        return self

    async def init_session(self) -> Session:
        return await super().init_session()

    def reset_app(self):
        return super().reset_app()

    async def check_token(self) -> dict:
        return await super().check_token()

    async def check_login(self):
        return await super().check_login()

    async def find_session_by_token(self):
        return await super().find_session_by_token()

    async def find_session_by_uid(self):
        return await super().find_session_by_uid()
