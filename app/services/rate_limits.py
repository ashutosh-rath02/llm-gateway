from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import Request

from app.api.security import AuthContext
from app.core.config import get_settings
from app.core.errors import GatewayError


class ExecuteRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def enforce(self, *, auth: AuthContext, request: Request) -> None:
        settings = get_settings()
        if not settings.execute_rate_limit_enabled:
            return

        now = monotonic()
        window_seconds = float(settings.execute_rate_limit_window_seconds)
        identifier = self._build_identifier(auth=auth, request=request)

        with self._lock:
            bucket = self._requests[identifier]
            while bucket and now - bucket[0] >= window_seconds:
                bucket.popleft()

            if len(bucket) >= settings.execute_rate_limit_requests:
                retry_after_seconds = max(1, int(window_seconds - (now - bucket[0])))
                raise GatewayError(
                    (
                        "Rate limit exceeded for execute requests. "
                        f"Try again in about {retry_after_seconds} seconds."
                    ),
                    error_type="rate_limit_exceeded",
                    status_code=429,
                )

            bucket.append(now)

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()

    def _build_identifier(self, *, auth: AuthContext, request: Request) -> str:
        if auth.tenant_id:
            return f"tenant:{auth.tenant_id}:{auth.name}"
        if auth.is_admin:
            return f"admin:{auth.name}"

        client_host = request.client.host if request.client else "unknown"
        return f"anonymous:{client_host}"


execute_rate_limiter = ExecuteRateLimiter()


def reset_execute_rate_limiter() -> None:
    execute_rate_limiter.reset()
