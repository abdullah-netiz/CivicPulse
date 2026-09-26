from app.providers.triage.base import Category, Priority, TriageResult


class RuleBasedTriage:
    name = "rules"

    async def triage(self, text: str, location: str) -> TriageResult:
        content = f"{text} {location}".lower()
        category = Category.OTHER
        keywords = {
            Category.WATER: ("water", "pipe", "flood", "leak", "sewer"),
            Category.ELECTRICITY: ("electric", "power", "wire", "transformer", "light"),
            Category.SANITATION: ("garbage", "waste", "drain", "smell", "sewage"),
            Category.ROADS: ("road", "pothole", "street", "bridge", "traffic"),
            Category.STREETLIGHTS: ("streetlight", "lamp", "dark road"),
        }
        for candidate, terms in keywords.items():
            if any(term in content for term in terms):
                category = candidate
                break
        urgent_terms = ("flood", "fire", "danger", "exposed", "accident", "burst")
        priority = Priority.HIGH if any(term in content for term in urgent_terms) else Priority.NORMAL
        summary = " ".join(text.split())[:140]
        return TriageResult(category=category, priority=priority, summary=summary, confidence=0.75)
