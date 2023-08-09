# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
from .mongo_base import *


def check_parse_json(str_test):
    try:
        str_test = ujson.loads(str_test)
    except ValueError as e:
        str_test = str_test.replace("'", '"')
        try:
            str_test = ujson.loads(str_test)
        except ValueError as e:
            return str_test
    return str_test


async def find_session_by_token(token: str) -> Any:
    query = {"token": token, "active": True, "login_complete": True}
    data = await find_one(Session, query)
    return data


async def get_param(name: str) -> Any:
    data = await get_param_name(name)
    vals = check_parse_json(data)
    if isinstance(vals, dict):
        return vals.copy()
    else:
        if isinstance(vals, str):
            return {}
        return vals


async def get_app(name: str) -> Any:
    data = await raw_find_one("settings", {"rec_name": name})
    if not data:
        return {}
    return data.copy()


# TODO for multiple instance of same user
async def find_session_by_token_req_id(token: str, req_id: str) -> Any:
    query = {
        "token": token,
        "active": True,
        "login_complete": True,
        "req_id": req_id,
    }
    data = await find_one(Session, query)
    return data_helper(data)


async def find_session_by_uid(uid: str) -> Any:
    query = {"uid": uid, "active": True}
    data = await find_one(Session, query)
    return data


async def find_session_by_uid_req_id(uid: str, req_id: str) -> Any:
    data = await find_one(Session, {"uid": uid, "req_id": req_id})
    return data_helper(data)
