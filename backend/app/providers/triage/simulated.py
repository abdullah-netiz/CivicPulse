from app.providers.triage.base import TriageResult
from app.providers.triage.rules import RuleBasedTriage


class SimulatedTriage:
    name = "simulated"

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    async def triage(self, text: str, location: str) -> TriageResult:
        if self.should_fail:
            raise RuntimeError("simulated provider failure")
        result = await RuleBasedTriage().triage(text, location)
        return result.model_copy(update={"confidence": 0.9})
