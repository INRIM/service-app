# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import logging
from typing import Optional, Union

import ujson
from fastapi import (
    FastAPI,
    Request,
    Header,
)
from fastapi.responses import (
    JSONResponse,
)

from core.ExportService import ExportService
from core.Gateway import Gateway
from settings import get_settings, templates

logger = logging.getLogger(__name__)

auth_api = FastAPI(
    title=f"{get_settings().module_name} Client",
    description=get_settings().description,
    version=get_settings().version,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)
