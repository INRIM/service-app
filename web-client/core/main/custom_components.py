# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import json
import math
from collections import OrderedDict

from formiodata.components import Component
from formiodata.utils import base64_encode_url, decode_resource_template, fetch_dict_get_value

from .DateEngine import DateEngine
import copy
from json_logic import jsonLogic
import re
import collections

import uuid
import logging
import jinja2

logger = logging.getLogger(__name__)


class CustomComponent(Component):

    def __init__(self, raw, builder, **kwargs):
        # TODO or provide the Builder object?
        # raw =
        super().__init__(copy.deepcopy(raw), builder, **kwargs)

        # i18n (language, translations)
        self.tmpe = builder.tmpe
        self.theme_cfg = builder.theme_cfg
        self.is_mobile = builder.is_mobile
        self.component_items = []
        self.default_data = {
            self.key: ""
        }
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
        self.grid_rows = []
        self.width = 12
        self.size = "lg"
        self.offset = 0
        self.component_tmp = self.raw.get('type')
        self.unique = self.raw.get('unique')
        self.authtoken = self.builder.authtoken
        self.search_object = {
            'id': self.key,
            'label': self.label,
            'default_operator': 'contains',
            'type': 'string'
        }

    def init_filter(self):
        self.search_object = {}

    @property
    def value(self):
        return self.form.get('value')

    @property
    def hidden(self):
        return self.raw.get('hidden')

    @value.setter
    def value(self, value):
        self.form['value'] = value

    @property
    def has_logic(self):
        return self.raw.get("logic", False)

    @property
    def has_conditions(self):
        return self.raw.get("conditional", False)

    @property
    def properties(self):
        return self.raw.get('properties', {})

    def aval_conditional(self, cfg):
        cond = cfg.get("conditional") and cfg.get("conditional").get('json')
        if cond:
            res = not jsonLogic(
                dict(cfg.get("conditional").get('json')), self.builder.context_data)
            logger.info(self.key)
            logger.info(self.builder.context_data['form'])
            logger.info(cond)
            logger.info(res)
            cfg['hidden'] = res
        return cfg.copy()

    def is_json(self, str_test):
        try:
            str_test = json.loads(str_test)
        except ValueError as e:
            str_test = str_test.replace("'", "\"")
            try:
                str_test = json.loads(str_test)
            except ValueError as e:
                return False
        return str_test

    def eval_action_value_json_logic(self, act_value):
        data = self.is_json(act_value)
        if not data:
            return act_value
        # logger.info(self.builder.context_data['form'])
        logic_data = jsonLogic(data, self.builder.context_data)
        logger.info(f"eval_action_value_json_logic result {data} --> {logic_data}")
        return logic_data

    def apply_action(self, action, cfg, logic_res):
        logger.info(f"comupte apply_action--> {action}")
        if action.get("type") == "property":
            item = action.get("property").get("value")
            value = action.get("state")
            if "validate" in item:
                item = item.split(".")[1]
            cfg[item] = value
            logger.info(f"<--> {cfg[item]}")
        elif action.get("type") == "value":
            if "=" not in action.get("value"):
                cfg[action.get("value")] = logic_res
                logger.info(f"complete <--> {cfg[action.get('value')]}")
                if self.properties and action.get('value') in self.properties:
                    self.properties[action.get('value')] = cfg[action.get("value")]
            else:
                func = action.get("value").strip().split('=', 1)
                cfg[func[0].strip()] = self.eval_action_value_json_logic(func[1])
                logger.info(f"complete <--> {cfg[func[0].strip()]}")
                if self.properties and func[0].strip() in self.properties:
                    self.properties[func[0].strip()] = cfg[func[0].strip()]
        return cfg.copy()

    def compute_logic(self, json_logic, actions, cfg):
        logic_res = jsonLogic(json_logic, self.builder.context_data)
        logger.info(f"comupte json_logic--> {json_logic}  -> {logic_res}")
        if logic_res:
            for action in actions:
                if action:
                    cfg = self.apply_action(action.copy(), cfg, logic_res)
        return cfg

    def eval_logic(self, cfg):
        logger.info(f"before_logic {cfg['key']}")
        if cfg.get("logic"):
            for logic in cfg.get("logic"):
                if logic.get("trigger") and logic.get("trigger").get("json"):
                    actions = logic.get("actions", [])
                    json_logic = logic.get("trigger").get("json")
                    cfg = self.compute_logic(json_logic, actions, cfg)
        return cfg.copy()

    def make_config_new(self, component={}, disabled=False, cls_width=" "):
        if not component:
            component = self.raw
        cfg_map = self.theme_cfg.form_component_default_cfg.copy()
        cfg = {}
        cvalue = self.value
        private_keys = ["label", "id", "value"]
        for key, value in component.items():
            if key not in cfg_map:
                if isinstance(value, list) and key == "attrs":
                    for prop in value:
                        if prop['attr'] not in cfg:
                            cfg[prop['attr']] = prop['value']
                elif isinstance(value, dict) and key not in ["conditional", "logic"]:
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
        if "customClass" not in cfg:
            cfg['customClass'] = f" col-{self.size}-{self.width} "
        else:
            if "col-lg-12" in cfg['customClass'].split(" "):
                cfg['customClass'].replace("col-lg-12", f"col-{self.size}-{self.width}")
            else:
                if not "row" in cfg['customClass'].split(" "):
                    cfg['customClass'] = f" {cfg['customClass']} col-{self.size}-{self.width} "
        if self.offset > 0:
            cfg['customClass'] = f" {cfg['customClass']} offset-{self.size}-{self.offset} "
        if disabled:
            cfg['disabled'] = disabled
        if self.builder.editable_fields:
            if self.key not in self.builder.editable_fields:
                cfg['readonly'] = True
        cfg['items'] = self.component_items
        cfg["value"] = cvalue
        cfg['authtoken'] = self.authtoken
        if self.unique:
            cfg['required'] = True
        if not cfg.get('model'):
            cfg['model'] = self.builder.model
        return cfg

    def render_template(self, name: str, context: dict):
        template = self.tmpe.get_template(name)
        return template.render(context)

    def log_render(self, cfg, size=""):
        logger.info("-------------------------")
        logger.info(self.key)
        logger.info("))))))))))))))))))))))))))))")
        logger.info(self.raw)
        logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~")
        logger.info(f"cfg: {cfg}")
        logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~")
        logger.info(self.form)
        logger.info("-------------------------/")

    def compute_logic_and_condition(self):
        cfg = self.make_config_new(
            self.raw, disabled=self.builder.disabled, cls_width=f"")
        if self.has_logic:
            cfg = self.eval_logic(cfg)
        if self.has_conditions:
            cfg = self.aval_conditional(cfg)
        return cfg.copy()

    def render(self, size="12", log=False):
        cfg = self.compute_logic_and_condition()
        if log:
            self.log_render(cfg, size)
        if self.key == "submit":
            return ""
        return self.make_html(cfg)

    def make_html(self, cfg):
        return self.render_template(
            self.theme_cfg.get_template("components", self.component_tmp), cfg)

    def compute_data(self, data):
        return data.copy()

    def compute_data_table(self, data):
        return data.copy()

    def get_filter_object(self):
        return self.search_object.copy()


# global
class layoutComponent(CustomComponent):
    pass


class formComponent(CustomComponent):
    pass


class textfieldComponent(CustomComponent):

    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.regex = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        self.defaultValue = self.raw.get('defaultValue', "")

    @CustomComponent.value.setter
    def value(self, value):
        clean = re.compile('<.*?>')
        val = re.sub(clean, '', str(value))
        self.form['value'] = val or ''

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super().make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg['is_url'] = False
        if self.regex.match(str(self.value)):
            cfg['is_url'] = True
        return cfg


class textareaComponent(CustomComponent):

    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.defaultValue = self.raw.get('defaultValue', "")
        self.typeobj = self.properties.get('type')
        if self.typeobj == "json":
            self.component_tmp = "jsondata"
            self.defaultValue = "{}"

    @CustomComponent.value.setter
    def value(self, value):
        clean = re.compile('<.*?>')
        val = re.sub(clean, '', str(value))
        self.form['value'] = val


class numberComponent(CustomComponent):

    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.defaultValue = self.raw.get('defaultValue', 0)
        self.search_object = {
            'id': self.key,
            'label': self.label,
            'type': 'integer',
            'input': 'text',
            'value_separator': '|',
            'default_operator': 'equal',
            'operators': [
                'equal', 'not_equal',
                'greater', 'greater_or_equal',
                'less', 'less_or_equal',
                'in', 'not_in'
            ]
        }
        self.aval_validate_row()

    def aval_validate_row(self):
        if self.raw.get("validate"):
            if self.raw.get("validate").get("minLength"):
                self.min_row = int(self.raw.get("validate").get("minLength"))
            if self.raw.get("validate").get("maxLength"):
                self.max_row = int(self.raw.get("validate").get("maxLength"))

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super().make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        if self.raw.get("validate"):
            for k, v in self.raw.get("validate").items():
                cfg[k] = v
        return cfg


class infoComponent(CustomComponent):
    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(infoComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg['customClass'] = f" col-{self.size}-{self.width} "
        return cfg


class passwordComponent(CustomComponent):

    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.defaultValue = self.raw.get('defaultValue', "")


class checkboxComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.search_object = {
            'id': self.key,
            'label': self.label,
            'type': 'boolean',
            'input': 'radio',
            'values': {
                "true": 'Yes',
                "false": 'No'
            },
            'operators': ['equal']
        }

    def compute_data(self, data):
        data = super(checkboxComponent, self).compute_data(data)
        new_dict = data.copy()
        if not new_dict.get(self.key):
            new_dict[self.key] = False
        else:
            new_dict[self.key] = True
        data = {**data, **new_dict}
        return data.copy()


class selectboxesComponent(CustomComponent):

    @property
    def values_labels(self):
        comp = self.builder.form_components.get(self.key)
        builder_values = comp.raw.get('values')
        values_labels = {}
        for b_val in builder_values:
            if self.value and b_val.get('value'):
                if self.i18n.get(self.language):
                    label = self.i18n[self.language].get(b_val['label'], b_val['label'])
                else:
                    label = b_val['label']
                val = {'key': b_val['value'], 'label': label, 'value': self.value.get(b_val['value'])}
                values_labels[b_val['value']] = val
        return values_labels


class selectComponent(CustomComponent):

    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.item_data = {}
        self.template_label_keys = []
        self.dataSrc = self.raw.get('dataSrc')
        self.valueProperty = self.raw.get('valueProperty')
        self.selectValues = self.raw.get('selectValues')
        self.selected_id = ""
        self.resource_id = ""
        self.url = ""
        self.header_key = ""
        self.header_value_key = ""
        self.path_value = ""
        self.idPath = self.raw.get('idPath')
        self.multiple = self.raw.get("multiple")
        self.search_object = {
            'id': self.key,
            'label': self.label,
            'type': 'string',
            'input': 'select',
            'operators': [
                'equal', 'not_equal', 'in', 'not_in', 'is_null', 'is_not_null', 'is_empty',
                'is_not_empty'],
            'values': {}

        }

        if self.multiple:
            self.component_tmp = "selectmulti"
        if self.dataSrc and self.dataSrc == "resource":
            if self.raw.get('template'):
                self.template_label_keys = decode_resource_template(self.raw.get('template'))
            else:
                self.template_label_keys = decode_resource_template("<span>{{ item.label }}</span>")
            if self.raw.get('data') and self.raw.get('data').get("resource"):
                self.resource_id = self.raw.get('data') and self.raw.get('data').get("resource")
        if self.dataSrc and self.dataSrc == "url":
            self.url = self.raw.get('data').get("url")
            self.header_key = self.raw.get('data', {}).get("headers", {})[0].get('key')
            self.header_value_key = self.raw.get('data', {}).get("headers", [])[0].get('value')

    def make_resource_list(self):
        resource_list = self.resources
        # logger.info(resource_list)
        self.raw['data'] = {"values": []}
        for item in resource_list:
            if self.dataSrc == "resource":
                label = fetch_dict_get_value(item, self.template_label_keys[:])
                iid = item['rec_name']
            else:
                label = item[self.properties['label']]
                iid = item[self.properties['id']]
            self.search_object['values'].update({iid: label})
            self.raw['data']['values'].append({
                "label": label,
                "value": iid
            })
        if self.selected_id:
            self.raw['value'] = self.selected_id

    @CustomComponent.value.setter
    def value(self, value):
        if self.template_label_keys and isinstance(value, dict):
            val = value.get('id', value)
        else:
            val = value
            if not val or val is None:
                val = self.selected_id
        if self.multiple and val is None or not val:
            val = []
        elif self.multiple and val is not None and not isinstance(val, list):
            val = [val]
        self.form['value'] = val

    @property
    def value_label(self):
        # value = self.raw['value']
        comp = self.builder.form_components.get(self.key)
        values = comp.raw.get('data') and comp.raw['data'].get('values')
        for val in values:
            if comp.value and val['value'] == (type(val['value'])(comp.value)):
                label = val['label']
                if self.i18n.get(self.language):
                    return self.i18n[self.language].get(label, label)
                else:
                    return label

    @property
    def value_labels(self):
        comp = self.builder.form_components.get(self.key)
        values = comp.raw.get('data') and comp.raw['data'].get('values')
        value_labels = []
        for val in values:
            if val and self.value and str(val['value']) in self.value:
                if self.i18n.get(self.language):
                    value_labels.append(self.i18n[self.language].get(val['label'], val['label']))
                else:
                    value_labels.append(val['label'])
        return value_labels

    @property
    def data(self):
        return self.raw.get('data')

    @property
    def values(self):
        return self.raw.get('data', {}).get('values')

    def compute_data(self, data):
        data = super(selectComponent, self).compute_data(data)
        new_dict = data.copy()
        if self.multiple:
            if not new_dict.get(self.key):
                new_dict[self.key] = []
            # logger.info(f"select compute_data {self.key} before {new_dict.get(self.key)}")
            if not isinstance(new_dict[self.key], list):
                d = new_dict[self.key]
                new_dict[self.key] = []
                if d:
                    new_dict[self.key].append(d)

            # logger.info(f"select compute_data {self.key} after {data[self.key]}")
        else:
            if not new_dict.get(self.key):
                new_dict[self.key] = ""
        data = {**data, **new_dict}
        return data.copy()

    def compute_data_table(self, data):
        if self.multiple:
            val = ", ".join(self.value_labels)
        else:
            val = self.value_label
        res = data.copy()
        res[self.key] = val
        return res.copy()

    def get_filter_object(self):
        self.search_object['values'] = self.values
        return self.search_object


class radioComponent(CustomComponent):

    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.search_object = {
            'id': self.key,
            'label': self.label,
            'type': 'string',
            'input': 'select',
            'operators': [
                'equal', 'not_equal', 'in', 'not_in', 'is_null', 'is_not_null', 'is_empty',
                'is_not_empty'],
            'values': {}

        }

    @property
    def values_labels(self):
        comp = self.builder.form_components.get(self.key)
        builder_values = comp.raw.get('values')
        values_labels = {}

        for b_val in builder_values:
            if self.i18n.get(self.language):
                label = self.i18n[self.language].get(b_val['label'], b_val['label'])
            else:
                label = b_val['label']
            val = {'key': b_val['value'], 'label': label, 'value': b_val['value'] == self.value}
            values_labels[b_val['value']] = val
        return values_labels

    @property
    def value_label(self):
        comp = self.builder.form_components.get(self.key)
        builder_values = comp.raw.get('values')
        value_label = {}

        for b_val in builder_values:
            if b_val['value'] == self.value:
                if self.i18n.get(self.language):
                    return self.i18n[self.language].get(b_val['label'], b_val['label'])
                else:
                    return b_val['label']
        else:
            return False

    def compute_data_table(self, data):
        res = data.copy()
        res[self.key] = self.value_label
        return res.copy()

    @property
    def values(self):
        return self.raw.get('values', [])

    def get_filter_object(self):
        self.search_object['values'] = self.values
        return self.search_object


class buttonComponent(CustomComponent):

    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.headers = []
        self.modal = False

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(buttonComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        if cfg.get('modalEdit'):
            self.component_tmp = "modalbutton"
        return cfg


class emailComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.defaultValue = self.raw.get('defaultValue', "")


class urlComponent(CustomComponent):
    pass


class ilinkComponent(CustomComponent):
    pass


class phoneNumberComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.defaultValue = self.raw.get('defaultValue', "")
        self.search_object = {
            'id': 'id',
            'label': 'Identifier',
            'type': 'string',
            'default_operator': 'equal',
            'placeholder': '____-____-____',
            'operators': ['equal', 'not_equal'],
        }


# TODO: tags, address

class datetimeComponent(CustomComponent):
    # format H 24 d/m/y H:i
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.headers = []
        self.is_date = self.raw.get('enableDate', True)
        self.is_time = self.raw.get('enableTime', True)
        self.min = self.raw['widget']['minDate']
        self.max = self.raw['widget']['maxDate']
        self.client_format = self.builder.settings.ui_date_mask
        self.format = self.raw['format']
        self.value_date = None
        self.defaultDate = self.raw.get('defaultDate')
        self.search_template = {
            'date': {
                'id': self.key,
                'label': self.label,
                'type': 'date',
                'default_operator': 'equal',
                'operators': [
                    'equal', 'not_equal',
                    'greater', 'greater_or_equal',
                    'less', 'less_or_equal'
                ],

                'get_format': self.builder.settings.server_date_mask

            },
            'datetime': {
                'id': self.key,
                'label': self.label,
                'type': 'datetime',
                'default_operator': 'equal',
                'operators': [
                    'equal', 'not_equal',
                    'greater', 'greater_or_equal',
                    'less', 'less_or_equal'
                ],
                'get_format': self.builder.settings.server_datetime_mask
            },
            'time': {
                'id': self.key,
                'label': self.label,
                'type': 'datetime',
                'default_operator': 'equal',
                'operators': [
                    'equal', 'not_equal',
                    'greater', 'greater_or_equal',
                    'less', 'less_or_equal'
                ],
                'get_format': self.builder.settings.server_datetime_mask
            }
        }
        # for dt --> 2021-08-11T17:22:04
        self.isodate_regex = re.compile('(\d{4}-\d{2}-\d{2})[A-Z]+(\d{2}:\d{2}:\d{2})')
        self.dte = DateEngine(
            UI_DATETIME_MASK=self.builder.settings.ui_datetime_mask,
            SERVER_DTTIME_MASK=self.builder.settings.server_datetime_mask
        )
        self.size = 12

    @property
    def value(self):
        vals = self.form.get('value', "1")
        return vals

    @CustomComponent.value.setter
    def value(self, vals):
        if not vals:
            vals = None
        self.value_date = vals
        if vals is None and self.defaultDate == "today":
            if self.is_time:
                self.value_date = self.dte.todayTime_ui
            elif self.is_date:
                self.value_date = self.dte.today_ui
        logger.info(self.value_date)
        if self.is_time and vals:
            try:
                # self.value_date = self.dte.server_datetime_to_ui_datetime_str(vals)
                if self.isodate_regex.match(vals):
                    v = self.isodate_regex.search(vals).group()
                    self.value_date = self.dte.server_datetime_to_ui_datetime_str(v)
            except ValueError as e:
                logger.warning(f"{e} of {vals}")
                self.value_date = vals
        elif self.is_date and vals:
            logger.info(vals)
            try:
                if self.isodate_regex.match(vals):
                    v = self.isodate_regex.search(vals).group()
                    self.value_date = self.dte.server_datetime_to_ui_date_str(v)
            except ValueError as e:
                logger.warning(e)
                self.value_date = vals
        self.form['value'] = self.value_date

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super().make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg['is_time'] = self.is_time
        cfg['is_date'] = self.is_date
        cfg['min'] = self.min
        cfg['max'] = self.max
        cfg['client_format'] = self.format
        # cfg['customClass'] = self.raw['customClass']
        return cfg

    def compute_data(self, data):
        # data = super(datetimeComponent, self).compute_data(data)
        new_dict = {}
        datestr = data.get(self.key)
        if datestr == "":
            data[self.key] = None
        if datestr is not None:
            if not self.is_time:
                datestr = f"{datestr} 00:00"
            try:
                new_dict[self.key] = self.dte.ui_datetime_to_server_datetime_str(
                    datestr)
            except ValueError as e:
                new_dict[self.key] = data.get(self.key)

            data = {**data, **new_dict}
        return data.copy()

    def compute_data_table(self, data):
        new_dict = self.default_data.copy()
        if self.key in data:
            todo = data[self.key]
            if self.is_date and self.is_time and todo:
                try:
                    new_dict[self.key] = self.dte.server_datetime_to_ui_datetime_str(todo)
                except ValueError as e:
                    new_dict[self.key] = todo

            elif self.is_date and todo:
                try:
                    new_dict[self.key] = self.dte.server_datetime_to_ui_date_str(todo)
                except ValueError as e:
                    new_dict[self.key] = todo

            elif self.is_time and todo:
                timev = todo
                if "T" in todo:
                    timev = todo.split("T")[1]
                new_dict[self.key] = timev
            data = {**data, **new_dict}
        return data.copy()

    def get_filter_object(self):
        if self.is_date and self.is_time:
            return self.search_template['datetime']
        elif self.is_date:
            return self.search_template['date']
        elif self.is_time:
            return self.search_template['time']
        return {}


class dateComponent(CustomComponent):
    pass


class timeComponent(CustomComponent):
    pass


class currencyComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.search_object = {
            'id': self.key,
            'label': self.label,
            'type': 'double',
            'input': 'text',
            'value_separator': '|',
            'default_operator': 'equal',
            'operators': [
                'equal', 'not_equal',
                'greater', 'greater_or_equal',
                'less', 'less_or_equal',
                'in', 'not_in'
            ]
        }


class surveyRowComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.headers = []
        self.grid = None
        self.min_row = 1
        self.max_row = 1
        self.row_id = 0
        self.size = 12

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(surveyRowComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg['row_id'] = self.row_id
        cfg['customClass'] = f" col-{self.size}-{self.width} "
        return cfg


class surveyComponent(CustomComponent):

    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.headers = []
        self.survey = True
        self.row_id = 0
        self.default_data = {
            self.key: {}
        }
        self.eval_rows()

    def eval_rows(self):
        self.component_items = []
        for row_id in range(len(self.raw['questions'])):
            row = self.get_row(row_id)
            self.component_items.append(row)

    @property
    def rows(self):
        return self.component_items

    def get_row(self, row_id):
        value = ""

        raw_row = OrderedDict()
        raw_row["key"] = f"{self.key}_surveyRow_{row_id}"
        raw_row["type"] = "surveyRow"
        row = self.builder.get_component_object(raw_row)
        row.row_id = row_id
        row.size = 12
        group = self.raw['questions'][row_id]['value']

        raw_info = OrderedDict()
        raw_info['key'] = f"{group}_{row_id}-info"
        raw_info["type"] = "info"
        raw_info["label"] = self.raw['questions'][row_id]['label']
        # raw_info["value"] = self.raw['questions'][row_id]['value']
        info = self.builder.get_component_object(raw_info)
        info.size = 12 - len(self.raw['values'])
        row.component_items.append(info)

        if self.value:
            value = self.value.get(group, "")

        raw_radio = OrderedDict()
        raw_radio['key'] = f"{self.key}_{group}"
        raw_radio["type"] = "radio"
        raw_radio["label"] = ""
        raw_radio["values"] = self.raw['values']
        raw_radio["value"] = value
        raw_radio["inline"] = True
        radio = self.builder.get_component_object(raw_radio)
        radio.size = len(self.raw['values'])
        row.component_items.append(radio)

        return row

    def compute_data(self, data):
        data = super(surveyComponent, self).compute_data(data)
        key = self.key
        list_to_pop = []
        new_dict = self.default_data.copy()
        for k, v in data.items():
            if f"{key}_" in k:
                list_to_pop.append(k)
                groups = k.split("_")
                new_dict[key][groups[1]] = v
        for i in list_to_pop:
            data.pop(i)
        data = {**data, **new_dict}
        return data.copy()


class signatureComponent(CustomComponent):
    pass


# Layout components


class htmlelementComponent(CustomComponent):

    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super().make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg['customClass'] = self.raw.get('customClass')
        return cfg


class contentComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.editor = self.properties.get('editor')
        self.eval_tmp = self.properties.get('eval_tmp', False)
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
        val = cfg.get('html', "")
        if self.value:
            val = self.value
        if self.eval_tmp:
            context_data = self.builder.context_data.copy()
            form_o = context_data.get('form', {}).copy()
            user_o = context_data.get('user', {}).copy()
            data_o = context_data.get('app', {}).copy()
            context = {"form": form_o, "user": user_o, "app": data_o}
            template = jinja2.Template(val)
            cfg['html'] = template.render(context)
        else:
            cfg['html'] = val
        return cfg


class columnComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.size = self.raw['size']
        self.width = self.raw['width']
        self.offset = self.raw['offset']

    def eval_components(self):
        for component in self.raw['components']:
            componet_obj = self.builder.get_component_by_key(component['key'])
            componet_obj.value = self.form.get(component['key'], componet_obj.defaultValue)
            self.builder.form_components[component['key']] = componet_obj
            # self.component_items.append(componet_obj)


class columnsComponent(CustomComponent):

    def eval_components(self):
        for col in self.raw.get('columns').copy():
            col['type'] = 'column'
            componet_obj = self.builder.get_component_object(col)
            componet_obj.form = self.form.copy()
            componet_obj.eval_components()
            # self.builder.form_components[col['key']] = componet_obj
            self.component_items.append(componet_obj)


class fieldsetComponent(CustomComponent):

    def eval_components(self):
        for component in self.raw['components']:
            componet_obj = self.builder.get_component_by_key(component['key'])
            componet_obj.value = self.form.get(component['key'], componet_obj.defaultValue)
            self.builder.form_components[component['key']] = componet_obj


class panelComponent(CustomComponent):

    @property
    def title(self):
        CustomComponent = self.builder.components.get(self.key)
        title = CustomComponent.raw.get('title')
        if not title:
            title = CustomComponent.raw.get('label')

        if self.i18n.get(self.language):
            return self.i18n[self.language].get(title, title)
        else:
            return title

    @property
    def label(self):
        label = self.raw.get('title')
        if self.i18n.get(self.language):
            return self.i18n[self.language].get(label, label)
        else:
            return label

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(panelComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg['label'] = self.raw.get('title')
        return cfg


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
        for component in self.raw['components']:
            componet_obj = self.builder.get_component_by_key(component['key'])
            componet_obj.value = self.form.get(component['key'], componet_obj.defaultValue)
            if component.get('type') in ['columns']:
                componet_obj.form = self.form.copy()
                componet_obj.eval_components()
            self.builder.form_components[component['key']] = componet_obj
            self.component_items.append(componet_obj)


class tabsComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.headers = []
        self.panels = []
        self.component_items = []
        self.tabs = True
        self.add_enabled = False
        self.default_data = {
            self.key: []
        }

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(tabsComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg['panels'] = self.panels
        return cfg

    def eval_panels(self):
        self.component_items = []
        count = 0
        for tab in self.raw['components'].copy():
            tab['type'] = "tabPanel"
            panel = self.builder.get_component_object(tab)
            panel.form = self.form
            panel.eval_components()
            if count == 0:
                panel.active = True
            self.panels.append(panel)
            self.component_items.append(panel)
            count += 1

    def compute_data(self, data):
        for panel in self.panels:
            for component in panel.component_items:
                data = component.compute_data(data)
        return data.copy()

    def compute_data_table(self, data):
        for panel in self.panels:
            for component in panel.component_items:
                data = component.compute_data_table(data)
        return data.copy()


class containerComponent(CustomComponent):

    @property
    def title(self):
        title = self.raw.get('title')
        if not title:
            title = self.raw.get('label')

        if self.i18n.get(self.language):
            return self.i18n[self.language].get(title, title)
        else:
            return title

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(containerComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg['label'] = self.title
        return cfg


# Data components

class datagridRowComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.headers = []
        self.grid = None
        self.min_row = 1
        self.max_row = 1
        self.row_id = 0
        self.col_size = 12

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(datagridRowComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg['parent_key'] = self.parent.key
        cfg['row_id'] = self.row_id
        return cfg


class datagridComponent(CustomComponent):

    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.headers = []
        self.multi_row = True
        self.min_row = 1
        self.max_row = 1
        self.add_enabled = True
        self.row_id = 0
        self.components_ext_data_src = []
        self.tables = []
        self.rows = []
        self.default_data = {
            self.key: []
        }
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
        cfg['min_rows'] = self.min_row
        cfg['max_rows'] = self.max_row
        cfg['rec_name'] = self.builder.rec_name
        return cfg

    def eval_rows(self):
        self.rows = []
        numrow = self.min_row
        if self.value:
            numrow = len(self.value)
        for row_id in range(numrow):
            row = self.get_row(row_id)
            self.rows.append(row)
        return self.rows

    def get_row(self, row_id):
        raw_row = OrderedDict()
        raw_row["key"] = f"{self.key}_dataGridRow_{row_id}"
        raw_row["type"] = "datagridRow"
        row = self.builder.get_component_object(raw_row)
        row.row_id = row_id
        row.parent = self
        num_c = len(self.component_items) + 1
        width_c = math.ceil(num_c / 12)
        for component in self.component_items:
            # Copy CustomComponent raw (dict), to ensure no binding and overwrite.
            component_raw = component.raw.copy()
            component_raw['key'] = f"{self.key}_dataGridRow_{row_id}_{component_raw.get('key')}"
            component_obj = self.builder.get_component_object(component_raw)
            # component_obj.size = "lg"
            # component_obj.width = width_c
            if component_obj.dataSrc and not component_obj.table:
                self.components_ext_data_src.append(component_obj)
            if self.value:
                for key, val in self.value[row_id].items():
                    if key == component.key:
                        component_obj.value = val
            row.component_items.append(component_obj)
        return row

    def add_row(self, num_rows):
        row = self.get_row(num_rows)
        self.rows.append(row)
        return self.rows

    def compute_row_data(self, components, row_data):
        new_row_data = row_data.copy()
        for component in components:
            new_row_data = component.compute_data(new_row_data)
        return new_row_data.copy()

    def compute_row_data_table(self, components, row_data):
        new_row_data = row_data.copy()
        for component in components:
            new_row_data = component.compute_data_table(new_row_data)
        return new_row_data.copy()

    def compute_data(self, data):
        data = super().compute_data(data)
        c_keys = []
        components = []
        for component in self.component_items:
            components.append(component)
            c_keys.append(component.key)
        key = self.key
        list_to_pop = []
        new_dict = self.default_data.copy()
        last_group = False
        data_row = {}
        rec_name = ""
        for k, v in data.items():
            if f"{key}_" in k and "dataGridRow" in k:
                list_to_pop.append(k)
                list_keys = k.split("_")
                if list_keys:
                    rec_name = "_".join(list_keys[:3])
                    groups = list_keys[:3]
                    if groups[2] != last_group:
                        if last_group:
                            data_row['rec_name'] = rec_name
                            new_dict[key].append(data_row.copy())
                            data_row = {}
                        last_group = groups[2]
                    if k in data:
                        data_row[list_keys[3]] = data[k]
        data_row['rec_name'] = rec_name
        new_dict[key].append(data_row.copy())
        for i in list_to_pop:
            data.pop(i)
        list_row = new_dict[key]
        new_list_row = []
        for item in list_row:
            new_list_row.append(self.compute_row_data(components, item))
        new_dict[key] = new_list_row[:]
        data = {**data, **new_dict}
        return data.copy()

    def compute_data_table(self, data):
        new_dict = self.default_data.copy()
        if self.key in data:
            components = []
            for component in self.component_items:
                components.append(component)
            new_dict[self.key] = []
            list_row = data[self.key]
            for item in list_row:
                new_dict[self.key].append(self.compute_row_data_table(components, item))
            data = {**data, **new_dict}
        return data.copy()


class fileComponent(CustomComponent):

    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)

        self.rows = []
        self.multiple = False  # self.raw.get("multiple")
        self.add_enabled = True
        self.dir = self.raw.get('dir')
        self.webcam = self.raw.get('webcam')
        self.uploaders = True
        self.file_url = ""
        # self.component_tmp = "file_container"
        self.default_data = {
            self.key: []
        }
        self.search_object = {
            'id': self.key,
            'label': self.label,
            'type': 'string',
            'input': 'text',
            'default_operator': 'is_not_null',
            'operators': [
                'is_not_null', 'is_null'
            ]
        }

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super().make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg['rec_name'] = self.builder.rec_name or ""
        cfg['model'] = self.builder.model
        return cfg

    def compute_data(self, data):
        data = super().compute_data(data)
        new_dict = self.default_data.copy()
        curr_data = self.form.get(self.key, [])
        new_dict[self.key] = curr_data
        for i in data.get(self.key):
            new_dict[self.key].append(i)
        data = {**data, **new_dict}
        return data

    def compute_data_table(self, data):
        this = data[self.key]
        res = data.copy()
        curr_data = self.form.get(self.key, [])
        res[self.key] = curr_data
        if isinstance(this, list):
            for i in this:
                res[self.key].append(i['filename'])
        return res.copy()

    @property
    def storage(self):
        return self.raw.get('storage')

    @property
    def url(self):
        return self.file_url

    @property
    def base64(self):
        res = ''
        for val in self.form.get('value'):
            name = val.get('name')
            url = val.get('url')
            res += base64_encode_url(url)
        return res


class resourceComponent(CustomComponent):
    pass


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
        self.parent = ""
        self.clickKey = "row_action"
        self.rec_name = "rec_name"
        self.col_reorder = "list_order"
        self.form_columns = []
        self.model = self.properties.get("model")
        self.action_url = self.properties.get('action_url')
        self.dom_todo = self.properties.get('dom', "iptilp")
        self.show_owner = self.properties.get('show_owner', "no") == "yes"
        self.show_select_chk = self.properties.get('hide_select_chk', "no") == "no"
        self.meta_to_show = self.properties.get("list_metadata_show", "").split(",")
        self.meta_keys = []
        self.hide_keys = []
        self.columns = []
        self.responsive = self.is_mobile
        self.row_id = 0
        self.default_data = {
            self.key: []
        }

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(tableComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )

        cfg['tab_id'] = self.key
        # cfg['parent'] = self.parent
        cfg['cols'] = [val for key, val in self.columns.items()]
        cfg['tab_responsive'] = self.responsive
        cfg["full_width"] = True
        cfg["rowReorder"] = self.col_reorder
        cfg["model"] = self.model
        cfg["select_chk"] = True
        cfg["columns"] = []
        for val in self.columns.keys():
            if not val == "check":
                cfg['columns'].append({'data': val})
            else:
                cfg['columns'].append({'data': "check", "defaultContent": ''})
        cfg["click_row"] = {
            "col": self.clickKey
        }

        cfg['dom_todo'] = self.dom_todo
        cfg["columnDefs"] = []
        if self.hide_rec_name and "rec_name" not in self.meta_to_show:
            self.meta_keys.append("rec_name")
        list_keys_cols = list(self.columns.keys())
        user_selected_form_columns = list(self.form_columns.keys())
        for key in ['check', 'list_order']:
            c_conf = {
                "targets": list_keys_cols.index(key),
                "width": 10
            }
            cfg["columnDefs"].append(
                c_conf
            )
        for key in self.meta_keys:
            if key not in self.meta_to_show and key in list_keys_cols and key not in user_selected_form_columns:
                c_conf = {
                    "targets": list_keys_cols.index(key),
                    "visible": False,
                }
                cfg["columnDefs"].append(
                    c_conf
                )
        return cfg


class wellComponent(CustomComponent):

    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.obj_type = self.properties.get('type')
        self.search_area = (self.obj_type == "search_area")
        self.export_area = (self.obj_type == "export_area")
        self.import_component = (self.obj_type == "import_component")
        getattr(self, f"init_{self.obj_type}")()

    def init_search_area(self):
        self.component_tmp = self.properties.get('type')
        self.object = self.properties.get('object', False)
        self.object_id = self.properties.get('object_id', False)
        self.model = self.properties.get('model', False)
        self.query = self.properties.get('query', {})
        self.table_builder = None
        self.filters = []

    def init_export_area(self):
        self.component_tmp = self.properties.get('type')
        self.search_id = self.properties.get('search_id', False)
        self.model = self.properties.get('model', False)
        self.query = self.properties.get('query', {})
        self.table_builder = None

    def init_import_component(self):
        self.component_tmp = self.properties.get('type')
        self.model = self.properties.get('model', False)

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super().make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        if self.search_area:
            cfg['object'] = self.object
            cfg['object_id'] = self.object_id
            cfg['filters'] = self.filters
            logger.info(self.query)
            cfg['query'] = self.query

        if self.export_area:
            cfg['search_id'] = self.search_id
            cfg['query'] = self.query

        return cfg
