from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.metrics import REQUEST_COUNT, REQUEST_LATENCY, metrics_payload
from app.routes import router


async def database_check() -> None:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    finally:
        await engine.dispose()


async def redis_check() -> None:
    from redis.asyncio import from_url

    client = from_url(get_settings().redis_url)
    try:
        await client.ping()
    finally:
        await client.aclose()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title=get_settings().app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    started = perf_counter()
    response: Response
    try:
        response = await call_next(request)
    except Exception:
        response = JSONResponse(status_code=500, content={"detail": "Internal server error"})
    elapsed = perf_counter() - started
    response.headers["X-Request-ID"] = request_id
    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, request.url.path).observe(elapsed)
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> JSONResponse:
    dependencies: dict[str, str] = {}
    for name, check in (("postgres", database_check), ("redis", redis_check)):
        try:
            await check()
            dependencies[name] = "ok"
        except Exception:
            dependencies[name] = "unavailable"
    status_code = 200 if all(value == "ok" for value in dependencies.values()) else 503
    return JSONResponse(status_code=status_code, content={"status": "ready" if status_code == 200 else "not_ready", "dependencies": dependencies})


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=metrics_payload(), media_type="text/plain; version=0.0.4")
