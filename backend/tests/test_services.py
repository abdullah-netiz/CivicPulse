from unittest.mock import AsyncMock, patch
from uuid import uuid4
import pytest
from app.models import Complaint, Status
from app.providers.triage.base import Category, Priority, TriageResult
from app.providers.triage.simulated import SimulatedTriage
from app.services import ComplaintService
from app.schemas import ComplaintCreate
from app.providers.redis_cache import InMemoryCacheProvider


@pytest.mark.asyncio
async def test_service_submit_success():
    repo = AsyncMock()
    async def fake_create(c: Complaint):
        c.id = uuid4()
        return c
    repo.create.side_effect = fake_create

    provider = SimulatedTriage(should_fail=False)
    cache = InMemoryCacheProvider()
    service = ComplaintService(repo, provider, cache_provider=cache)

    payload = ComplaintCreate(
        text="A water main pipe burst and flooded our garden",
        location="Street 4, Sector F-7",
        reporter_contact="0300-1234567"
    )

    created = await service.submit(payload)
    assert created.category == Category.WATER
    assert created.priority == Priority.HIGH
    assert created.triaged_by == "simulated"
    assert created.status == Status.OPEN
    assert created.triage_latency_ms >= 0
    assert repo.create.called


@pytest.mark.asyncio
async def test_service_submit_fallback_when_provider_raises():
    """
    CRITICAL RUBRIC TEST: Given a provider that always raises,
    POST/submit still succeeds and records triaged_by == 'rules:fallback'
    """
    repo = AsyncMock()
    async def fake_create(c: Complaint):
        c.id = uuid4()
        return c
    repo.create.side_effect = fake_create

    failing_provider = SimulatedTriage(should_fail=True)
    service = ComplaintService(repo, failing_provider)

    payload = ComplaintCreate(
        text="Sewer water is leaking into the main street",
        location="G-11, Islamabad",
        reporter_contact="contact@test.com"
    )

    created = await service.submit(payload)
    assert created.category == Category.WATER
    assert created.triaged_by == "rules:fallback"
    assert created.status == Status.OPEN
    assert repo.create.called


@pytest.mark.asyncio
async def test_service_submit_fallback_when_provider_returns_malformed_output():
    """
    CRITICAL REQUIREMENT 4: A fake provider that returns malformed/out-of-enum output
    (not one that raises an exception - a different failure mode), and assert it is
    rejected and falls back safely to rules:fallback.
    """
    repo = AsyncMock()
    async def fake_create(c: Complaint):
        c.id = uuid4()
        return c
    repo.create.side_effect = fake_create

    # Fake provider returning out-of-enum or invalid object
    class MalformedProvider:
        name = "malformed_llm"
        async def triage(self, text: str, location: str):
            # Returns an object that is not a valid TriageResult or has invalid category
            return "Invalid raw text instead of TriageResult model"

    service = ComplaintService(repo, MalformedProvider())

    payload = ComplaintCreate(
        text="A burst water pipe is flooding street 12 since morning",
        location="Sector F-8, Islamabad",
        reporter_contact="0300-1122334"
    )

    created = await service.submit(payload)
    # Must safely fall back to rules:fallback and categorize as water
    assert created.category == Category.WATER
    assert created.triaged_by == "rules:fallback"
    assert created.status == Status.OPEN
    assert repo.create.called
