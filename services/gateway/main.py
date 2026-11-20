"""FastAPI Application for ClassSync Security Gateway Microservice.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System
Port: 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from services.gateway.config import settings
from services.gateway.auth.jwt import JWTManager
from services.gateway.auth.routes import auth_router
from services.gateway.middleware.rbac import RBACRouteGuard
from services.gateway.middleware.security_headers import (
    SecurityHeadersMiddleware,
    apply_security_headers,
)
from services.gateway.middleware.rate_limiter import InMemoryRateLimiter
from services.gateway.proxy.reverse_proxy import ReverseProxyHandler

# ---------------------------------------------------------------------------
# Lifespan Management
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize connection pooled AsyncClient
    limits = httpx.Limits(max_keepalive_connections=50, max_connections=200)
    timeout = httpx.Timeout(10.0, connect=5.0)
    app.state.http_client = httpx.AsyncClient(limits=limits, timeout=timeout)
    yield
    # Graceful shutdown
    if hasattr(app.state, "http_client") and not app.state.http_client.is_closed:
        await app.state.http_client.aclose()


app = FastAPI(
    title="ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System - Security Gateway",
    description="Zero-Trust Ingress Reverse Proxy, Cloudflare Turnstile, Google Workspace OAuth, Argon2id Auth & RBAC Middleware on Port 8000.",
    version="1.0.0",
    lifespan=lifespan,
)

# Shared Singletons
jwt_manager = JWTManager(
    secret=settings.jwt_secret,
    access_exp_minutes=settings.access_token_expire_minutes,
    refresh_exp_days=settings.refresh_token_expire_days,
)
rate_limiter = InMemoryRateLimiter()
proxy_handler = ReverseProxyHandler(
    service_routes={
        "/api/v1/academic": settings.academic_service_url,
        "/api/v1/scheduling": settings.scheduling_service_url,
        "/api/v1/presence": settings.presence_service_url,
        "/api/v1/notification": settings.notification_service_url,
    }
)


# ---------------------------------------------------------------------------
# Ingress Middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def security_gateway_middleware(request: Request, call_next):
    """Global Gateway Middleware: Rate Limiter, Auth Token Extraction, RBAC, & Reverse Proxy."""
    try:
        path = request.url.path

        # 1. Rate Limiting Check
        rate_limiter.check_request(request)

        # 2. Extract Token and Resolve User Context
        token = jwt_manager.extract_token_from_request(request)
        user_context = None
        user_role = None
        if token:
            try:
                user_context = jwt_manager.decode_and_verify(token, expected_type="access")
                user_role = user_context.get("role")
            except HTTPException:
                # If a token was provided but invalid/expired on a protected route, raise it
                if not RBACRouteGuard.is_public_path(path):
                    raise
                user_context = None
                user_role = None
            except Exception:
                user_context = None
                user_role = None

        # Attach to request state
        request.state.user = user_context

        # 3. RBAC Route Guard Enforcement
        RBACRouteGuard.check_access(path, user_role)

        # 4. Proxy Dispatching vs Local Handlers
        if (
            path.startswith("/api/v1/academic")
            or path.startswith("/api/v1/scheduling")
            or path.startswith("/api/v1/presence")
            or path.startswith("/api/v1/notification")
        ):
            client = getattr(app.state, "http_client", None)
            if client is None or client.is_closed:
                client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))
                app.state.http_client = client
            return await proxy_handler.proxy_request(request, client, user_context)

        # Local Route Processing (e.g. /api/v1/auth/*, /health, /docs)
        return await call_next(request)

    except HTTPException as exc:
        headers = dict(exc.headers) if exc.headers else {}
        resp = JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=headers,
        )
        return apply_security_headers(resp)


# ---------------------------------------------------------------------------
# Middleware Registration
# (Starlette builds middleware in reverse addition order: last added is outermost)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# SecurityHeadersMiddleware is added last so it acts as the outermost middleware,
# ensuring all responses (including 401, 403, 429, 502) carry complete security headers.
app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
    """Explicit exception handler ensuring all raised HTTPExceptions carry security headers."""
    headers = dict(exc.headers) if exc.headers else {}
    resp = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers,
    )
    return apply_security_headers(resp)



# Mount Local Routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])


@app.get("/health", tags=["Monitoring"])
def health_check():
    """Service health monitoring endpoint."""
    return {
        "status": "healthy",
        "service": "gateway",
        "port": 8000,
        "title": "ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System",
    }
