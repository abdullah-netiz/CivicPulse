# CivicPulse

CivicPulse is a municipal complaint intake system. A citizen submits free text and a location; the backend validates it, triages it through a replaceable provider, stores the result, and returns the category, priority, summary, and provider.

## Person 1 Slice

The first complete workflow is complaint submission through the frontend and API:

- `POST /api/complaints` validates, triages, and persists a complaint.
- `GET /api/complaints/{id}` retrieves a stored complaint.
- `/health` is liveness only.
- `/ready` checks PostgreSQL and Redis.
- `/metrics` exposes Prometheus text metrics.
- nginx serves the frontend and proxies `/api` to the backend.

## Local Quickstart

Copy `.env.example` to `.env`, then run:

```bash
docker compose up --build
```

Open <http://localhost:8080>. The first startup applies the Alembic migration before starting the API. Stop with `Ctrl+C`; named volumes preserve PostgreSQL and Redis data.

For deterministic local work, keep `TRIAGE_PROVIDER=simulated`. Hosted providers and Kubernetes belong to the later handoff phase.

## Development Checks

```bash
python3.12 -m compileall -q backend/app backend/alembic
docker compose config --quiet
```

The backend follows the required four-layer direction: routes handle HTTP, services handle business rules, repositories handle SQL, and providers handle external integrations.
