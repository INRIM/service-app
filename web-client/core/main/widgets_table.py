# Copyright INRIM (https://www.inrim.eu)
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
            cls, templates_engine, session, request, content, disabled=False, **kwargs):
        self = TableWidgetBase()
        self.content = deepcopy(content)
        sett = session.get('app')['settings'].copy()
        self.init(
            templates_engine=templates_engine, session=session, request=request,
            settings=sett, disabled=disabled, **kwargs
        )
        self.model = self.content.get("model")
        self.schema = self.content.get("schema")
        self.builder = CustomBuilder(
            self.schema, template_engine=templates_engine,
            disabled=self.disabled, settings=sett, authtoken=self.authtoken,
            theme_cfg=self.theme_cfg, is_mobile=self.is_mobile
        )
        logger.info("make_def_table")
        self.form_c = CustomForm({}, self.builder)
        self.parent = kwargs.get("parent")
        self.form_columns = []
        self.rec_name_is_meta = False
        self.columns = self.get_columns()
        self.columns_meta_list = self.list_metadata_keys()
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
            self.form_columns = cols.copy()
        else:
            cols = self.make_cols_component()
        # if "row_action" not in cols:
        #     cols['row_action'] = 'Action'
        return collections.OrderedDict(cols.copy())

    def get_header_component(self):
        cols = {
            'list_order': 'O',
            'check': "Chk",
            'title': 'Title',
            'rec_name': 'Name',
            'sys': 'Di Sistema',
            'type': 'Tipo',
            'display': 'Display',
            'demo': 'Dati Demo',
            "row_action": 'Action'

        }
        return cols.copy()

    def make_cols_component(self):
        cols = collections.OrderedDict({
            'list_order': 'O',
            'check': "Chk",
            'owner_name': 'Operatore',
        })
        cols_c = {}
        for component in self.builder.main.component_items:
            # if component.raw.get('tableView'):
            #     cols[component.key] = component.label
            cols_c = self._compute_table_fields(component, cols_c)
        self.form_columns = cols_c.copy()
        if "rec_name" not in cols_c:
            self.rec_name_is_meta = True
            cols.update({'rec_name': 'Name'})
        cols.update(cols_c)
        end_cols = collections.OrderedDict(self.get_columns_metadata())
        cols.update(end_cols)
        return cols.copy()

    def get_columns_metadata(self):
        return {
            'owner_sector': "Utente Div/Uo",
            'owner_function': "Utente Funz",
            'owner_personal_type': "Tipo Personale",
            'owner_job_title': "Qualifica",
            'create_datetime': 'Creato il',
            'update_datetime': 'Aggiornato il',
            'sys': 'Di Sistema',
            'type': 'Tipo',
            'display': 'Display',
            'demo': 'Dati Demo',
            'row_action': 'Action'
        }.copy()

    def list_metadata_keys(self):
        list_res = ["rec_name", "owner_name"]
        list_kyes = list(self.columns.keys())
        for item in self.get_columns_metadata():
            if item in list_kyes:
                list_res.append(item)
        return list_res

    # TODO impelemntare per il sorting corretto delle date
    # https://datatables.net/forums/discussion/45692/how-to-date-sort-as-date-instead-of-string
    # <td data-sort="<%= my_date.strftime("%Y%m%d%H%M%s") %>">
    #   <%= Display your date using any format here %>
    # </td>
