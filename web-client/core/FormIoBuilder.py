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
from .main.builder_custom import FormioBuilderFields
from fastapi.concurrency import run_in_threadpool
from copy import deepcopy

logger = logging.getLogger(__name__)


class FormIoBuilder(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        if cls not in cls.plugins:
            cls.plugins.append(cls())

    @classmethod
    def compute_builder_data(cls, list_data):
        res = {item['name']: item['value'] for item in list_data}
        if "properties" not in res:
            res['properties'] = {}
        data = cls.compute_report_data(res.copy())
        data = cls.compute_mail_setting(data.copy())
        data = cls.compute_logic_and_sort(data.copy())

        return data

    @classmethod
    def compute_report_data(cls, data):
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

    @classmethod
    def compute_mail_setting(cls, data):
        if data.get("send_mail_create"):
            data['properties']['send_mail_create'] = data.get("send_mail_create").rstrip()
            data.pop("send_mail_create")
        if data.get("send_mail_update"):
            data['properties']['send_mail_update'] = data.get("send_mail_update").rstrip()
            data.pop("send_mail_update")
        return data

    @classmethod
    def compute_logic_and_sort(cls, data):
        if data.get("form_disabled"):
            data['properties']['form_disabled'] = data.get("form_disabled").rstrip()
            data.pop("form_disabled")
        if data.get("no_submit"):
            data['properties']['no_submit'] = data.get("no_submit").rstrip()
            data.pop("no_submit")
        if data.get("sort"):
            data['properties']['sort'] = data.get("sort").rstrip()
            data.pop("sort")
        if data.get("query-form-editable"):
            data['properties']['queryformeditable'] = data.get("query-form-editable").rstrip()
            data.pop("query-form-editable")
        return data

class FormIoBuilderBase(FormIoBuilder):
    @classmethod
    def create(
            cls, request: Request, session: dict, settings, response: dict, templates, list_models, **kwargs):
        self = FormIoBuilderBase()
        self.resp = response
        self.content = response.get("content")
        self.list_models = list_models
        self.request = request
        self.local_settings = settings
        self.parent_model_components = {}
        self.theme = settings['theme']
        self.session = session
        self.templates = templates
        self.parent_model_schema = kwargs.get('parent_model_schema', {})
        self.builder = None
        return self
        # "/formio/builder_frame.html"

    async def form_builder(self):
        if not self.request.query_params.get("iframe"):
            content = await self.compute_formio_builder_container()
        else:
            content = await self.compute_formio_builder()
        return content

    def eval_parent_commponents(self):
        components = deepcopy(self.parent_model_schema.get("components"))
        fields_maker = FormioBuilderFields(components)
        fields_maker.load_components()
        self.parent_model_components = fields_maker.parent_model_components

    async def compute_formio_builder_container(self):
        logger.info("compute_formio_builder_container")
        page = PageWidget.create(
            templates_engine=self.templates, session=self.session,
            request=self.request,
            settings=self.session.get('app', {}).get("settings", self.local_settings).copy(),
            theme=self.theme, content=self.content)
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
        else:
            if self.parent_model_schema:
                self.eval_parent_commponents()

        page = FormIoBuilderWidget.new(
            templates_engine=self.templates, session=self.session,
            request=self.request,
            settings=self.session.get('app', {}).get("settings", self.local_settings).copy(),
            form_dict=schema.copy(),
            name=self.content.get("name"), title=self.content.get("title"),
            preview_link=self.content.get("preview_link"),
            page_api_action=self.content.get("page_api_action"),
            action_buttons=self.content.get("context_buttons"),
            list_models=self.list_models,
            parent_model_components=self.parent_model_components
        )
        # builder_tmp = f"{page.template_base_path}{form_component_map['formio_builder']}"
        builder_tmp = page.theme_cfg.get_template("template", 'formio_builder')
        return page.response_custom(builder_tmp, page.get_config())
