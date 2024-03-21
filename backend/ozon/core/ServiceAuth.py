# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import os
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse

from .BaseClass import PluginBase
from .ModelData import ModelData
from .SessionMain import SessionMain
# from ozon.settings import get_settings
from .database.mongo_core import *


logger = logging.getLogger(__name__)


class ServiceAuth(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class ServiceAuthBase(ServiceAuth):
    @classmethod
    def create(
            cls,
            settings=None,
            public_endpoint="",
            parent=None,
            request=None,
            pwd_context=None,
            req_id="",
    ):
        self = ServiceAuthBase()
        self.init(
            settings, public_endpoint, parent, request, pwd_context, req_id
        )
        return self

    def init(
            self,
            settings=None,
            public_endpoint="",
            parent=None,
            request=None,
            pwd_context=None,
            req_id="",
    ):
        self.session = None
        self.app_code = parent.app_code
        self.settings = settings
        self.mdata = ModelData.new(
            session=None, pwd_context=pwd_context, app_code=self.app_code
        )
        self.pwd_context = pwd_context
        self.request_login_required = False
        self.user = None
        self.need_token = True
        self.user_is_logged = False
        self.public_request = False
        self.ws_request = False
        self.token = ""
        self.public_endpoint = public_endpoint[:]
        self.parent = parent
        self.request = request
        self.req_id = req_id
        self.session_service = self.create_session_service()

    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password):
        return self.pwd_context.hash(password)

    def create_session_service(self):
        return SessionMain.new(
            token="",
            app_code=self.app_code,
            req_id=self.req_id,
            request=self.request,
            mdata=self.mdata,
            user_token={},
            uid="",
            session={},
            user={},
            app={},
            action={},
            user_preferences={},
            pwd_context=self.pwd_context,
            public_endpoint=self.public_endpoint[:],
            settings=self.settings,
            is_admin=False,
            use_auth=True,
        )

    async def make_settings(self):
        self.app_settings = await self.mdata.get_app_settings(
            app_code=self.app_code
        )

    async def create_session_public_user(self):
        self.token = str(uuid.uuid4())
        self.session_service.token = self.token
        self.session = await self.session_service.init_public_session()
        return self.session

    async def find_user(self):
        user = await self.session_service.get_uid_info(self.username)
        self.user = user.get_dict()
        self.user.get("allowed_users").append(self.user.get("uid"))
        return self.user

    async def init_user_session(self):
        await self.find_user()
        self.session_service.uid = self.user.get("uid")
        self.session = await self.session_service.init_session(
            self.user.copy()
        )
        self.token = self.session_service.token
        return self.session

    async def handle_request(self, request, req_id):
        self.request = request
        self.req_id = req_id
        self.app_code = request.headers.get("app_code", "admin")
        return await self.check_session()

    async def check_default_token_header(self):
        self.token = False
        authtoken = self.request.cookies.get("authtoken", "")
        if not authtoken:
            authtoken = self.request.headers.get("authtoken", "")
        apitoken = self.request.headers.get("apitoken", False)
        token = self.request.query_params.get("token", False)
        if authtoken:
            self.token = authtoken
        if token and not self.token:
            self.token = token
        if self.token is False and apitoken:
            # TODO handle here ws-users token | self.ws_request = True
            logger.debug(f"ws_request {apitoken}")
            self.ws_request = True
            self.token = apitoken
            logger.debug(f" Is WS {self.ws_request} with token {self.token}")

    async def check_session(self):
        logger.info("check_session")
        await self.check_default_token_header()
        self.session_service.token = self.token
        if self.ws_request and not self.session:
            self.session = await self.init_api_user_session()

        else:
            self.session = await self.init_session()
        return self.session

    async def find_api_user(self):
        user = await self.mdata.user_by_token(self.token)
        if user:
            self.user = user.get_dict()
            self.user.get("allowed_users").append(self.user.get("uid"))
            return self.user
        return {}

    async def init_api_user_session(self):
        await self.find_api_user()
        if self.user:
            self.session_service.uid = self.user.get("uid")
            self.session = await self.session_service.init_api_session(
                self.user.copy(), self.token
            )
            # self.token = self.session_service.token
        return self.session

    async def init_session(self):
        self.session = await self.session_service.find_session_by_token()
        if not self.session and self.is_public_endpoint:
            self.session = await self.create_session_public_user()
        if self.session and self.session.expire_datetime < datetime.now():
            self.session.active = False
            await self.mdata.save_record(self.session)
            self.session = None
        return self.session

    async def check_auth(self, username="", password=""):
        user = await self.mdata.by_uid(User, username)
        if not user:
            logger.warning(f"user {username} not found")
            return False
        verify = self.verify_password(password, user.password)
        if not verify:
            return False
        return True

    # TODO handle multiple instance of same user with req_id
    async def login(self):
        data = await self.request.json()
        await self.make_settings()
        await self.session_service.make_settings()
        self.username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        login_ok = await self.check_auth(self.username, password)
        logger.info(f"login {self.username} --> {login_ok}")
        if login_ok:
            self.session = await self.init_user_session()
            self.session.app["save_session"] = True
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
        response = JSONResponse(
            {"content": {"status": "ok", "reload": True, "link": f"/login"}}
        )

        return response

    def login_error(self):
        response = JSONResponse(
            {
                "content": {
                    "status": "error",
                    "message": f"Errore login utente o password non validi",
                    "model": "login",
                }
            }
        )
        return response

    def get_login_complete_response(self):
        response = JSONResponse(
            {
                "content": {
                    "status": "ok",
                    "reload": True,
                    "link": f"/?token={self.token}",
                }
            }
        )
        return response

    def reload_page_response(self):
        response = JSONResponse(
            {"content": {"status": "ok", "reload": True, "link": f"#"}}
        )
        return response

    async def logout(self):
        self.session = await self.session_service.logout()
        self.parent.session = self.session
        self.parent.token = self.session.token
        return self.logout_page()

    def logout_page(self):
        response = JSONResponse({"action": "redirect", "url": f"/login/"})
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
