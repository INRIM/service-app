from .main.base.base_class import BaseClass, PluginBase
from fastapi.responses import RedirectResponse, JSONResponse
import logging
import uuid
import time as time_

logger = logging.getLogger(__name__)


class Interceptor(PluginBase):
    plugins = []

    def __init_subclass__(cls, **kwargs):
        cls.plugins.append(cls())


class InterceptorBase(Interceptor):

    @classmethod
    def create(cls):
        self = InterceptorBase()
        return self

    async def before_request(self, request):
        self.idm = str(uuid.uuid4())
        if not "/polling/calendar_tasks" in request.url.path or not request.url.path.startswith('/static'):
            logger.info(
                f"rid={self.idm} start request path={request.url.path},req_id={request.headers.get('req_id')}")
            self.start_time = time_.time()

    async def before_response(self, request, response):
        if not "/polling/calendar_tasks" in request.url.path or not request.url.path.startswith('/static'):
            process_time = (time_.time() - self.start_time) * 1000
            formatted_process_time = '{0:.2f}'.format(process_time)
            logger.info(
                f"rid={self.idm} completed_in={formatted_process_time}ms status_code={response.status_code}, "
                f"req_id={response.headers.get('req_id')}"
            )
        if response.status_code == 404:
            return RedirectResponse("/")
        return response
