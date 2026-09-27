from redis.asyncio import Redis, from_url
from app.providers.cache import CacheProvider


class RedisCacheProvider(CacheProvider):
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._client: Redis | None = None

    def _get_client(self) -> Redis:
        if self._client is None:
            self._client = from_url(self.redis_url, decode_responses=True)
        return self._client

    async def get(self, key: str) -> str | None:
        client = self._get_client()
        return await client.get(key)

    async def set(self, key: str, value: str, expire_seconds: int = 30) -> None:
        client = self._get_client()
        await client.set(key, value, ex=expire_seconds)

    async def delete(self, key: str) -> None:
        client = self._get_client()
        await client.delete(key)

    async def increment_rate_limit(self, key: str, window_seconds: int) -> int:
        client = self._get_client()
        # Atomic incr and expire
        async with client.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, window_seconds)
            res = await pipe.execute()
        return res[0]

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()


class InMemoryCacheProvider(CacheProvider):
    def __init__(self):
        self.store: dict[str, str] = {}
        self.counters: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, expire_seconds: int = 30) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def increment_rate_limit(self, key: str, window_seconds: int) -> int:
        count = self.counters.get(key, 0) + 1
        self.counters[key] = count
        return count
