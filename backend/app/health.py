from collections.abc import Awaitable, Callable


async def check_ready(
    database_check: Callable[[], Awaitable[None]],
    redis_check: Callable[[], Awaitable[None]],
) -> dict[str, str]:
    dependencies: dict[str, str] = {}
    for name, check in (("postgres", database_check), ("redis", redis_check)):
        try:
            await check()
            dependencies[name] = "ok"
        except Exception:
            dependencies[name] = "unavailable"
    return dependencies
