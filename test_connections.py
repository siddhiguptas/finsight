import asyncio
import os
import traceback
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis

load_dotenv()

async def test_postgres():
    print("--- Testing Postgres (Neon) ---")
    url = os.getenv("DATABASE_URL")
    try:
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"Postgres Success: {result.scalar()}")
        await engine.dispose()
    except Exception:
        print("Postgres Failed:")
        print(traceback.format_exc())

async def test_mongo():
    print("--- Testing MongoDB (Atlas) ---")
    uri = os.getenv("MONGO_URI")
    try:
        client = AsyncIOMotorClient(uri)
        await client.admin.command('ismaster')
        print("MongoDB Success")
        client.close()
    except Exception:
        print("MongoDB Failed:")
        print(traceback.format_exc())

async def test_redis():
    print("--- Testing Redis (Upstash) ---")
    url = os.getenv("REDIS_URL")
    try:
        redis = Redis.from_url(url, decode_responses=True)
        await redis.set("test_connection", "ok", ex=10)
        val = await redis.get("test_connection")
        print(f"Redis Success: {val}")
        await redis.close()
    except Exception:
        print("Redis Failed:")
        print(traceback.format_exc())

async def main():
    await test_postgres()
    await test_mongo()
    await test_redis()

if __name__ == "__main__":
    asyncio.run(main())

