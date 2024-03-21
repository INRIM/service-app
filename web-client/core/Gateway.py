# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import copy
import logging
import re

import httpx
import ujson
from core.cache.cache import get_cache
from fastapi import Request
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from starlette.datastructures import QueryParams
from starlette.status import HTTP_303_SEE_OTHER

from .ContentService import ContentService
from .main.base.base_class import PluginBase
from .main.base.utils_for_service import requote_uri

logger = logging.getLogger(__name__)


class Gateway(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        if cls not in cls.plugins:
            cls.plugins.append(cls())


class GatewayBase(Gateway):
    @classmethod
    def create(cls, request: Request, settings, templates):
        self = GatewayBase()
        self.init(request, settings, templates)
        return self

    def init(self, request: Request, settings, templates):
        self.request = request
        self.remote_req_id = ""
        self.name_allowed = re.compile(r"^[A-Za-z0-9._~():+-]*$")
        self.local_settings = settings
        self.templates = templates
        self.session = {}
        self.token = ""
        self.is_api = False
        self.params = self.request.query_params.__dict__["_dict"].copy()
        self.headers = self.deserialize_header_list()
        self.cookies = self.request.cookies
        self.init_headers_and_token()

    @classmethod
    def query_params(cls, url) -> QueryParams:
        qstring = url.split("?")[1] if "?" in url else ""
        return QueryParams(qstring)

    def clean_form(self, form_data):
        # logger.info(f"{form_data}")
        dat = {}

        dat = ujson.loads(form_data.get("formObj"))
        for k, v in form_data.items():
            if not k == "formObj":
                dat[k] = v
        return dat

    def init_headers_and_token(self):
        # logger.info(f"before")
        dat = {}

        if "content-length" in self.headers:
            self.headers.pop("content-length")

        if "Content-Type" in self.headers:
            self.headers.pop("Content-Type")

        if "Cache-control" in self.headers:
            self.headers.pop("Cache-control")

        if "cache-control" in self.headers:
            self.headers.pop("cache-control")

        if "content-type" in self.headers:
            self.headers.pop("content-type")
        if "accept" in self.headers:
            self.headers.pop("accept")
        if "token" in self.params:
            self.token = self.params.get("token", "")

        base_url = str(self.request.base_url)[:-1]
        self.headers.update(
            {
                "Content-Type": "application/json",
                "accept": "application/json",
                "app_code": self.local_settings.app_code,
                "referer": requote_uri(f"{base_url}{self.request.url.path}"),
                "base_url_ref": f"{base_url}",
                "req_id": self.request.headers.get("req_id", ""),
            }
        )

        if not self.token:
            if self.request.headers.get("authtoken"):
                self.token = self.request.headers.get("authtoken")
            elif self.request.headers.get("apitoken"):
                self.token = self.request.headers.get("apitoken")
                self.is_api = True
        else:
            self.headers.update(
                {
                    "authtoken": self.token,
                }
            )

        # TODO move in shibboleth Gateway
        if "x-remote-user" not in self.request.headers:
            self.headers["x-remote-user"] = self.request.headers.get(
                "x-remote-user", ""
            )

        logger.debug(f"complete token: {self.token} is Api {self.is_api}")

    async def load_post_request_data(self):
        await self.get_session()
        submitted_data = {}
        content_service = ContentService.new(gateway=self, remote_data={})
        try:
            submitted_data = await self.request.json()
        except ValueError as e:
            try:
                submit_data = await self.request.form()
                submitted_data = self.clean_form(submit_data._dict)
            except ValueError as e:
                logger.error(f"error {e}")
                err = {
                    "status": "error",
                    "message": f"Request data must be json or form",
                    "model": "",
                }
                return await content_service.form_post_complete_response(
                    err, None
                )
        if isinstance(submitted_data, dict):
            return submitted_data.copy()
        else:
            return submitted_data

    async def compute_datagrid_rows(self, key, model_name, rec_name=""):
        logger.info("compute_datagrid_rows")
        await self.get_session()
        server_response = await self.get_record(model_name, rec_name=rec_name)
        content_service = ContentService.new(
            gateway=self, remote_data=server_response.copy()
        )

        res = await content_service.compute_datagrid_rows(key)
        return res

    async def compute_datagrid_add_row(
            self, key, num_rows, model_name, rec_name="", data={}
    ):
        logger.info("compute_datagrid_add_row")
        await self.get_session()
        server_response = await self.get_record(model_name, rec_name=rec_name)
        content_service = ContentService.new(
            gateway=self, remote_data=server_response.copy()
        )
        res = await content_service.compute_datagrid_add_row(
            key, num_rows, data=data
        )
        return res

    async def content_service_from_record(self, model_name, rec_name=""):
        await self.get_session()
        server_response = await self.get_record(model_name, rec_name=rec_name)
        # logger.info(server_response)
        return ContentService.new(
            gateway=self, remote_data=server_response.copy()
        )

    async def before_submit(self, data, is_create=False):
        return data.copy()

    async def middleware_server_post_action(
            self, content_service, submitted_data
    ) -> dict:
        """
        This middleware method is triggered form Gateway.server_post_action method
        before create ContentService and post data to server.
        Is possible to handle three different pathway for data thougt status directive


        Dict mandatory key
            "status" possible values --> "done", "content", "error"
            "data" data dictionary

        Logic:
          if status == "error" --> add keys "message" and "model"
                                   server_post_action  return this error

          if status == "done" --> server_post_action execute submit of datas conined in key "data"

          if status == "content"  --> server_post_action

        :param content_service: an instance of content_service with empty data
        :param submitted_data: data recived from post call
        :return: structured Dict see above
        """
        content = {}
        # content_service = ContentService.new(gateway=self, remote_data={})

        if "rec_name" in submitted_data:
            allowed = (
                    self.name_allowed.match(submitted_data.get("rec_name"))
                    or False
            )
            if not allowed:
                logger.error(f"name {submitted_data.get('rec_name')}")

                err = {
                    "status": "error",
                    "message": f"Errore nel campo name "
                               f"{submitted_data.get('rec_name')} "
                               f"caratteri non consentiti",
                    "model": submitted_data.get("data_model"),
                    "data": {},
                }
                return err
        if "/builder_mode" in self.request.url.path:
            await self.get_session()
            content = {"status": "done", "data": {}}
        if "/login" in self.request.url.path:
            await self.get_session()
            content = {"status": "done", "data": submitted_data}
        return content

    async def server_post_action(self, ui_response=True):
        logger.info(f"server_post_action {self.request.url}")
        url_path = self.request.scope["path"]
        # load request data
        await self.get_session()
        submitted_data = await self.load_post_request_data()
        # if submitted_data not dict is error then return
        if isinstance(submitted_data, JSONResponse):
            return submitted_data
        return await self.post_data(
            submitted_data, url_path=url_path, ui_response=ui_response
        )

    async def post_data(self, submitted_data, url_path="", ui_response=True):
        # logger.info(submitted_data)
        logger.info(f"server_post_action {self.request.url}")
        cookies = self.cookies
        params = self.params.copy()
        status = True
        builder = params.get("builder")
        if not url_path:
            url_path = submitted_data.get("action_url")
            logger.info(url_path)
        data = {}
        content_service = ContentService.new(gateway=self, remote_data={})
        mid_data = await self.middleware_server_post_action(
            content_service, submitted_data
        )
        if mid_data.get("status", "") == "error":
            return await content_service.form_post_complete_response(
                mid_data, None
            )
        elif mid_data.get("status", "") == "done":
            data = mid_data["data"].copy()
        elif not mid_data or mid_data.get("status") == "content":
            if builder:
                content_service = ContentService.new(
                    gateway=self, remote_data={}
                )
                data = content_service.compute_builder_data(submitted_data)
            else:
                if mid_data.get("status") == "content":
                    content = await self.get_record(
                        submitted_data.get("data_model")
                    )
                    content["content"]["data"] = mid_data["data"].copy()
                else:
                    content = await self.get_record(
                        submitted_data.get("data_model"),
                        submitted_data.get("rec_name", ""),
                    )

                # TODO chek use remote data to eval is_create create_datetime
                remote_data = content.get("content").get("data")
                content_service = ContentService.new(
                    gateway=self, remote_data=content.copy()
                )
                status, data = await content_service.form_post_handler(
                    submitted_data
                )

        logger.info(f"going to submit on server? {status}")
        if status:
            data = await self.before_submit(
                data.copy(), is_create=content_service.is_create
            )
            data = await content_service.before_submit(data.copy())
            url = f"{self.local_settings.service_url}{url_path}"
            server_response = await self.post_remote_object(
                url, data=data, params=params, cookies=cookies
            )
            resp = server_response.get("content")
            if not builder:
                server_response = (
                    await content_service.after_form_post_handler(
                        server_response, data
                    )
                )
        else:
            resp = data
            server_response = None

        if ui_response:
            return await content_service.form_post_complete_response(
                resp, server_response
            )
        else:
            return resp, server_response, content_service

    async def server_get_action(self, url_action="", modal=False):
        logger.info(f"server_get_action {self.request.url} - modal {modal} ")
        params = self.params.copy()
        cookies = self.cookies
        await self.get_session(params=params)
        if not modal:
            url = f"{self.local_settings.service_url}{self.request.scope['path']}"
            server_response = await self.get_remote_object(
                url, params=params, cookies=cookies
            )
        else:
            url = url_action
            server_response = {}
        if server_response and (
                server_response.get("action")
                or server_response.get("content", {}).get("action")
                or server_response.get("content", {}).get("reload")
        ):
            content = server_response
            if "content" in server_response:
                content = server_response.get("content")
            if not modal:
                if content.get("action") == "redirect" or content.get("link"):
                    url = content.get("url")
                    if content.get("link"):
                        url = content.get("link")
                    headers = self.headers.copy()
                    content_length = str(0)
                    headers["content-length"] = content_length
                    response = RedirectResponse(
                        url, headers=headers, status_code=HTTP_303_SEE_OTHER
                    )
            else:
                return await self.complete_json_response(content)
        else:
            if not modal:
                content_service = ContentService.new(
                    gateway=self, remote_data=server_response.copy()
                )

                if self.request.query_params.get("miframe"):
                    res = await content_service.compute_form()
                    response = HTMLResponse(res)

                else:
                    response = await content_service.make_page()
            else:
                content_service = ContentService.new(
                    gateway=self, remote_data={}
                )
                resp = await content_service.compute_form(modal=True, url=url)
                return await self.complete_json_response({"body": resp})
        return self.complete_response(response)

    async def get_session(self, params={}):
        if not params:
            params = self.params
        url = f"{self.local_settings.service_url}/session"
        res = await self.get_remote_object(url, params=params)
        self.session = res.copy()
        return res.copy()

    async def get_record(self, model, rec_name=""):
        url = f"{self.local_settings.service_url}/record/{model.strip()}"
        if rec_name.strip():
            url = f"{self.local_settings.service_url}/record/{model.strip()}/{rec_name.strip()}"
        res = await self.get_remote_object(url)
        return res.copy()

    async def get_record_data(self, model, rec_name):
        res = await self.get_record(model, rec_name)
        return res.get("content", {}).get("data")

    async def get_schema(self, model):
        url = f"{self.local_settings.service_url}/schema/{model}"
        res = await self.get_remote_object(url)
        return res

    async def get_param(self, param_name):
        url = f"{self.local_settings.service_url}/param/{param_name}"
        res = await self.get_remote_object(url)
        data = res.get("content").get("data")
        return data

    async def get_ext_submission(self, name, params={}):
        """
        name is a model name
        """
        logger.info(f"get_ext_submission -> {name}")

        url = f"{self.local_settings.service_url}/resource/data/{name}"
        res = await self.get_remote_object(url, params=params)
        data = res.get("content").get("data")[:]
        logger.info(f"get_ext_submission Response -> {len(data)}")
        return data

    async def get_list_models(self, domain={}, compute_label="title"):
        url = f"{self.local_settings.service_url}/models/distinct"
        res = await self.get_remote_object(
            url,
            params={"domain": domain.copy(), "compute_label": compute_label},
        )
        data = res.get("content").get("data")[:]
        logger.info(f"get_remote_object Response -> {len(data)}")
        return data

    async def get_remote_data_select(
            self, url, path_value, header_key, header_value_key
    ):
        """
        name is a model name
        """

        cache = await get_cache()
        editing = self.session.get("app").get("builder")
        use_cahe = True
        memc = await cache.get("client", f"{url}.{path_value}")
        if memc and not editing and use_cahe:
            logger.info(f"get_remote_data_select -> CACHE {url}")
            return copy.copy(memc)
        logger.info(f"get_remote_data_select ->for url:{url}")
        local_url = f"{self.local_settings.service_url}/get_remote_data_select"
        params = {
            "url": url,
            "path_value": path_value,
            "header_key": header_key,
            "header_value_key": header_value_key,
        }
        res = await self.get_remote_object(local_url, params=params)
        data = res.get("content").get("data")
        await cache.clear("client", f"{url}.{path_value}")
        await cache.set("client", f"{url}.{path_value}", data, expire=30)
        return copy.copy(data)

    async def get_resource_schema_select(self, type, select):
        """
        name is a model name
        """
        logger.info(f"get_resource_schema_select --> params: {type}, {select}")
        url = f"{self.local_settings.service_url}/resource/schema/select"
        res = await self.get_remote_object(
            url, params={"otype": type, "select": select}
        )
        data = res.get("content").get("data")
        logger.info(f"get_resource_schema_select --> {data}")
        return data

    async def complete_json_response(
            self, res, orig_resp=None
    ) -> JSONResponse:
        response = JSONResponse(res)
        return self.complete_response(response)

    def complete_response(self, resp):
        resp.headers.append("req_id", self.remote_req_id or "")
        if "/logout/" not in self.request.scope["path"]:
            if not self.is_api:
                resp.set_cookie("authtoken", value=self.token or "")
                resp.headers.append("authtoken", self.token or "")
            else:
                resp.headers.append("apitoken", self.token or "")
        if "/logout/" in self.request.scope["path"]:
            resp.set_cookie("authtoken", value="")
            resp.headers.append("authtoken", "")
        return resp

    async def eval_headers(self, headers={}):
        orig_params = self.request.query_params.__dict__["_dict"].copy()

        if not self.remote_req_id:
            req_id = self.request.headers.get("req_id", "")
        else:
            req_id = self.remote_req_id

        headers["req_id"] = req_id

        if self.is_api:
            headers["apitoken"] = self.token
        else:
            headers["authtoken"] = self.token

        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        if "accept" not in headers:
            headers["accept"] = "application/json"

        # TODO move in shibboleth Gateway
        return headers.copy()

    async def get_remote_object(self, url, headers={}, params={}, cookies={}):
        if self.local_settings.service_url not in url:
            url = f"{self.local_settings.service_url}{url}"

        if "token" in params:
            cookies = {"authtoken": params.get("token")}
            if "cookie" in self.headers:
                self.headers.pop("cookie")

        if not cookies:
            cookies = self.request.cookies.copy()

        # logger.info(f" request headers   {self.headers}")
        logger.debug(f"get_remote_object --> {url} cookies {cookies} self.headers {self.headers}")

        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.get(
                url=requote_uri(url),
                params=params,
                headers=self.headers,
                cookies=cookies,
            )

        if res.status_code == 200:
            req_id = res.headers.get("req_id")
            if res.headers.get("apitoken"):
                self.token = res.headers.get("apitoken")
                self.is_api = True
            elif res.headers.get("authtoken", ""):
                self.token = res.headers.get("authtoken")
                self.is_api = False
            self.remote_req_id = req_id
            logger.debug(
                f"SUCCESS --> {url}  req_id={req_id}  token={self.token} "
            )
            result = res.json()
            return result.copy()
        else:
            logger.warning(
                f"get_remote_object --> {url} ERROR {res.status_code} "
            )
            return {}

    async def get_remote_request(
            self, url, headers={}, params={}, cookies={}, use_app=True, service_url=False
    ):
        if use_app:
            headers = self.headers

        if service_url:
            url = f"{self.local_settings.service_url}{url}"

        logger.info(f"get_remote_request --> {url}")
        logger.info(f" request updated headers before  {headers}")
        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.get(
                url=requote_uri(url),
                params=params,
                headers=headers,
                cookies=cookies,
            )
        if res.status_code == 200:
            logger.debug(f"SUCCESS SIMPLE REMOTE REQUEST --> {url}")
            result = res.json()
            return result.copy()
        else:
            logger.warning(
                f"get_remote_request --> {url} ERROR {res.status_code} "
            )
            return {"status": "error", "msg": res.status_code}

    async def post_remote_object(
            self, url, data={}, headers={}, params={}, cookies={}
    ):
        logger.debug(url)
        if self.local_settings.service_url not in url:
            url = f"{self.local_settings.service_url}{url}"

        if "token" in params:
            cookies = {"authtoken": params.get("token")}
        if not cookies:
            cookies = self.request.cookies.copy()
        logger.debug(f"post_remote_object --> {url} ")
        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.post(
                url=requote_uri(url),
                json=data,
                params=params,
                headers=self.headers,
                cookies=cookies,
            )
        if res.status_code == 200:
            self.remote_req_id = res.headers.get("req_id")
            if res.headers.get("apitoken"):
                self.token = res.headers.get("apitoken")
                self.is_api = True
            elif res.headers.get("authtoken", ""):
                self.token = res.headers.get("authtoken")
                self.is_api = False
            logger.debug(
                f"SUCCESS --> {url} SUCCESS req_id={self.remote_req_id}  token {self.token} "
            )
            return res.json()
        else:
            logger.warning(
                f"post_remote_object --> {url} ERROR {res.status_code} "
            )
            return {"status": "error", "msg": f"{url} ERROR {res.status_code}"}

    async def post_remote_request(
            self, url, data={}, headers={}, params={}, cookies={}, use_app=True
    ):
        if use_app:
            headers = self.headers.copy()
        logger.debug(f"post_remote_request --> {url}")
        logger.debug(f" request headers   {headers}")
        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.post(
                url=requote_uri(url),
                json=data,
                params=params,
                headers=headers,
                cookies=cookies,
            )
        if res.status_code == 200:
            logger.debug(f"SUCCESS SIMPLE POST REMOTE REQUEST --> {url}")
            result = res.json()
            return result.copy()
        else:
            logger.warning(
                f"post_remote_request --> {url} ERROR {res.status_code} "
            )
            return {}

    async def delete_remote_object(
            self, url, data={}, headers={}, params={}, cookies={}
    ):
        logger.debug(f"delete_remote_object --> {url}")

        if self.local_settings.service_url not in url:
            url = f"{self.local_settings.service_url}{url}"

        if "token" in params:
            cookies = {"authtoken": params.get("token")}
        if not cookies:
            cookies = self.request.cookies.copy()

        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.post(
                url=requote_uri(url),
                json=data,
                params=params,
                headers=self.headers,
                cookies=cookies,
            )
        if res.status_code == 200:
            logger.info(f"delete_remote_object --> {url}  success")
            self.remote_req_id = res.headers.get("req_id")
            if res.headers.get("apitoken"):
                self.token = res.headers.get("apitoken")
                self.is_api = True
            elif res.headers.get("authtoken", ""):
                self.token = res.headers.get("authtoken")
                self.is_api = False
            logger.debug(
                f"SUCCESS --> {url} SUCCESS req_id={self.remote_req_id}  token {self.token} "
            )
            result = res.json()
            return result.copy()
        else:
            return {"status": "error", "msg": res.status_code}

    def deserialize_header_list(self):
        res = dict(self.request.headers)
        return res.copy()

    def deserialize_list_key_values(self, list_data):
        res = {item["name"]: item["value"] for item in list_data}
        return res

    async def empty_content_service(self):
        return ContentService.new(gateway=self, remote_data={})
