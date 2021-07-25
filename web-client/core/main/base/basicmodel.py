# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.

from typing import List, Optional, Dict, Any, Literal
from bson.objectid import ObjectId
from slugify import slugify
from datetime import date, datetime, time, timedelta
from typing import Type, TypeVar
from pydantic import BaseModel


class Component(BaseModel):
    title: str = ""
    rec_name: str = ""
    data_model: str = ""
    path: str = ""
    parent: str = ""
    parent_name: str = ""
    components: List[Dict] = []
    childs: Optional[List[str]] = []
    links: Dict = {}
    type: str = 'form'
    no_cancel: int = 0
    display: str = ""
    action: str = ""
    tags: Optional[List[str]] = []
    deleted: float = 0
    list_order: int = 10
    settings: Dict = {}
    properties: Dict = {}
    handle_global_change: int = 1
    process_tenant: str = ""
    process_id: str = ""
    process_task_id: str = ""
    owner_name: str = ""
    owner_uid: str = ""
    owner_function: str = ""
    owner_sector: str = ""
    update_uid: str = ""
    create_datetime: Optional[datetime]
    update_datetime: Optional[datetime]
    make_virtual_model: bool = False
    sys: bool = False
    default: bool = False
    active: bool = True
    demo: bool = False
    projectId: str = ""  # needed for compatibility with fomriojs


class Session(BaseModel):
    uid: str
    token: str = ""
    is_admin: bool = False
    use_auth: bool = False
    user: dict = {}
    app: dict = {}
    action: dict = {}
    list_order: int = 0
    user_preferences: dict = {}
    create_datetime: Optional[datetime]
    update_datetime: Optional[datetime]
    sys: bool = False
    active: bool = True
    default: bool = True
    demo: bool = False


class TokenUser(BaseModel):
    uid: str
    uid_fuction: Optional[str]
    token: str
    app: str
    ip: Optional[str] = "0.0.0.0"
    mobile: bool = False
    create_datetime: datetime
    expire_datetime: datetime
    life_hours: int = 36
    function: str = ""
    sector: str = ""
    sector_id: int = 0
    sector_uid: str = ""
    valid: bool = False
    user_data: dict = {}

    def update_validity(self):
        if self.expire_datetime < datetime.now():
            self.valid = False


class UserTokenHistory(BaseModel):
    uid: str
    history: List[Dict] = []

# TODO to remove ASAP
# class Submission(BaseModel):
#     component_name: str = ""  # default {component.name}
#     parent: str = ""
#     name: str = ""  # default {component.name}_{self.id}
#     childs: Optional[Dict] = {}
#     deleted: float = 0
#     list_order: int = 0
#     data: Dict
#     data_value: Dict = {}
#     type: str = ''
#     owner_name: str = ""
#     owner_uid: str = ""
#     owner_function: str = ""
#     owner_sector: str = ""
#     update_uid: str = ""
#     create_datetime: Optional[datetime]
#     update_datetime: Optional[datetime]
#     sys: bool = False
#     default: bool = False
#     active: bool = True
#     demo: bool = False


# TODO Remove
# class settingData(BaseModel):
#     rec_name: str = "settingData"
#     deleted: float = 0
#     next_refresh: float = 0
#     data: dict = {}
#     owner_name: str = ""
#     owner_uid: str = ""
#     owner_function: str = ""
#     owner_sector: str = ""
#     update_uid: str = ""
#     list_order: int = 0
#     create_datetime: Optional[datetime]
#     update_datetime: Optional[datetime]
#     sys: bool = False
#     default: bool = False
#     active: bool = True
#     demo: bool = False