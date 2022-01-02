# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.

import ujson
from fastapi import Request
import httpx
import logging
from typing import Any, Callable, Coroutine, Dict, List, Optional, Sequence, Type, Union
import uuid
import bson

logger = logging.getLogger(__name__)


class PluginBase:
    plugins = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.plugins.append(cls())

    @classmethod
    def get_last(cls):
        return cls.plugins[-1]

    @classmethod
    def new(cls, **kwargs):
        """
        Use this method for plugin components that have a create method to instance object
        """
        clz = cls.plugins[-1]
        return clz.create(**kwargs)


class BaseClass(dict):

    def __init__(self, **kwargs):
        for i, j in kwargs.items():
            if isinstance(j, dict):
                o = BaseClass(**j)
                object.__setattr__(self, i, o)
            else:
                object.__setattr__(self, i, j)
        super().__init__()

    def __getattribute__(self, attr):
        return super().__getattribute__(attr)

    def __setattr__(self, attr, value):
        return super().__setattr__(attr, value)

    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    def dict(self):
        if self.get("setting"):
            self.pop("setting")
        if self.get("request"):
            self.pop("request")
        return self.copy()

    def json(self):
        if self.get("setting"):
            self.pop("setting")
        if self.get("request"):
            self.pop("request")
        return ujson.dumps(self, escape_forward_slashes=False, ensure_ascii=False)

    def __repr__(self):
        return '%s' % self.__dict__

    @classmethod
    async def get_remote_object_json(self, url, key, headers={}, params={}, cookies={}):
        async with httpx.AsyncClient(timeout=None) as client:
            headers.update({"authtoken": key})
            req = await client.get(
                url=url, params=params, headers=headers, cookies=cookies
            )
            if req.status_code == 200:
                return proxy.json()
            else:
                err_msg = f"response {proxy.statuscode} for url {url}"
                logger.error(f"{err_msg} params {params} headers {headers} cookies {headers}")
                return ujson.dumps(
                    {"error": err_msg, "code": req.status_code}, escape_forward_slashes=False, ensure_ascii=False)
