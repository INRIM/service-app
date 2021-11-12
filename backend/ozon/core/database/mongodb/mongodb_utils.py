from motor.motor_asyncio import AsyncIOMotorClient
from app import config
from .mongodb import db
import logging

logger = logging.getLogger(__name__)



async def connect_to_mongo():
    logging.info("...")
    settings = config.SettingsApp()
    mongocfg = f"mongodb://{settings.mongo_user}:{settings.mongo_pass}@{settings.mongo_url}"
    logger.info(f" DB Url {settings.mongo_url} DB {settings.mongo_db}  ..")
    if not db.client or db.client is None:
        db.client = AsyncIOMotorClient(
            mongocfg,
            replicaset=settings.mongo_replica,
            connectTimeoutMS=30000, socketTimeoutMS=None, socketKeepAlive=True,
            minPoolSize=10)
        db.engine = db.client[settings.mongo_db]  #
        logging.info("connected new connection")
    else:
        logging.info("connection exist")


async def close_mongo_connection():
    logging.info("colse Db...")
    db.client.close()
    logging.info("closed！")