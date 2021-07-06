# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
from requests import Response
from datetime import date, datetime, time, timedelta
import logging

logger = logging.getLogger(__name__)


def data_helper_list(d, fields=[], merge_field=""):
    dres = {}
    data = d.copy()
    if not merge_field == "":
        dres = data[merge_field].copy()
        for k in fields:
            if not k == merge_field:
                dres[k] = data[k]
        return dres
    else:
        if fields:
            for k in fields:
                dres[k] = data[k]
            return dres
        else:
            return data


def list_format(list_data, fields=[], merge_field=""):
    list_res = []
    for item in list_data:
        list_res.append(data_helper_list(item, fields=fields, merge_field=merge_field))
    return list_res


class UtilsForService:

    def _finditem(self, obj, key):
        if key in obj: return obj[key]
        for k, v in obj.items():
            if isinstance(v, dict):
                item = self._finditem(v, key)
                if item is not None:
                    return item

    def deserialize_list_key_values(self, list_data):
        res = {item['name']: item['value'] for item in list_data}
        return res

    def clean_save_form_data(self, data):
        """
        Clean data dictionary
        :param data:
        :return:
        """
        dat = {}

        dat = {k.replace('_in', '').replace('_tl', '').replace('_ck', '').replace('_sel', ''): True if v == 'on' else v
               for k, v in data.items()}
        return dat

    def log_req_resp(self, req_resp: object):
        logger.info("------")
        logger.info("------")
        logger.info("--LOG RESP---")
        logger.info("..................................")
        logger.info(req_resp)
        logger.info("------")
        logger.info("------")
