"""HS256 JWT Token Lifecycle Implementation.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Provides constant-time HMAC-SHA256 signature verification, access token (15m),
refresh token (7d), cookie extraction, and Authorization Bearer header support.
Zero third-party dependencies (pure standard library: hmac, hashlib, base64, json, time).
Zero 're' module imports (strictly enforced per D-02).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status

from classync_contracts.enums import UserRole


def _b64url_encode(data: bytes) -> str:
    """Encode bytes to unpadded URL-safe Base64 string."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    """Decode unpadded or padded URL-safe Base64 string to bytes."""
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


class JWTManager:
    """Standard library HS256 JWT Manager."""

    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        access_exp_minutes: int = 15,
        refresh_exp_days: int = 7,
    ):
        self.secret = secret
        self.algorithm = algorithm
        self.access_exp_seconds = access_exp_minutes * 60
        self.refresh_exp_seconds = refresh_exp_days * 86400

    def create_token(self, payload: Dict[str, Any]) -> str:
        """Create a signed HS256 JWT string."""
        header = {"alg": self.algorithm, "typ": "JWT"}
        h_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        p_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
        sig = hmac.new(self.secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        sig_b64 = _b64url_encode(sig)
        return f"{h_b64}.{p_b64}.{sig_b64}"

    def create_access_token(
        self,
        user_id: str,
        email: str,
        role: str,
        hd: Optional[str] = None,
        requires_password_change: bool = False,
        full_name: Optional[str] = None,
    ) -> str:
        """Create a short-lived access token (default 15 minutes)."""
        now = int(time.time())
        role_str = role.value if isinstance(role, UserRole) else str(role)
        payload = {
            "sub": str(user_id),
            "email": str(email),
            "role": role_str,
            "hd": hd or ("student.pnm.edu.ph" if role_str == "STUDENT" else "pnm.edu.ph"),
            "token_type": "access",
            "requires_password_change": requires_password_change,
            "name": full_name or "",
            "iat": now,
            "exp": now + self.access_exp_seconds,
        }
        return self.create_token(payload)

    def create_refresh_token(self, user_id: str) -> str:
        """Create a long-lived refresh token (default 7 days)."""
        now = int(time.time())
        payload = {
            "sub": str(user_id),
            "token_type": "refresh",
            "iat": now,
            "exp": now + self.refresh_exp_seconds,
        }
        return self.create_token(payload)

    def decode_and_verify(self, token: str, expected_type: str = "access") -> Dict[str, Any]:
        """Decode and verify an HS256 JWT, enforcing signature, expiration, and token type.

        Raises HTTPException(401) on invalid signature, malformed structure, or expiration.
        """
        if not isinstance(token, str) or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please sign in to access this portal area.",
            )

        parts = token.split(".")
        if len(parts) != 3:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token structure.",
            )

        h_b64, p_b64, sig_b64 = parts
        signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
        expected_sig = hmac.new(self.secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        expected_sig_b64 = _b64url_encode(expected_sig)

        if not hmac.compare_digest(expected_sig_b64, sig_b64):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token signature verification failed.",
            )

        try:
            payload = json.loads(_b64url_decode(p_b64).decode("utf-8"))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed token payload.",
            )

        # Expiration Check
        now = int(time.time())
        if "exp" in payload and payload["exp"] < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired. Please sign in again.",
            )

        # Token Type Check
        if expected_type and payload.get("token_type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Expected {expected_type} token.",
            )

        return payload

    def extract_token_from_request(self, request: Request) -> Optional[str]:
        """Extract JWT string from Authorization Bearer header or access_token cookie."""
        # 1. Bearer Header
        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:].strip()

        # 2. HttpOnly Cookie
        cookie_token = request.cookies.get("access_token")
        if cookie_token:
            return cookie_token.strip()

        return None
