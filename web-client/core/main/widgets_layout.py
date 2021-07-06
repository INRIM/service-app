# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
import sys
from copy import deepcopy
import logging
import ujson
from fastapi.templating import Jinja2Templates

from .builder_custom import *
from .widgets_content import PageWidget
from .base.base_class import BaseClass, PluginBase

logger = logging.getLogger(__name__)


class LayoutWidget(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class LayoutWidgetBase(LayoutWidget, PageWidget):

    @classmethod
    def create(
            cls, templates_engine, session, request, settings, content, schema={}, **kwargs):
        self = LayoutWidgetBase()
        self.settings = settings
        self.content = content
        disabled = not self.content.get('editable')

        self.init(
            templates_engine, session, request, settings, disabled=disabled, **kwargs
        )
        self.page_config = content
        self.schema = schema
        self.cls_title = " text-center "
        self.curr_row = []
        self.submission_id = ""
        self.context = kwargs.get('context', {})
        self.breadcrumb = kwargs.get("breadcrumb")
        self.form_name = ""
        self.rec_name = self.schema.get("rec_name")
        self.form_data = {}
        self.form_data_values = {}
        self.context_buttons = []
        self.builder = CustomBuilder(
            self.schema.copy(), template_engine=templates_engine,
            disabled=self.disabled, settings=settings, context=self.context, authtoken=self.authtoken,
            theme_cfg=self.theme_cfg
        )
        self.init_layout()
        logger.info("LayoutWidget init complete")
        return self

    def make_menu(self):
        logger.info("make_menu")
        self.menu_headers = []
        menus = self.page_config.get('menu')
        for item in menus:
            for k, v in item.items():
                cfg = {
                    "key": k,
                    "label": k,
                    "items": v,
                }
                self.menu_headers.append(
                    self.render_custom(
                        # f"{self.components_base_path}{form_component_map['menu']}",
                        self.theme_cfg.get_template("components", 'menu'),
                        cfg.copy()
                    )
                )

    def make_context_button(self, content):
        logger.info("make_context_button")
        self.context_buttons = []
        buttons = content.get('context_buttons')
        if buttons:
            for item in buttons:
                if not (content.get("builder") and content['mode'] == "form") and item:
                    if not content.get("builder") and item.get("builder") and item.get("btn_action_type"):
                        pass
                    else:
                        cfg = item.copy()
                        cfg['customClass'] = "col"
                        self.context_buttons.append(
                            self.render_custom(
                                # f"{self.components_base_path}{form_component_map['ctxbuttonaction']}",
                                self.theme_cfg.get_template("components", 'ctxbuttonaction'),
                                cfg
                            )
                        )
        if self.context_buttons:
            row_cfg = {
                "customClass": "container",
                "rows": self.context_buttons
            }
            self.beforerows.append(
                # self.get_component_by_key("beforerows").render()
                self.render_custom(
                    # f"{self.components_base_path}{form_component_map['blockcolumns']}",
                    self.theme_cfg.get_template("components", 'blockcolumns'),
                    row_cfg
                )
            )

    def init_layout(self):

        self.title = self.schema['title']
        self.name = self.schema['rec_name']
        self.form_id = self.schema['id']
        self.sys_component = self.schema['sys']
        self.handle_global_change = int(self.schema.get('handle_global_change', 0)) == 1
        self.no_cancel = int(self.schema.get('no_cancel', 0)) == 1
        self.make_menu()
        self.make_layout()

    def print_structure(self):
        for node in self.builder.main.component_items:
            print(node, node.key, node.value, "---")
            if node.component_items:
                for sub_node in node.component_items:
                    print("--->", sub_node, sub_node.key, sub_node.value)
                    if sub_node.multi_row:
                        for row in sub_node.grid_rows:
                            for sub3_node in row:
                                print("------------->", sub3_node, sub3_node.key, sub3_node.value)
                    elif sub_node.component_items:
                        for sub2_node in sub_node.component_items:
                            print("-------->", sub2_node, sub2_node.key, sub2_node.value)
                            if sub2_node.component_items:
                                for sub3_node in sub2_node.component_items:
                                    print("------------->", sub3_node, sub3_node.key, sub3_node.value)

    def get_component_by_key(self, key):
        return self.builder.get_component_by_key(key)

    def make_layout(self):
        # self.print_structure()
        CustomForm({}, self.builder)
        # submit = self.builder.components.get("submit")
        # if submit:
        #     self.label = submit.label
        self.afterrrows.append(
            self.get_component_by_key("afterrows").render()
        )

    def render_layout(self):
        # template = f"{self.components_base_path}{form_component_map[self.builder.main.type]}"
        template = self.theme_cfg.get_template("components", self.builder.main.type)
        values = {
            "rows": self.rows,
            "title": self.title,
            "cls_title": self.cls_title,
            "label": self.label,
            "name": self.name,
            "rec_name": self.rec_name,
            "authtoken": self.authtoken,
            "req_id": self.req_id,
            "sys_form": self.sys_component,
            "menu_headers": self.menu_headers,
            "breadcrumb": self.breadcrumb
        }

        return self.render_page(
            template, **values
        )
