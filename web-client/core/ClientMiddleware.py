import asyncio
import typing

from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from .main.base.base_class import BaseClass, PluginBase
from .Interceptor import Interceptor
import logging


logger = logging.getLogger(__name__)

RequestResponseEndpoint = typing.Callable[
    [Request], typing.Awaitable[Response]
]
DispatchFunction = typing.Callable[
    [Request, RequestResponseEndpoint], typing.Awaitable[Response]
]


class ClientMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        request.scope["interceptor"] = Interceptor.new()

        # async def send_wrapper(message: Message) -> None:
        #     await request.scope['ozon'].handle_response(message)
        #     await send(message)

        await request.scope["interceptor"].before_request(request)
        if request.scope.get("security_next_call"):
            response = await request.scope.get("security_next_call")(request)
        else:
            response = await self.call_next(request)
            response = await request.scope["interceptor"].before_response(
                request, response
            )

        await response(scope, receive, send)

    async def call_next(self, request: Request) -> Response:
        loop = asyncio.get_event_loop()
        queue: "asyncio.Queue[typing.Optional[Message]]" = asyncio.Queue()

        scope = request.scope
        receive = request.receive
        send = queue.put

        async def coro() -> None:
            try:
                await self.app(scope, receive, send)
            finally:
                await queue.put(None)

        task = loop.create_task(coro())
        message = await queue.get()
        if message is None:
            task.result()
            raise RuntimeError("No response returned.")
        assert message["type"] == "http.response.start"

        async def body_stream() -> typing.AsyncGenerator[bytes, None]:
            while True:
                message = await queue.get()
                if message is None:
                    break
                assert message["type"] == "http.response.body"
                yield message.get("body", b"")
            task.result()

        response = StreamingResponse(
            status_code=message["status"], content=body_stream()
        )
        response.raw_headers = message["headers"]
        return response
