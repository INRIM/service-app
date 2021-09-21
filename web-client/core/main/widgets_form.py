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

logger = logging.getLogger(__name__)


class FormIoWidget(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class FormIoWidgetBase(FormIoWidget, PageWidget):

    @classmethod
    def create(
            cls, templates_engine, session, request, settings, content, schema={}, **kwargs):
        self = FormIoWidgetBase()
        self.content = deepcopy(content)
        disabled = not self.content.get('editable')
        editable_fields = self.content.get('editable_fields', [])
        self.init(
            templates_engine, session, request, settings, disabled=disabled, editable_fields=editable_fields, **kwargs)
        self.disabled = disabled
        self.model = self.content.get("model")
        self.cls_title = " text-center "
        self.api_action = self.content.get('action_url')
        self.rec_name = self.content.get('rec_name', "")
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
        # self.theme_cfg
        self.builder = CustomBuilder(
            self.schema, template_engine=templates_engine,
            disabled=self.disabled, settings=settings, context=self.context_data.copy(), authtoken=self.authtoken,
            rec_name=self.rec_name, model=self.model, theme_cfg=self.theme_cfg, is_mobile=self.is_mobile,
            editable_fields=self.editable_fields
        )
        self.components_ext_data_src = self.builder.components_ext_data_src
        self.components_change_ext_data_src = []
        self.tables = self.builder.tables
        self.filters = self.builder.filters
        self.search_areas = self.builder.search_areas
        self.uploaders = self.builder.uploaders
        self.uploaders_keys = self.builder.uploaders_keys
        self.html_components = self.builder.html_components
        self.init_form()
        return self

    def init_form(self):
        self.title = self.schema.get('title')
        self.rec_name = self.schema.get('rec_name')
        self.sys_component = self.schema.get('sys')
        self.handle_global_change = int(self.schema.get('handle_global_change', 0)) == 1
        self.no_cancel = int(self.schema.get('no_cancel', 0)) == 1
        logic_components = []
        for node in self.builder.main.component_items:
            logic_components = self._eval_logic(node, logic_components)
        if self.components_change_ext_data_src:
            for comp in self.components_change_ext_data_src:
                logger.info(comp)
                comp.compute_logic_and_condition()

    def get_component_by_key(self, key):
        return self.builder.get_component_by_key(key)

    def clean_record_for_table_value(self, data):
        res = {}
        default_fields = self.session['app']['default_fields']
        # default_fields.append("data_value")
        for k, v in data.items():
            if k not in default_fields:
                res[k] = v
        return res

    def compute_components_data(self, data_form):
        logger.info("compute_components_data")
        data = deepcopy(data_form)
        self.builder.form_data = data_form.copy()
        for node in self.builder.main.component_items:
            data = self._compute_form_data(node, data)
        self.form_data = data.copy()
        self.builder.form_data = self.form_data.copy()
        submissions = self.clean_record_for_table_value(self.form_data)
        CustomForm(submissions.copy(), self.builder)
        for node in self.builder.main.component_items:
            submissions = self._compute_form_data_table(node, submissions)
        self.form_data_values = submissions.copy()
        self.form_data['data_value'] = self.form_data_values.copy()
        self.builder.context_data['form'] = self.form_data.copy()
        # if 'app' in self.builder.context_data:
        #     self.builder.context_data.pop('app')

    def sanitize_submitted_data(self, submitted_data):
        data = {}
        clean = re.compile('<.*?>')
        for k, v in submitted_data.items():
            if k not in self.html_components:
                if isinstance(v, str):
                    val = re.sub(clean, '', str(v))
                elif isinstance(v, dict) and k not in self.uploaders_keys:
                    val = self.sanitize_submitted_data(v)
                elif isinstance(v, list) and k not in self.uploaders_keys:
                    val = [re.sub(clean, '', str(value)) for value in v]
                else:
                    val = v
            else:
                val = v
            data[k] = val
        return data.copy()

    def compute_component_data_submission(self, submitted_data):
        data = self.sanitize_submitted_data(submitted_data)
        self.compute_components_data(data.copy())

    def form_load_data(self):
        logger.info("load_form")
        data_tmp = self.content.get('data', {}) or {}
        data = data_tmp.copy()
        self.context_data = self.session
        self.context_data['form'] = data.copy()
        self.builder.context_data = self.context_data.copy()
        CustomForm(data.copy(), self.builder)

    def render_report_html(self):
        self.form_load_data()
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
                "logo": self.settings.logo_img_url
            }
            base = self.render_template(
                template, values
            )
            file_report = f"/tmp/header_{str(uuid.uuid4())}.html"
            with open(file_report, 'w') as f:
                f.write(base)
            options['header-html'] = file_report
            options['margin-top'] = self.settings.report_header_space
        if rfooter == "1":
            template = self.theme_cfg.get_template("reports", "report_footer")
            values = {
                "report_footer_company": self.settings.report_footer_company,
                "report_footer_title": self.settings.report_footer_title or self.title,
                "report_footer_sub_title": self.settings.report_footer_sub_title,
                "report_footer_pagination": self.settings.report_footer_pagination
            }
            base = self.render_template(
                template, values
            )
            file_report_f = f"/tmp/footer_{str(uuid.uuid4())}.html"
            with open(file_report_f, 'w') as f:
                f.write(base)
            options['footer-html'] = file_report_f
            options['margin-bottom'] = self.settings.report_footer_space
        return options

    def make_form(self):
        self.form_load_data()
        submit = self.builder.components.get("submit")
        if submit:
            self.label = submit.label
        return self.render_form()

    def render_form(self):
        # template = f"{self.components_base_path}{self.theme_cfg.form_component_map.get(self.builder.main.type)}"
        tmp = self.builder.main.type
        if self.modal:
            tmp = "modalform"
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
            "uploaders_keys": self.uploaders_keys
        }
        return self.render_template(
            template, values
        )

    def form_compute_submit(self, submitted_data) -> dict:
        logger.info(f"form_compute_submit data")
        self.compute_component_data_submission(submitted_data)
        data = self.builder.context_data['form'].copy()
        return data

    def form_compute_change(self, submitted_data) -> list:
        list_res = []
        logic_components = []
        # data = self.content.get('data')
        self.compute_component_data_submission(submitted_data)
        for node in self.builder.main.component_items:
            logic_components = self._eval_logic(node, logic_components)
        if self.components_change_ext_data_src:
            for comp in self.components_change_ext_data_src:
                logger.info(comp)
                comp.compute_logic_and_condition()
        return logic_components[:]

    def render_change_components(self, logic_components):
        list_res = []
        for comp in logic_components:
            if comp:
                list_res.append({
                    "value": comp.render(),
                    "selector": "#" + comp.key
                })
        return list_res

    def grid_rows(self, key):
        self.form_load_data()
        self.data_grid = self.get_component_by_key(key)
        self.data_grid.eval_rows()
        return self.data_grid

    def grid_add_row(self, key, num_rows):
        self.data_grid = self.get_component_by_key(key)
        row = self.data_grid.add_row(num_rows)
        self.datagrid_rows.append(row)
        return self.data_grid
