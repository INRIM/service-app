# Copyright INRIM (https://www.inrim.eu)
# Author Alessio Gerace @Inrim
# See LICENSE file for full licensing details.

from typing import Optional, Sequence, Union, Any
from fastapi.responses import RedirectResponse, JSONResponse

from starlette.requests import HTTPConnection, Request
from starlette.types import Message, Receive, Scope, Send
from fastapi import FastAPI
from .Ozon import Ozon
from .SessionMain import SessionMain, SessionBase
import logging
import bson

logger = logging.getLogger(__name__)


class OzonRawMiddleware:
    def __init__(
            self, app: FastAPI, ozon_class: Optional[Any] = None
    ) -> None:
        self.app = app
        self.ozon = None

    async def set_ozon(
            self, request: Union[Request, HTTPConnection]
    ) -> Union[Request, HTTPConnection]:
        """
        You might want to override this method.
        The dict it returns will be saved in the scope of a context. You can
        always do that later.
        """

        request.scope['ozon'] = Ozon.new()
        session = await request.scope['ozon'].init_request(request)
        return session

    @staticmethod
    def get_request_object(
            scope, receive, send
    ) -> Union[Request, HTTPConnection]:
        # here we instantiate HTTPConnection instead of a Request object
        # because only headers are needed so that's sufficient.
        # If you need the payload etc for your plugin
        # instantiate Request(scope, receive, send)
        return Request(scope, receive, send)

    async def __call__(
            self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] not in ("http", "websocket"):  # pragma: no cover
            await self.app(scope, receive, send)
            return

        request = self.get_request_object(scope, receive, send)
        logger.info(f" Middleware receive request : {request.url.path} params {request.query_params}")

        async def send_wrapper(message: Message) -> None:
            await request.scope['ozon'].handle_response(message)
            await send(message)

        session = await self.set_ozon(request)

        logger.info(
            f"check need_session: session: {type(session)}")

        need_login = False
        if not session or session is None:
            logger.info(
                f"no session detected url: {request.url}, "
                f"object: {request.scope['ozon']} , params: {request.query_params}, headers{request.headers}"
            )
            # self.session = await self.init_request(request)
            need_login = True
            need_login = request.scope['ozon'].need_session(request)

        if need_login:
            response = request.scope['ozon'].login_response(request)
            await response(scope, receive, send)
        else:
            request.scope['ozon'].session = session
            await self.app(scope, receive, send_wrapper)
