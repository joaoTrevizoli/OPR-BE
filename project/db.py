from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import logging
from project.config import settings
from project.api import models as models

mongo_client: AsyncIOMotorClient | None = None

async def get_db() -> AsyncIOMotorDatabase:
    assert mongo_client is not None, "Database not initialized"
    db_name = settings.MONGODB_SETTINGS[0]['db']
    return mongo_client[db_name]


async def initiate_database():
    global mongo_client
    mongo_client = AsyncIOMotorClient(settings.MONGODB_SETTINGS[0]["host"])
    db = await get_db()
    await init_beanie(database=db, document_models=models.cocccidiosis_models)


async def close_db_connect():
    global mongo_client
    if mongo_client is None:
        logging.warning('Connection is None, nothing to close.')
        return
    mongo_client.close()
    mongo_client = None
    logging.info('Mongo connection closed.')
