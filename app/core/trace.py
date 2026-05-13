from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def create_trace_id() -> str:
    return f"trace_{uuid4().hex}"


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = request.headers.get("X-Trace-Id") or create_trace_id()
        request.state.trace_id = trace_id

        started_at = perf_counter()
        response = await call_next(request)
        duration_ms = (perf_counter() - started_at) * 1000

        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
        return response

