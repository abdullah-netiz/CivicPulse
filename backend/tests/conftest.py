import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import get_settings
from app.db import get_session
from app.main import app
from app.models import Base
from app.providers.triage.simulated import SimulatedTriage

# Set test environment defaults
os.environ["TRIAGE_PROVIDER"] = "simulated"

# We use an in-memory SQLite database with async support for tests if postgres is unavailable,
# or test against the configured db.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


from app.providers.redis_cache import InMemoryCacheProvider
from app.routes import get_cache_provider


@pytest_asyncio.fixture
async def in_memory_cache() -> InMemoryCacheProvider:
    return InMemoryCacheProvider()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, in_memory_cache: InMemoryCacheProvider) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_session():
        yield db_session

    def override_get_cache():
        return in_memory_cache

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_cache_provider] = override_get_cache
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
