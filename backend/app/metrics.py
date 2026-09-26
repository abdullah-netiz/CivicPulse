from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter("civicpulse_requests_total", "HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("civicpulse_request_latency_seconds", "HTTP request latency", ["method", "path"])
TRIAGE_LATENCY = Histogram("civicpulse_triage_latency_seconds", "Triage latency")
TRIAGE_FALLBACKS = Counter("civicpulse_triage_fallback_total", "Triage fallbacks")


def metrics_payload() -> bytes:
    return generate_latest()
