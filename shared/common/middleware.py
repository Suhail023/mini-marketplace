"""FastAPI middleware for correlation ID propagation."""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from common.logging_config import CORRELATION_ID_VAR

CORRELATION_ID_HEADER = "X-Correlation-ID"


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Extract or generate a correlation ID, store in contextvar, and attach to response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        cid = request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())
        CORRELATION_ID_VAR.set(cid)

        response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = cid
        return response
