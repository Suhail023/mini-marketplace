"""FastAPI middleware for correlation ID propagation."""

import re
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from common.logging_config import CORRELATION_ID_VAR

CORRELATION_ID_HEADER = "X-Correlation-ID"

# Client-supplied IDs are echoed into logs and response headers, so only accept
# short, safe values; anything else is replaced with a fresh UUID.
_VALID_CORRELATION_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Extract or generate a correlation ID, store in contextvar, and attach to response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        cid = request.headers.get(CORRELATION_ID_HEADER, "")
        if not _VALID_CORRELATION_ID.match(cid):
            cid = str(uuid.uuid4())
        token = CORRELATION_ID_VAR.set(cid)
        try:
            response = await call_next(request)
        finally:
            CORRELATION_ID_VAR.reset(token)
        response.headers[CORRELATION_ID_HEADER] = cid
        return response
