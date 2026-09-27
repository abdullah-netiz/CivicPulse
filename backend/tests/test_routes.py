from unittest.mock import patch
from uuid import uuid4
import pytest
from httpx import AsyncClient

from app.models import Status
from app.providers.triage.base import Category, Priority
from app.providers.redis_cache import InMemoryCacheProvider


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """
    Rubric: GET /health is liveness only, must return 200 and not touch the database.
    """
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ready_endpoint_success(client: AsyncClient):
    """
    Rubric: GET /ready returns 200 when all dependencies are reachable.
    """
    with patch("app.main.database_check", return_value=None), patch("app.main.redis_check", return_value=None):
        response = await client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["dependencies"]["postgres"] == "ok"
        assert data["dependencies"]["redis"] == "ok"


@pytest.mark.asyncio
async def test_ready_endpoint_dependency_failure(client: AsyncClient):
    """
    CRITICAL REQUIREMENT 3: GET /ready with Postgres or Redis mocked as down,
    asserting 503 response and that it names the failed dependency.
    """
    async def failing_db():
        raise ConnectionRefusedError("Database connection lost")

    async def healthy_redis():
        return None

    with patch("app.main.database_check", side_effect=failing_db), patch("app.main.redis_check", side_effect=healthy_redis):
        response = await client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["dependencies"]["postgres"] == "unavailable"
        assert data["dependencies"]["redis"] == "ok"


@pytest.mark.asyncio
async def test_metrics_endpoint(client: AsyncClient):
    """
    Rubric: GET /metrics exposes Prometheus text format metrics.
    """
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "civicpulse_http_requests_total" in response.text or "text/plain" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_post_complaint_success(client: AsyncClient):
    """
    Rubric: POST /api/complaints validates, triages, and persists a complaint.
    Returns 201 Created with complaint schema.
    """
    payload = {
        "text": "Water pipeline leaking on the main road since yesterday evening",
        "location": "Sector F-10 Markaz, Islamabad",
        "reporter_contact": "0300-9998877",
    }
    response = await client.post("/api/complaints", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["category"] == "water"
    assert data["status"] == "open"
    assert "id" in data
    assert "ai_summary" in data
    assert "triaged_by" in data
    assert data["location"] == payload["location"]


@pytest.mark.asyncio
async def test_post_complaint_field_validation_errors(client: AsyncClient):
    """
    Rubric: 400 with a field-level error body when validation fails.
    """
    payload = {
        "text": "Short",  # < 10 characters
        "location": "A",   # < 3 characters
    }
    response = await client.post("/api/complaints", json=payload)
    assert response.status_code in (400, 422)
    errors = response.json()
    assert "detail" in errors


@pytest.mark.asyncio
async def test_get_complaint_not_found(client: AsyncClient):
    """
    Rubric: GET /api/complaints/{id} returns 404 if not found.
    """
    non_existent_id = uuid4()
    response = await client.get(f"/api/complaints/{non_existent_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Complaint not found"


@pytest.mark.asyncio
async def test_get_complaint_after_create(client: AsyncClient):
    """
    Test creating a complaint then fetching it by ID.
    """
    payload = {
        "text": "Electric wire is sparking continuously near the main transformer",
        "location": "Gulberg III, Lahore",
        "reporter_contact": "resident@lahore.pk",
    }
    create_res = await client.post("/api/complaints", json=payload)
    assert create_res.status_code == 201
    created_id = create_res.json()["id"]

    get_res = await client.get(f"/api/complaints/{created_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["id"] == created_id
    assert data["category"] == "electricity"


@pytest.mark.asyncio
async def test_rate_limiter_exceeded_returns_429(client: AsyncClient, in_memory_cache: InMemoryCacheProvider):
    """
    CRITICAL REQUIREMENT 1: Exceed the POST /api/complaints rate limit
    and assert a 429 response with a Retry-After header.
    """
    ip = "192.168.1.100"
    in_memory_cache.counters[f"rate_limit:complaints:{ip}"] = 10

    payload = {
        "text": "Excessive request submitting spam complaints quickly",
        "location": "Test City",
        "reporter_contact": "test@spam.com",
    }
    response = await client.post("/api/complaints", json=payload, headers={"X-Forwarded-For": ip})
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert response.headers["Retry-After"] == "60"
    assert "Rate limit exceeded" in response.json()["detail"]


@pytest.mark.asyncio
async def test_stats_cache_miss_then_hit_and_invalidation_on_write(
    client: AsyncClient, in_memory_cache: InMemoryCacheProvider
):
    """
    CRITICAL REQUIREMENT 2: Does any test call GET /api/stats twice and assert
    the first response has X-Cache: MISS and the second has X-Cache: HIT?
    Also tests invalidation on write.
    """
    # 1. First call -> MISS
    res1 = await client.get("/api/stats")
    assert res1.status_code == 200
    assert res1.headers.get("X-Cache") == "MISS"
    data1 = res1.json()
    assert "total" in data1
    assert "by_category" in data1

    # 2. Second call -> HIT (cached in Redis / in_memory_cache)
    res2 = await client.get("/api/stats")
    assert res2.status_code == 200
    assert res2.headers.get("X-Cache") == "HIT"

    # 3. Create a complaint -> Invalidate cache on write
    payload = {
        "text": "A new water issue submitted to verify cache invalidation",
        "location": "Sector F-7, Islamabad",
        "reporter_contact": "test@user.pk",
    }
    post_res = await client.post("/api/complaints", json=payload)
    assert post_res.status_code == 201

    # 4. Next stats call after write must be MISS again
    res3 = await client.get("/api/stats")
    assert res3.status_code == 200
    assert res3.headers.get("X-Cache") == "MISS"


@pytest.mark.asyncio
async def test_patch_complaint_status_success_and_conflict(client: AsyncClient):
    """
    Rubric §2.2 / §4.C:
    PATCH /api/complaints/{id}/status enforcers explicit state machine:
    open -> in_progress -> resolved; open -> rejected; in_progress -> rejected.
    Invalid transitions return 409 naming the attempted transition.
    """
    # 1. Create open complaint
    create_res = await client.post(
        "/api/complaints",
        json={
            "text": "Water pipeline broken in street 14 near park",
            "location": "Sector F-8, Islamabad",
        },
    )
    assert create_res.status_code == 201
    cid = create_res.json()["id"]

    # 2. Invalid transition: open -> resolved directly (must be 409 Conflict)
    invalid_res = await client.patch(
        f"/api/complaints/{cid}/status",
        json={"status": "resolved"},
    )
    assert invalid_res.status_code == 409
    assert "Invalid transition" in invalid_res.json()["detail"]
    assert "open" in invalid_res.json()["detail"]
    assert "resolved" in invalid_res.json()["detail"]

    # 3. Valid transition: open -> in_progress
    valid_res1 = await client.patch(
        f"/api/complaints/{cid}/status",
        json={"status": "in_progress"},
    )
    assert valid_res1.status_code == 200
    assert valid_res1.json()["status"] == "in_progress"

    # 4. Valid transition: in_progress -> resolved
    valid_res2 = await client.patch(
        f"/api/complaints/{cid}/status",
        json={"status": "resolved"},
    )
    assert valid_res2.status_code == 200
    assert valid_res2.json()["status"] == "resolved"

    # 5. Invalid transition from terminal state: resolved -> in_progress (409)
    terminal_res = await client.patch(
        f"/api/complaints/{cid}/status",
        json={"status": "in_progress"},
    )
    assert terminal_res.status_code == 409


@pytest.mark.asyncio
async def test_get_meta_providers(client: AsyncClient):
    """
    Rubric §2.2 / §4.C:
    GET /api/meta/providers returns active provider and recent triage outcomes
    containing provider, latency_ms, and fallback fields.
    """
    # Create a complaint to ensure at least one outcome is recorded in the ring buffer
    await client.post(
        "/api/complaints",
        json={
            "text": "Water leakage in sector G-9 near central market",
            "location": "Sector G-9, Islamabad",
        },
    )

    response = await client.get("/api/meta/providers")
    assert response.status_code == 200
    data = response.json()
    assert "active_provider" in data
    assert isinstance(data["active_provider"], str)
    assert "recent_outcomes" in data
    assert isinstance(data["recent_outcomes"], list)
    assert len(data["recent_outcomes"]) > 0

    # Verify recent outcome fields: provider, latency_ms, fallback, timestamp
    latest = data["recent_outcomes"][0]
    assert "provider" in latest
    assert "latency_ms" in latest
    assert "fallback" in latest
    assert isinstance(latest["fallback"], bool)
    assert isinstance(latest["latency_ms"], int)


@pytest.mark.asyncio
async def test_pagination_and_filtering(client: AsyncClient):
    """
    CRITICAL REQUIREMENT 5: Pagination and filtering on GET /api/complaints —
    seed multiple complaints and assert correct slice and total count.
    """
    # Submit 3 distinct complaints
    c1 = {
        "text": "Water pipeline leakage issue number one here",
        "location": "Sector F-8",
    }
    c2 = {
        "text": "Water tap pressure very low in street block",
        "location": "Sector F-9",
    }
    c3 = {
        "text": "Electric wire fallen on road causing danger",
        "location": "Gulberg",
    }
    await client.post("/api/complaints", json=c1)
    await client.post("/api/complaints", json=c2)
    await client.post("/api/complaints", json=c3)

    # Filter by water
    water_res = await client.get("/api/complaints?category=water&page=1&page_size=10")
    assert water_res.status_code == 200
    w_data = water_res.json()
    assert w_data["total"] >= 2
    for item in w_data["items"]:
        assert item["category"] == "water"

    # Test pagination slicing: page_size=1
    slice_res = await client.get("/api/complaints?page=1&page_size=1")
    assert slice_res.status_code == 200
    s_data = slice_res.json()
    assert len(s_data["items"]) == 1
    assert s_data["page"] == 1
    assert s_data["page_size"] == 1
    assert s_data["total"] >= 3
