# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import sys
from typing import Optional

import requests

from fastapi import FastAPI, Request, Header, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import httpx
import logging
import ujson

from .main.widgets_table_form import TableFormWidget
from .main.widgets_table import TableWidget
from .main.widgets_form import FormIoWidget
from .main.widgets_content import PageWidget
from .main.widgets_form_builder import FormIoBuilderWidget
from .main.widgets_layout import LayoutWidget
from .main.base.basicmodel import *
from .main.base.base_class import BaseClass, PluginBase
from .main.base.utils_for_service import *
from fastapi.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)


class FormIoBuilder(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class FormIoBuilderBase(FormIoBuilder):
    @classmethod
    def create(cls, request: Request, session: dict, settings, response: dict, templates):
        self = FormIoBuilderBase()
        self.resp = response
        self.content = response.get("content")
        self.request = request
        self.local_settings = settings
        self.theme = settings.theme
        self.session = session
        self.templates = templates
        self.builder = None
        return self
        # "/formio/builder_frame.html"

    async def form_builder(self):
        if not self.request.query_params.get("iframe"):
            content = await self.compute_formio_builder_container()
        else:
            content = await self.compute_formio_builder()
        return content

    async def compute_formio_builder_container(self):
        logger.info("compute_formio_builder_container")
        page = PageWidget.create(
            templates_engine=self.templates, session=self.session,
            request=self.request, settings=self.session['app']['settings'], theme=self.theme, content=self.content)
        template_formio_builder_container = page.theme_cfg.get_template("template", 'formio_builder_container')
        block = page.render_custom(template_formio_builder_container, self.content)
        return block

    async def compute_formio_builder(self):
        logger.info("Compute form builder")
        schema = self.content.get("data")
        if not schema:
            schema = {
                'type': self.content.get('component_type')
            }
        component = Component(**schema)
        page = FormIoBuilderWidget.new(
            templates_engine=self.templates, session=self.session,
            request=self.request, settings=self.session['app']['settings'], form_object=component,
            name=self.content.get("name"), title=self.content.get("title"),
            preview_link=self.content.get("preview_link"),
            page_api_action=self.content.get("page_api_action"),
            action_buttons=self.content.get("context_buttons")
        )
        # builder_tmp = f"{page.template_base_path}{form_component_map['formio_builder']}"
        builder_tmp = page.theme_cfg.get_template("template", 'formio_builder')
        return page.response_custom(builder_tmp, page.get_config())
