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
        self.model = kwargs.get('model')
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
        self.default_fields = []
        self.components_ext_data_src = []
        self.html_components = []
        self.form_data = kwargs.get('form_data', {})
        self.form_data_values = {}
        self.search_areas = []
        self.uploaders = []
        self.uploaders_keys = []
        self.components_logic = []
        self.components_change_ext_data_src = []
        logger.info(f"builder with security {self.security_headers}")
        super(CustomBuilder, self).__init__(schema_json, **kwargs)

    def load_components(self):
        self._raw_components = self.schema.get('components')
        self.raw_components = deepcopy(self.schema.get('components'))
        schema_type = self.schema.get('type')
        self.main = self.get_component_object(self.schema)
        self.main.form_data = self.form_data.copy()
        self.context_data['form'] = self.form_data.copy()
        self.main.form_data['data_value'] = {}
        self.main.eval_components()
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
        # self.form_components[component.get('key')] = model_c
        self.components[component.get('key')] = model_c
        self.main.component_items.append(model_c)

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
        return self.components[key]

    def compute_components_data(self, data):
        self.context_data['form'] = self.main.form_data.copy()
        self.main.form_data['data_value'] = {}

    def compute_form_data_table(self, data):
        data_v = self.main.compute_data_table(data)
        for node in self.main.component_items:
            data_v = self._compute_form_data_table(node, data_v)
        self.main.form_data['data_value'] = data_v.copy()

    def _compute_form_data_table(self, node, form_data):
        # TODO dataGrid
        data = node.compute_data_table(form_data)
        if node.component_items:
            for sub_node in node.component_items:
                data = self._compute_form_data_table(sub_node, data)
        return data

    def clean_record_for_table_value(self, data):
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
