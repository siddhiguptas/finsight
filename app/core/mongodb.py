from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

mongo_client = AsyncIOMotorClient(settings.mongo_uri)
mongo_db = mongo_client.get_default_database(default="finsight")
