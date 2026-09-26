from time import perf_counter

from app.models import Complaint, Status
from app.providers.triage.base import TriageProvider
from app.repositories import ComplaintRepository
from app.schemas import ComplaintCreate


class ComplaintService:
    def __init__(self, repository: ComplaintRepository, provider: TriageProvider):
        self.repository = repository
        self.provider = provider

    async def submit(self, payload: ComplaintCreate) -> Complaint:
        started = perf_counter()
        provider_name = self.provider.name
        try:
            result = await self.provider.triage(payload.text, payload.location)
        except Exception:
            from app.providers.triage.rules import RuleBasedTriage

            result = await RuleBasedTriage().triage(payload.text, payload.location)
            provider_name = "rules:fallback"
        latency_ms = round((perf_counter() - started) * 1000)
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
        return await self.repository.create(complaint)
