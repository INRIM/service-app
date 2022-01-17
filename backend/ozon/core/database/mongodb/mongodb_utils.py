from motor.motor_asyncio import AsyncIOMotorClient
import config
from .mongodb import db
import logging

logger = logging.getLogger(__name__)


async def connect_to_mongo():
    logger.info("...")
    settings = config.SettingsApp()
    mongocfg = f"mongodb://{settings.mongo_user}:{settings.mongo_pass}@{settings.mongo_url}"
    logger.info(f" DB Url {settings.mongo_url} DB {settings.mongo_db}  ..")
    if not db.client or db.client is None:
        if settings.mongo_replica:
            db.client = AsyncIOMotorClient(
                mongocfg,
                replicaset=settings.mongo_replica,
                connectTimeoutMS=30000, socketTimeoutMS=None, socketKeepAlive=True,
                minPoolSize=20)
        else:
            db.client = AsyncIOMotorClient(
                mongocfg,
                connectTimeoutMS=30000, socketTimeoutMS=None, socketKeepAlive=True,
                minPoolSize=20)
        db.engine = db.client[settings.mongo_db]  #
        logging.info("connected new connection")
    else:
        logging.info("connection exist")


async def close_mongo_connection():
    logger.info("colse Db...")
    db.client.close()
    logger.info("closed！")
