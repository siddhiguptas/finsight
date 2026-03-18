import asyncio
from app.core.database import engine
from app.models.schemas import Base

async def init_db():
    print("Initializing Database Tables...")
    async with engine.begin() as conn:
        # This will create all tables defined in models/schemas.py
        await conn.run_sync(Base.metadata.create_all)
    print("Database Initialized Successfully.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())
