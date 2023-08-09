# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
from .test_builder import BuilderTestCase
from core.main.custom_components import *


class ComponentsTestCase(BuilderTestCase):
    def get_action_submit_data(self):
        return {
            "list_order": "0",
            "title": "Test",
            "rec_name": "test",
            "user_function": "",
            "model": "",
            "component_type": "",
            "action_type": "task",
            "process_name_to_complete": "",
            "menu_group": "config",
            "action_root_path": "/action",
            "type": "",
            "mode": "",
            "list_query": "",
            "listOrderString": "",
            "context_button_mode": "form",
            "button_icon": "it-plus",
            "next_action_name": "",
            "ref": "",
            "parent": "",
            "data_model": "action",
        }

    def test_components_compute_data(self):
        data = self.get_action_submit_data()
        ctx = self.get_context(data.copy())
        self._formData(data, "action", context=ctx.copy())
        self.assertEqual(type(data["context_button_mode"]), str)
        self.builder.compute_components_data(data)
        data = self.builder.context_data["form"]
        self.assertEqual(type(data["context_button_mode"]), list)

    def test_component_data_logic_admin_new(self):
        data = {}
        ctx = self.get_context(data)
        self._formData(data, "action", context=ctx.copy())
        comp = self.builder.get_component_by_key("elimina")
        cfg = comp.compute_logic_and_condition()
        self.assertTrue(cfg.get("hidden"))

    def test_component_data_logic_admin_values(self):
        data = self.get_data("action", "save_edit_mode")
        ctx = self.get_context(data.copy())
        self._formData(data, "action", context=ctx.copy())
        self.builder.compute_components_data(data)
        comp = self.builder.get_component_by_key("elimina")
        cfg = comp.compute_logic_and_condition()
        self.assertFalse(cfg.get("hidden"))

    def test_component_data_logic_user(self):
        data = {}
        ctx = self.get_context(data, user_type="user")
        self._formData(data, "action", context=ctx.copy())
        comp = self.builder.get_component_by_key("elimina")
        cfg = comp.compute_logic_and_condition()
        self.assertTrue(cfg.get("hidden"))

    def test_component_data_logic_user_values(self):
        data = self.get_data("action", "save_edit_mode")
        ctx = self.get_context(data.copy(), user_type="user")
        self._formData(data, "action", context=ctx.copy())
        self.builder.compute_components_data(data)
        comp = self.builder.get_component_by_key("elimina")
        cfg = comp.compute_logic_and_condition()
        self.assertTrue(cfg.get("hidden"))

    def test_components_compute_data_table(self):
        data = self.get_action_submit_data()
        data["action_type"] = "menu"
        data["mode"] = "list"
        data["type"] = "component"
        action_type_res = [
            {"rec_name": "menu", "label": "Menu"},
            {"rec_name": "task", "label": "Task"},
        ]
        user_function_res = [
            {"rec_name": "user", "label": "User"},
            {"rec_name": "resp", "label": "Resp"},
        ]
        model_res = [
            {"rec_name": "action", "title": "Action"},
            {"rec_name": "user", "title": "User"},
        ]
        menu_group_res = [
            {"rec_name": "action", "label": "Actions"},
            {"rec_name": "user", "label": "Users"},
        ]
        delete_cascade_res = [
            {"rec_name": "action", "label": "Actions"},
            {"rec_name": "user", "label": "Users"},
        ]
        next_action_name_res = [
            {"rec_name": "action_open", "title": "Open Actions"},
            {"rec_name": "actions_save", "title": "Save Action"},
        ]
        ctx = self.get_context(data.copy())
        self._formData(data, "action", context=ctx.copy())
        action_type = self.builder.get_component_by_key("action_type")
        action_type.resources = action_type_res
        action_type.make_resource_list()
        # fake loar remote resource
        user_function = self.builder.get_component_by_key("user_function")
        user_function.resources = user_function_res
        user_function.make_resource_list()
        model = self.builder.get_component_by_key("model")
        model.resources = model_res
        model.make_resource_list()
        menu_group = self.builder.get_component_by_key("menu_group")
        menu_group.resources = menu_group_res
        menu_group.make_resource_list()
        delete_cascade = self.builder.get_component_by_key("delete_cascade")
        delete_cascade.resources = delete_cascade_res
        delete_cascade.make_resource_list()
        next_action_name = self.builder.get_component_by_key(
            "next_action_name"
        )
        next_action_name.resources = next_action_name_res
        next_action_name.make_resource_list()
        # compute form
        self.builder.compute_components_data(data.copy())
        # compute form data value
        self.builder.compute_form_data_table(data.copy())
        data = self.builder.context_data["form"]
        data_values = self.builder.form_data["data_value"]
        self.assertEqual(type(data["context_button_mode"]), list)
        self.assertEqual(data_values["type"], "Schema")
        self.assertEqual(data_values["mode"], "List")
