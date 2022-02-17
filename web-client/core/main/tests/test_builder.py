# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
from .base_test import CommonTestCase
from core.main.builder_custom import CustomBuilder, CustomForm


class BuilderTestCase(CommonTestCase):

    def _builder(self, model_name, context={}, disabled=False):
        self.model = model_name
        self.schema = self.get_schema_name()
        self.url_action = ""
        self.builder = CustomBuilder(
            self.schema, template_engine=self.templates,
            disabled=disabled, settings=self.settings, context=context, authtoken=self.authtoken,
            rec_name=self.rec_name, model=self.model, theme_cfg=self.theme_cfg, is_mobile=self.is_mobile,
            editable_fields=self.editable_fields, security_headers=self.security_headers,
            action_url=self.api_action
        )

    def _formData(self, data, model_name, context={}, disabled=False):
        self.model = model_name
        self.schema = self.get_schema_name()
        self._builder(model_name, context=context, disabled=disabled)
        # self.form_data = CustomForm(data, self.builder)

    def test_builder(self):
        self._builder("action")
        self.assertEqual(self.authtoken, self.builder.authtoken)
        self.components_ext_data_src = self.builder.components_ext_data_src

    def test_get_component_by_key(self):
        self._builder("fast_search_config")
        component = self.builder.get_component_by_key("searchForm")
        self.assertEqual(component.key, "searchForm")

    def test_form_components(self):
        self._builder("action")
        keys = ('rec_name', 'list_order', 'modal', 'data_model', 'elimina', 'title', 'user_function')
        for k in keys:
            component = self.builder.get_component_by_key(k)
            self.assertEqual(k, component.key)

    def test_set_model_field(self):
        self._builder("fast_search_config")
        component = self.builder.get_component_by_key("data_model")
        self.assertTrue(component)

    def test_form_data_new(self):
        self._formData({}, "action")
        component = self.builder.get_component_by_key("action_type")
        self.assertTrue(component.value, "menu")

    def test_form_data_with_alues(self):
        data = self.get_data("action", "save_edit_mode")
        self._formData(data, "action")
        component = self.builder.get_component_by_key("action_type")
        self.assertTrue(component.value, "save")
