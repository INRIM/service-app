# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import copy
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
        self.model = kwargs.get('model')
        self.action_url = kwargs.get('action_url', "")
        self.disabled = kwargs.get('disabled', False)
        self.authtoken = kwargs.get('authtoken')
        self.theme_cfg = kwargs.get('theme_cfg', "")
        self.editable_fields = kwargs.get('editable_fields', [])
        # self.components_base_path = kwargs.get('components_base_path', False)
        self.settings = kwargs.get('settings', {}).copy()
        self.context_data = kwargs.get('context', {})
        self.security_headers = kwargs.get('security_headers', {}).copy()
        self.table_colums = collections.OrderedDict({
            'list_order': 'O',
            'check': "Chk",
            'owner_name': 'Operatore',
        })
        self.rec_name = kwargs.get('rec_name', "")
        self.is_mobile = kwargs.get("is_mobile", False)
        self.tables = []
        self.filters = []
        self.default_fields = kwargs.get('default_fields', []).copy()
        self.components_ext_data_src = []
        self.html_components = []
        self.form_data = kwargs.get('form_data', {})
        self.form_data_values = {}
        self.search_areas = []
        self.uploaders = []
        self.uploaders_keys = []
        self.components_logic = []
        self.filter_keys = []
        self.components_change_ext_data_src = []
        self.new_record = False
        if self.form_data.get("rec_name", "") == "":
            self.new_record = True
        # logger.info(f"builder with security {self.security_headers}")
        super(CustomBuilder, self).__init__(schema_json, **kwargs)

    def load_components(self):
        self._raw_components = self.schema.get('components')
        self.raw_components = deepcopy(self.schema.get('components'))
        # schema_type = self.schema.get('type')
        self.main = self.get_component_object(self.schema)
        self.main.eval_components()
        self.set_model_field()

    def load_data(self, data):
        self.form_data = copy.deepcopy(data)
        self.main.form_data = copy.deepcopy(data)
        if "data_value" not in self.main.form_data:
            self.main.form_data['data_value'] = {}
        self.main.load_data()
        self.context_data['form'] = self.main.form_data.copy()


    def compute_data(self):
        self.main.compute_data()
        if self.new_record:
            self.main.form_data['data_value'] = {}

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
        # self.form_components[component.get('key')] = model_c
        self.components[component.get('key')] = model_c
        self.main.component_items.append(model_c)
        if self.action_url:
            component = {}
            component['type'] = 'textfield'
            component['key'] = 'action_url'
            component['label'] = 'Action Url'
            component['hidden'] = True
            component['defaultValue'] = self.action_url
            model_c = self.get_component_object(component.copy())
            model_c.id = component.get('id', str(uuid.uuid4()))
            model_c.parent = self.main
        # self.form_components[component.get('key')] = model_c
        self.components[component.get('key')] = model_c
        self.main.component_items.append(model_c)
        if not self.get_component_by_key("rec_name"):
            component = {}
            component['type'] = 'textfield'
            component['key'] = 'rec_name'
            component['label'] = 'Name'
            component['hidden'] = True
            component['defaultValue'] = ""
            rec_name_c = self.get_component_object(component.copy())
            rec_name_c.id = component.get('id', str(uuid.uuid4()))
            rec_name_c.parent = self.main
            # self.form_components[component.get('key')] = model_c
            self.components[component.get('key')] = rec_name_c
            self.main.component_items.append(rec_name_c)

    def get_component_object(self, component):
        """
        @param component
        """
        component_type = component.get('type')
        # if not component_type == "components":
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
            # logger.warnin(component)
            # logger.warning(e, exc_info=True)
            return custom_components.CustomComponent(component, self)
        # else:
        #     return False

    def _get_component_by_key(self, node, key):
        if node.key == key:
            return node
        if node.component_items:
            for sub_node in node.component_items:
                comp = self._compute_form_data(sub_node, key)
                if comp:
                    return comp

    def get_component_by_key(self, key):
        return self.components.get(key)

    def compute_components_data(self, data):
        self.context_data['form'] = self.main.form_data.copy()
        self.main.form_data['data_value'] = {}

    def compute_form_data_table(self):
        data_v = self.main.compute_data_table(self.main.form_data)
        for node in self.main.component_items:
            data_v = self._compute_form_data_table(node, data_v)
        # clean metadata
        to_pop = []
        for k, v in data_v.items():
            if any(x in k for x in ["data_value", "_surveyRow_", "_dataGridRow_"]):
                to_pop.append(k)
        for x in to_pop:
            data_v.pop(x)
        self.main.form_data['data_value'] = data_v.copy()

    def _compute_form_data_table(self, node, form_data):
        # TODO dataGrid
        data = node.compute_data_table(form_data)
        if node.component_items:
            for sub_node in node.component_items:
                data = self._compute_form_data_table(sub_node, data)
        return data

    def clean_record_for_table_value(self, data):
        return self.clean_record(data)

    def clean_record(self, data):
        res = {}
        for k, v in data.items():
            if k not in self.default_fields:
                res[k] = v
        return res.copy()


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
            component.eval_components()
        if component.tabs:
            component.form = self.form.copy()
            component.eval_components()


COMPONENT_UI_TEMPLATE = {
    "title": "",
    "key": "",
    "icon": "plus-square-o",
    "schema": {}
}


class FormioBuilderFields:

    def __init__(self, schema_components):
        self.parent_model_components = {}
        self.schema_components = schema_components

    def load_components(self):
        self._load_components(self.schema_components)

    def _load_components(self, components):
        for component in components:
            if component.get('key') and not component.get('type') in ["button"]:
                self.parent_model_components[component["key"]] = COMPONENT_UI_TEMPLATE.copy()
                self.parent_model_components[component["key"]]['title'] = component['label']
                self.parent_model_components[component["key"]]['key'] = component["key"]
                self.parent_model_components[component["key"]]['schema'] = component.copy()
                if component.get('type') == "columns":
                    self.parent_model_components[component["key"]]['icon'] = "columns"
                if component.get('type') == "panel":  #
                    self.parent_model_components[component["key"]]['icon'] = "list-alt"
                if component.get('type') == "tabs":  #
                    self.parent_model_components[component["key"]]['icon'] = "folder-o"

            # if component.get('components'):
            #     self._load_components(component.get('components'))
            #
            # # (Layout) nested components (e.g. columns, panels)
            # for k, vals in component.copy().items():
            #     if isinstance(vals, list):
            #         for v in vals:
            #             if 'components' in v:
            #                 self._load_components(v.get('components'))
            #             elif isinstance(v, list):
            #                 for sub_v in v:
            #                     if 'components' in sub_v:
            #                         self._load_components(sub_v.get('components'))
