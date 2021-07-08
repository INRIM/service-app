import httpx
import logging
import ujson
import json
import pandas
from fastapi.responses import RedirectResponse, FileResponse, StreamingResponse
from datetime import datetime, timedelta
from .main.base.base_class import BaseClass, PluginBase
import aiofiles
import logging
from io import BytesIO
from collections import OrderedDict
import xlsxwriter

logger = logging.getLogger(__name__)


class ExportService(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class ExportServiceBase(ExportService):

    @classmethod
    def create(cls, gateway):
        self = ExportServiceBase()
        self.gateway = gateway
        self.request = gateway.request
        self.local_settings = gateway.local_settings
        self.templates = gateway.templates
        self.session = gateway.session
        return self

    async def export_file(self, model, file_type, data, parent=""):
        logger.info(f"export_json_list {model}, {file_type}, {data['query']}")
        url = f"{self.local_settings.service_url}/export_data/{model}"
        self.content_service = await self.gateway.post_remote_object(
            url, data['query'], {"parent": parent}
        )
        file_obj_response = await getattr(self, f"export_{file_type}")(model)
        return file_obj_response

    async def export_json(self, model_name):
        dict_data = self.content_service.get('content').get('data')
        dt_report = datetime.now().strftime(
            self.local_settings.server_datetime_mask
        )
        file_name = f"/tmp/{model_name}_{dt_report}.json"
        output = BytesIO()
        data = ujson.dumps(dict_data, escape_forward_slashes=False, ensure_ascii=False)
        # data = json.dumps(dict_data)
        output.write(data.encode('utf-8'))
        output.seek(0)
        headers = {
            'Content-Disposition': f'attachment; filename="{file_name}"',
        }
        logger.info(f"Make Export file Done: {file_name}")
        return StreamingResponse(output, headers=headers, media_type='text/plain')

    async def export_xls(self, model_name):
        dt_report = datetime.now().strftime(
            self.local_settings.server_datetime_mask
        )
        file_name = f"/tmp/{model_name}_{dt_report}.xlsx"
        dict_data = self.content_service.get('content').get('data')
        output = BytesIO()
        wb = xlsxwriter.Workbook(output)
        ws = wb.add_worksheet(model_name)
        self.json_to_excel(ws, dict_data)
        wb.close()
        output.seek(0)

        headers = {
            'Content-Disposition': f'attachment; filename="{file_name}"'
        }
        return StreamingResponse(output, headers=headers)

    def json_to_excel(self, ws, data, row=0, col=0):
        if isinstance(data, list):
            row -= 1
            for value in data:
                row = self.json_to_excel(ws, value, row + 1, col)
        elif isinstance(data, dict):
            max_row = row
            start_row = row
            for key, value in data.items():
                row = start_row
                ws.write(row, col, key)
                row = self.json_to_excel(ws, value, row + 1, col)
                max_row = max(max_row, row)
                col += 1
            row = max_row
        else:
            ws.write(row, col, data)

        return row
