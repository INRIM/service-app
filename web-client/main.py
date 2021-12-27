from appinit import *
import logging
import importlib

logger = logging.getLogger(__name__)

for name_app in get_settings().plugins:
    try:
        logger.info(f"import app: {name_app}")
        importlib.import_module(name_app)
    except ImportError as e:
        logger.error(f"Error import app: {name_app} msg: {e} ", exc_info=True)
