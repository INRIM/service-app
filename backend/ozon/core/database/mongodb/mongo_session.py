# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.
from .mongo_base import *


async def find_session_by_token(token: str) -> Any:
    query = (Session.token == token) & (Session.active == True) & (Session.login_complete == True)
    data = await engine.find_one(Session, query)
    return data_helper(data)

#TODO for multiple instance of same user
async def find_session_by_token_req_id(token: str, req_id: str) -> Any:
    query = (Session.token == token) & (Session.active == True) & (Session.login_complete == True) & (
            Session.req_id == req_id)
    data = await engine.find_one(Session, query)
    return data_helper(data)


async def find_session_by_uid(uid: str) -> Any:
    query = (Session.uid == uid) & (Session.active == True)
    data = await engine.find_one(Session, query)
    return data_helper(data)


async def find_session_by_uid_req_id(uid: str, req_id: str) -> Any:
    data = await engine.find_one(Session, Session.uid == uid, Session.req_id == req_id)
    return data_helper(data)
