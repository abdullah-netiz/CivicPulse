from contextlib import asynccontextmanager
import asyncio
import json
import logging
import signal
import sys
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.metrics import REQUEST_COUNT, REQUEST_LATENCY, metrics_payload
from app.routes import router


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "request_id": getattr(record, "request_id", None),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONFormatter())
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
# Clear default handlers and attach json handler to stdout
root_logger.handlers = [handler]

logger = logging.getLogger("civicpulse")


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
    logger.info("Application starting up")
    
    # Graceful shutdown handler for SIGTERM / SIGINT
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def handle_sigterm(signame):
        logger.info(f"Received {signame}, draining in-flight requests and initiating graceful shutdown...")
        stop_event.set()

    for signame in ("SIGTERM", "SIGINT"):
        if hasattr(signal, signame):
            try:
                loop.add_signal_handler(getattr(signal, signame), lambda s=signame: handle_sigterm(s))
            except (NotImplementedError, RuntimeError):
                # On Windows or unsupported environments, signals might not be addable to loop
                pass

    yield

    logger.info("Application shutdown complete. Closed connections.")


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
    except Exception as exc:
        logger.error(
            "Unhandled server exception during request processing",
            extra={"request_id": request_id},
            exc_info=True,
        )
        response = JSONResponse(status_code=500, content={"detail": "Internal server error"})
    elapsed = perf_counter() - started
    response.headers["X-Request-ID"] = request_id
    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, request.url.path).observe(elapsed)

    # Log request line with propagated request_id
    logger.info(
        f"{request.method} {request.url.path} {response.status_code} in {round(elapsed * 1000, 2)}ms",
        extra={"request_id": request_id},
    )
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
