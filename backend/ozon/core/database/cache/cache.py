from aioredis.client import Redis

import logging


class OzonCache:
    client: Redis = None


ioredis = OzonCache()


async def get_redis() -> Redis:
    return ioredis.client
