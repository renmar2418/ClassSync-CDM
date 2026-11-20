"""Cryptographic OTP generation and in-memory TTL session management.
OWASP ASVS 4.0 compliant, constant-time verification, max attempt locking.
"""

from __future__ import annotations

import hmac
import secrets
import time
import uuid
from typing import Dict, Optional, Tuple


class OTPSession:
    def __init__(self, email: str, otp_code: str, expiry_seconds: int = 300, max_attempts: int = 3):
        self.session_id: str = str(uuid.uuid4())
        self.email: str = email.lower()
        self.otp_code: str = otp_code
        self.expires_at: float = time.time() + expiry_seconds
        self.max_attempts: int = max_attempts
        self.attempts: int = 0
        self.is_verified: bool = False

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    @property
    def remaining_attempts(self) -> int:
        return max(0, self.max_attempts - self.attempts)


class OTPManager:
    def __init__(self, expiry_seconds: int = 300, max_attempts: int = 3):
        self.expiry_seconds = expiry_seconds
        self.max_attempts = max_attempts
        self._sessions: Dict[str, OTPSession] = {}

    def _cleanup_expired(self) -> None:
        """Purge stale expired sessions to prevent unbounded memory growth."""
        now = time.time()
        expired_keys = [k for k, s in self._sessions.items() if now > s.expires_at]
        for k in expired_keys:
            self._sessions.pop(k, None)

    def generate_code(self, length: int = 6) -> str:
        """Generate a cryptographically secure numeric OTP."""
        digits = "0123456789"
        return "".join(secrets.choice(digits) for _ in range(length))

    def create_session(self, email: str, length: int = 6) -> OTPSession:
        """Create and store a new active OTP session for the email."""
        self._cleanup_expired()
        code = self.generate_code(length)
        session = OTPSession(
            email=email,
            otp_code=code,
            expiry_seconds=self.expiry_seconds,
            max_attempts=self.max_attempts,
        )
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[OTPSession]:
        self._cleanup_expired()
        return self._sessions.get(session_id)

    def verify_code(self, session_id: str, code: str) -> Tuple[bool, str, Optional[str]]:
        """Verify OTP with constant-time equality check.
        Returns: (success: bool, message: str, email: Optional[str])
        """
        session = self._sessions.get(session_id)
        if not session:
            return False, "Verification session not found or already completed. Please request a new code.", None

        if session.is_expired:
            self._sessions.pop(session_id, None)
            return False, "Your verification code has expired. Please sign in again to receive a fresh code.", None

        if session.attempts >= session.max_attempts:
            self._sessions.pop(session_id, None)
            return False, "Too many incorrect attempts. This verification code has been invalidated.", None

        session.attempts += 1

        # Constant-time comparison
        is_match = hmac.compare_digest(session.otp_code.encode("utf-8"), code.strip().encode("utf-8"))
        if is_match:
            email = session.email
            session.is_verified = True
            self._sessions.pop(session_id, None)  # Single-use consumption
            return True, "Identity verified successfully.", email

        remaining = session.remaining_attempts
        if remaining == 0:
            self._sessions.pop(session_id, None)
            return False, "Too many incorrect attempts. This code is now invalid. Please sign in again.", None

        return False, f"Incorrect verification code. You have {remaining} attempt(s) remaining.", None

    def reset(self) -> None:
        """Reset all sessions (for unit testing)."""
        self._sessions.clear()
