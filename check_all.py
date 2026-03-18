import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis

load_dotenv()

async def test():

    # -------------------
    # Postgres
    # -------------------
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        print("DATABASE_URL:",DATABASE_URL)

        engine = create_async_engine(DATABASE_URL, echo=False)

        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("PG: OK", result.scalar())

        await engine.dispose()

    except Exception as e:
        print(f"PG: ERROR - {str(e)[:120]}")

    # -------------------
    # MongoDB
    # -------------------
    try:
        client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
        await client.admin.command("ping")
        print("MG: OK")
        client.close()

    except Exception as e:
        print(f"MG: ERROR - {str(e)[:120]}")

    # -------------------
    # Redis
    # -------------------
    try:
        redis = Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)
        await redis.ping()
        print("RD: OK")
        await redis.aclose()

    except Exception as e:
        print(f"RD: ERROR - {str(e)[:120]}")


if __name__ == "__main__":
    asyncio.run(test())