import aioredis
from app import config
import logging
from .cache import ioredis, get_redis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

logger = logging.getLogger(__name__)


async def init_cache():
    logger.info("...")
    logger.info(f" start Redis Cache ..")
    settings = config.SettingsApp()
    if not ioredis.client or ioredis.client is None:
        ioredis.client = aioredis.from_url(
            "redis://redis_cache", encoding="utf8", decode_responses=True,
            socket_keepalive=True,
        )
        FastAPICache.init(RedisBackend(ioredis.client), prefix=f"{settings.app_code}")
        logging.info("new Redis Cache created")
    else:
        logging.info("Redis Cache  exist")


async def stop_cache():
    logger.info("stopping Redis Cache...")
    redis = await get_redis()
    await redis.close()
    logger.info("stopped！")
