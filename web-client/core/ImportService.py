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
from fastapi.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)
default_list_metadata_fields = [
    "id",
    "owner_name",
    "owner_sector",
    "owner_sector_id",
    "owner_function",
    "update_datetime",
    "create_datetime",
    "owner_mail",
    "update_uid",
    "owner_function_type",
    "sys",
    "demo",
    "deleted",
    "list_order",
    "owner_personal_type",
    "owner_job_title",
]


# https://github.com/TonyGermaneri/canvas-datagrid


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
        self.session = await self.gateway.get_session()

        schema_model = await self.gateway.get_remote_object(
            f"/schema_model/{data_model}"
        )
        if not schema_model:
            return {"status": "error", "msg": "Errore nel Form"}
        model_fields_names = schema_model["fields"]
        file_fields_names = [row["name"] for row in submit_data["fields"]]
        fields_names = file_fields_names + default_list_metadata_fields
        if not all(item in fields_names for item in file_fields_names):
            return {
                "status": "error",
                "msg": "Impossibile importate il documento, i campi non coincidono, scaricare il templete e compilare",
            }

        schama = schema_model["schema"]
        field_types = {
            k: schama["properties"][k]["type"]
            for k, v in schama["properties"].items()
        }
        typesd = {
            "array": list,
            "object": dict,
        }
        delete_before = submit_data.get("delete_before")
        if delete_before:
            server_response = await self.gateway.post_remote_object(
                f"/import/clean/{data_model}", data={}
            )
            if "error" in server_response.get("status", ""):
                return {
                    "status": "done",
                    "ok": 0,
                    "error": "<br/>".join([server_response]),
                    "error_list": [server_response]
                }
        for row in submit_data["data"]:
            row_data = {}
            for k, v in row.items():
                if (
                    field_types[k] in typesd
                    and not type(v) == typesd[field_types[k]]
                ):
                    row_data[k] = eval(v)
                else:
                    row_data[k] = v
            status = True
            if data_model == "component":
                import_data = row_data.copy()
            else:
                status, import_data = await self.form_post_handler(row_data)
            if status:
                server_response = await self.gateway.post_remote_object(
                    f"/import/{data_model}", data=import_data
                )

                if "error" in server_response.get('status', ""):
                    err_msg = f"Record:{row_data.get('rec_name')}, " \
                              f"msg: {server_response.get('message')}"
                    res_err.append(err_msg)
                    logger.error(err_msg)
                else:
                    res_ok.append(server_response)
            else:
                res_err.append(row_data)

        response_import = {
            "status": "done",
            "ok": len(res_ok),
            "error": "<br/>".join(res_err),
            "error_list": res_err[:]
        }
        return response_import.copy()

    async def template_xls(self, data_model, with_data=False):
        logger.info("template Xls")
        dt_report = datetime.now().strftime(
            self.gateway.local_settings.server_datetime_mask
        )
        schema_model = await self.gateway.get_remote_object(
            f"/schema_model/{data_model}"
        )
        if not schema_model:
            return {"status": "error", "msg": "Errore nel Form"}
        model_fields_names = schema_model["fields"]
        model_fields_names.append("owner_uid")
        data = {}
        if with_data:
            data_res = await self.gateway.get_remote_object(
                f"/resource/data/{data_model}?fields={','.join(model_fields_names)}"
            )
            data = data_res.get("content", {}).get("data", {})
        file_name = f"{data_model}_{dt_report}.xlsx"
        df = pd.DataFrame(data, columns=model_fields_names)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer) as writer:
            df.to_excel(writer, header=model_fields_names, index=False)
        buffer.seek(0)

        headers = {
            "Content-Disposition": f'attachment; filename="{file_name}"'
        }
        return StreamingResponse(buffer, headers=headers)
