# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import sys
from copy import deepcopy
import logging
import ujson
from fastapi.templating import Jinja2Templates

from .widgets_content import PageWidget
from .base.base_class import PluginBase

logger = logging.getLogger(__name__)


class FormIoBuilderWidget(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class FormIoBuilderWidgetBase(FormIoBuilderWidget, PageWidget):

    @classmethod
    def create(
            cls, templates_engine, session, request, settings, theme="italia", disabled=False, form_dict=None,
            **kwargs
    ):
        # super().__init__(templates_engine, session, request, settings, schema={}, disabled=disabled, **kwargs)
        self = FormIoBuilderWidgetBase()
        self.init(templates_engine, session, request, settings, theme, **kwargs)
        self.form_dict = form_dict.copy()
        self.components = form_dict.get('components', [])
        self.is_create = False
        create_datetime = form_dict.get("create_datetime", None) is None
        update_datetime = form_dict.get("update_datetime", None) is None
        if create_datetime is None and update_datetime is None:
            self.is_create = True
        return self
        # self.form_id = form_dict.id
        # self.custom_components = kwargs.get('custom_components', custom_builder_oject)

    def init(self, templates_engine: Jinja2Templates, session: dict, request, settings, theme="italia", **kwargs):
        super().init(templates_engine, session, request, settings, theme=theme, **kwargs)
        self.cls_title = " text-center "
        self.api_action = "/"
        self.action_buttons = kwargs.get('action_buttons', "/")
        self.base_form_url = kwargs.get('base_form_url', "/")
        self.preview_link = kwargs.get('preview_link', "/")
        self.parent_model_components = kwargs.get('parent_model_components', {})
        self.models = kwargs.get('list_models', [])

        self.curr_row = []
        self.submission_id = ""
        self.form_name = ""

    def builder_components(self):
        return self.theme_cfg.custom_builder_oject.copy()

    def get_config(self, **context):
        cfg = {}
        cfg["request"] = self.request
        cfg['base_form_url'] = self.base_form_url
        cfg['action_buttons'] = self.action_buttons
        cfg['preview_link'] = self.preview_link
        cfg['components'] = ujson.dumps(self.components, escape_forward_slashes=False, ensure_ascii=False)
        cfg['rec_name'] = self.form_dict.get('rec_name', "")
        cfg['deleted'] = self.form_dict.get('deleted', 0)
        cfg['data_model'] = self.form_dict.get('data_model', "")
        cfg['title'] = self.form_dict.get('title', "")
        cfg['no_cancel'] = self.form_dict.get('no_cancel', False)
        cfg['properties'] = self.form_dict.get('properties', {})
        cfg['sort'] = self.form_dict.get('properties', {}).get("sort", "list_order:asc,rec_name:desc")
        cfg['queryformeditable'] = self.form_dict.get('properties', {}).get("queryformeditable", "{}")
        cfg['sys'] = self.form_dict.get('sys', False)
        cfg['models'] = self.models
        cfg['handle_global_change'] = self.form_dict.get('handle_global_change', True)
        cfg['custom_builder_components'] = ujson.dumps(
            self.theme_cfg.custom_builder_oject.copy(), escape_forward_slashes=False, ensure_ascii=False)
        cfg['type'] = self.form_dict.get('type', "form")
        cfg['parent_model_components'] = ujson.dumps(
            self.parent_model_components.copy(), escape_forward_slashes=False, ensure_ascii=False)
        return cfg.copy()
