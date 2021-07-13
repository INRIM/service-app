# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
import collections
import sys
from copy import deepcopy
import logging
import ujson
from fastapi.templating import Jinja2Templates

from .builder_custom import *
from . import custom_components
from .widgets_content import PageWidget
from .base.base_class import BaseClass, PluginBase

logger = logging.getLogger(__name__)


class TableWidget(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class TableWidgetBase(TableWidget, PageWidget):

    @classmethod
    def create(
            cls, templates_engine, session, request, content, disabled=False,
            **kwargs):
        self = TableWidgetBase()
        self.content = deepcopy(content)
        settings = self.content.get("settings")
        self.init(
            templates_engine, session, request, settings, disabled=disabled, **kwargs
        )
        self.model = self.content.get("model")
        self.schema = self.content.get("schema")
        self.builder = CustomBuilder(
            self.schema, template_engine=templates_engine,
            disabled=self.disabled, settings=settings, authtoken=self.authtoken,
            theme_cfg=self.theme_cfg, is_mobile=self.is_mobile
        )
        logger.info("make_def_table")
        self.form_c = CustomForm({}, self.builder)
        # logger.info("print_structure")
        # self.print_structure()
        self.columns = self.get_columns()
        return self

    def _compute_table_fields(self, node, cols):
        if node.raw.get('tableView'):
            cols[node.key] = node.label
        if not node.survey and not node.multi_row and node.component_items:
            for sub_node in node.component_items:
                cols = self._compute_table_fields(sub_node, cols)
        return cols.copy()

    def get_columns(self):
        logger.info(f" get_columns ")
        if self.model == "component":
            cols = self.get_header_component()
        else:
            cols = {'list_order': 'O'}
            for component in self.builder.main.component_items:
                # if component.raw.get('tableView'):
                #     cols[component.key] = component.label
                cols = self._compute_table_fields(component, cols)
        if "row_action" not in cols:
            cols['row_action'] = 'Action'
        return collections.OrderedDict(cols.copy())

    def get_header_component(self):
        cols = {
            'list_order': 'O',
            'title': 'Title',
            'rec_name': 'Name',
            'sys': 'Di Sistema',
            'type': 'Tipo',
            'display': 'Display',
            'demo': 'Dati Demo',

        }
        return cols.copy()

    # TODO
    def get_columns_metadata(self):
        cols = {
            'rec_name': 'Name',
            'owner_uid': 'Uid',
            'row_action': 'Action',
            'owner_name': 'Operatore',
            'create_datetime': 'Creato il',
            'update_datetime': 'Aggiornato il',
            'list_order': 'Ordinamento'
        }
        return cols

    def hide_metadata(self, show_owner=True):
        list_res = []
        list_kyes = list(self.data_config['columns'].keys())
        for item in self.get_columns_metadata():
            if item in list_kyes:
                if item == "owner_name":
                    if not show_owner:
                        list_res.append(list_kyes.index(item))
                else:
                    list_res.append(list_kyes.index(item))
        return list_res

    # TODO impelemntare per il sorting corretto delle date
    # https://datatables.net/forums/discussion/45692/how-to-date-sort-as-date-instead-of-string
    # <td data-sort="<%= my_date.strftime("%Y%m%d%H%M%s") %>">
    #   <%= Display your date using any format here %>
    # </td>
