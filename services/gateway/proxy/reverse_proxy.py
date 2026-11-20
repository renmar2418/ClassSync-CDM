"""HTTPX Streaming Reverse Proxy & Downstream Trust Header Injector.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Dispatches:
- /api/v1/academic/*   -> http://localhost:8001
- /api/v1/scheduling/* -> http://localhost:8002
- /api/v1/presence/*   -> http://localhost:8004

Sanitizes headers: Strips untrusted client-supplied X-User-* headers.
Injects verified downstream trust headers:
- X-User-ID
- X-User-Role
- X-User-Email
- X-Forwarded-For
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
import httpx
from fastapi import HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}

DOWNSTREAM_TIMEOUT_ERROR_MESSAGE = (
    "The requested campus service is momentarily unavailable. Please retry in a few moments."
)


class ReverseProxyHandler:
    """Handles reverse proxying requests with downstream trust header injection."""

    def __init__(self, service_routes: Dict[str, str]):
        """service_routes maps URL prefix to destination base URL.

        e.g. {
            "/api/v1/academic": "http://localhost:8001",
            "/api/v1/scheduling": "http://localhost:8002",
            "/api/v1/presence": "http://localhost:8004",
        }
        """
        self.service_routes = service_routes

    def resolve_target_url(self, request_path: str) -> Optional[Tuple[str, str]]:
        """Resolves target base URL and path prefix."""
        for prefix, target_base in self.service_routes.items():
            if request_path.startswith(prefix):
                return target_base.rstrip("/"), request_path
        return None

    async def proxy_request(
        self,
        request: Request,
        client: httpx.AsyncClient,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Proxies an HTTP request to downstream microservices."""
        resolved = self.resolve_target_url(request.url.path)
        if not resolved:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service route not found.",
            )

        target_base, target_path = resolved
        url = f"{target_base}{target_path}"
        if request.url.query:
            url = f"{url}?{request.url.query}"

        # 1. Prepare Forwarded Headers (Header Sanitization & Anti-Spoofing)
        headers: Dict[str, str] = {}
        for key, value in request.headers.items():
            lower_k = key.lower()
            # Strip hop-by-hop headers, untrusted client-supplied user headers, and prior forwarded header
            if (
                lower_k in HOP_BY_HOP_HEADERS
                or lower_k.startswith("x-user-")
                or lower_k == "x-forwarded-for"
            ):
                continue
            headers[key] = value

        # 2. Inject Downstream Trust Headers if authenticated
        if user_context:
            headers["X-User-ID"] = str(user_context.get("sub", ""))
            headers["X-User-Role"] = str(user_context.get("role", ""))
            headers["X-User-Email"] = str(user_context.get("email", ""))

        # 3. Client IP Forwarding
        client_ip = request.headers.get("x-forwarded-for") or (
            request.client.host if request.client else "127.0.0.1"
        )
        headers["X-Forwarded-For"] = client_ip

        # 4. Read body or stream safely
        try:
            body = await request.body()
        except RuntimeError:
            body = b""

        try:
            req = client.build_request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
            )
            resp = await client.send(req, stream=True)

            # Filter response hop-by-hop headers
            resp_headers = {
                k: v
                for k, v in resp.headers.items()
                if k.lower() not in HOP_BY_HOP_HEADERS
            }

            return StreamingResponse(
                resp.aiter_bytes(),
                status_code=resp.status_code,
                headers=resp_headers,
                background=resp.aclose,
            )
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=DOWNSTREAM_TIMEOUT_ERROR_MESSAGE,
            )
