from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import logging


class Mongo:
    client: AsyncIOMotorClient = None
    engine: AsyncIOMotorDatabase = None


db = Mongo()


async def get_database() -> AsyncIOMotorDatabase:
    return db.engine


async def get_client() -> AsyncIOMotorClient:
    return db.client
