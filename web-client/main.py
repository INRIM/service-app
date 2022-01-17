from appinit import *
import logging
import importlib
import sys
import pathlib

logger = logging.getLogger(__name__)

sys.path.append(pathlib.Path(__file__).parent.resolve())

for name_app in get_settings().depends:
    try:
        logger.info(f"import app: {name_app}")
        sys.path.append(name_app)
        importlib.import_module(name_app)
    except ImportError as e:
        logger.error(f"Error import app: {name_app} msg: {e} ", exc_info=True)
