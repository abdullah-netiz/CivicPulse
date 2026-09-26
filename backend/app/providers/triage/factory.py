from app.config import Settings
from app.providers.triage.base import TriageProvider
from app.providers.triage.rules import RuleBasedTriage
from app.providers.triage.simulated import SimulatedTriage


def build_triage_provider(settings: Settings) -> TriageProvider:
    if settings.triage_provider == "rules":
        return RuleBasedTriage()
    if settings.triage_provider == "simulated":
        return SimulatedTriage()
    return RuleBasedTriage()
