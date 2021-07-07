import httpx
import logging
import ujson
import pandas
from fastapi.responses import RedirectResponse, FileResponse
from datetime import datetime, timedelta
from .main.base.base_class import BaseClass, PluginBase


class ExportService(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class ExportServiceBase(ExportService):

    @classmethod
    async def create(cls, gateway):
        self = ExportServiceBase()
        self.gateway = gateway
        self.request = gateway.request
        self.local_settings = gateway.local_settings
        self.templates = gateway.templates
        self.session = gateway.session
        return self

    async def export_json_list(self, remote_data):
        logger.info("export_json_list")
        # get_layout
        # route form or table
        # add layout
        # render layout

        if self.content.get("builder") and self.content.get('mode') == "form":
            logger.info("FormIoBuilder")
            form_builder = FormIoBuilder.new(
                request=self.request, session=self.session, settings=self.local_settings, response=self.remote_data,
                templates=self.templates
            )
            content = await form_builder.form_builder()
            if self.request.query_params.get("iframe"):
                return content
        else:
            logger.info("Make Page Builder??")
            content = await getattr(self, f"compute_{self.content.get('mode')}")()

        self.layout = await self.get_layout()
        # if not self.content.get("builder"):
        self.layout.make_context_button(self.content)
        self.layout.rows.append(content)
        logger.info("Make Page Done")
        return self.layout.render_layout()