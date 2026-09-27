from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.providers.cache import CacheProvider
from app.providers.redis_cache import RedisCacheProvider
from app.providers.triage.factory import build_triage_provider
from app.repositories import ComplaintRepository
from app.schemas import (
    ComplaintCreate,
    ComplaintListResponse,
    ComplaintResponse,
    ProvidersMetaResponse,
    StatsResponse,
    StatusUpdateRequest,
)
from app.services import ComplaintService

router = APIRouter(prefix="/api")


def get_cache_provider() -> CacheProvider:
    return RedisCacheProvider(get_settings().redis_url)


async def rate_limiter(request: Request, cache: CacheProvider = Depends(get_cache_provider)):
    # Rate limit: max 10 requests per 60 seconds window per client IP
    client_ip = (
        request.headers.get("X-Forwarded-For")
        or (request.client.host if request.client else None)
        or "127.0.0.1"
    )
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    key = f"rate_limit:complaints:{client_ip}"
    limit = 10
    window = 60

    count = await cache.increment_rate_limit(key, window)
    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
            headers={"Retry-After": str(window)},
        )


@router.post(
    "/complaints",
    response_model=ComplaintResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limiter)],
)
async def create_complaint(
    payload: ComplaintCreate,
    session: AsyncSession = Depends(get_session),
    cache: CacheProvider = Depends(get_cache_provider),
):
    service = ComplaintService(
        ComplaintRepository(session),
        build_triage_provider(get_settings()),
        cache_provider=cache,
    )
    return await service.submit(payload)


@router.get("/complaints", response_model=ComplaintListResponse)
async def list_complaints(
    category: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    cache: CacheProvider = Depends(get_cache_provider),
):
    service = ComplaintService(
        ComplaintRepository(session),
        build_triage_provider(get_settings()),
        cache_provider=cache,
    )
    items, total = await service.list_complaints(
        category=category,
        priority=priority,
        status=status,
        page=page,
        page_size=page_size,
    )
    return ComplaintListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/complaints/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint(complaint_id: UUID, session: AsyncSession = Depends(get_session)):
    complaint = await ComplaintRepository(session).get(complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint


@router.patch("/complaints/{complaint_id}/status", response_model=ComplaintResponse)
async def update_complaint_status(
    complaint_id: UUID,
    payload: StatusUpdateRequest,
    session: AsyncSession = Depends(get_session),
    cache: CacheProvider = Depends(get_cache_provider),
):
    from app.services import InvalidStatusTransitionError

    service = ComplaintService(
        ComplaintRepository(session),
        build_triage_provider(get_settings()),
        cache_provider=cache,
    )
    try:
        return await service.update_status(complaint_id, payload.status)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")
    except InvalidStatusTransitionError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid transition from '{err.current_status}' to '{err.attempted_status}'",
        )


@router.get("/meta/providers", response_model=ProvidersMetaResponse)
async def get_meta_providers(
    session: AsyncSession = Depends(get_session),
    cache: CacheProvider = Depends(get_cache_provider),
):
    service = ComplaintService(
        ComplaintRepository(session),
        build_triage_provider(get_settings()),
        cache_provider=cache,
    )
    return service.get_meta_providers()


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    response: Response,
    session: AsyncSession = Depends(get_session),
    cache: CacheProvider = Depends(get_cache_provider),
):
    service = ComplaintService(
        ComplaintRepository(session),
        build_triage_provider(get_settings()),
        cache_provider=cache,
    )
    stats, cache_state = await service.get_stats()
    response.headers["X-Cache"] = cache_state
    return stats
