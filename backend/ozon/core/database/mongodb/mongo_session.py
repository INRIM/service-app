# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
from .mongo_base import *


async def find_session_by_token(token: str) -> Any:
    data = await engine.find_one(Session, Session.token == token)
    return data_helper(data)


async def find_session_by_token_req_id(token: str, req_id: str) -> Any:
    data = await engine.find_one(Session, Session.token == token, Session.req_id == req_id)
    return data_helper(data)


async def find_session_by_uid(uid: str) -> Any:
    data = await engine.find_one(Session, Session.uid == uid)
    return data_helper(data)


async def find_session_by_uid_req_id(uid: str, req_id: str) -> Any:
    data = await engine.find_one(Session, Session.uid == uid, Session.req_id == req_id)
    return data_helper(data)
