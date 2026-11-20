"""Role-Based Access Control (RBAC) Route Guard Middleware.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Enforces the ClassSync Zero-Trust Route Enforcement Matrix:
- /api/v1/academic/admin/*, /api/v1/scheduling/solve* -> ADMIN only
- /api/v1/scheduling/swaps*, /api/v1/presence/totp/* -> FACULTY or ADMIN
- /api/v1/presence/checkin*, /api/v1/presence/rooms/* -> STUDENT, FACULTY, or ADMIN
- /api/v1/auth/*, /health, /docs, /openapi.json, /redoc -> Public

Strictly enforces Decision Log D-12 empathetic error copy:
- 403 Forbidden: "You do not have access to this portal area. Please contact the Academic Administrator if you need permission."
- 401 Unauthorized: "Please sign in to access this portal area."
- Zero 're' module imports (strictly enforced per D-02).
"""

from __future__ import annotations

from typing import Optional, Set, Union
from fastapi import HTTPException, Request, status

from classync_contracts.enums import UserRole

# ---------------------------------------------------------------------------
# Constants & Empathetic Plain-Language Messages (Decision Log D-12)
# ---------------------------------------------------------------------------

FORBIDDEN_ERROR_MESSAGE = (
    "You do not have access to this portal area. Please contact the Academic Administrator if you need permission."
)
UNAUTHORIZED_ERROR_MESSAGE = (
    "Please sign in to access this portal area."
)


class RBACRouteGuard:
    """Enforces zero-trust role-based route access controls."""

    @staticmethod
    def is_public_path(path: str) -> bool:
        """Determines if a route path is public without requiring authentication."""
        return (
            path == "/health"
            or path.startswith("/health/")
            or path.startswith("/api/v1/auth/")
            or path.startswith("/docs")
            or path.startswith("/openapi.json")
            or path.startswith("/redoc")
        )

    @classmethod
    def get_required_roles(cls, path: str) -> Optional[Set[UserRole]]:
        """Returns the set of permitted UserRoles for a given path, or None if public."""
        if cls.is_public_path(path):
            return None

        # 1. Admin-Only Routes
        if (
            path.startswith("/api/v1/academic/admin")
            or path.startswith("/api/v1/scheduling/solve")
        ):
            return {UserRole.ADMIN}

        # 2. Faculty + Admin Routes
        if (
            path.startswith("/api/v1/scheduling/swaps")
            or path.startswith("/api/v1/presence/totp")
        ):
            return {UserRole.FACULTY, UserRole.ADMIN}

        # 3. Student + Faculty + Admin Routes
        if (
            path.startswith("/api/v1/presence/checkin")
            or path.startswith("/api/v1/presence/checkout")
            or path.startswith("/api/v1/presence/rooms")
            or path.startswith("/api/v1/presence/scanner")
            or path.startswith("/api/v1/presence/logs")
            or path.startswith("/api/v1/presence/events")
            or path.startswith("/api/v1/academic")
            or path.startswith("/api/v1/scheduling")
        ):
            return {UserRole.STUDENT, UserRole.FACULTY, UserRole.ADMIN}

        # Default fall-through for any other protected endpoints
        return {UserRole.STUDENT, UserRole.FACULTY, UserRole.ADMIN}

    @classmethod
    def check_access(
        cls,
        path: str,
        user_role: Optional[Union[UserRole, str]],
    ) -> None:
        """Checks access for a user role against the required route permissions.

        Raises:
            HTTPException(401) if authentication is missing on a protected route.
            HTTPException(403) with D-12 copy if the role is insufficient.
        """
        required_roles = cls.get_required_roles(path)
        if required_roles is None:
            return  # Public route, access granted

        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=UNAUTHORIZED_ERROR_MESSAGE,
            )

        try:
            role_enum = UserRole(user_role)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=FORBIDDEN_ERROR_MESSAGE,
            )

        if role_enum not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=FORBIDDEN_ERROR_MESSAGE,
            )
