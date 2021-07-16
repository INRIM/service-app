# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
import logging
import uuid
from .BaseClass import BaseClass, PluginBase
from fastapi.requests import Request
from abc import ABC, abstractmethod
from .database.mongo_core import *
from .DateEngine import DateEngine

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

    async def init_public_session(self) -> Session:
        logger.info(f"** Session Auth Free")
        self.user['uid'] = f"user.{str(uuid.uuid4())}"
        self.user['nome'] = "public"
        self.user['full_name'] = "Public User"
        self.uid = self.user.get("uid")
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
        self.reset_app()

        logger.info(f"** Session Auth Free---> uid: {self.session.uid}")
        return self.session

    async def init_session(self, user: User) -> Session:
        logger.info(f"New Session Auth for {user.uid}")
        self.user = user
        self.session = await self.find_session_by_token()
        dict_user = ujson.loads(self.user.json()).copy()
        dte = DateEngine()
        min, max = dte.gen_datetime_min_max_hours(
            max_hours_delata_date_to=self.settings.session_expire_hours)
        if not self.session:
            self.session = data_helper(
                Session(
                    token=self.token,
                    uid=self.user.uid,
                    user=dict_user,
                    create_datetime=min,
                    expire_datetime=max,
                )
            )
            self.session.is_admin = self.user.is_admin
            self.session.use_auth = True
            self.reset_app()

        logger.info(f"Done Session Auth ---> uid: {self.user.uid}")
        return self.session

    async def find_session_by_token(self):
        logger.info(f"check token for uid {self.uid}")
        # return await find_session_by_token_req_id(self.token, self.req_id)
        return await find_session_by_token(self.token)

    async def find_session_by_uid(self):

        # return await find_session_by_uid_req_id(self.uid, self.req_id)
        session = await find_session_by_uid(self.uid)
        logger.info(f"exist session for uid {self.uid} --> {type(session)}")
        return session

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
            "save_session": False,
            "data": {},
            "breadcrumb": {}
        }

    async def check_token(self):
        return {}

    async def logout(self):
        # return await find_session_by_token_req_id(self.token, self.req_id)
        self.session = await find_session_by_token(self.token)
        self.session.active = False
        self.session.last_update = datetime.now().timestamp()
        await save_record(self.session)
        return self.session
