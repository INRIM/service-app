# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
import json
from collections import OrderedDict

from formiodata.components import Component
from formiodata.utils import base64_encode_url, decode_resource_template, fetch_dict_get_value

from .DateEngine import DateEngine
import copy
import requests
from json_logic import jsonLogic
import re
import collections

import uuid
import logging

logger = logging.getLogger(__name__)


class CustomComponent(Component):

    def __init__(self, raw, builder, **kwargs):
        # TODO or provide the Builder object?
        super(CustomComponent, self).__init__(raw, builder, **kwargs)
        self.raw = copy.deepcopy(raw)

        # i18n (language, translations)

        self.tmpe = builder.tmpe
        self.theme_cfg = builder.theme_cfg
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
        self.grid_rows = []
        self.width = 12
        self.size = "lg"
        self.offset = 0
        self.component_tmp = self.raw.get('type')
        self.authtoken = self.builder.authtoken
        self.search_object = {
            'id': self.key,
            'label': self.label,
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

    def aval_conditional(self, cfg):
        if cfg.get("conditional") and cfg.get("conditional").get('json'):
            if self.builder.form_data:
                cfg['hidden'] = not jsonLogic(
                    dict(cfg.get("conditional").get('json')), self.builder.context_data)
            else:
                cfg['hidden'] = True
        return cfg.copy()

    def apply_action(self, action, cfg, logic_res):
        logger.info(f"comupte apply_action--> {action}")
        logger.info("<--> ")

        if action.get("type") == "property":
            item = action.get("property").get("value")
            value = action.get("state")
            cfg[item] = value
        elif action.get("type") == "value":
            cfg[action.get("value")] = logic_res
        return cfg.copy()

    def compute_logic(self, json_logic, actions, cfg):
        logger.info(f"comupte json_logic--> {json_logic} ")
        logic_res = jsonLogic(json_logic, self.builder.context_data)
        if logic_res:
            for action in actions:
                if action:
                    cfg = self.apply_action(action, cfg, logic_res)
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

    def make_config_new(self, component, disabled=False, cls_width=" "):
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
        cfg['items'] = self.component_items
        # if cvalue:
        cfg["value"] = cvalue
        cfg['authtoken'] = self.authtoken
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
        logger.info(cfg)
        logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~")
        logger.info(self.form)
        logger.info("-------------------------/")

    def render(self, size="12", log=False):
        cfg = self.make_config_new(
            self.raw, disabled=self.builder.disabled, cls_width=f"")
        cfg = self.aval_conditional(cfg)
        if self.has_logic:
            cfg = self.eval_logic(cfg)
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
        self.defaultValue = self.raw.get('defaultValue', "")

    @CustomComponent.value.setter
    def value(self, value):
        clean = re.compile('<.*?>')
        val = re.sub(clean, '', str(value))
        self.form['value'] = val

    # @property
    # def value(self):
    #     return self.form.get('value', "")


class textareaComponent(CustomComponent):

    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.defaultValue = self.raw.get('defaultValue', "")

    @CustomComponent.value.setter
    def value(self, value):
        clean = re.compile('<.*?>')
        val = re.sub(clean, '', str(value))
        self.form['value'] = val

    # @property
    # def value(self):
    #     return self.form.get('value', "")


class numberComponent(CustomComponent):

    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.search_object = {
            'id': self.key,
            'label': self.label,
            'type': 'integer',
            'input': 'text',
            'value_separator': '|',
            'operators': [
                'equal', 'not_equal',
                'greater', 'greater_or_equal',
                'less', 'less_or_equal',
                'in', 'not_in'
            ]
        }


class infoComponent(CustomComponent):
    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(infoComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg['customClass'] = f" col-{self.size}-{self.width} "
        return cfg


class passwordComponent(CustomComponent):
    pass


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
            'operators': ['equal', 'not_equal', 'in', 'not_in', 'is_null', 'is_not_null'],
            'values': {}

        }

        if self.multiple:
            self.component_tmp = "selectmulti"
        if self.dataSrc and self.dataSrc == "resource":
            if self.raw.get('template'):
                self.template_label_keys = decode_resource_template(self.raw.get('template'))
            else:
                self.template_label_keys = decode_resource_template("<span>{{ item.title }}</span>")
            if self.raw.get('data') and self.raw.get('data').get("resource"):
                self.resource_id = self.raw.get('data') and self.raw.get('data').get("resource")
        if self.dataSrc and self.dataSrc == "url":
            self.url = self.raw.get('data').get("url")
            self.header_key = self.raw.get('data', {}).get("headers", {})[0].get('key')
            self.header_value_key = self.raw.get('data', {}).get("headers", [])[0].get('value')

    def make_resource_list(self):
        resource_list = self.resources
        self.raw['data'] = {"values": []}
        for item in resource_list:
            if self.dataSrc == "resource":
                label = fetch_dict_get_value(item, self.template_label_keys[:])
                iid = item['rec_name']
            else:
                label = item[self.raw['properties']['label']]
                iid = item[self.raw['properties']['id']]
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
        if self.multiple and val is None:
            val = []
        self.form['value'] = val

    @property
    def value_label(self):
        # value = self.raw['value']
        comp = self.builder.form_components.get(self.key)
        values = []
        # if comp.raw.get('data') and comp.raw['data'].get('values'):
        #     values = comp.raw['data'].get('values')
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
        return self.raw.get('data').get('values')

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
            val = self.value_labels
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
            'id': 'id',
            'label': 'Identifier',
            'type': 'string',
            'placeholder': '____-____-____',
            'operators': ['equal', 'not_equal'],
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


# Advanced

class emailComponent(CustomComponent):
    pass


class urlComponent(CustomComponent):
    pass


class ilinkComponent(CustomComponent):
    pass


class phoneNumberComponent(CustomComponent):
    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.search_object = {
            'id': 'id',
            'label': 'Identifier',
            'type': 'string',
            'placeholder': '____-____-____',
            'operators': ['equal', 'not_equal'],
        }


# TODO: tags, address


class datetimeComponent(CustomComponent):

    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.headers = []
        self.is_date = self.raw.get('enableDate', True)
        self.is_time = self.raw.get('enableTime', True)
        self.min = self.raw['widget']['minDate']
        self.max = self.raw['widget']['maxDate']
        self.client_format = self.builder.settings.ui_date_mask
        self.value_date = ""
        self.value_time = "00:00"
        self.value_datetime = ""
        self.search_template = {
            'date': {
                'id': self.key,
                'label': self.label,
                'type': 'date',
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
                'operators': [
                    'equal', 'not_equal',
                    'greater', 'greater_or_equal',
                    'less', 'less_or_equal'
                ],
                'get_format': self.builder.settings.server_datetime_mask

            }
        }
        self.dte = DateEngine(
            UI_DATETIME_MASK=self.builder.settings.ui_datetime_mask,
            SERVER_DTTIME_MASK=self.builder.settings.server_datetime_mask
        )
        self.size = 12

    @property
    def value(self):
        return self.form.get('value')

    @CustomComponent.value.setter
    def value(self, vals):
        self.form['value'] = vals
        if self.is_date and self.is_time and vals:
            date_v = vals.split("T")[0]
            if len(vals.split("T")) > 1:
                time_v = vals.split("T")[1][:5]
            else:
                time_v = "00:00"
            try:
                self.value_date = self.dte.server_datetime_to_ui_date_str(date_v)
            except ValueError as e:
                self.value_date = date_v
            self.value_time = f"{time_v}"
        elif self.is_date and vals:
            try:
                self.value_date = self.dte.server_datetime_to_ui_date_str(vals)
            except ValueError as e:
                self.value_date = vals
        elif self.is_time and vals:
            self.value_time = f"{vals}"

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(datetimeComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg['value_date'] = self.value_date
        cfg['value_time'] = self.value_time
        if ":" in self.value_time:
            cfg['value_time_H'] = self.value_time.split(":")[0]
            cfg['value_time_M'] = self.value_time.split(":")[1]
        cfg['is_time'] = self.is_time
        cfg['is_date'] = self.is_date
        cfg['min'] = self.min
        cfg['max'] = self.max
        cfg['client_format'] = self.client_format
        # cfg['customClass'] = self.raw['customClass']
        return cfg

    def compute_data(self, data):
        data = super(datetimeComponent, self).compute_data(data)
        new_dict = self.default_data.copy()
        datek = f"{self.key}-date"
        timek = f"{self.key}-time"
        if self.is_date and self.is_time and data[datek] and timek in data:
            new_dict[self.key] = self.dte.ui_datetime_to_server_datetime_str(
                f"{data[datek]} {data[timek]}")
            data.pop(datek)
            data.pop(timek)
        elif self.is_date and data[datek]:
            if "T" in data[datek]:
                data[datek] = data[datek].split("T")[0]
            new_dict[self.key] = self.dte.ui_date_to_server_datetime_str(
                f"{data[datek]}")
            data.pop(datek)
        elif self.is_time and timek in data:
            new_dict[self.key] = f"{data[timek]}"
            data.pop(timek)
        data = {**data, **new_dict}
        return data.copy()

    def compute_data_table(self, data):
        new_dict = self.default_data.copy()
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
            new_dict[self.key] = todo
        data = {**data, **new_dict}
        return data.copy()

    def get_filter_object(self):
        if self.is_date and self.is_time:
            return self.search_template['datetime']
        elif self.is_date:
            return self.search_template['date']
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

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super().make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        cfg['customClass'] = self.raw.get('customClass')
        return cfg


class contentComponent(CustomComponent):
    pass


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
    pass


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
        cfg['model'] = self.builder.model
        return cfg

    @property
    def labels(self):
        labels = OrderedDict()
        for comp in self.raw['components']:
            if self.i18n.get(self.language):
                label = self.i18n[self.language].get(comp['label'], comp['label'])
            else:
                label = comp['label']
            labels[comp['key']] = label
            self.columns.append(label)
        return labels

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
        for component in self.component_items:
            # Copy CustomComponent raw (dict), to ensure no binding and overwrite.
            component_raw = component.raw.copy()
            component_raw['key'] = f"{self.key}_dataGridRow_{row_id}-{component_raw.get('key')}"
            component_obj = self.builder.get_component_object(component_raw)
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

    def compute_data(self, data):
        data = super(datagridComponent, self).compute_data(data)
        c_keys = []
        for component in self.component_items:
            c_keys.append(component.key)
        key = self.key
        list_to_pop = []
        new_dict = self.default_data.copy()
        last_group = False
        data_row = {}
        rec_name = ""
        for k, v in data.items():
            if f"{key}_" in k:
                list_to_pop.append(k)
                list_keys = k.split("-")
                if list_keys:
                    rec_name = list_keys[0]
                    groups = list_keys[0].split("_")
                    if groups[2] != last_group:
                        if last_group:
                            data_row['rec_name'] = rec_name
                            new_dict[key].append(data_row.copy())
                            data_row = {}
                        last_group = groups[2]
                    if list_keys[1] in c_keys:
                        data_row[list_keys[1]] = data[k]
        data_row['rec_name'] = rec_name
        new_dict[key].append(data_row.copy())
        for i in list_to_pop:
            data.pop(i)
        data = {**data, **new_dict}
        return data.copy()


# Premium components

class fileComponent(CustomComponent):

    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)

    @property
    def storage(self):
        return self.raw.get('storage')

    @property
    def url(self):
        return self.raw.get('url')

    @property
    def base64(self):
        if self.storage == 'url':
            res = ''
            for val in self.form.get('value'):
                name = val.get('name')
                url = val.get('url')
                res += base64_encode_url(url)
            return res
        elif self.storage == 'base64':
            return super().value


class resourceComponent(CustomComponent):
    pass


class tableComponent(CustomComponent):

    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.headers = []
        self.filter = {}
        self.table = True
        self.hide_rec_name = False
        self.min_row = 1
        self.max_row = 1
        self.clickKey = "row_action"
        self.rec_name = "rec_name"
        self.col_reorder = "list_order"
        self.model = self.raw.get('properties').get("model")
        self.action_url = self.raw.get('properties').get('action_url')
        self.columns = []
        self.responsive = kwargs.get("responsive", False)
        self.row_id = 0
        self.default_data = {
            self.key: []
        }

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(tableComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )

        cfg['tab_id'] = self.key
        cfg['cols'] = [val for key, val in self.columns.items()]
        cfg['tab_responsive'] = self.responsive
        cfg["full_width"] = True
        cfg["rowReorder"] = self.col_reorder
        cfg["model"] = self.model
        cfg["columns"] = [{'data': val} for val in self.columns.keys()]
        cfg["click_row"] = {
            "col": self.clickKey
        }
        cfg['dom_todo'] = 'irtlp'
        cfg["columnDefs"] = [{
            "targets": list(self.columns.keys()).index(self.clickKey),
            "visible": False,
        }]
        if self.hide_rec_name:
            cfg["columnDefs"].append(
                {
                    "targets": list(self.columns.keys()).index(self.rec_name),
                    "visible": False,
                }
            )
        return cfg


class wellComponent(CustomComponent):

    def __init__(self, raw, builder, **kwargs):
        super().__init__(raw, builder, **kwargs)
        self.obj_type = self.raw.get('properties').get('type')
        self.search_area = (self.obj_type == "search_area")
        self.export_area = (self.obj_type == "export_area")
        getattr(self, f"init_{self.obj_type}")()

    def init_search_area(self):
        self.component_tmp = self.raw.get('properties').get('type')
        self.object = self.raw.get('properties').get('object', False)
        self.object_id = self.raw.get('properties').get('object_id', False)
        self.model = self.raw.get('properties').get('model', False)
        self.query = self.raw.get('properties').get('query', {})
        self.table_builder = None
        self.filters = []

    def init_export_area(self):
        self.component_tmp = self.raw.get('properties').get('type')
        self.search_id = self.raw.get('properties').get('search_id', False)
        self.model = self.raw.get('properties').get('model', False)
        self.query = self.raw.get('properties').get('query', {})
        self.table_builder = None

    def make_config_new(self, component, disabled=False, cls_width=" "):
        cfg = super(wellComponent, self).make_config_new(
            component, disabled=disabled, cls_width=cls_width
        )
        if self.search_area:
            cfg['object'] = self.object
            cfg['object_id'] = self.object_id
            cfg['filters'] = self.filters
            cfg['query'] = self.query

        if self.export_area:
            cfg['search_id'] = self.search_id
            cfg['query'] = self.query

        return cfg
