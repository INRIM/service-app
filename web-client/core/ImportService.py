# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import httpx
import logging
import ujson
import json
from fastapi.responses import RedirectResponse, FileResponse, StreamingResponse
from datetime import datetime, timedelta
from .main.base.base_class import BaseClass, PluginBase
from .MailService import MailService
import shutil
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from .main.widgets_content import PageWidget
from jinja2 import Template
import pandas as pd

import logging

logger = logging.getLogger(__name__)


class ImportService(MailService):

    @classmethod
    def create(cls, gateway, remote_data):
        self = ImportService()
        self.init(gateway, remote_data)
        return self

    async def import_data(self, data_model, submit_data):
        logger.info(f" {data_model}")
        res_err = []
        res_ok = []
        params = {}
        headers = self.gateway.deserialize_header_list()
        cookies = self.request.cookies
        for row in submit_data:
            import_data = await self.form_post_handler(row)
            url = f"/import/{data_model}"
            server_response = await self.gateway.post_remote_object(
                url, headers=headers, data=import_data, params=params, cookies=cookies)
            if "error" in server_response.get('status', ""):
                res_err.append(server_response)
            else:
                res_ok.append(server_response)

        response_import = {
            "ok": len(res_ok),
            "error": len(res_err),
            "error_list": res_err[:]
        }
        return response_import.copy()
    # import
    # model_schema = remote.service_get_schema_model()
    # fields = {k: model_schema['properties'][k]['type'] for k, v in model_schema['properties'].items()}
    # each row -> data = form_post_handler
    #
