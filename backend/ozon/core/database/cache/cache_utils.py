from redis import asyncio as aioredis
import config
import logging
from .cache import ioredis, get_redis, RedisBackend

logger = logging.getLogger(__name__)


async def init_cache():
    logger.info("...")
    logger.info(f" start Redis Cache ..")
    settings = config.SettingsApp()
    if not ioredis.client or ioredis.client is None:
        ioredis.client = aioredis.from_url(
            "redis://redis_cache",
            encoding="utf8",
            decode_responses=False,
            socket_keepalive=True,
        )
        ioredis.cache = RedisBackend(ioredis.client)
        logging.info("new Redis Cache created")
    else:
        logging.info("Redis Cache  exist")


async def stop_cache():
    logger.info("stopping Redis Cache...")
    redis = await get_redis()
    await redis.close()
    logger.info("stopped！")
