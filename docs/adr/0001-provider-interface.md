# ADR 0001: Provider Interface

## Decision

Triage is called through a `TriageProvider` protocol and returns a validated `TriageResult`. The service does not depend on a specific model vendor.

## Consequences

CI can use deterministic simulated triage. Production providers can time out or fail without changing routes or persistence. The service can record fallback behavior consistently.
