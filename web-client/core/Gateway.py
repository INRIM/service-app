# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import sys
from typing import Optional
from fastapi import FastAPI, Request, Header, HTTPException, Depends, Form
from fastapi.responses import RedirectResponse, JSONResponse
from .ContentService import ContentService
from .main.base.base_class import BaseClass, PluginBase
from .main.base.utils_for_service import requote_uri
from starlette.status import HTTP_302_FOUND, HTTP_303_SEE_OTHER
from fastapi.concurrency import run_in_threadpool
import httpx
import logging
import ujson
import re

logger = logging.getLogger(__name__)


class Gateway(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class GatewayBase(Gateway):
    @classmethod
    def create(cls, request: Request, settings, templates):
        self = GatewayBase()
        self.request = request
        self.remote_req_id = ""
        self.name_allowed = re.compile("^[A-Za-z0-9._~-]*$")
        self.local_settings = settings
        self.templates = templates
        self.session = {}
        self.token = ""
        self.is_api = False
        self.params = self.request.query_params.__dict__['_dict'].copy()
        self.headers = self.deserialize_header_list()
        self.cookies = self.request.cookies
        self.init_headers_and_token()
        return self

    def clean_form(self, form_data):
        # logger.info(f"before")
        dat = {}

        dat = ujson.loads(form_data['formObj'])
        for k, v in form_data.items():
            if not k == 'formObj':
                dat[k] = v
        return dat

    def init_headers_and_token(self):
        # logger.info(f"before")
        dat = {}

        if 'content-length' in self.headers:
            self.headers.pop("content-length")

        if "Content-Type" in self.headers:
            self.headers.pop('Content-Type')

        if "Cache-control" in self.headers:
            self.headers.pop('Cache-control')

        if "cache-control" in self.headers:
            self.headers.pop('cache-control')

        if "content-type" in self.headers:
            self.headers.pop('content-type')
        if "accept" in self.headers:
            self.headers.pop('accept')
        if "token" in self.params:
            self.token = self.params.get("token", "")

        base_url = str(self.request.base_url)[:-1]
        self.headers.update({
            "Content-Type": "application/json",
            "accept": "application/json",
            "app_code": self.local_settings.app_code,
            "referer": requote_uri(f"{base_url}{self.request.url.path}"),
            "base_url_ref": f"{base_url}",
            "req_id": self.request.headers.get("req_id", "")
        })

        if not self.token:
            if self.request.headers.get("authtoken"):
                self.token = self.request.headers.get("authtoken")
            elif self.request.headers.get("apitoken"):
                self.token = self.request.headers.get("apitoken")
                self.is_api = True

        # TODO move in shibboleth Gateway
        if "x-remote-user" not in self.request.headers:
            self.headers['x-remote-user'] = self.request.headers.get('x-remote-user', "")

        logger.info(f"complete token: {self.token} is Api {self.is_api}")

    async def load_post_request_data(self):
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
                    "model": ""
                }
                return await content_service.form_post_complete_response(err, None)
        if isinstance(submitted_data, dict):
            return submitted_data.copy()
        else:
            return submitted_data

    async def compute_datagrid_rows(self, key, model_name, rec_name=""):
        logger.info("compute_datagrid_rows")
        server_response = await self.get_record(model_name, rec_name=rec_name)
        self.session = await self.get_session()
        content_service = ContentService.new(gateway=self, remote_data=server_response.copy())
        res = await content_service.compute_datagrid_rows(key)
        return res

    async def compute_datagrid_add_row(self, key, num_rows, model_name, rec_name=""):
        logger.info("compute_datagrid_add_row")
        server_response = await self.get_record(model_name, rec_name=rec_name)
        self.session = await self.get_session()
        content_service = ContentService.new(gateway=self, remote_data=server_response.copy())
        res = await content_service.compute_datagrid_add_row(key, num_rows)
        return res

    async def content_service_from_record(self, model_name, rec_name=""):
        server_response = await self.get_record(model_name, rec_name=rec_name)
        self.session = await self.get_session()
        return ContentService.new(gateway=self, remote_data=server_response.copy())

    async def before_submit(self, data, is_create=False):
        return data.copy()

    async def server_post_action(self):
        logger.info(f"server_post_action {self.request.url}")
        params = self.params.copy()
        builder = params.get('builder')
        cookies = self.cookies
        # load request data
        submitted_data = await self.load_post_request_data()
        is_create = False
        # if submitted_data not dict is error then return
        if isinstance(submitted_data, JSONResponse):
            return submitted_data

        if builder:
            content_service = ContentService.new(gateway=self, remote_data={})
            self.session = await self.get_session()
            data = self.compute_builder_data(submitted_data)
        else:
            self.session = await self.get_session()
            # if "rec_name" in submitted_data and submitted_data.get("rec_name") or "/identity" in self.request.url.path:
            content_service = ContentService.new(gateway=self, remote_data={})
            # ------
            if "/identity" in self.request.url.path:
                model = submitted_data.get("data_model")
                schema = await self.get_schema(model)
                content = {
                    "content": {
                        "editable": True,
                        "model": model,
                        "schema": schema.copy(),
                        "data": {},
                    }
                }
            else:
                if "rec_name" in submitted_data:
                    allowed = self.name_allowed.match(submitted_data.get("rec_name"))
                    if not allowed:
                        logger.error(f"name {submitted_data.get('rec_name')}")

                        err = {
                            "status": "error",
                            "message": f"Errore nel campo name {submitted_data.get('rec_name')} caratteri non consentiti",
                            "model": submitted_data.get('data_model')
                        }
                        return await content_service.form_post_complete_response(err, None)
                content = await self.get_record(submitted_data.get('data_model'),
                                                submitted_data.get('rec_name', ""))

            is_create = False
            # TODO chek use remote data to eval is_create
            remote_data = content.get("content").get("data")
            if len(self.request.scope['path'].split("/")) < 4:
                is_create = True
            content_service = ContentService.new(gateway=self, remote_data=content.copy())
            data = await content_service.form_post_handler(submitted_data)
                # -------
            # else:
            #     content_service = ContentService.new(gateway=self, remote_data=submitted_data)
            #     data = submitted_data.copy()
            logger.info(f"submit on server data")
        data = await self.before_submit(data.copy(), is_create=is_create)
        data = await content_service.before_submit(data.copy(), is_create=is_create)
        url = f"{self.local_settings.service_url}{self.request.scope['path']}"

        server_response = await self.post_remote_object(url, data=data, params=params, cookies=cookies)

        if not builder:
            server_response = await content_service.after_form_post_handler(
                server_response, data, is_create=is_create
            )
        # logger.info(f"server_post_action result: {server_response}")
        resp = server_response.get("content")
        return await content_service.form_post_complete_response(resp, server_response)

    async def server_get_action(self, url_action="", modal=False):
        logger.info(f"server_get_action {self.request.url}")
        params = self.params.copy()
        cookies = self.cookies
        if not modal:
            url = f"{self.local_settings.service_url}{self.request.scope['path']}"
        else:
            url = f"{self.local_settings.service_url}{url_action}"

        server_response = await self.get_remote_object(url, params=params, cookies=cookies)

        if (
                server_response.get("action") or
                server_response.get("content").get("action") or
                server_response.get("content").get("reload")
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
                        url, headers=headers,
                        status_code=HTTP_303_SEE_OTHER
                    )
            else:
                return await self.complete_json_response(content)
        else:
            if not modal:
                self.session = await self.get_session(params=params)
                content_service = ContentService.new(gateway=self, remote_data=server_response.copy())
                response = await content_service.make_page()
            else:
                self.session = await self.get_session(params=params)
                content_service = ContentService.new(gateway=self, remote_data=server_response.copy())
                resp = await content_service.compute_form(modal=True)
                return await self.complete_json_response({"body": resp})
        return self.complete_response(response)

    async def get_session(self, params={}):
        url = f"{self.local_settings.service_url}/session"
        res = await self.get_remote_object(url, params=params)
        return res

    async def get_record(self, model, rec_name=""):
        url = f"{self.local_settings.service_url}/record/{model.strip()}"
        if rec_name.strip():
            url = f"{self.local_settings.service_url}/record/{model.strip()}/{rec_name.strip()}"
        res = await self.get_remote_object(url)
        return res

    async def get_schema(self, model):
        url = f"{self.local_settings.service_url}/schema/{model}"
        res = await self.get_remote_object(url)
        return res

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

    async def get_remote_data_select(self, url, path_value, header_key, header_value_key):
        """
        name is a model name
        """
        logger.info(f"get_remote_data_select ->for url:{url}")
        local_url = f"{self.local_settings.service_url}/get_remote_data_select"
        params = {
            "url": url,
            "path_value": path_value,
            "header_key": header_key,
            "header_value_key": header_value_key
        }
        res = await self.get_remote_object(local_url, params=params)
        data = res.get("content").get("data")
        logger.info(f"get_remote_data_select Response -> {type(data)}")
        return data

    async def get_resource_schema_select(self, type, select):
        """
        name is a model name
        """
        logger.info(f"get_resource_schema_select --> params: {type}, {select}")
        url = f"{self.local_settings.service_url}/resource/schema/select"
        res = await self.get_remote_object(url, params={"otype": type, "select": select})
        data = res.get("content").get("data")
        logger.info(f"get_resource_schema_select --> {data}")
        return data

    async def complete_json_response(self, res, orig_resp=None):
        response = JSONResponse(res)
        return self.complete_response(response)

    def complete_response(self, resp):
        resp.headers.append("req_id", self.remote_req_id or "")
        if '/logout/' not in self.request.scope['path']:
            if not self.is_api:
                resp.set_cookie('authtoken', value=self.token or "")
                resp.headers.append("authtoken", self.token or "")
            else:
                resp.headers.append("apitoken", self.token or "")
        if '/logout/' in self.request.scope['path']:
            resp.set_cookie('authtoken', value="")
            resp.headers.append("authtoken", "")
        return resp

    async def eval_headers(self, headers={}):
        orig_params = self.request.query_params.__dict__['_dict'].copy()

        if not self.remote_req_id:
            req_id = self.request.headers.get("req_id", "")
        else:
            req_id = self.remote_req_id

        headers['req_id'] = req_id

        if self.is_api:
            headers['apitoken'] = self.token
        else:
            headers['authtoken'] = self.token

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

        if not cookies:
            cookies = self.request.cookies.copy()

        logger.info(f" request headers   {headers}")
        logger.info(f"get_remote_object --> {url}")

        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.get(
                url=requote_uri(url), params=params, headers=self.headers, cookies=cookies
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
            logger.info(f"SUCCESS --> {url}  req_id={req_id}  token={self.token} ")
            result = res.json()
            return result.copy()
        else:
            logger.warning(f"get_remote_object --> {url} ERROR {res.status_code} ")
            return {}

    async def get_remote_request(
            self, url, headers={}, params={}, cookies={}, use_app=True):
        if use_app:
            headers = self.headers
        # else:
        #     headers = await self.eval_headers(headers, token=token, is_api=is_api)

        logger.info(f"get_remote_request --> {url}")
        logger.info(f" request updated headers before  {headers}")
        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.get(
                url=requote_uri(url), params=params, headers=headers, cookies=cookies
            )
        if res.status_code == 200:
            logger.info(f"SUCCESS SIMPLE REMOTE REQUEST --> {url}")
            result = res.json()
            return result.copy()
        else:
            logger.warning(f"get_remote_request --> {url} ERROR {res.status_code} ")
            return {"status": "error", "msg": res.status_code}

    async def post_remote_object(self, url, data={}, headers={}, params={}, cookies={}):
        if self.local_settings.service_url not in url:
            url = f"{self.local_settings.service_url}{url}"

        if "token" in params:
            cookies = {"authtoken": params.get("token")}
        if not cookies:
            cookies = self.request.cookies.copy()

        logger.info(f" request headers   {self.headers}")
        logger.info(f"post_remote_object --> {url}")
        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.post(
                url=requote_uri(url), json=ujson.dumps(data, escape_forward_slashes=False, ensure_ascii=False),
                params=params,
                headers=self.headers,
                cookies=cookies
            )
        if res.status_code == 200:
            self.remote_req_id = res.headers.get("req_id")
            if res.headers.get("apitoken"):
                self.token = res.headers.get("apitoken")
                self.is_api = True
            elif res.headers.get("authtoken", ""):
                self.token = res.headers.get("authtoken")
                self.is_api = False
            logger.info(f"SUCCESS --> {url} SUCCESS req_id={self.remote_req_id}  token {self.token} ")
            return res.json()
        else:
            return {}

    async def post_remote_request(
            self, url, data={}, headers={}, params={}, cookies={}, use_app=True):

        if use_app:
            headers = self.headers.copy()
        # else:
        #     headers = await self.eval_headers(headers, token=token, is_api=is_api)

        logger.info(f"post_remote_request --> {url}")
        logger.info(f" request headers   {headers}")
        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.post(
                url=requote_uri(url),
                json=data,
                params=params,
                headers=headers,
                cookies=cookies
            )
        if res.status_code == 200:
            logger.info(f"SUCCESS SIMPLE POST REMOTE REQUEST --> {url}")
            result = res.json()
            return result.copy()
        else:
            logger.warning(f"post_remote_request --> {url} ERROR {res.status_code} ")
            return {}

    async def delete_remote_object(self, url, data={}, headers={}, params={}, cookies={}):
        logger.info(f"delete_remote_object --> {url}")

        if self.local_settings.service_url not in url:
            url = f"{self.local_settings.service_url}{url}"

        if "token" in params:
            cookies = {"authtoken": params.get("token")}
        if not cookies:
            cookies = self.request.cookies.copy()

        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.post(
                url=requote_uri(url),
                json=ujson.dumps(data, escape_forward_slashes=False, ensure_ascii=False),
                params=params,
                headers=self.headers,
                cookies=cookies
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
            logger.info(f"SUCCESS --> {url} SUCCESS req_id={self.remote_req_id}  token {self.token} ")
            result = res.json()
            return result.copy()
        else:
            return {"status": "error", "msg": res.status_code}

    def deserialize_header_list(self):
        res = dict(self.request.headers)
        return res.copy()

    def deserialize_list_key_values(self, list_data):
        res = {item['name']: item['value'] for item in list_data}
        return res

    def compute_builder_data(self, list_data):
        res = {item['name']: item['value'] for item in list_data}
        if not "properties" in res:
            res['properties'] = {}
        data = self.compute_report_data(res.copy())
        data = self.compute_mail_setting(data.copy())
        return data

    def compute_report_data(self, data):
        if data.get("rheader"):
            data['properties']['rheader'] = data.get("rheader").rstrip()
            data.pop("rheader")
        if data.get("report"):
            data['properties']['report'] = data.get("report").rstrip()
            data.pop("report")
        if data.get("rfooter"):
            data['properties']['rfooter'] = data.get("rfooter").rstrip()
            data.pop("rfooter")
        return data

    def compute_mail_setting(self, data):
        if data.get("send_mail_create"):
            data['properties']['send_mail_create'] = data.get("send_mail_create").rstrip()
            data.pop("send_mail_create")
        if data.get("send_mail_update"):
            data['properties']['send_mail_update'] = data.get("send_mail_update").rstrip()
            data.pop("send_mail_update")
        return data

    async def empty_content_service(self):
        return ContentService.new(gateway=self, remote_data={})
