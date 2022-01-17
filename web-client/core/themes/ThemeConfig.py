import os
import sys

import ujson
from core.main.base.base_class import PluginBase


class ThemeConfig(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class ThemeConfigBase(ThemeConfig):

    @classmethod
    def create(cls, theme):
        self = ThemeConfigBase()
        self.init(theme)
        return self

    def init(self, theme):
        self.theme = theme
        self.local_path = os.path.realpath(".")
        self.form_component_map = self.get_form_component_map()
        self.form_component_default_cfg = self.get_form_component_default_cfg()
        self.custom_builder_oject = self.get_custom_builder_oject()
        self.alert_base = self.get_alert_base()
        self.base_template_layout = self.get_base_template_layout()
        self.make_default_path()

    def make_default_path(self):
        self.path_obj = {}
        self.path_obj['template'] = f"/{self.theme}/templates/"
        self.path_obj['components'] = f"/{self.theme}/templates/components/"
        self.path_obj['reports'] = f"/{self.theme}/templates/reports/"
        self.path_obj['mail'] = f"/{self.theme}/templates/mail/"

    def get_template(self, path_tag, name):
        tname = self.form_component_map.get(name)
        tmp_path = f"{self.path_obj[path_tag]}{tname}"
        return tmp_path

    def get_custom_template(self, name):
        tmp_path = f"{self.path_obj['template']}{self.base_template_layout.get(name)}"
        return tmp_path

    def get_page_template(self, name):
        return self.get_custom_template(name)

    def get_custom_builder_oject(self):
        custom_builder_object_file = f"{self.local_path}/core/themes/{self.theme}/custom_builder_object.json"
        with open(custom_builder_object_file) as f:
            data = ujson.load(f)
        return data.copy()

    def get_form_component_default_cfg(self):
        form_component_default_cfg_file = f"{self.local_path}/core/themes/{self.theme}/default_component_cfg.json"
        with open(form_component_default_cfg_file) as f:
            data = ujson.load(f)
        return data.copy()

    def get_form_component_map(self):
        form_component_map_file = f"{self.local_path}/core/themes/{self.theme}/components_config_map.json"
        with open(form_component_map_file) as f:
            data = ujson.load(f)
        return data.copy()

    def get_base_template_layout(self):
        base_template_layout_file = f"{self.local_path}/core/themes/{self.theme}/page_layout_cfg.json"
        with open(base_template_layout_file) as f:
            data = ujson.load(f)
        return data.copy()

    def get_alert_base(self):
        form_component_alert_file = f"{self.local_path}/core/themes/{self.theme}/components_alert.json"
        with open(form_component_alert_file) as f:
            data = ujson.load(f)
        return data.copy()

    def get_default_error_alert_cfg(self):
        return self.alert_base['error']

    def get_default_success_alert_cfg(self):
        return self.alert_base['succcess']

    def get_default_warning_alert_cfg(self):
        return self.alert_base['warning']

    def get_form_alert(self, values):
        if values.get("success"):
            kkwargs = self.get_default_success_alert_cfg()
        if values.get("error"):
            kkwargs = self.get_default_error_alert_cfg()
        if values.get("warning"):
            kkwargs = self.get_default_warning_alert_cfg()
        kwargs_def = {**kkwargs, **values}
        return kwargs_def.copy()

    def get_update_alert_error(self, selector, message, cls=""):
        to_update = {}

        cfg = {
            "error": True,
            "message": message,
            "cls": " mx-auto mt-lg-n3 ",
            "name": selector
        }
        if not '#' in selector and not '.' in selector:
            selector = "#" + selector
        if cls:
            cfg['cls'] = cls
        to_update["value"] = self.get_form_alert(cfg)

        to_update["selector"] = selector
        return to_update.copy()

    def get_update_alert_warning(self, selector, message, cls=""):
        to_update = {}

        cfg = {
            "warning": True,
            "message": message,
            "cls": " mx-auto mt-n5 ",
            "name": selector
        }
        if not '#' in selector and not '.' in selector:
            selector = "#" + selector
        if cls:
            cfg['cls'] = cls
        to_update["value"] = self.get_form_alert(cfg)

        to_update["selector"] = selector
        return to_update.copy()
