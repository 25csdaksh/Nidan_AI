import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from app.core.config import settings
from app.core.logging import logger


class CDSSDisclaimerMiddleware(BaseHTTPMiddleware):
    """
    Mandatory middleware ensuring every HTTP response emitted by the NIDAN AI
    platform carries explicit Clinical Decision Support System (CDSS) guardrails
    and non-diagnostic disclaimers.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Generate or extract unique request correlation ID
        request_id = request.headers.get("X-Request-ID", f"req_{uuid.uuid4()}")
        request.state.request_id = request_id

        start_time = time.time()
        
        response: Response = await call_next(request)
        
        process_time_ms = round((time.time() - start_time) * 1000, 2)

        # Inject Required Medical Decision Support Disclaimers
        response.headers["X-CDSS-Disclaimer"] = settings.CDSS_DISCLAIMER
        response.headers["X-CDSS-Confidence-Policy"] = "Human-in-the-loop review mandatory for all clinical findings"
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-MS"] = str(process_time_ms)
        
        # Security response headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"

        if request.url.path not in ["/api/v1/health", "/docs", "/openapi.json"]:
            logger.info(
                "%s %s -> %d (%s ms) [Req: %s]",
                request.method,
                request.url.path,
                response.status_code,
                process_time_ms,
                request_id,
            )

        return response
