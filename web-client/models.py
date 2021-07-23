# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
from enum import Enum
from pydantic import BaseModel, Field, PrivateAttr
from typing import List, Optional, Generic, TypeVar
import base64
from datetime import date, datetime, time, timedelta

from pydantic.generics import GenericModel
import logging

logger = logging.getLogger(__name__)

class Token(BaseModel):
    username: str
    password: str
    secret: str
    alg: str

class BaseSuccessResponse(BaseModel):
    Success: str = "done"


class BaseErrorResponse(BaseModel):
    status: str = "error"
    message: str


ItemT = TypeVar('ItemT')


class Auth(BaseModel):
    username: str
    password: str
    base_url_ws: str
    _token: str = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        token = f"{self.username}:{self.password}"
        bytemsg = base64.b64encode(token.encode('utf-8'))
        tokenb64 = str(bytemsg, "utf-8")
        self._token = f"Basic {tokenb64}"


class ListModel(GenericModel, Generic[ItemT]):
    items: List[ItemT]
    length: int


class DataModel(GenericModel, Generic[ItemT]):
    data: ItemT
