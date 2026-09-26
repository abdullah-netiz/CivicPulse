# CivicPulse Architecture

Person 1 foundation target: React/Vite served by nginx reaches FastAPI through the `/api` proxy. FastAPI owns validation, triage orchestration, and persistence boundaries. PostgreSQL is durable storage; Redis will provide cache and distributed rate limiting.

The frontend joins the `edge` network only. The backend joins `edge` and `internal`; PostgreSQL and Redis join `internal` only. The frontend therefore has no network route to the data services.

The Submit slice is complete at `POST /api/complaints` and `GET /api/complaints/{id}`. Triage is selected through `TRIAGE_PROVIDER` and is represented by a provider interface, so deterministic CI providers and production providers share the same service path.

The frontend uses nginx proxying rather than an absolute API URL. This keeps the browser bundle environment-independent: one built image can be deployed behind different hosts without rebuilding JavaScript.
