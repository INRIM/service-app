# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
from .mongo_base import *


async def find_session_by_token(token: str) -> Any:
    query = {"token": token, "active": True, "login_complete": True}
    data = await find_one(Session, query)
    return data_helper(data)


# TODO for multiple instance of same user
async def find_session_by_token_req_id(token: str, req_id: str) -> Any:
    query = {"token": token, "active": True, "login_complete": True, "req_id": req_id}
    data = await find_one(Session, query)
    return data_helper(data)


async def find_session_by_uid(uid: str) -> Any:
    query = {"uid": uid, "active": True}
    data = await find_one(Session, query)
    return data_helper(data)


async def find_session_by_uid_req_id(uid: str, req_id: str) -> Any:
    data = await find_one(Session, {"uid": uid, "req_id": req_id})
    return data_helper(data)
