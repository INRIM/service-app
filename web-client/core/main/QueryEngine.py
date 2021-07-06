# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.

from typing import Any, Dict, Optional, List
from datetime import datetime, date, time
import logging

logger = logging.getLogger(__name__)


class ActionQueryEngine:
    def __init__(self, model_name: str, components: list):
        self.components = components[:]
        self.model_name = model_name
        self.model = None
        self.tmp = {
            "textfield": {
                'id': '',
                'label': '',
                'type': 'string'
            },
            "textarea": {
                'id': '',
                'label': '',
                'type': 'string'
            },
            "number": {
                'id': "",
                'label': "",
                'type': 'integer',
                'input': 'text',
                'value_separator': '|',
                'operators': [
                    'equal', 'not_equal',
                    'greater', 'greater_or_equal',
                    'less', 'less_or_equal',
                    'in', 'not_in'
                ]
            },
            "number_f": {
                'id': "",
                'label': "",
                'type': 'double',
                'input': 'text',
                'value_separator': '|',
                'operators': [
                    'equal', 'not_equal',
                    'greater', 'greater_or_equal',
                    'less', 'less_or_equal',
                    'in', 'not_in'
                ]
            },
            "select": {
                'id': '',
                'label': '',
                'type': 'integer',
                'input': 'radio',
                'operators': ['equal', 'not_equal', 'in', 'not_in', 'is_null', 'is_not_null'],
                'values': {}

            },
            'date': {
                'id': '',
                'label': '',
                'type': 'date',
                'validation': {
                    'format': ''
                },
                'plugin': 'datepicker',
                'plugin_config': {
                    'format': '',
                    'todayBtn': 'linked',
                    'todayHighlight': True,
                    'autoclose': True
                }
            },
            'datetime': {
                'id': '',
                'label': '',
                'type': 'datetime',
                'validation': {
                    'format': ''
                },
                'plugin': 'datepicker',
                'plugin_config': {
                    'format': '',
                    'todayBtn': 'linked',
                    'todayHighlight': True,
                    'autoclose': True
                }
            }
        }
