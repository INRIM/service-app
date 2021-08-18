# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
from copy import deepcopy
from formiodata.builder import Builder
from formiodata.form import Form
import collections
from . import custom_components

import logging
import uuid

logger = logging.getLogger(__name__)


class CustomBuilder(Builder):

    def __init__(self, schema_json, **kwargs):
        self.tmpe = kwargs.get('template_engine', False)
        self.model = kwargs.get('model', "")
        self.disabled = kwargs.get('disabled', False)
        self.authtoken = kwargs.get('authtoken')
        self.theme_cfg = kwargs.get('theme_cfg', "")
        # self.components_base_path = kwargs.get('components_base_path', False)
        self.settings = kwargs.get('settings', False)
        self.context_data = kwargs.get('context', {})
        self.table_colums = {"list_order": "O"}
        self.rec_name = kwargs.get('rec_name', "")
        self.is_mobile = kwargs.get("is_mobile", False)
        self.tables = []
        self.filters = []
        self.components_ext_data_src = []
        self.html_components = []
        self.form_data = {}
        self.form_data_values = {}
        self.search_areas = []
        self.uploaders = []
        self.uploaders_keys = []
        super(CustomBuilder, self).__init__(schema_json, **kwargs)

    def load_components(self):
        self._raw_components = self.schema.get('components')
        self.raw_components = deepcopy(self.schema.get('components'))
        schema_type = self.schema.get('type')
        if schema_type == "resource":
            schema_type = "form"
        if schema_type == "form":
            self.main = self.get_component_object({'type': schema_type})
        else:
            self.main = self.get_component_object(self.schema)
        if self.raw_components:
            self._load_components(self.raw_components, self.main)

        self.set_model_field()

    def set_model_field(self):
        component = {}
        component['type'] = 'textfield'
        component['key'] = 'data_model'
        component['label'] = 'Data Model'
        component['hidden'] = True
        component['defaultValue'] = self.model
        model_c = self.get_component_object(component.copy())
        model_c.id = component.get('id', str(uuid.uuid4()))
        model_c.parent = self.main
        self.form_components[component.get('key')] = model_c
        self.components[component.get('key')] = model_c
        self.main.component_items.append(model_c)

    def _load_components(self, components, parent=None, is_columns=False):
        """
        @param components
        """
        for component in components:
            if not parent.type == "components":
                if is_columns:
                    if component['width'] == 0:
                        return
                    component['type'] = 'column'
                    component['customClass'] = parent.raw.get('customClass', "")
                component_obj = self.get_component_object(component)
                if parent:
                    component_obj.parent = parent

                component_obj.id = component.get('id', str(uuid.uuid4()))
                self.component_ids[component_obj.id] = component_obj

                component['_object'] = component_obj
                if component.get('key') and component.get('input'):
                    self.form_components[component.get('key')] = component_obj
                    self.components[component.get('key')] = component_obj
                    self.filters.append(component_obj)
                else:
                    if component.get('key'):
                        key = component.get('key')
                    elif self.components.get(component.get('type')):
                        key = component.get('type') + '_x'
                    else:
                        key = component.get('type')
                    if not component.get('type') == "components":
                        self.components[key] = component_obj
                parent.component_items.append(component_obj)
                if component_obj.raw.get('tableView'):
                    if component_obj.key not in self.table_colums:
                        self.table_colums[component_obj.key] = component_obj.label
                if component_obj.dataSrc and not component_obj.table:
                    self.components_ext_data_src.append(component_obj)
                if component_obj.search_area:
                    self.search_areas.append(component_obj)
                if component_obj.uploaders:
                    self.uploaders.append(component_obj)
                    self.uploaders_keys.append(component_obj.key)
                if component_obj.table:
                    self.tables.append(component_obj)
                if component_obj.is_html:
                    self.html_components.append(component_obj.key)
                if component.get('components'):
                    self._load_components(component.get('components'), component_obj)
                if component.get('columns'):
                    self._load_components(component.get('columns'), component_obj, is_columns=True)

    def get_component_object(self, component):
        """
        @param component
        """
        component_type = component.get('type')
        if not component_type == "components":
            try:
                cls_name = '%sComponent' % component_type
                cls = getattr(custom_components, cls_name)
                return cls(
                    component, self, language=self.language,
                    i18n=self.i18n, resources=self.resources,
                    resources_ext=self.resources_ext
                )
            except AttributeError as e:
                # TODO try to find/load first from self._component_cls else
                # re-raise exception or silence (log error and return False)
                # logger.error(component)
                logger.error(e)
                return custom_components.CustomComponent(component, self)
        else:
            return False

    def get_component_by_key(self, key):
        for id, node in self.component_ids.items():
            if node.key == key:
                return node
        return False


class CustomForm(Form):

    def load_components(self):
        for component in self.builder.main.component_items:
            self._load_components(component)

    def _load_components(self, component):
        component.value = self.form.get(component.key, component.defaultValue)
        if (
                not component.survey and
                not component.multi_row and
                not component.tabs and
                component.component_items
        ):
            for sub_component in component.component_items:
                self._load_components(sub_component)
        if component.survey:
            component.eval_rows()
        if component.tabs:
            component.form = self.form.copy()
            component.eval_panels()
