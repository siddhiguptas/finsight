import json
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.redis import redis_client
from app.models.schemas import UserWatchlist

CACHE_TTL = 300

class PersonalizationService:
    def __init__(self):
        self.cache_ttl = CACHE_TTL

    async def get_user_context(
        self,
        user_id: UUID,
        db: AsyncSession
    ) -> dict:
        cache_key = f"user_ctx:{user_id}"

        cached = await redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

        portfolio_tickers = await db.execute(
            select(UserWatchlist.ticker).where(UserWatchlist.user_id == user_id)
        )
        watchlist_tickers = [row[0] for row in portfolio_tickers.all()]

        context = {
            "portfolio_tickers": watchlist_tickers,
            "watchlist_tickers": watchlist_tickers,
            "all_tickers": list(set(watchlist_tickers)),
            "subscribed_sectors": [],
        }

        await redis_client.setex(cache_key, self.cache_ttl, json.dumps(context, default=str))
        return context

    async def invalidate_user_cache(self, user_id: UUID):
        cache_key = f"user_ctx:{user_id}"
        await redis_client.delete(cache_key)

        feed_pattern = f"feed:{user_id}:*"
        keys = await redis_client.keys(feed_pattern)
        if keys:
            await redis_client.delete(*keys)

personalization_service = PersonalizationService()
