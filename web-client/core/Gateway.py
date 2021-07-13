# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
import sys
from typing import Optional

import requests

from fastapi import FastAPI, Request, Header, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from .ContentService import ContentService
import httpx
import logging
import ujson
from .main.base.base_class import BaseClass, PluginBase

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
        self.local_settings = settings
        self.templates = templates
        self.session = {}
        return self

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
        # headers.pop("content-length")
        cookies = self.request.cookies
        builder = params.get('builder')
        if builder:
            submitted_data = await self.request.json()
            data = self.compute_builder_data(submitted_data)
            content_service = ContentService.new(gateway=self, remote_data={})

        else:
            self.session = await self.get_session()
            submitted_data = await self.request.json()
            contet = await self.get_record(submitted_data.get('data_model'))

            content_service = ContentService.new(gateway=self, remote_data=contet.copy())
            data = await content_service.form_post_handler(submitted_data)

        url = f"{self.local_settings.service_url}{self.request.scope['path']}"
        server_response = await self.post_remote_object(
            url, headers=headers, data=data, params=params, cookies=cookies)

        # logger.info(f"server_post_action result: {server_response}")
        resp = server_response.get("content")

        return await content_service.form_post_complete_response(resp, server_response)

    async def server_get_action(self):
        logger.info(f"server_get_action {self.request.url}")
        params = self.request.query_params.__dict__['_dict'].copy()
        headers = self.deserialize_header_list()
        cookies = self.request.cookies
        url = f"{self.local_settings.service_url}{self.request.scope['path']}"

        server_response = await self.get_remote_object(
            url, headers=headers, params=params, cookies=cookies)

        if server_response.get("action") or server_response.get("content").get("action"):
            content = server_response
            if "content" in server_response:
                content = server_response.get("content")

            if content.get("action") == "redirect":
                content_length = str(0)
                headers = self.deserialize_header_list()
                headers["content-length"] = content_length
                response = RedirectResponse(
                    content.get("url"), headers=headers
                )
        else:
            self.session = await self.get_session(params=params)
            content_service = ContentService.new(gateway=self, remote_data=server_response.copy())
            response = await content_service.make_page()

        if "token" in params and response:
            response.set_cookie('authtoken', value=params.get("token"))
            response.headers['apitoken'] = params.get("token")
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
        url = f"{self.local_settings.service_url}/record/{model}/{rec_name}"
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
        if '/login' in self.request.scope['path']:
            response.headers.append("cookie", f"authtoken={self.token}")
        return self.complete_response(response)

    def complete_response(self, resp):
        resp.headers.append("req_id", self.remote_req_id or "")
        return resp

    async def get_remote_object(self, url, headers={}, params={}, cookies={}):
        orig_params = self.request.query_params.__dict__['_dict'].copy()
        if not self.remote_req_id:
            req_id = self.request.headers.get("req_id", "")
        else:
            req_id = self.remote_req_id

        logger.info(f"get_remote_object --> {url}, req_id={req_id}")
        if "token" in orig_params:
            cookies = {"authtoken": params.get("token")}
            headers['apitoken'] = params.get("token")
            params.update(orig_params)
        elif not cookies:
            cookies = self.request.cookies.copy()

        base_url = str(self.request.base_url)[:-1]
        headers.update({
            "Content-Type": "application/json",
            "apitoken": self.request.cookies.get("authtoken", ""),
            "req_id": req_id,
            "referer": f"{base_url}{self.request.url.path}",
            "base_url_ref": f"{base_url}"
        })

        async with httpx.AsyncClient() as client:
            res = await client.get(
                url=url, params=params, headers=headers, cookies=cookies
            )
        if res.status_code == 200:
            req_id = res.headers.get("req_id")
            logger.info(f"get_remote_object --> {url} SUCCESS req_id={req_id}  ")
            self.remote_req_id = req_id
            result = res.json()
            return result.copy()
        else:
            logger.info(f"get_remote_object --> {url} ERROR {res.status_code} ")
            return {}

    async def post_remote_object(self, url, data={}, headers={}, params={}, cookies={}):
        logger.info(f"post_remote_object --> {url}")
        if not self.remote_req_id:
            req_id = self.request.headers.get("req_id", "")
        else:
            req_id = self.remote_req_id
        logger.info(f"post_remote_object --> {url}, req_id={req_id}")
        if "token" in params:
            cookies = {"authtoken": params.get("token")}
            headers['apitoken'] = params.get("token")
        elif not cookies:
            cookies = self.request.cookies.copy()
        base_url = str(self.request.base_url)[:-1]
        headers.update({
            "Content-Type": "application/json",
            "apitoken": self.request.cookies.get("authtoken", ""),
            "req_id": req_id,
            "referer": f"{base_url}{self.request.url.path}",
            "base_url_ref": f"{base_url}"
        })
        async with httpx.AsyncClient() as client:
            res = await client.post(
                url=url, json=ujson.dumps(data, escape_forward_slashes=False, ensure_ascii=False), params=params,
                headers=headers,
                cookies=cookies
            )
        if res.status_code == 200:
            logger.info(f"post_remote_object --> {url}  success")
            self.remote_req_id = res.headers.get("req_id")
            if "/login" in url:
                self.token = res.cookies.get('authtoken')
                logger.info(f"post_remote_object --> {url}  success cookie {res.cookies}")
            return res.json()
        else:
            return {}

    async def delete_remote_object(self, url, data={}, headers={}, params={}, cookies={}):
        logger.info(f"delete_remote_object --> {url}")
        if not self.remote_req_id:
            req_id = self.request.headers.get("req_id", "")
        else:
            req_id = self.remote_req_id
        logger.info(f"delete_remote_object --> {url}, req_id={req_id}")
        if not cookies:
            cookies = self.request.cookies.copy()
        base_url = str(self.request.base_url)[:-1]
        headers.update({
            "Content-Type": "application/json",
            "apitoken": self.request.cookies.get("authtoken", ""),
            "req_id": req_id,
            "referer": f"{base_url}{self.request.url.path}",
            "base_url_ref": f"{base_url}"
        })
        async with httpx.AsyncClient() as client:
            res = await client.post(
                url=url, json=ujson.dumps(data, escape_forward_slashes=False, ensure_ascii=False), params=params,
                headers=headers,
                cookies=cookies
            )
        if res.status_code == 200:
            logger.info(f"get_remote_object --> {url}  success")
            self.remote_req_id = res.headers.get("req_id")
            result = res.json()
            return result.copy()
        else:
            return {}

    def deserialize_header_list(self):
        # list_data = self.request.headers.mutablecopy().__dict__['_list']
        list_data = self.request.headers.mutablecopy()
        res = {item[0]: item[1] for item in list_data}
        return res.copy()

    def deserialize_list_key_values(self, list_data):
        res = {item['name']: item['value'] for item in list_data}
        return res

    def compute_builder_data(self, list_data):
        res = {item['name']: item['value'] for item in list_data}
        if not "properties" in res:
            res['properties'] = {}
        data = self.compute_report_data(res.copy())
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

    async def empty_content_service(self):
        return ContentService.new(gateway=self, remote_data={})
