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
            cls, templates_engine, session, request, settings, theme="italia", disabled=False, form_object=None,
            **kwargs
    ):
        # super().__init__(templates_engine, session, request, settings, schema={}, disabled=disabled, **kwargs)
        self = FormIoBuilderWidgetBase()
        self.init(templates_engine, session, request, settings, theme, **kwargs)
        self.form_object = deepcopy(form_object)
        self.components = form_object.components
        return self
        # self.form_id = form_object.id
        # self.custom_components = kwargs.get('custom_components', custom_builder_oject)

    def init(self, templates_engine: Jinja2Templates, session: dict, request, settings, theme="italia", **kwargs):
        super().init(templates_engine, session, request, settings, theme=theme, **kwargs)
        self.cls_title = " text-center "
        self.api_action = "/"
        self.action_buttons = kwargs.get('action_buttons', "/")
        self.base_form_url = kwargs.get('base_form_url', "/")
        self.preview_link = kwargs.get('preview_link', "/")
        self.curr_row = []
        self.submission_id = ""
        self.form_name = ""

    def builder_components(self):
        return self.theme_cfg.custom_builder_oject.copy()

    def get_config(self, **context):
        cfg = {}
        cfg["request"] = self.request
        cfg["token"] = self.authtoken
        cfg["req_id"] = self.req_id
        cfg['base_form_url'] = self.base_form_url
        cfg['action_buttons'] = self.action_buttons
        cfg['preview_link'] = self.preview_link
        cfg['components'] = ujson.dumps(self.form_object.components, escape_forward_slashes=False, ensure_ascii=False)
        cfg['rec_name'] = self.form_object.rec_name
        cfg['deleted'] = self.form_object.deleted
        cfg['data_model'] = self.form_object.data_model
        cfg['title'] = self.form_object.title
        cfg['no_cancel'] = self.form_object.no_cancel
        cfg['properties'] = self.form_object.properties
        cfg['sys'] = self.form_object.sys
        cfg['handle_global_change'] = self.form_object.handle_global_change
        cfg['custom_builder_components'] = ujson.dumps(self.theme_cfg.custom_builder_oject.copy(),
                                                       escape_forward_slashes=False, ensure_ascii=False)
        cfg['type'] = self.form_object.type
        return cfg.copy()
