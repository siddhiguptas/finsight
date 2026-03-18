class RateLimitExceeded(Exception):
    pass


class APIRateLimiter:
    def __init__(self, redis, key: str, max_calls: int, window_seconds: int):
        self.redis = redis
        self.key = f"rate_limit:{key}"
        self.max_calls = max_calls
        self.window = window_seconds

    async def acquire(self):
        count = await self.redis.incr(self.key)
        if count == 1:
            await self.redis.expire(self.key, self.window)
        if count > self.max_calls:
            wait = await self.redis.ttl(self.key)
            raise RateLimitExceeded(f"Rate limit hit. Retry in {wait}s")
