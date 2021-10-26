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
from io import BytesIO
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

        schema_model = await self.gateway.get_remote_object(f"/schema_model/{data_model}")
        if not schema_model:
            return {"status": "error", "msg": "Errore nel Form"}
        model_fields_names = schema_model['fields']
        logger.info(model_fields_names)
        file_fields_names = [row['name'] for row in submit_data['fields']]
        if not all(item in model_fields_names for item in file_fields_names):
            return {
                "status": "error",
                "msg": "Impossibile importate il documento, i campi non coincidono, scaricare il templete e compilare"
            }

        for row in submit_data['data']:
            import_data = await self.form_post_handler(row)
            url = f"/import/{data_model}"
            server_response = await self.gateway.post_remote_object(
                url, headers=headers, data=import_data, params=params, cookies=cookies)
            if "error" in server_response.get('status', ""):
                res_err.append(server_response)
            else:
                res_ok.append(server_response)

        response_import = {
            "status": "done",
            "ok": len(res_ok),
            "error": len(res_err),
            "error_list": res_err[:]
        }
        return response_import.copy()

    async def template_xls(self, data_model, with_data=False):
        logger.info("template Xls")
        dt_report = datetime.now().strftime(
            self.gateway.local_settings.server_datetime_mask
        )
        schema_model = await self.gateway.get_remote_object(f"/schema_model/{data_model}")
        if not schema_model:
            return {"status": "error", "msg": "Errore nel Form"}
        model_fields_names = schema_model['fields']
        data = {}
        if with_data:
            data_res = await self.gateway.get_remote_object(
                f"/resource/data/{data_model}?fields={','.join(model_fields_names)}")
            data = data_res.get("content", {}).get("data", {})
        file_name = f"{data_model}_{dt_report}.xlsx"
        df = pd.DataFrame(data, columns=model_fields_names)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer) as writer:
            df.to_excel(writer, header=model_fields_names, index=False)
        buffer.seek(0)

        headers = {
            'Content-Disposition': f'attachment; filename="{file_name}"'
        }
        return StreamingResponse(buffer, headers=headers)
