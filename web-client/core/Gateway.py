# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import sys
from typing import Optional

from fastapi import FastAPI, Request, Header, HTTPException, Depends, Form
from fastapi.responses import RedirectResponse, JSONResponse
from .ContentService import ContentService
import httpx
from requests.utils import requote_uri
import logging
import ujson
import re
from .main.base.base_class import BaseClass, PluginBase
from starlette.status import HTTP_302_FOUND, HTTP_303_SEE_OTHER

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
        self.token = ""
        self.name_allowed = re.compile("^[A-Za-z0-9._~-]*$")
        self.local_settings = settings
        self.templates = templates
        self.session = {}
        return self

    def clean_form(self, form_data):
        # logger.info(f"before")
        dat = {}

        dat = ujson.loads(form_data['formObj'])
        for k, v in form_data.items():
            if not k == 'formObj':
                dat[k] = v
        return dat

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

    async def server_post_action(self):
        logger.info(f"server_post_action {self.request.url}")
        params = self.request.query_params.__dict__['_dict'].copy()
        headers = self.deserialize_header_list()
        headers.pop("content-length")
        cookies = self.request.cookies
        builder = params.get('builder')
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
            if "rec_name" in submitted_data and submitted_data.get("rec_name"):
                content_service = ContentService.new(gateway=self, remote_data={})
                allowed = self.name_allowed.match(submitted_data.get("rec_name"))
                if not allowed:
                    logger.error(f"name {submitted_data.get('rec_name')}")

                    err = {
                        "status": "error",
                        "message": f"Errore nel campo name {submitted_data.get('rec_name')} caratteri non consentiti",
                        "model": submitted_data.get('data_model')
                    }
                    return await content_service.form_post_complete_response(err, None)

            contet = await self.get_record(submitted_data.get('data_model'), submitted_data.get('rec_name', ""))
            is_create = False
            remote_data = contet.get("content").get("data")
            if len(self.request.scope['path'].split("/")) < 4:
                is_create = True
            content_service = ContentService.new(gateway=self, remote_data=contet.copy())
            data = await content_service.form_post_handler(submitted_data)
            logger.info(f"submit on server data")
        url = f"{self.local_settings.service_url}{self.request.scope['path']}"
        server_response = await self.post_remote_object(
            url, headers=headers, data=data, params=params, cookies=cookies)
        if not builder:
            server_response = await content_service.after_form_post_handler(
                server_response, data, is_create=is_create
            )
        # logger.info(f"server_post_action result: {server_response}")
        resp = server_response.get("content")
        return await content_service.form_post_complete_response(resp, server_response)

    async def server_get_action(self, url_action="", modal=False):
        logger.info(f"server_get_action {self.request.url}, \n headers: {self.request.headers}")
        params = self.request.query_params.__dict__['_dict'].copy()
        headers = self.deserialize_header_list()
        cookies = self.request.cookies
        if not modal:
            url = f"{self.local_settings.service_url}{self.request.scope['path']}"
        else:
            url = f"{self.local_settings.service_url}{url_action}"

        server_response = await self.get_remote_object(
            url, headers=headers, params=params, cookies=cookies)

        if (
                server_response.get("action") or
                server_response.get("content").get("action") or
                server_response.get("content").get("reload")
        ):
            content = server_response
            if "content" in server_response:
                content = server_response.get("content")
            if not modal:
                if content.get("action") == "redirect":
                    content_length = str(0)
                    headers = self.deserialize_header_list()
                    headers["content-length"] = content_length
                    headers["authtoken"] = self.token
                    response = RedirectResponse(
                        content.get("url"), headers=headers,
                        status_code=HTTP_303_SEE_OTHER
                    )
                    # response = self.complete_response(resp)
                if content.get("link"):
                    content_length = str(0)
                    headers = self.deserialize_header_list()
                    headers["content-length"] = content_length
                    headers["authtoken"]= self.token
                    response = RedirectResponse(
                        content.get("link"), headers=headers,
                        status_code=HTTP_303_SEE_OTHER
                    )
                    # response = self.complete_response(resp)
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
        headers = {
            "referer": self.request.url.path
        }
        url = f"{self.local_settings.service_url}/session"
        res = await self.get_remote_object(url, headers=headers, params=params)
        return res

    async def get_record(self, model, rec_name=""):
        headers = {
            "referer": self.request.url.path
        }
        url = f"{self.local_settings.service_url}/record/{model.strip()}/{rec_name.strip()}"
        res = await self.get_remote_object(url, headers=headers)
        return res

    async def get_schema(self, model):
        headers = {
            "referer": self.request.url.path
        }
        url = f"{self.local_settings.service_url}/schema/{model}"
        res = await self.get_remote_object(url, headers=headers)
        return res

    async def get_ext_submission(self, name):
        """
        name is a model name
        """
        logger.info(f"get_ext_submission -> {name}")
        headers = {
            "referer": self.request.url.path
        }
        url = f"{self.local_settings.service_url}/resource/data/{name}"
        res = await self.get_remote_object(url, headers=headers)
        data = res.get("content").get("data")[:]
        logger.info(f"get_ext_submission Response -> {len(data)}")
        return data

    async def get_remote_data_select(self, url, path_value, header_key, header_value_key):
        """
        name is a model name
        """
        logger.info(f"get_remote_data_select ->for url:{url}")
        headers = {
            "referer": self.request.url.path
        }
        local_url = f"{self.local_settings.service_url}/get_remote_data_select"
        params = {
            "url": url,
            "path_value": path_value,
            "header_key": header_key,
            "header_value_key": header_value_key
        }
        res = await self.get_remote_object(local_url, headers=headers, params=params)
        data = res.get("content").get("data")
        logger.info(f"get_remote_data_select Response -> {type(data)}")
        return data

    async def get_resource_schema_select(self, type, select):
        """
        name is a model name
        """
        logger.info(f"get_resource_schema_select --> params: {type}, {select}")
        headers = {
            "referer": self.request.url.path
        }
        url = f"{self.local_settings.service_url}/resource/schema/select"
        res = await self.get_remote_object(url, headers=headers, params={"otype": type, "select": select})
        data = res.get("content").get("data")
        logger.info(f"get_resource_schema_select --> {data}")
        return data

    async def complete_json_response(self, res, orig_resp=None):
        response = JSONResponse(res)
        return self.complete_response(response)

    def complete_response(self, resp):
        resp.headers.append("req_id", self.remote_req_id or "")
        if '/logout/' not in self.request.scope['path']:
            resp.set_cookie('authtoken', value=self.token)
            resp.headers.append("authtoken", self.token or "")
        if '/logout/' in self.request.scope['path']:
            resp.set_cookie('authtoken', value="")
            resp.headers.append("authtoken", "")
        return resp

    async def get_remote_object(self, url, headers={}, params={}, cookies={}):
        orig_params = self.request.query_params.__dict__['_dict'].copy()
        logger.info(f" request headers before  {headers}")
        if self.local_settings.service_url not in url:
            url = f"{self.local_settings.service_url}{url}"
        if not self.remote_req_id:
            req_id = self.request.headers.get("req_id", "")
        else:
            req_id = self.remote_req_id

        if not self.token:
            token = self.request.headers.get("authtoken", "")
        else:
            token = self.token

        if "token" in params:
            cookies = {"authtoken": params.get("token")}
            headers['authtoken'] = params.get("token")
        elif not cookies:
            cookies = self.request.cookies.copy()

        logger.info(f"get_remote_object --> {url}, req_id={req_id}, token={token}")

        if not cookies:
            cookies = self.request.cookies.copy()

        base_url = str(self.request.base_url)[:-1]
        headers.update({
            "Content-Type": "application/json",
            "authtoken": token,
            "req_id": req_id,
            "referer": requote_uri(f"{base_url}{self.request.url.path}"),
            "base_url_ref": f"{base_url}"
        })
        logger.info(f" request updated headers before  {headers}")
        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.get(
                url=requote_uri(url), params=params, headers=headers, cookies=cookies
            )
        if res.status_code == 200:
            req_id = res.headers.get("req_id")
            self.token = res.headers.get("authtoken")
            self.remote_req_id = req_id
            logger.info(f"SUCCESS --> {url}  req_id={req_id}  token={self.token} ")
            result = res.json()
            return result.copy()
        else:
            logger.info(f"get_remote_object --> {url} ERROR {res.status_code} ")
            return {}

    async def post_remote_object(self, url, data={}, headers={}, params={}, cookies={}):
        if self.local_settings.service_url not in url:
            url = f"{self.local_settings.service_url}{url}"
        if not self.remote_req_id:
            req_id = self.request.headers.get("req_id", "")
        else:
            req_id = self.remote_req_id
        if not self.token:
            token = self.request.headers.get("authtoken", "")
        else:
            token = self.token
        logger.info(f"post_remote_object --> {url}, req_id={req_id}, token={self.token}")
        if "token" in params:
            cookies = {"authtoken": params.get("token")}
            headers['authtoken'] = params.get("token")
        elif not cookies:
            cookies = self.request.cookies.copy()
        base_url = str(self.request.base_url)[:-1]
        headers.update({
            "Content-Type": "application/json",
            "authtoken": token,
            "req_id": req_id,
            "referer": requote_uri(f"{base_url}{self.request.url.path}"),
            "base_url_ref": f"{base_url}"
        })
        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.post(
                url=requote_uri(url), json=ujson.dumps(data, escape_forward_slashes=False, ensure_ascii=False),
                params=params,
                headers=headers,
                cookies=cookies
            )
        if res.status_code == 200:
            self.remote_req_id = res.headers.get("req_id")
            self.token = res.headers.get("authtoken")
            logger.info(f"SUCCESS --> {url} SUCCESS req_id={self.remote_req_id}  token {self.token} ")
            return res.json()
        else:
            return {}

    async def delete_remote_object(self, url, data={}, headers={}, params={}, cookies={}):
        logger.info(f"delete_remote_object --> {url}")
        if not self.remote_req_id:
            req_id = self.request.headers.get("req_id", "")
        else:
            req_id = self.remote_req_id
        if not self.token:
            token = self.request.headers.get("authtoken", "")
        else:
            token = self.token
        logger.info(f"delete_remote_object --> {url}, req_id={req_id}")
        if not cookies:
            cookies = self.request.cookies.copy()
        base_url = str(self.request.base_url)[:-1]
        headers.update({
            "Content-Type": "application/json",
            "authtoken": token,
            "req_id": req_id,
            "referer": requote_uri(f"{base_url}{self.request.url.path}"),
            "base_url_ref": f"{base_url}"
        })
        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.post(
                url=requote_uri(url), json=ujson.dumps(data, escape_forward_slashes=False, ensure_ascii=False),
                params=params,
                headers=headers,
                cookies=cookies
            )
        if res.status_code == 200:
            logger.info(f"get_remote_object --> {url}  success")
            self.remote_req_id = res.headers.get("req_id")
            self.token = res.headers.get("authtoken")
            logger.info(f"SUCCESS --> {url} SUCCESS req_id={self.remote_req_id}  token {self.token} ")
            result = res.json()
            return result.copy()
        else:
            return {}

    def deserialize_header_list(self):
        # list_data = self.request.headers.mutablecopy().__dict__['_list']
        res = dict(self.request.headers)
        # res = {item[0]: item[1] for item in list_data}
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
