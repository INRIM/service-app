# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import sys
from copy import deepcopy
import logging
import ujson
from .builder_custom import *
from .widgets_content import PageWidget, BaseClass
from .base.base_class import PluginBase
from datetime import datetime, date
import uuid
import re
import json
from core.cache.cache import get_cache

logger = logging.getLogger(__name__)


class FormIoWidget(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        if cls not in cls.plugins:
            cls.plugins.append(cls())


SUBMIT_LABELS = {
    "new": "Salva",
    "update": "Aggiorna"
}


class FormIoWidgetBase(FormIoWidget, PageWidget):

    @classmethod
    def create(
            cls, templates_engine, session, request, settings, content,
            schema={}, **kwargs):
        self = FormIoWidgetBase()
        self.content = deepcopy(content)
        disabled = not self.content.get('editable')
        editable_fields = self.content.get('editable_fields', [])
        self.init(
            templates_engine, session, request, settings, disabled=disabled,
            editable_fields=editable_fields, **kwargs)
        self.disabled = disabled
        self.model = self.content.get("model")
        self.cls_title = " text-center "
        self.api_action = self.content.get('action_url')
        self.rec_name = self.content.get('data', {}).get("rec_name")
        self.modal_form_url = kwargs.get('modal_form_url')
        self.curr_row = []
        self.schema = schema
        self.action_buttons = []
        self.filters = []
        self.context_data = session.copy()
        if "app" not in self.context_data:
            self.context_data['app'] = {}
        self.context_data['app']["year"] = date.today().year
        self.context_data['app']["month"] = date.today().month
        self.context_data['form'] = content.get("data", {})
        self.report = ""
        self.submission_id = ""
        self.modal = kwargs.get("modal", False)
        self.form_name = ""
        self.form_report_data = None
        self.handle_global_change = 1
        self.no_cancel = 0
        self.form_data = {}
        self.form_data_values = {}
        self.tables = []
        self.datagrid_rows = []
        self.data_grid = None
        self.uploaders = None
        self.datagrid_new_rows = []
        return self

    def init_form(self, data={}):
        self.title = self.schema.get('title')
        self.rec_name = self.rec_name
        self.sys_component = self.schema.get('sys')
        self.handle_global_change = int(
            self.schema.get('handle_global_change', 0)) == 1
        self.no_cancel = int(self.schema.get('no_cancel', 0)) == 1
        self.init_data = data.copy()
        build_modal = self.modal
        if not build_modal and self.request.query_params.get("miframe"):
            build_modal = True

        self.builder = CustomBuilder(
            self.schema, template_engine=self.tmpe,
            disabled=self.disabled,
            settings=self.settings,
            context=self.context_data.copy(),
            authtoken=self.authtoken,
            rec_name=self.rec_name,
            model=self.model, theme_cfg=self.theme_cfg,
            is_mobile=self.is_mobile,
            editable_fields=self.editable_fields,
            security_headers=self.security_headers,
            form_data=data.copy(),
            default_fields=self.session.get('app', {}).get(
                'default_fields')[:],
            action_url=self.api_action,
            modal=build_modal
        )
        # self.builder.default_fields = self.session.get('app', {}).get('default_fields')[:]
        self.components_ext_data_src = self.builder.components_ext_data_src
        self.components_change_ext_data_src = self.builder.components_change_ext_data_src
        self.tables = self.builder.tables
        self.filters = self.builder.filters
        self.search_areas = self.builder.search_areas
        self.uploaders = self.builder.uploaders
        self.uploaders_keys = self.builder.uploaders_keys
        self.html_components = self.builder.html_components
        self.load_data(data)

    def load_data(self, data):
        self.builder.load_data(data)

    def get_component_by_key(self, key):
        return self.builder.get_component_by_key(key)

    def clean_record_for_table_value(self, data):
        res = {}
        default_fields = self.session['app']['default_fields']
        for k, v in data.items():
            if k not in default_fields:
                res[k] = v
        return res

    def render_report_html(self):
        # self.form_load_data()
        logger.info("render_report_html")
        data = self.content.get('data', {}).copy()
        self.report = self.schema.get("properties", {}).get("report")
        self.form_report_data = BaseClass(**data)

        values = {
            "form": self.form_report_data
        }
        base = """{% set new_page  %}
<div style="display:block; clear:both; page-break-after:before;"></div>
{% endset %}"""
        report = f'{self.report}{base}'
        html_report_doc = self.render_str_template(
            report, values
        )
        template = self.theme_cfg.get_template("reports", "report_doc")
        values = {
            "document": html_report_doc
        }
        html_report = self.render_template(
            template, values
        )
        return html_report

    def handle_header_footer(self, options):
        rheader = self.schema.get("properties", {}).get("rheader")
        rfooter = self.schema.get("properties", {}).get("rfooter")
        if rheader == "1":
            # template = f"{self.reports_base_path}header.html"
            template = self.theme_cfg.get_template("reports", "report_header")
            values = {
                "logo": self.settings.get('logo_img_url')
            }
            base = self.render_template(
                template, values
            )
            file_report = f"/tmp/header_{str(uuid.uuid4())}.html"
            with open(file_report, 'w') as f:
                f.write(base)
            options['header-html'] = file_report
            options['margin-top'] = self.settings.get('report_header_space',
                                                      "30mm")
        if rfooter == "1":
            template = self.theme_cfg.get_template("reports", "report_footer")
            values = {
                "report_footer_company": self.settings.get(
                    'report_footer_company'),
                "report_footer_title": self.settings.get('report_footer_title',
                                                         self.title),
                "report_footer_sub_title": self.settings.get(
                    'report_footer_sub_title', ""),
                "report_footer_pagination": self.settings.get(
                    'report_footer_pagination', "")
            }
            base = self.render_template(
                template, values
            )
            file_report_f = f"/tmp/footer_{str(uuid.uuid4())}.html"
            with open(file_report_f, 'w') as f:
                f.write(base)
            options['footer-html'] = file_report_f
            options['margin-bottom'] = self.settings.get('report_footer_space',
                                                         "8mm")
        return options.copy()

    def make_form(self):
        # self.form_load_data()
        no_submit = self.schema.get('properties', {}).get("no_submit", "0")
        if no_submit == "1" and self.builder.components.get("submit"):
            self.builder.components.pop('submit')
        else:
            submit = self.builder.components.get("submit")
            if submit:
                self.label = SUBMIT_LABELS['update']
                if self.builder.new_record:
                    self.label = SUBMIT_LABELS['new']

        return self.render_form()

    def render_form(self):
        logger.debug(f"render {self.model} - {self.title} ")
        # template = f"{self.components_base_path}{self.theme_cfg.form_component_map.get(self.builder.main.type)}"
        tmp = self.builder.main.type
        if self.modal:
            tmp = "modalformcontainer"
        if self.request.query_params.get("miframe"):
            tmp = "modalform"
        form_disabled = self.schema.get('properties', {}).get(
            "form_disabled", "0")
        if form_disabled == "1":
            self.disabled = True

        template = self.theme_cfg.get_template("components", tmp)
        values = {
            "items": self.builder.main.component_items,
            "title": self.title,
            "cls_title": self.cls_title,
            "api_action": self.api_action,
            "label": self.label,
            "rec_name": self.rec_name,
            "disabled": self.disabled,
            "handle_global_change": self.handle_global_change,
            "no_cancel": self.no_cancel,
            "authtoken": self.authtoken,
            "model": self.model,
            "sys_form": self.sys_component,
            "uploaders_keys": self.uploaders_keys,
            "url_form": self.modal_form_url,
            "modal": self.modal
        }
        if self.request.query_params.get("miframe"):
            return self.render_paget(
                template, values
            )
        else:
            return self.render_template(
                template, values
            )

    def form_compute_submit(self) -> dict:
        self.builder.compute_data()
        self.builder.compute_form_data_table()
        data = self.builder.main.form_data.copy()
        # logger.info(f" compted data {data} ")
        return data

    def form_compute_change(self, submitted_data) -> list:
        logic_components = []
        # self.builder.compute_data(submitted_data)
        for node in self.builder.components_logic:
            logic_components = self._eval_logic(node, logic_components)
        if self.components_change_ext_data_src:
            for comp in self.components_change_ext_data_src:
                comp.compute_logic_and_condition()
        return logic_components[:]

    def form_compute_change_form(self) -> list:
        logger.debug(
            f"self.builder.components_logic --> "
            f"{self.builder.components_logic}")
        for comp in self.builder.components_logic:
            comp.compute_logic_and_condition()
        return self.builder.components_logic[:]

    async def render_change_components(self, content_service):
        list_res = []
        for comp in self.builder.components_logic:
            if comp:
                cfg = comp.compute_logic_and_condition()
                if comp in self.components_ext_data_src:
                    await content_service.eval_data_src_component(comp)
                list_res.append({
                    "value": comp.make_html(cfg),
                    "selector": "#" + comp.key
                })
        return list_res

    def grid_rows(self, key):
        # self.form_load_data()
        # logger.info(key)
        self.data_grid = self.get_component_by_key(key)
        # self.data_grid.eval_components()
        return self.data_grid

    def grid_add_row(self, key, num_rows):
        logger.info(f"- {key} - {num_rows}")
        self.data_grid = self.get_component_by_key(key)
        self.data_grid.add_row(num_rows)
        return self.data_grid

    def json_from_str(self, str_test) -> dict:
        try:
            str_test = json.loads(str_test)
        except ValueError as e:
            str_test = str_test.replace("'", "\"")
            try:
                str_test = json.loads(str_test)
            except ValueError as e:
                return False
        return str_test
