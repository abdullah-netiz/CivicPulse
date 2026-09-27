from time import perf_counter
import logging

from app.models import Complaint, Status
from app.providers.triage.base import TriageProvider
from app.repositories import ComplaintRepository
from app.schemas import ComplaintCreate

from datetime import datetime, timezone
import json
from app.providers.cache import CacheProvider
from app.providers.triage.base import Category, Priority, TriageResult

logger = logging.getLogger(__name__)

# Valid state machine transitions as explicit table (Rubric §2.2 & §4.C):
# open -> in_progress -> resolved;
# open -> rejected;
# in_progress -> rejected.
# resolved and rejected are terminal.
VALID_STATUS_TRANSITIONS: dict[Status, set[Status]] = {
    Status.OPEN: {Status.IN_PROGRESS, Status.REJECTED},
    Status.IN_PROGRESS: {Status.RESOLVED, Status.REJECTED},
    Status.RESOLVED: set(),
    Status.REJECTED: set(),
}

# Global in-memory ring buffer for last 20 triage outcomes
RECENT_TRIAGE_OUTCOMES: list[dict] = []
MAX_RECENT_OUTCOMES = 20


def record_triage_outcome(provider: str, latency_ms: int, fallback: bool) -> None:
    outcome = {
        "provider": provider,
        "latency_ms": latency_ms,
        "fallback": fallback,
        "timestamp": datetime.now(timezone.utc),
    }
    RECENT_TRIAGE_OUTCOMES.append(outcome)
    if len(RECENT_TRIAGE_OUTCOMES) > MAX_RECENT_OUTCOMES:
        RECENT_TRIAGE_OUTCOMES.pop(0)


class InvalidStatusTransitionError(Exception):
    def __init__(self, current_status: Status, attempted_status: Status):
        self.current_status = current_status
        self.attempted_status = attempted_status
        super().__init__(f"Cannot transition complaint from '{current_status}' to '{attempted_status}'")


class ComplaintService:
    STATS_CACHE_KEY = "complaints:stats"

    def __init__(
        self,
        repository: ComplaintRepository,
        provider: TriageProvider,
        cache_provider: CacheProvider | None = None,
    ):
        self.repository = repository
        self.provider = provider
        self.cache_provider = cache_provider

    async def submit(self, payload: ComplaintCreate) -> Complaint:
        started = perf_counter()
        provider_name = self.provider.name
        result: TriageResult | None = None

        try:
            raw_result = await self.provider.triage(payload.text, payload.location)
            # Strict validation against schema/enums if raw_result was malformed
            if not isinstance(raw_result, TriageResult) or not isinstance(raw_result.category, Category) or not isinstance(raw_result.priority, Priority):
                raise ValueError("Malformed triage output from provider")
            result = raw_result
        except Exception:
            from app.providers.triage.rules import RuleBasedTriage

            logger.warning("Triage fallback activated: provider=%s", provider_name)
            result = await RuleBasedTriage().triage(payload.text, payload.location)
            provider_name = "rules:fallback"

        latency_ms = round((perf_counter() - started) * 1000)
        is_fallback = provider_name == "rules:fallback"
        record_triage_outcome(provider_name, latency_ms, is_fallback)

        complaint = Complaint(
            text=payload.text,
            location=payload.location,
            reporter_contact=payload.reporter_contact,
            category=result.category,
            priority=result.priority,
            status=Status.OPEN,
            ai_summary=result.summary,
            triaged_by=provider_name,
            triage_latency_ms=latency_ms,
        )
        created = await self.repository.create(complaint)

        # Invalidate stats cache on write as specified in requirements
        if self.cache_provider is not None:
            await self.cache_provider.delete(self.STATS_CACHE_KEY)

        return created

    async def update_status(self, complaint_id, new_status: Status) -> Complaint:
        complaint = await self.repository.get(complaint_id)
        if complaint is None:
            raise KeyError(f"Complaint {complaint_id} not found")

        current = Status(complaint.status)
        target = Status(new_status)

        allowed = VALID_STATUS_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise InvalidStatusTransitionError(current, target)

        updated = await self.repository.update_status(complaint, target.value)
        # Invalidate stats cache on write
        if self.cache_provider is not None:
            await self.cache_provider.delete(self.STATS_CACHE_KEY)

        return updated

    def get_meta_providers(self) -> dict:
        return {
            "active_provider": self.provider.name,
            "recent_outcomes": list(reversed(RECENT_TRIAGE_OUTCOMES)),
        }

    async def list_complaints(
        self,
        category: str | None = None,
        priority: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Complaint], int]:
        page_size = min(max(page_size, 1), 100)
        page = max(page, 1)
        return await self.repository.list_complaints(
            category=category,
            priority=priority,
            status=status,
            page=page,
            page_size=page_size,
        )

    async def get_stats(self) -> tuple[dict, str]:
        if self.cache_provider is not None:
            cached = await self.cache_provider.get(self.STATS_CACHE_KEY)
            if cached is not None:
                return json.loads(cached), "HIT"

        stats = await self.repository.get_stats()

        if self.cache_provider is not None:
            await self.cache_provider.set(self.STATS_CACHE_KEY, json.dumps(stats), expire_seconds=30)

        return stats, "MISS"
