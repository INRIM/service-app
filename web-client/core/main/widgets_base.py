# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
import sys

sys.path.append("..")

from datetime import datetime

from fastapi import Request
from starlette.templating import Jinja2Templates, jinja2

from .base.base_class import BaseClass
from .DateEngine import DateEngine
from core.themes.ThemeConfig import ThemeConfig

import logging
import copy

logger = logging.getLogger(__name__)


class WidgetsBase:

    @classmethod
    def create(cls, templates_engine: Jinja2Templates, session, theme="italia", **kwargs):
        self = WidgetsBase()
        self.init(templates_engine, session, theme, **kwargs)
        return self

    # self.template_base_path = f"/{self.theme}/templates/"
    # self.components_base_path = f"/{self.theme}/templates/components/"
    # self.reports_base_path = f"/{self.theme}/templates/reports/"
    def init(self, templates_engine: Jinja2Templates, session: dict, request, theme="italia", **kwargs):
        self.tmpe = templates_engine
        self.list_ajax_reponse = []
        self.dte = DateEngine()
        self.session = session
        self.request = request
        self.rows = []
        self.title = ""
        self.error = ""
        self.label = ""
        self.export_btn = False
        self.backtop = True
        self.i18n = {}
        self.name = ""
        self.theme = theme
        self.theme_cfg = ThemeConfig.new(theme=theme)

    def convert_bool(self, item):
        if type(item) == bool:
            return "No" if item == False else "Si"
        else:
            return item

    def convert_str_server_ui(self, str_to_conver):
        if str_to_conver:
            return str_to_conver
        else:
            return "--"

    def convert_link(self, template, item):
        return self.render_template(template, item)

    def parse_date_ui(self, datp):
        if len(datp) > 10:
            return datetime.strptime(
                datp, self.settings.server_datetime_mask).strftime(self.settings.ui_datetime_mask)
        else:
            return datetime.strptime(datp, self.settings.server_date_mask).strftime(self.settings.ui_date_mask)

    def parse_datetime_ui(self, datp):
        return datetime.strptime(datp, self.settings.server_date_mask).strftime(self.settings.ui_date_mask)

    def convert_date_server_ui(self, date_to_conver, exclude):
        if date_to_conver and date_to_conver != exclude:
            return self.parse_date_ui(date_to_conver)
        else:
            return "--"

    def render_template(self, name: str, context: dict):
        template = self.tmpe.get_template(name)
        return template.render(context)

    def render_str_template(self, tmp: str, context: dict):
        logger.info("render_str_template")
        logger.info(".....")
        logger.info(context)
        logger.info(".")
        template = jinja2.Template(tmp)
        return template.render(context)

    def render_ajax_reload(self, link):
        return {
            "reload": True,
            "link": link
        }

    def add_ajax_resp_item(self, selector, widget, values):
        to_update = {}
        if not '#' in selector and not '.' in selector:
            selector = "#" + selector
        to_update["value"] = self.render_template(widget, values)
        to_update["selector"] = selector
        self.list_ajax_reponse.append(to_update)

    def response_ajax(
            self, redirect: bool = False, link: str = "#"):
        if redirect:
            return self.render_ajax_reload(link)
        list_res = self.list_ajax_reponse[:]
        self.list_ajax_reponse = []
        return list_res

    def response_ajax_notices(
            self, resp_type: str, selector: str, resp_message: str):
        list_res = []
        to_update = {}
        self.list_ajax_reponse = []
        dat_update = getattr(
            self.theme_cfg, f"get_update_alert_{resp_type}")(selector, resp_message)
        to_update["value"] = self.render_template(
            self.theme_cfg.get_template("components", "alert_msg"), dat_update['value'])
        to_update["selector"] = dat_update['selector']
        list_res.append(to_update)
        return list_res

    def response_template(self, name: str, context: dict):
        resp = self.tmpe.TemplateResponse(name, context)
        return resp

    def render_component(self, component, cfg):
        return ""
