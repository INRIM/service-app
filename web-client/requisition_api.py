# Copyright INRIM (https://www.inrim.eu)
# See LICENSE file for full licensing details.
import logging

from fastapi import FastAPI, Request
from fastapi.responses import (
    JSONResponse,
)

from core.ContentService import ContentService
from core.Gateway import Gateway
from settings import get_settings, templates

logger = logging.getLogger(__name__)

requisition_api = FastAPI()

