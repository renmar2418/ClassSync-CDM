"""Security Headers Middleware for ClassSync Gateway.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Configures:
- Content-Security-Policy (Turnstile-compatible)
- Strict-Transport-Security (HSTS)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy
- X-XSS-Protection: 1; mode=block
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

CSP_DIRECTIVE = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com; "
    "style-src 'self' 'unsafe-inline'; "
    "frame-src 'self' https://challenges.cloudflare.com; "
    "connect-src 'self' https://challenges.cloudflare.com https://*.pnm.edu.ph; "
    "img-src 'self' data: https:; "
    "font-src 'self' data:; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self';"
)


def apply_security_headers(response: Response) -> Response:
    """Attach standard security headers to any Starlette / FastAPI Response."""
    response.headers["Content-Security-Policy"] = CSP_DIRECTIVE
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains; preload"
    )
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Starlette middleware injecting production security headers on every response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        return apply_security_headers(response)

