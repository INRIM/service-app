# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import copy
import json
import logging
import re
import uuid
from collections import OrderedDict

import jinja2
from formiodata.utils import (
    base64_encode_url,
    decode_resource_template,
    fetch_dict_get_value,
)
from json_logic import jsonLogic

from .DateEngine import DateEngine

logger = logging.getLogger(__name__)


class CustomComponent:
    def __init__(self, raw, builder, **kwargs):
        # TODO or provide the Builder object?
        # raw =
        # super().__init__(copy.deepcopy(raw), builder, **kwargs)

        # TODO i18n (language, translations)
        self.raw = copy.deepcopy(raw)
        self.builder = builder
        self.is_mobile = builder.is_mobile
        self.modal = builder.modal
        self.default_data = {self.key: ""}
        self.survey = False
        self.multi_row = False
        self.tabs = False
        self.dataSrc = False
        self.table = False
        self.search_area = False
        self.uploaders = False
        self.scanner = False
        self.stepper = False
        self.is_html = False
        self._parent = False
        self.grid_rows = []
        self.form_data = {}
        self.component_items = []
        self.width = 12
        self.size = "lg"
        self.offset = 0
        self.row_id = -1
        self.raw_key = ""
        self.key_prefix = ""
        self.parent_key = ""
        self.component_tmp = self.raw.get("type")
        self.unique = self.raw.get("unique")
        self.security_headers = self.builder.security_headers.copy()
        self.req_id = ""
        self.authtoken = self.builder.authtoken
        self.language = kwargs.get("language", "it")
        self.i18n = kwargs.get("i18n", {})
        self.clean = re.compile("<.*?>")
        self.search_object = {
            "id": self.key,
            "label": self.label,
            "default_operator": "contains",
            "type": "string",
        }
        self.resources = kwargs.get("resources", False)
        self.resources_ext = kwargs.get("resources_ext", False)
        self.defaultValue = self.raw.get("defaultValue")
        if self.resources and isinstance(self.resources, str):
            self.resources = json.loads(self.resources)

    def init_filter(self):
        self.search_object = {}

    @property
    def key(self):
        return self.raw.get("key")

    @key.setter
    def key(self, value):
        self.raw["key"] = value

    @property
    def label(self):
        label = self.raw.get("label")
        if self.i18n.get(self.language):
            return self.i18n[self.language].get(label, label) or ""
        else:
            return label or ""

    @label.setter
    def label(self, value):
        if self.raw.get("label"):
            self.raw["label"] = value

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, parent):
        if parent:
            self._parent = parent

    @property
    def type(self):
        return self.raw.get("type")

    @property
    def value(self):
        val = self.builder.main.form_data.get(self.key)
        if not val:
            val = self.defaultValue
        return val

    @value.setter
    def value(self, value):
        # self.form['value'] = value
        val = value
        if not self.is_html:
            val = re.sub(self.clean, "", str(value))
        self.builder.main.form_data[self.key] = val

    @property
    def tableView(self):
        return self.raw.get("tableView", False)

    @property
    def hideLabel(self):
        return self.raw.get("hideLabel", False)

    @property
    def hidden(self):
        return self.raw.get("hidden")

    @property
    def readonly(self):
        ro = self.raw.get("readOnlyValue", False)
        if self.raw.get("properties") and self.raw.get("properties").get(
                "readonly"
        ):
            ro = True
        return ro

    @property
    def trigger_change(self):
        trig_chage = False
        if self.raw.get("properties") and self.raw.get("properties").get(
                "trigger_change"
        ):
            trig_chage = True
        return trig_chage

    @property
    def has_logic(self):
        return self.raw.get("logic", False)

    @property
    def has_conditions(self):
        return self.raw.get("conditional", False)

    @property
    def properties(self):
        if not self.raw.get("properties"):
            self.raw["properties"] = {}
        return self.raw.get("properties")

    def aval_conditional(self, cfg):
        cond = (
                cfg.get("conditional")
                and cfg.get("conditional").get("json")
                and self.is_json(cfg.get("conditional").get("json"))
        )
        if cond:
            res = not jsonLogic(
                self.is_json(cfg.get("conditional").get("json")),
                self.builder.context_data,
            )
            cfg["hidden"] = res
        return cfg.copy()

    def is_json(self, str_test):
        if isinstance(str_test, str):
            try:
                str_test = json.loads(str_test)
            except ValueError as e:
                str_test = str_test.replace("'", '"')
                try:
                    str_test = json.loads(str_test)
                except ValueError as e:
                    return False
            return str_test
        elif isinstance(str_test, dict):
            return str_test

    def eval_action_value_json_logic(self, act_value):
        data = self.is_json(act_value)
        if not data:
            return None
        logic_data = jsonLogic(data, self.builder.context_data)
        if data == logic_data:
            return None

        return logic_data

    def apply_action(self, action, cfg, logic_res):
        logger.debug(f"comupte apply_action--> {action} field: {self.key} ")
        if action.get("type") == "property":
            item = action.get("property").get("value")
            value = action.get("state")
            if "validate" in item:
                item = item.split(".")[1]
            cfg[item] = value
            logger.debug(f"{item} --> {cfg[item]}")
        elif action.get("type") == "value":
            if "=" not in action.get("value"):
                cfg[action.get("value")] = logic_res
                logger.debug(
                    f"complete <--> {action.get('value')} = {cfg[action.get('value')]}"
                )
                self.properties[action.get("value")] = cfg[action.get("value")]
            else:
                func = action.get("value").strip().split("=", 1)
                if "{" in func[1] or "}" in func[1]:
                    resjl = self.eval_action_value_json_logic(func[1])
                else:
                    resjl = func[1].replace('"', "")
                if resjl is not None:
                    cfg[func[0].strip()] = resjl
                    logger.debug(
                        f"complete <-->{func[0].strip()} = {cfg[func[0].strip()]}"
                    )
                    self.properties[func[0].strip()] = cfg[func[0].strip()]
                    if func[0].strip() == "value":
                        self.value = resjl
                        self.defaultValue = resjl
                else:
                    logger.debug(f"complete <--> logic is none")
        return cfg.copy()

    def compute_logic(self, json_logic, actions, cfg):
        logic_res = jsonLogic(json_logic, self.builder.context_data)
        logger.debug(f" data --> {self.builder.context_data.get('form')}")
        logger.debug(f"comupte json_logic--> {json_logic}  -> {logic_res}")
        if logic_res:
            for action in actions:
                if action:
                    cfg = self.apply_action(action.copy(), cfg, logic_res)
        return cfg

    def eval_logic(self, cfg):
        logger.debug(f"before_logic {cfg['key']}")
        if cfg.get("logic"):
            for logic in cfg.get("logic"):
                if logic.get("trigger") and logic.get("trigger").get("json"):
                    actions = logic.get("actions", [])
                    json_logic = logic.get("trigger").get("json")
                    cfg = self.compute_logic(json_logic, actions, cfg)
        return cfg.copy()

    def make_config_new(self, component={}, disabled=False, cls_width="12"):
        if not component:
            component = self.raw
        cfg_map = self.builder.theme_cfg.form_component_default_cfg.copy()
        cfg = {}
        cvalue = self.value
        for key, value in component.items():
            if key not in cfg_map:
                if isinstance(value, list) and key == "attrs":
                    for prop in value:
                        if prop["attr"] not in cfg:
                            cfg[prop["attr"]] = prop["value"]
                elif isinstance(value, dict) and key not in [
                    "conditional",
                    "logic",
                ]:
                    for k, v in value.items():
                        if k not in cfg:
                            cfg[k] = v
                else:
                    cfg[key] = value
            else:
                if isinstance(cfg_map[key], dict):
                    if component.get(key):
                        node_cfg = cfg_map.get(key)
                        node = value
                        for iitem in node_cfg:
                            k = node_cfg[iitem]
                            v = node.get(iitem, "")
                            if k and k not in cfg:
                                cfg[k] = v
                else:
                    k = cfg_map[key]
                    v = value
                    if k:
                        cfg[k] = v
        if not cfg.get("customClass"):
            cfg["customClass"] = f" col-{self.size}-{self.width} "
        if cfg.get("customClass"):
            if "col-" not in cfg["customClass"]:
                cfg["customClass"] = (
                    f" {cfg['customClass']} " f"col-{self.size}-{self.width} "
                )
        if self.offset > 0:
            cfg["customClass"] = (
                f" {cfg['customClass']} " f"offset-{self.size}-{self.offset} "
            )

        if disabled:
            cfg["disabled"] = disabled
        cfg["readonly"] = self.readonly
        if self.builder.editable_fields:
            if self.key not in self.builder.editable_fields:
                cfg["readonly"] = True
        cfg["items"] = self.component_items
        cfg["value"] = cvalue
        if not cfg.get("model"):
            cfg["model"] = self.builder.model
        if self.unique:
            cfg["required"] = True
        if self.hidden:
            cfg["hidden"] = True
        cfg["modal_form"] = self.modal
        return cfg

    def add_security(self, context):
        kwargs_def = {
            **context,
            **{
                "security_headers": {
                    **self.security_headers,
                    "token": self.authtoken,
                    "req_id": self.req_id,
                    "authtoken": self.authtoken,
                }
            },
        }
        return kwargs_def.copy()

    def render_template(self, name: str, context: dict):
        cfg = self.add_security(context.copy())
        template = self.builder.tmpe.get_template(name)
        return template.render(cfg)

    def log_render(self, cfg, size=""):
        logger.debug("-------------------------")
        logger.debug(self.key)
        logger.debug("))))))))))))))))))))))))))))")
        logger.debug(self.raw)
        logger.debug("~~~~~~~~~~~~~~~~~~~~~~~~~")
        logger.debug(f"cfg: {cfg}")
        logger.debug("~~~~~~~~~~~~~~~~~~~~~~~~~")
        logger.debug(f"data {self.builder.main.form_data.get(self.key)}")
        logger.debug("-------------------------/")

    def compute_logic_and_condition(self):
        cfg = self.make_config_new(
            self.raw, disabled=self.builder.disabled, cls_width=f"12"
        )
        if self.has_logic:
            cfg = self.eval_logic(cfg.copy())
        if self.has_conditions:
            cfg = self.aval_conditional(cfg)
        return cfg.copy()

    def render(self, size="12", log=False):
        cfg = self.compute_logic_and_condition()
        if log:
            self.log_render(cfg, size)
        if self.key == "submit":
            return ""
        html = self.make_html(cfg)
        return html

    def make_html(self, cfg):
        return self.render_template(
            self.builder.theme_cfg.get_template(
                "components", self.component_tmp
            ),
            cfg,
        )

    def compute_data_table(self, data):
        return data.copy()

    def get_filter_object(self):
        return self.search_object.copy()

    def eval_components(self):
        if self.search_area:
            self.builder.search_areas.append(self)
        if self.tableView:
            if not self.survey and not self.multi_row:
                self.builder.table_colums[self.key] = self.label
        self.builder.components[self.key] = self
        if (
                self.key
                and self.key is not None
                and self.type not in ["columns", "column", "well", "panel"]
                and self.key not in self.builder.filter_keys
        ):
            self.builder.filters.append(self)
            self.builder.filter_keys.append(self.key)
        if self.has_logic or self.has_conditions:
            self.builder.components_logic.append(self)
        if not self.type == "table":
            self.compute_logic_and_condition()

    def compute_data(self):
        for component in self.component_items:
            component.compute_data()

    def load_data(self):
        for component in self.component_items:
            component.load_data()


# global
class layoutComponent(CustomComponent):
    def eval_components(self):
        super().eval_components()


class formComponent(CustomComponent):
    def eval_components(self):
        for cmp in self.raw.get("components", []):
            component = self.builder.get_component_object(cmp)
            if component:
                component.parent = self
                component.eval_components()
                self.component_items.append(component)
        super().eval_components()
        # self.builder.context_data['form'] = self.builder.main.form_data.copy()


class resourceComponent(CustomComponent):
    def eval_components(self):
        for cmp in self.raw.get("components", []):
            component = self.builder.get_component_object(cmp)
            if component:
                component.parent = self
                component.eval_components()
                self.component_items.append(component)
        super().eval_components()
        # self.builder.context_data['form'] = self.builder.main.form_data.copy()

    @property
    def type(self):
        return "form"


class containerComponent(formComponent):
    @property
    def title(self):
        title = self.raw.get("title")
        if not title:
            title = self.raw.get("label")

        if self.i18n.get(self.language):
            return self.i18n[self.language].get(title, title)
        else:
            return title

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(containerComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg["label"] = self.title
        return cfg


class textfieldComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.regex = re.compile(
            r"^(?:http|ftp)s?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
            r"localhost|"  # localhost...
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )
        self.defaultValue = self.raw.get("defaultValue", "")

    @CustomComponent.value.setter
    def value(self, value):
        clean = re.compile("<.*?>")
        val = re.sub(clean, "", str(value))
        # self.form['value'] = val or ''
        self.builder.main.form_data[self.key] = val or ""

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super().make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg["is_url"] = False
        if self.regex.match(str(self.value)):
            cfg["is_url"] = True
        return cfg


class textareaComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.defaultValue = self.raw.get("defaultValue", "")
        self.typeobj = self.properties.get("type")
        if self.typeobj == "json":
            self.component_tmp = "jsondata"
            self.defaultValue = "{}"

    @CustomComponent.value.setter
    def value(self, value):
        clean = re.compile("<.*?>")
        val = re.sub(clean, "", str(value))
        # self.form['value'] = val
        self.builder.main.form_data["key"] = val

    def load_data(self):
        if not self.builder.main.form_data.get(self.key):
            self.builder.main.form_data[self.key] = self.defaultValue


class numberComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.defaultValue = self.raw.get("defaultValue", False)
        self.data_type = float if self.raw.get("requireDecimal") else int
        self.data_type_filter = (
            "decimal" if self.raw.get("requireDecimal") else "integer"
        )
        self.search_object = {
            "id": self.key,
            "label": self.label,
            "type": "integer",
            "input": "text",
            "value_separator": "|",
            "default_operator": "equal",
            "operators": [
                "equal",
                "not_equal",
                "greater",
                "greater_or_equal",
                "less",
                "less_or_equal",
                "in",
                "not_in",
                "is_null",
            ],
        }
        self.aval_validate_row()

    def aval_validate_row(self):
        if self.raw.get("validate"):
            if self.raw.get("validate").get("min"):
                self.min = self.data_type(self.raw.get("validate").get("min"))
            if self.raw.get("validate").get("max"):
                self.max = self.data_type(self.raw.get("validate").get("max"))

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super().make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        # TODO  FIX validae min max value
        if self.raw.get("validate"):
            for k, v in self.raw.get("validate").items():
                try:
                    cfg[k] = self.data_type(v)
                except Exception as e:
                    cfg[k] = v
        if self.defaultValue:
            cfg["defaultValue"] = self.defaultValue
        return cfg

    def load_data(self):
        if not self.builder.main.form_data.get(self.key):
            self.builder.main.form_data[self.key] = self.defaultValue


class infoComponent(CustomComponent):
    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(infoComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg["customClass"] = f" col-{self.size}-{self.width} "
        return cfg


class passwordComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.defaultValue = self.raw.get("defaultValue", "")


class checkboxComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.search_object = {
            "id": self.key,
            "label": self.label,
            "type": "boolean",
            "input": "radio",
            "values": {"true": "Yes", "false": "No"},
            "operators": ["equal", "is_null"],
        }
        self.chk = self.properties.get("template")
        if self.chk:
            self.component_tmp = "checkbox_chk"

    def compute_data(self):
        # data = super(checkboxComponent, self).compute_data(data)
        # new_dict = data.copy()
        if not self.builder.main.form_data.get(self.key):
            self.builder.main.form_data[self.key] = False
        else:
            self.builder.main.form_data[self.key] = True
        super().compute_data()


class selectboxesComponent(CustomComponent):
    @property
    def values_labels(self):
        comp = self.builder.component.get(self.key)
        builder_values = comp.raw.get("values")
        values_labels = {}
        for b_val in builder_values:
            if self.value and b_val.get("value"):
                if self.i18n.get(self.language):
                    label = self.i18n[self.language].get(
                        b_val["label"], b_val["label"]
                    )
                else:
                    label = b_val["label"]
                val = {
                    "key": b_val["value"],
                    "label": label,
                    "value": self.value.get(b_val["value"]),
                }
                values_labels[b_val["value"]] = val
        return values_labels


class selectComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.item_data = {}
        self.template_label_keys = []
        self.dataSrc = self.raw.get("dataSrc")
        self.valueProperty = self.raw.get("valueProperty")
        self.selectValues = self.raw.get("selectValues")
        self.defaultValue = self.raw.get("defaultValue", "")
        self.selected_id = ""
        self.resource_id = ""
        self.url = ""
        self.header_key = ""
        self.header_value_key = ""
        self.path_value = ""

        self.idPath = self.raw.get("idPath", "")
        self.multiple = self.raw.get("multiple", False)
        self.search_object = {
            "id": self.key,
            "label": self.label,
            "type": "string",
            "input": "select",
            "multiple": 1,
            "operators": [
                "equal",
                "not_equal",
                "in",
                "not_in",
                "is_null",
                "is_not_null",
                "is_empty",
                "is_not_empty",
                "contains",
            ],
            "plugin": "selectpicker",
            "plugin_config": {
                "liveSearch": 1,
                "width": "auto",
                "size": "auto",
            },
            "values": {},
        }
        if self.multiple:
            self.component_tmp = "selectmulti"
        if self.dataSrc and self.dataSrc in ["resource", "custom"]:
            if self.raw.get("template"):
                self.template_label_keys = decode_resource_template(
                    self.raw.get("template")
                )
            else:
                self.template_label_keys = decode_resource_template(
                    "<span>{{ item.label }}</span>"
                )
            if self.dataSrc == "custom" and not self.idPath:
                self.idPath = "rec_name"
            if self.raw.get("data") and self.raw.get("data").get("resource"):
                self.resource_id = self.raw.get("data") and self.raw.get(
                    "data"
                ).get("resource")
        if self.dataSrc and self.dataSrc == "url":
            self.url = self.raw.get("data").get("url")
            self.header_key = (
                self.raw.get("data", {}).get("headers", {})[0].get("key")
            )
            self.header_value_key = (
                self.raw.get("data", {}).get("headers", [])[0].get("value")
            )

    def make_resource_list(self):
        resource_list = self.resources
        self.raw["data"] = {"values": []}
        for item in resource_list:
            if self.dataSrc == "resource":
                label = fetch_dict_get_value(item, self.template_label_keys[:])
                iid = item["rec_name"]
            elif self.dataSrc == "custom":
                label = fetch_dict_get_value(item, self.template_label_keys[:])
                if not item.get(self.idPath):
                    logger.error(
                        f" No key {self.idPath} in resouces for source Custom"
                    )
                iid = item.get(self.idPath)
            else:
                label = item[self.properties["label"]]
                iid = item[self.properties["id"]]
            self.search_object["values"].update({iid: label})
            self.raw["data"]["values"].append({"label": label, "value": iid})

    @property
    def value_label(self):
        # value = self.raw['value']
        comp = self.builder.components.get(self.key)
        values = comp.raw.get("data") and comp.raw["data"].get("values")
        for val in values:
            if comp.value and val["value"] == (type(val["value"])(comp.value)):
                label = val["label"]
                if self.i18n.get(self.language):
                    return self.i18n[self.language].get(label, label) or ""
                else:
                    return label or ""

    @property
    def value_labels(self):
        comp = self.builder.components.get(self.key)
        values = comp.raw.get("data") and comp.raw["data"].get("values")
        value_labels = []
        for val in values:
            if val and self.value and str(val["value"]) in self.value:
                if self.i18n.get(self.language):
                    value_labels.append(
                        self.i18n[self.language].get(
                            val["label"], val["label"]
                        )
                    )
                else:
                    value_labels.append(val["label"])
        return value_labels or []

    @property
    def data(self):
        return self.raw.get("data")

    @property
    def values(self):
        return self.raw.get("data", {}).get("values")

    def get_default(self):
        logger.info(f"self.defaultValue -> {self.defaultValue}")
        default = self.defaultValue
        if self.multiple:
            if self.defaultValue:
                default = [self.defaultValue]
            else:
                default = []
        if (
                self.valueProperty
                and not self.selected_id
                and self.builder.new_record
        ):
            if "." in self.valueProperty:
                to_eval = self.valueProperty.split(".")
                if len(to_eval) > 0:
                    obj = self.builder.context_data.get(to_eval[0], {})
                    if obj and isinstance(obj, dict):
                        self.selected_id = obj.get(to_eval[1], "")
                if self.multiple:
                    default.append(self.selected_id)
                else:
                    default = self.selected_id
        logger.info(f"res default -> {default}")
        return default

    def load_data(self):
        if (
                not self.builder.main.form_data.get(self.key)
                and self.builder.new_record
                and (self.defaultValue or self.valueProperty)
        ):
            self.builder.main.form_data[self.key] = self.get_default()
        else:
            if (
                    self.builder.main.form_data.get(self.key)
                    and self.multiple
                    and not type(self.builder.main.form_data[self.key]) == list
            ):
                d = self.builder.main.form_data[self.key]
                self.builder.main.form_data[self.key] = []
                if d:
                    self.builder.main.form_data[self.key].append(d)

    def compute_data(self):
        if self.multiple:
            if self.builder.main.form_data.get(self.key, False) is False:
                self.builder.main.form_data[self.key] = self.get_default()
            elif not type(self.builder.main.form_data[self.key]) == list:
                d = self.builder.main.form_data[self.key]
                self.builder.main.form_data[self.key] = []
                if d:
                    self.builder.main.form_data[self.key].append(d)
        else:
            if not self.builder.main.form_data.get(self.key):
                self.builder.main.form_data[self.key] = self.get_default()
        super().compute_data()

    def compute_data_table(self, data):
        if self.multiple:
            val = ", ".join(self.value_labels) or ""
        else:
            val = self.value_label
        res = data.copy()
        res[self.key] = val
        return res.copy()

    def get_filter_object(self):
        self.search_object["values"] = self.values
        return self.search_object

    def eval_components(self):
        if self.dataSrc:
            self.builder.components_ext_data_src.append(self)
        super().eval_components()

    def apply_action(self, action, cfg, logic_res):
        logger.info(f" {self.key} ")
        new_cfg = super().apply_action(action, cfg, logic_res)
        has_url = self.properties.get("url")
        logger.info(f" {self.key} has_url -->{has_url}")
        if has_url and not has_url == self.url:
            self.url = has_url
        return new_cfg


class radioComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.search_object = {
            "id": self.key,
            "label": self.label,
            "type": "string",
            "input": "select",
            "operators": [
                "equal",
                "not_equal",
                "in",
                "not_in",
                "is_null",
                "is_not_null",
                "is_empty",
                "is_not_empty",
                "contains",
            ],
            "values": {},
        }

    @property
    def values_labels(self):
        comp = self.builder.components.get(self.key)
        builder_values = comp.raw.get("values")
        values_labels = {}

        for b_val in builder_values:
            if self.i18n.get(self.language):
                label = self.i18n[self.language].get(
                    b_val["label"], b_val["label"]
                )
            else:
                label = b_val["label"]
            val = {
                "key": b_val["value"],
                "label": label,
                "value": b_val["value"] == self.value,
            }
            values_labels[b_val["value"]] = val
        return values_labels

    @property
    def value_label(self):
        comp = self.builder.components.get(self.key)
        builder_values = comp.raw.get("values")
        value_label = {}

        for b_val in builder_values:
            if b_val["value"] == self.value:
                if self.i18n.get(self.language):
                    return self.i18n[self.language].get(
                        b_val["label"], b_val["label"]
                    )
                else:
                    return b_val["label"]
        else:
            return False

    def compute_data_table(self, data):
        res = data.copy()
        res[self.key] = self.value_label
        return res.copy()

    @property
    def values(self):
        return self.raw.get("values", [])

    def get_filter_object(self):
        self.search_object["values"] = self.values
        return self.search_object

    def load_data(self):
        if self.key in self.builder.main.form_data:
            return
        datas = {
            k: v
            for k, v in self.builder.main.form_data.items()
            if k.startswith(f"{self.key}")
        }
        if datas:
            k = list(datas.keys())[0]
            val = k.split("-")
            if len(val) > 0:
                self.builder.main.form_data[val[0]] = val[1]


class buttonComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.headers = []
        # self.modal = False

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(buttonComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        if cfg.get("modalEdit"):
            self.component_tmp = "modalbutton"
        return cfg


class emailComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.defaultValue = self.raw.get("defaultValue", "")


class urlComponent(CustomComponent):
    pass


class ilinkComponent(CustomComponent):
    pass


class phoneNumberComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.defaultValue = self.raw.get("defaultValue", "")
        self.search_object = {
            "id": "id",
            "label": "Identifier",
            "type": "string",
            "default_operator": "equal",
            "placeholder": "____-____-____",
            "operators": ["equal", "not_equal"],
        }


# TODO: tags, address


class datetimeComponent(CustomComponent):
    # format H 24 d/m/y H:i
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.headers = []
        self.is_date = self.raw.get("enableDate", True)
        self.is_time = self.raw.get("enableTime", True)
        self.min = self.raw["widget"]["minDate"]
        self.max = self.raw["widget"]["maxDate"]
        # self.client_format = self.builder.settings['ui_date_mask']
        self.format = self.raw["format"]
        self.value_date = None
        self.server_format = self.builder.settings["server_datetime_mask"]
        self.defaultDate = self.properties.get("defaultDate")
        self.isodate_regex = re.compile(
            "(\d{4}-\d{2}-\d{2})[A-Z]+(\d{2}:\d{2}:\d{2})"
        )
        self.search_template = {
            "date": {
                "id": self.key,
                "label": self.label,
                "type": "date",
                "default_operator": "equal",
                "operators": [
                    "equal",
                    "not_equal",
                    "greater",
                    "greater_or_equal",
                    "less",
                    "less_or_equal",
                    "is_null",
                ],
                "get_format": self.builder.settings["server_date_mask"],
            },
            "datetime": {
                "id": self.key,
                "label": self.label,
                "type": "datetime",
                "default_operator": "equal",
                "operators": [
                    "equal",
                    "not_equal",
                    "greater",
                    "greater_or_equal",
                    "less",
                    "less_or_equal",
                ],
                "get_format": self.builder.settings["server_datetime_mask"],
            },
            "time": {
                "id": self.key,
                "label": self.label,
                "type": "datetime",
                "default_operator": "equal",
                "operators": [
                    "equal",
                    "not_equal",
                    "greater",
                    "greater_or_equal",
                    "less",
                    "less_or_equal",
                ],
                "get_format": self.builder.settings["server_datetime_mask"],
            },
        }
        # for dt --> 2021-08-11T17:22:04

        self.dte = DateEngine(
            UI_DATETIME_MASK=self.builder.settings["ui_datetime_mask"],
            SERVER_DTTIME_MASK=self.builder.settings["server_datetime_mask"],
        )
        self.isodate_regex = self.dte.isodate_regex

        self.size = 12

    def parse_date(self, val):
        value_date = val
        if isinstance(val, str) and self.isodate_regex.match(val):
            v = self.isodate_regex.search(val).group()
            if not self.is_time:
                value_date = self.dte.server_datetime_to_ui_date_str(v)
            else:
                value_date = self.dte.server_datetime_to_ui_datetime_str(v)
        return value_date

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super().make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg["is_time"] = self.is_time
        cfg["is_date"] = self.is_date
        cfg["min"] = self.min
        cfg["max"] = self.max
        cfg["client_format"] = self.format
        cfg["base_format"] = "Z"
        cfg["server_format"] = self.server_format
        # cfg['customClass'] = self.raw['customClass']
        return cfg

    def load_data(self):
        if not self.builder.main.form_data.get(self.key) and self.defaultValue:
            if self.defaultDate == "today":
                self.builder.main.form_data.get[self.key] = self.dte.today

    def compute_data_table(self, data):
        datestr = self.builder.main.form_data.get(self.key, "")
        data[self.key] = self.parse_date(datestr)
        return data.copy()

    def get_filter_object(self):
        if self.is_date and self.is_time:
            return self.search_template["datetime"]
        elif self.is_date:
            return self.search_template["date"]
        elif self.is_time:
            return self.search_template["time"]
        return {}

    def compute_data(self):
        if not self.builder.main.form_data.get(self.key):
            self.builder.main.form_data[self.key] = "1970-01-01T00:00:00"
        super().compute_data()

    @property
    def value(self):
        if (
                self.builder.main.form_data.get(self.key, self.defaultValue)
                == "1970-01-01T00:00:00"
        ):
            val = ""
        else:
            val = self.builder.main.form_data.get(self.key, self.defaultValue)
        return val


class dateComponent(CustomComponent):
    pass


class timeComponent(CustomComponent):
    pass


class currencyComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.search_object = {
            "id": self.key,
            "label": self.label,
            "type": "double",
            "input": "text",
            "value_separator": "|",
            "default_operator": "equal",
            "operators": [
                "equal",
                "not_equal",
                "greater",
                "greater_or_equal",
                "less",
                "less_or_equal",
                "in",
                "not_in",
            ],
        }


class surveyRowComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.headers = []
        self.grid = None
        self.min_row = 1
        self.max_row = 1
        self.row_questions = {}
        self.row_values = []
        self.row_result = ""
        self.size = "md"
        self.width = 12

    @property
    def group(self):
        return self.questions["value"]

    def eval_components(self):
        row_slot_width = int(12 - (len(self.row_values) + 1))
        raw_info = OrderedDict()
        raw_info["key"] = f"{self.group}-info"
        raw_info["type"] = "info"
        raw_info["label"] = self.questions["label"]
        info = self.builder.get_component_object(raw_info)
        info.width = row_slot_width
        info.eval_components()
        info.parent = self
        self.component_items.append(info)

        raw_radio = OrderedDict()
        raw_radio["key"] = f"{self.parent_key}_surveyRow_{self.group}"
        raw_radio["type"] = "radio"
        raw_radio["label"] = ""
        raw_radio["values"] = self.row_values
        raw_radio["value"] = self.row_result
        raw_radio["inline"] = True
        radio = self.builder.get_component_object(raw_radio)
        radio.width = row_slot_width
        radio.parent = self
        radio.parent_key = self.parent_key
        radio.eval_components()
        self.component_items.append(radio)
        super().eval_components()

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(surveyRowComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg["row_id"] = self.row_id
        cfg["customClass"] = f" col-{self.size}-{self.width} "
        return cfg


class surveyComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.headers = []
        self.survey = True
        self.questions = []
        self.default_data = {self.key: {}}
        self.rows_data = {}

    def eval_components(self):
        self.component_items = []

        for row_id in range(len(self.raw["questions"])):
            row = self.get_row(row_id)
            row.parent = self
            self.component_items.append(row)
        super().eval_components()

    @property
    def rows(self):
        return self.component_items

    def get_row(self, row_id):
        value = ""
        raw_row = OrderedDict()
        raw_row["key"] = f"{self.key}_surveyRow_{str(uuid.uuid4())}"
        raw_row["type"] = "surveyRow"
        row = self.builder.get_component_object(raw_row)
        row.parent = self
        row.parent_key = self.key
        row.row_values = self.raw["values"][:]
        row.questions = self.raw["questions"][row_id]
        # row.row_result = self.builder.main.form_data[self.key]
        row.size = 12
        row.eval_components()
        return row

    def compute_data(self):
        datas = {
            k: v
            for k, v in self.builder.main.form_data.items()
            if k.startswith(f"{self.key}_surveyRow_")
        }
        to_pop = []
        if datas:
            for k, v in datas.items():
                base = k.split("_surveyRow_")
                to_pop.append(k)
                self.rows_data.update({base[1]: v})
        for k in to_pop:
            self.builder.main.form_data.pop(k)
        self.builder.main.form_data[self.key] = self.rows_data.copy()

    def load_data(self):
        datas = self.builder.main.form_data.get(self.key, [])
        if datas:
            for k, v in datas.items():
                self.builder.main.form_data[f"{self.key}_surveyRow_{k}"] = v
            self.builder.main.form_data.pop(self.key)


class signatureComponent(CustomComponent):
    pass


class htmlelementComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super().make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg["customClass"] = self.raw.get("customClass")
        return cfg


class contentComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.editor = self.properties.get("editor")
        self.eval_tmp = self.properties.get("eval_tmp", False)
        self.component_tmp = "content"
        self.is_html = True
        if self.editor:
            self.component_tmp = "editor"
        if self.eval_tmp:
            self.component_tmp = "contenteval"

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super().make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        val = cfg.get("html", "")
        if self.value:
            val = self.value

        cfg["html"] = val
        cfg["eval_tmp"] = self.eval_tmp

        return cfg

    def eval_components(self):
        self.builder.html_components.append(self.key)
        super().eval_components()

    def load_data(self):
        if self.eval_tmp:

            def parse_json(inputd):
                """Custom filter"""
                res = {}
                try:
                    return json.loads(inputd)
                except Exception as e:
                    logger.warning(inputd)
                    logger.exception(e)
                    return res

            context_data = self.builder.context_data.copy()
            self.builder.main.form_data[self.key] = ""
            form_o = copy.copy(self.builder.main.form_data)
            user_o = copy.deepcopy(context_data.get("user", {}))
            data_o = copy.deepcopy(context_data.get("app", {}))
            context = {"form": form_o, "user": user_o, "app": data_o}
            val = self.raw.get("html", "")
            myenv = jinja2.Environment()
            myenv.filters["parse_json"] = parse_json
            template = myenv.from_string(val)
            self.builder.main.form_data[self.key] = template.render(context)


class columnComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.size = self.raw["size"]
        self.width = self.raw["width"]
        self.offset = self.raw["offset"]
        self.raw_key = ""
        self.key_prefix = ""
        # self.currentWidth = self.raw['currentWidth']

    def eval_components(self):
        for component in self.raw["components"]:
            componet_obj = self.builder.get_component_object(component)
            componet_obj.parent = self
            componet_obj.parent_key = self.key
            if not componet_obj.type == "columns":
                componet_obj.parent_key = self.parent_key
            # componet_obj.value = self.form.get(component['key'], componet_obj.defaultValue)
            if self.key_prefix:
                componet_obj.raw_key = component["key"]
                componet_obj.key = f"{self.key_prefix}_{component['key']}"
            # componet_obj.form = self.form.copy()
            componet_obj.eval_components()
            self.component_items.append(componet_obj)
        super().eval_components()


class columnsComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.key_prefix = ""
        self.col_max_size = 12

    def check_slots(self, cols_size, slot):
        res = False
        if cols_size + slot.width + slot.offset <= self.col_max_size:
            res = True
        return res

    def eval_components(self):
        cols_size = 0
        for col in self.raw.get("columns"):
            col["type"] = "column"
            column_slot = self.builder.get_component_object(col)
            if self.check_slots(cols_size, column_slot):
                cols_size += column_slot.width + column_slot.offset
                column_slot.key_prefix = self.key_prefix
                column_slot.parent_key = self.parent_key
                if self.key_prefix:
                    column_slot.parent = self.parent
                else:
                    column_slot.parent = self
                column_slot.eval_components()
                self.component_items.append(column_slot)
        super().eval_components()


class fieldsetComponent(CustomComponent):
    def eval_components(self):
        for component in self.raw["components"]:
            componet_obj = self.builder.get_component_object(component)
            # componet_obj.value = self.builder.main.form_data.get(self.key, componet_obj.defaultValue)
            componet_obj.eval_components()
            self.component_items.append(componet_obj)
        super().eval_components()


class panelComponent(CustomComponent):
    def has_filter(self, id):
        return False

    @property
    def title(self):
        CustomComponent = self.builder.components.get(self.key)
        title = CustomComponent.raw.get("title")
        if not title:
            title = CustomComponent.raw.get("label")

        if self.i18n.get(self.language):
            return self.i18n[self.language].get(title, title)
        else:
            return title

    @property
    def label(self):
        label = self.raw.get("title")
        if self.i18n.get(self.language):
            return self.i18n[self.language].get(label, label)
        else:
            return label

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(panelComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg["label"] = self.raw.get("title")
        return cfg

    def eval_components(self):
        for component in self.raw["components"]:
            componet_obj = self.builder.get_component_object(component)
            componet_obj.parent = self
            componet_obj.eval_components()
            self.component_items.append(componet_obj)
        super().eval_components()


class tabPanelComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.headers = []
        self.active = False
        self.add_enabled = False
        self.tab_id = f"{self.key}-tab"
        self.panel_id = self.key
        self.href = f"#{self.panel_id}"
        self.controls = self.panel_id

    def eval_components(self):
        for component in self.raw["components"]:
            componet_obj = self.builder.get_component_object(component)
            componet_obj.parent = self
            componet_obj.eval_components()
            self.component_items.append(componet_obj)
        super().eval_components()


class tabsComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.headers = []
        self.panels = []
        self.component_items = []
        self.tabs = True
        self.add_enabled = False
        self.default_data = {self.key: []}

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(tabsComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg["panels"] = self.panels
        return cfg

    def eval_components(self):
        count = 0
        for tab in self.raw["components"]:
            tab["type"] = "tabPanel"
            panel = self.builder.get_component_object(tab)
            panel.parent = self
            if count == 0:
                panel.active = True
            self.panels.append(panel)
            self.component_items.append(panel)
            panel.eval_components()
            count += 1
        super().eval_components()


# Data components


class datagridRowComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.headers = []
        self.grid = None
        self.datagridRow = True
        self.min_row = 1
        self.max_row = 1
        self.row_data = {}
        self.row_id = 0
        self.col_size = 12

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(datagridRowComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg["parent_key"] = self.parent_key
        cfg["row_id"] = self.row_id
        return cfg

    def eval_components(self):
        for component in self.parent.raw.get("components"):
            # Copy CustomComponent raw (dict), to ensure no binding and overwrite.
            component_raw = component.copy()
            if component_raw.get("type") == "columns":
                component_obj = self.builder.get_component_object(
                    component_raw
                )
                component_obj.key_prefix = self.key
                component_obj.eval_components()
            else:
                component_raw["key"] = f"{self.key}_{component_raw.get('key')}"
                component_obj = self.builder.get_component_object(
                    component_raw
                )
            component_obj.parent = self
            component_obj.parent_key = self.parent_key
            self.component_items.append(component_obj)
        super().eval_components()


class datagridComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.headers = []
        self.multi_row = True
        self.min_row = 1
        self.max_row = 1
        self.add_enabled = True
        if self.raw.get("disableAddingRemovingRows"):
            self.add_enabled = False
        self.row_id = 0
        self.components_ext_data_src = []
        self.tables = []
        self.rows = []
        self.rows_data = []
        self.rows_id = []
        self.default_data = {self.key: []}
        self.curr_data = []
        self.aval_validate_row()

    def aval_validate_row(self):
        if self.raw.get("validate"):
            if self.raw.get("validate").get("minLength"):
                self.min_row = int(self.raw.get("validate").get("minLength"))
            if self.raw.get("validate").get("maxLength"):
                self.max_row = int(self.raw.get("validate").get("maxLength"))

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(datagridComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg["model"] = self.builder.model
        cfg["min_rows"] = self.min_row
        cfg["max_rows"] = self.max_row
        cfg["rec_name"] = self.builder.main.form_data.get("rec_name", "")
        cfg["add_remove_enabled"] = self.add_enabled
        return cfg

    def eval_components(self):
        super().eval_components()

    def get_row(self, row_id):
        raw_row = OrderedDict()
        raw_row["key"] = f"{self.key}_dataGridRow_{row_id}"
        raw_row["type"] = "datagridRow"
        row = self.builder.get_component_object(raw_row)
        row.row_id = row_id
        row.parent = self
        row.parent_key = self.key
        row.eval_components()
        self.component_items.append(row)
        self.rows.append(row)
        return row

    def add_row(self, num_rows):
        self.get_row(num_rows)
        return self.rows

    def load_data(self):
        datas = self.builder.main.form_data.get(self.key, [])
        if datas:
            self.rows = []
            row_n = 0
            for row_data in datas:
                clean_data = self.builder.clean_record(row_data)
                for k, v in clean_data.items():
                    self.builder.main.form_data[
                        f"{self.key}_dataGridRow_{row_n}_{k}"
                    ] = v
                self.get_row(row_n)
                row_n += 1
            self.builder.main.form_data.pop(self.key)

    def compute_data(self):
        self.builder.main.form_data[self.key] = []
        datas = {
            k: v
            for k, v in self.builder.main.form_data.items()
            if k.startswith(f"{self.key}_dataGridRow_")
        }
        if datas:
            # external_proxy_uri_configs _dataGridRow_ 0 _ domain
            d_res = {}
            for k, v in datas.items():
                base = k.split("_dataGridRow_")
                id_and_field = base[1].split("_")
                if not d_res.get(id_and_field[0]):
                    d_res[id_and_field[0]] = {}
                d_res[id_and_field[0]].update({id_and_field[1]: v})

            for k, v in d_res.items():
                self.builder.main.form_data[self.key].append(v.copy())

            for k in datas.keys():
                self.builder.main.form_data.pop(k)

    @property
    def labels(self):
        labels = OrderedDict()
        for comp in self.raw["components"]:
            if self.i18n.get(self.language):
                label = self.i18n[self.language].get(
                    comp["label"], comp["label"]
                )
            else:
                label = comp["label"]
            labels[comp["key"]] = label
        return labels

    @property
    def value(self):
        labels = OrderedDict()
        for comp in self.raw["components"]:
            if self.i18n.get(self.language):
                label = self.i18n[self.language].get(
                    comp["label"], comp["label"]
                )
            else:
                label = comp["label"]
            labels[comp["key"]] = label
        return labels


class fileComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)

        self.rows = []
        self.multiple = False  # self.raw.get("multiple")
        self.add_enabled = True
        self.dir = self.raw.get("dir")
        self.webcam = self.raw.get("webcam")
        self.uploaders = True
        self.max_delay_delete = 4
        self.file_url = ""
        # self.component_tmp = "file_container"
        self.default_data = {self.key: []}
        self.search_object = {
            "id": self.key,
            "label": self.label,
            "type": "string",
            "input": "text",
            "default_operator": "is_not_null",
            "operators": ["is_not_null", "is_null"],
        }

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super().make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg["rec_name"] = self.builder.main.form_data.get("rec_name", "")
        cfg["model"] = self.builder.model
        if "no_upload" not in cfg:
            cfg["no_upload"] = False
        if "no_trash_delete" not in cfg:
            cfg["no_trash_delete"] = False
        if "max_delay_delete" not in cfg:
            cfg["max_delay_delete"] = self.max_delay_delete
        return cfg

    # def compute_data(self):
    #     # data = super().compute_data(data)
    #     new_dict = self.default_data.copy()
    #     curr_data = self.form.get(self.key, [])
    #     new_dict[self.key] = curr_data
    #     for i in data.get(self.key):
    #         new_dict[self.key].append(i)
    #     data = {**data, **new_dict}
    #     return data

    # def compute_data_table(self):
    #     this = data[self.key]
    #     res = data.copy()
    #     curr_data = self.form.get(self.key, [])
    #     res[self.key] = curr_data
    #     if isinstance(this, list):
    #         for i in this:
    #             res[self.key].append(i['filename'])
    #     return res.copy()

    @property
    def storage(self):
        return self.raw.get("storage")

    @property
    def url(self):
        return self.file_url

    @property
    def base64(self):
        res = ""
        for val in self.form.get("value"):
            name = val.get("name")
            url = val.get("url")
            res += base64_encode_url(url)
        return res

    def eval_components(self):
        self.builder.uploaders.append(self)
        self.builder.uploaders_keys.append(self.key)
        super().eval_components()


class tableComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.headers = []
        self.filter = {}
        self.table = True
        self.hide_rec_name = False
        self.show_select = False
        self.min_row = 1
        self.max_row = 1
        self.clickKey = "row_action"
        self.rec_name = "rec_name"
        self.col_reorder = "list_order"
        self.form_columns = {}
        self.model = self.properties.get("model")
        self.action_url = self.properties.get("action_url")
        self.url_action_copy = self.properties.get("copy_url", "")
        self.url_action_remove = self.properties.get("remove_url", "")
        self.dom_todo = self.properties.get("dom", "iptilp")
        self.show_owner = self.properties.get("show_owner", "no") == "yes"
        self.show_select_chk = (
                self.properties.get("hide_select_chk", "no") == "no"
        )
        self.meta_to_show = self.properties.get(
            "list_metadata_show", ""
        ).split(",")
        self.order = self.properties.get("order", "")
        self.meta_keys = []
        self.hide_keys = []
        self.columns = {}
        self.responsive = self.is_mobile
        self.row_id = 0
        self.sort_dir = {1: "asc", -1: "desc"}
        self.default_data = {self.key: []}

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(tableComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )

        cfg["tab_id"] = self.key
        cfg["cols"] = [val for key, val in self.columns.items()]
        cfg["tab_responsive"] = self.responsive
        cfg["full_width"] = True
        cfg["rowReorder"] = self.col_reorder
        cfg["model"] = self.model
        cfg["select_chk"] = True
        cfg["columns"] = []
        cfg["order"] = []  # self.order
        for val in self.columns.keys():
            if not val == "check":
                cfg["columns"].append({"data": val})
            else:
                cfg["columns"].append({"data": "check", "defaultContent": ""})
        if self.url_action_copy:
            cfg["columns"].append({
                "data": "copy",
                "defaultContent": ""
            })
            cfg["cols"].append("Copy")
        if self.url_action_remove:
            cfg["columns"].append({
                "data": "delete",
                "defaultContent": ""
            })
            cfg["cols"].append("Delete")

        cfg["click_row"] = {"col": self.clickKey}

        cfg["dom_todo"] = self.dom_todo
        cfg["columnDefs"] = []
        if self.hide_rec_name and "rec_name" not in self.meta_to_show:
            self.meta_keys.append("rec_name")
        elif "rec_name" in self.meta_keys:
            self.meta_keys.remove("rec_name")
        list_keys_cols = list(self.columns.keys())

        user_selected_form_columns = list(self.form_columns.keys())

        for key in ["check", "list_order"]:
            c_conf = {"targets": list_keys_cols.index(key), "width": 10}
            cfg["columnDefs"].append(c_conf)

        list_sorting = self.order.split(",")
        for item in list_sorting:
            r = item.split(":")
            if len(r) > 1:
                col = list_keys_cols.index(r[0])
                val = r[1]
                cfg["order"].append([col, val])

        for key in self.meta_keys:
            if (
                    key not in self.meta_to_show
                    and key not in user_selected_form_columns
            ):
                if key in list_keys_cols:
                    c_conf = {
                        "targets": list_keys_cols.index(key),
                        "visible": False,
                    }
                    cfg["columnDefs"].append(c_conf)
        if self.url_action_copy:
            cfg["url_action_copy"] = self.url_action_copy
        if self.url_action_remove:
            cfg["url_action_remove"] = self.url_action_remove

        return cfg

    def eval_components(self):
        self.builder.tables.append(self)
        # self.builder.components_ext_data_src.append(self)
        super().eval_components()


class wellComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.obj_type = self.properties.get("type")
        self.search_area = self.obj_type == "search_area"
        self.export_area = self.obj_type == "export_area"
        self.import_component = self.obj_type == "import_component"
        getattr(self, f"init_{self.obj_type}")()

    def has_filter(self, name_id):
        for filter in self.filters:
            if filter.get("id") == name_id:
                return True
        return False

    def init_search_area(self):
        self.component_tmp = self.properties.get("type")
        self.object = self.properties.get("object", False)
        self.object_id = self.properties.get("object_id", False)
        self.model = self.properties.get("model", False)
        self.query = self.properties.get("query", {})
        self.table_builder = None
        self.filters = []

    def init_export_area(self):
        self.component_tmp = self.properties.get("type")
        self.search_id = self.properties.get("search_id", False)
        self.model = self.properties.get("model", False)
        self.query = self.properties.get("query", {})
        self.table_builder = None

    def init_import_component(self):
        self.component_tmp = self.properties.get("type")
        self.model = self.properties.get("model", False)

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super().make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        if self.search_area:
            cfg["object"] = self.object
            cfg["object_id"] = self.object_id
            cfg["filters"] = self.filters
            cfg["query"] = self.query

        if self.export_area:
            cfg["search_id"] = self.search_id
            cfg["query"] = self.query

        return cfg

    # def eval_components(self):
    #     self.builder.tables.append(self)
    #     # self.builder.components_ext_data_src.append(self)
    #     super().eval_components()
