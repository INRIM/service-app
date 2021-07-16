# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
import sys
import os
from os import listdir
from os.path import isfile, join
from fastapi.responses import RedirectResponse, JSONResponse
import ujson
from ozon.settings import get_settings
from .database.mongo_core import *
from collections import OrderedDict
from pathlib import Path
from fastapi import Request
from .SessionMain import SessionMain
from .ModelData import ModelData
from .BaseClass import BaseClass, PluginBase
from pydantic import ValidationError

import logging
import pymongo
import requests
import httpx
import uuid

logger = logging.getLogger(__name__)


class ServiceAuth(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class ServiceAuthBase(ServiceAuth):

    @classmethod
    def create(cls, public_endpoint="", parent=None, request=None, req_id=""):
        self = ServiceAuthBase()
        self.init(public_endpoint, parent, request, req_id)
        return self

    def init(self, public_endpoint="", parent=None, request=None, req_id=""):
        self.mdata = ModelData.new()
        self.session = None
        self.request_login_required = False
        self.user = None
        self.need_token = True
        self.user_is_logged = False
        self.public_request = False
        self.token = ""
        self.public_endpoint = public_endpoint[:]
        self.parent = parent
        self.request = request
        self.req_id = req_id
        self.session_service = self.create_session_service()

    def create_session_service(self):
        return SessionMain.new(
            token="",
            req_id=self.req_id,
            request=self.request,
            user_token={},
            uid="",
            session={},
            user={},
            app={},
            action={},
            user_preferences={},
            public_endpoint=self.public_endpoint[:],
            settings=get_settings(),
            is_admin=False,
            use_auth=True
        )

    async def create_session_public_user(self):
        self.token = str(uuid.uuid4())
        self.session_service.token = self.token
        self.session = await self.session_service.init_public_session()
        return self.session

    async def init_user_session(self):
        self.session_service.uid = self.user.uid
        # self.session = await self.session_service.find_session_by_uid()
        # if not self.session:
        self.token = str(uuid.uuid4())
        self.session_service.token = self.token
        self.session = await self.session_service.init_session(self.user)
        return self.session

    async def handle_request(self, request, req_id):
        self.request = request
        self.req_id = req_id
        return await self.check_session()

    async def check_session(self):
        logger.info("check_session")
        authtoken = self.request.cookies.get("authtoken", "")
        apitoken = self.request.headers.get("apitoken", "")
        token = self.request.query_params.get("token", False)
        if authtoken:
            self.token = authtoken
        if apitoken and not self.token:
            self.token = apitoken
        if token and not self.token:
            self.token = token
        self.session_service.token = self.token
        self.session = await self.init_session()

        return self.session

    async def init_session(self):
        self.session = await self.session_service.find_session_by_token()
        if not self.session and self.is_public_endpoint:
            self.session = await self.create_session_public_user()
        if self.session.expire_datetime < datetime.now():
            self.session.active = False
            await self.mdata.save_record(self.session)
            self.session = None
        return self.session

    async def init_token(self):
        self.token = str(uuid.uuid4())
        user_data = await self.mdata.by_uid(User, self.username)
        user = User(**user_data)
        user.token = str(uuid.uuid4())
        user.id = user_data['id']
        await self.mdata.save_record(user)
        return self.init_session()

    async def check_auth(self, username="", password=""):
        query = {
            "$and": [
                {"uid": username},
                {"password": password},
                {"deleted": 0}
            ]
        }
        exist = await self.mdata.count_by_filter(
            User, query)
        return exist > 0

    # TODO handle multiple instance of same user with req_id
    async def login(self):
        dataj = await self.request.json()
        data = ujson.loads(dataj)
        self.username = data.get("username", "")
        password = data.get("password", "")
        login_ok = await self.check_auth(self.username, password)
        if login_ok:
            self.user = await self.mdata.by_uid(User, self.username)
            self.session = await self.init_user_session()
            self.session.app['save_session'] = True
            self.token = self.session.token
            self.parent.session = self.session
            self.parent.token = self.session.token
            return await self.login_next_and_complete()
        else:
            return self.login_error()

    async def login_next_and_complete(self):
        return self.login_complete()

    def login_complete(self):
        self.session.login_complete = True
        return self.get_login_complete_response()

    def login_page(self):
        response = JSONResponse({
            "content": {
                "reload": True,
                "link": f"/login"
            }
        })

        return response

    def login_error(self):
        response = JSONResponse({
            "content": {
                "status": "error",
                "message": f"Errore login utente o password non validi",
                "model": 'login'
            }
        })
        return response

    def get_login_complete_response(self):
        response = JSONResponse({
            "content": {
                "reload": True,
                "link": f"/?token={self.token}"
            }

        })
        return response

    async def logout(self):
        self.session = await self.session_service.logout()
        self.parent.session = self.session
        self.parent.token = self.session.token
        return self.logout_page()

    def logout_page(self):
        response = JSONResponse({
            "action": "redirect",
            "url": f"/login/"
        })

        return response

    def is_public_endpoint(self):
        # if any(x not in self.request.url.path for x in self.public_endpoint):
        if self.request.url.path in self.public_endpoint:
            return True
        return False

    def deserialize_header_list(self, request: Request):
        # list_data = self.request.headers.mutablecopy().__dict__['_list']
        list_data = request.headers.mutablecopy()
        res = {item[0]: item[1] for item in list_data}
        return res.copy()
