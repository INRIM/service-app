# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import sys
import os
import logging
import ujson
from .BaseClass import PluginBase
from fastapi.exceptions import HTTPException
from .DateEngine import DateEngine, datetime, date, time, DateTimeEncoder
from .database.mongo_core import *
import re

# class JsonDatetime(datetime):
#     def __json__(self):
#         return '"%s"' % self.isoformat()
#
#
# datetime = JsonDatetime

logger = logging.getLogger(__name__)


class QueryEngine(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class QueryEngineBase(QueryEngine):
    @classmethod
    def create(cls, session, app_code=""):
        self = QueryEngineBase()
        self.init(session, app_code)

        return self

    def init(self, session, app_code):
        # logger.info(app_code)
        self.session = session
        self.app_code = app_code
        self.date_datetime_mask = '%Y-%m-%dT%H:%M:%S'
        self.dte = DateEngine(SERVER_DTTIME_MASK='%Y-%m-%dT%H:%M:%S')
        # for dt --> 2021-08-11T17:22:04
        self.isodate_regex = re.compile('(\d{4}-\d{2}-\d{2})[A-Z]+(\d{2}:\d{2}:\d{2})')
        self.autodate_parser = {
            "year": lambda y=0: self.dte.year_range(year=y),
            "month": lambda y=0, m=0, me=0: self.dte.month_range(year=y, month=m, monthe=me),
            "today": lambda d=0: self.dte.today(days=d),
            "now": lambda: self.dte.now
        }
        # for dt --> 2021-08-11T17:22:04.51+01:00
        # self.isodate_regex = re.compile('(\d{4}-\d{2}-\d{2})[A-Z]+(\d{2}:\d{2}:\d{2}).([0-9+-:]+)')

    def get_today_first_last(self):
        return {}

    def get_now(self):
        return {}

    def _check_update_date(self, obj_val):
        if not isinstance(obj_val, str):
            return obj_val
        if self.isodate_regex.match(obj_val):
            # val = datetime.strptime(obj_val, self.date_datetime_mask)
            val = self.dte.strdatetime_server_to_datetime(obj_val)
            logger.info(f" render {obj_val} -> {val}")
            return val
        elif "_date_" in obj_val:
            val = self.dte.eval_date_filter(obj_val)
            logger.info(f" date render {obj_val} -> {val}")
            return val
        else:
            return obj_val

    def _check_update_user(self, obj_val):
        if not isinstance(obj_val, str):
            return obj_val
        if "_user_" in obj_val:
            # logger.info(f" render {obj_val}")
            x = obj_val.replace("_user_", "")
            return getattr(self.session, x)  # self.session.get(x, "")
        else:
            return obj_val

    def get_query_date(self, strcode):
        pass

    def _check_update_auto_date(self, obj_val):
        """
        :param obj_val: possible config
            year  --> return range current year
            year-2020  --> return range for year 2020
            month  --> return range current year and current month
            month-6  --> return today date after 6 month
            month-1-0  --> return range current year for January
            month-1-3  --> return range current year frm 1st January  and 31st March
            month-1-3-2020  --> return range frm 1st January  and 31st March 2020
            today --> return date today at 00:00:00 (TZ)
            today-1 --> return date tommorrow at 00:00:00 (TZ)
            today_n_1 --> return  n means negative date yesterday at 00:00:00 (TZ)
            now --> return date today at this tick time (TZ)
        :return: date range or date objects
        """
        if not isinstance(obj_val, str):
            return obj_val
        if "_date_" in obj_val:
            logger.info(f" render {obj_val}")
            x = obj_val.replace("_date_", "")
            return getattr(self.session, x)  # self.session.get(x, "")
        else:
            return obj_val

    def update(self, data):
        if isinstance(data, dict):
            for k, v in data.copy().items():
                if isinstance(v, dict):  # For DICT
                    data[k] = self.update(v)
                elif isinstance(v, list):  # For LIST
                    data[k] = [self.update(i) for i in v]
                else:  # Update Key-Value
                    data[k] = self.update(v)
                    # logger.info(f"updated data[k] {data}")
        else:
            data = self._check_update_date(data)
            data = self._check_update_user(data)
            return data
        return data.copy()

    def scan_find_key(self, data, key):
        res = []
        if isinstance(data, dict):
            for k, v in data.items():
                res.append(k == key)
                if isinstance(v, dict):  # For DICT
                    res.append(self.scan_find_key(v, key))
                elif isinstance(v, list):  # For LIST
                    for i in v:
                        res.append(self.scan_find_key(i, key))
        return res[:]

    def flatten(self, l):
        for item in l:
            try:
                yield from self.flatten(item)
            except TypeError:
                yield item

    def check_key(self, data, key):
        # logger.info("check key")
        res_l = self.scan_find_key(data, key)
        res_flat = list(self.flatten(res_l))
        try:
            i = res_flat.index(True)
            return True
        except ValueError:
            return False

    def check_parse_json(self, str_test):
        try:
            str_test = ujson.loads(str_test)
        except ValueError as e:
            str_test = str_test.replace("'", "\"")
            try:
                str_test = ujson.loads(str_test)
            except ValueError as e:
                return False
        return str_test

    async def default_query(self, model: BasicModel, query: dict, parent="", model_type="") -> dict:
        # model_schema = model.schema()
        # fields = {k: model_schema['properties'][k]['type'] for k, v in model_schema['properties'].items()}
        if model.str_name().lower() in ["menu_group"] and self.app_code:
            query.update({"$or": [{'apps': {'$in': [self.app_code]}}, {'apps': []}]})

        if not self.check_key(query, "deleted"):
            query.update({"deleted": 0})

        if not self.check_key(query, "active"):
            query.update({"active": True})

        if not self.check_key(query, "parent") and parent:
            query.update({"parent": {"$eq": parent}})

        if not self.check_key(query, "type") and model_type:
            query.update({"type": {"$eq": model_type}})

        q = self.update(query)
        q = self.update(q.copy())
        logger.debug(f"result query: {q}")
        return q
