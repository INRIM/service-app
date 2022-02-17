# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import httpx
import logging
import ujson
import json
from fastapi.responses import RedirectResponse, FileResponse, StreamingResponse
from datetime import datetime, timedelta
from .main.base.base_class import BaseClass, PluginBase
from .main.widgets_table_export import TableWidgetExport
from fastapi.concurrency import run_in_threadpool
import logging

logger = logging.getLogger(__name__)


class ExportService(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        if cls not in cls.plugins:
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

    async def export_data(self, model, file_type, data, parent=""):
        logger.info(f"export_json_list {model}, {file_type}, {data['query']}")
        url = f"{self.local_settings.service_url}/export_data/{model}"

        self.session = await self.gateway.get_session()

        data['data_mode'] = 'json'
        if not file_type == 'json':
            data['data_mode'] = 'value'

        self.content_service = await self.gateway.post_remote_object(
            url, data, params={"parent": parent}
        )

        page_export = TableWidgetExport.new(
            templates_engine=self.templates, session=self.session,
            settings=self.session.get('app', {}).get("settings", self.local_settings.dict()).copy(),
            request=self.gateway.request, content=self.content_service.get('content').copy(),
            file_type=file_type
        )

        file_obj_response = await page_export.export_data()
        return file_obj_response
