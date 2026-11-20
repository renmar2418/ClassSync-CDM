"""RFC 6238 15-Second Rotating TOTP Generator for ClassSync Physical Presence.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Specifications:
- RFC 6238 Time-Based One-Time Password
- Time Step (Interval): Strictly 15 seconds (interval=15)
- Digest Algorithm: HMAC-SHA256 (hashlib.sha256)
- Digit Count: 6 digits (digits=6, zero-padded)
- Verification Window: ±1 step tolerance (30-second effective window)
- Dynamic QR Payload: {"room": room_code, "session": session_id, "totp": token, "ts": epoch_seconds}
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
import uuid
from typing import Any, Dict, Optional, Union

import pyotp


class TOTPGenerator:
    """RFC 6238 TOTP Engine configured for 15-second rotation and HMAC-SHA256."""

    INTERVAL: int = 15
    DIGITS: int = 6
    DIGEST: Any = hashlib.sha256
    VALID_WINDOW: int = 1  # ±1 step tolerance (30s effective window)

    def __init__(self, interval: int = 15, digits: int = 6):
        self.interval = interval
        self.digits = digits
        self.digest = hashlib.sha256

    @staticmethod
    def generate_secret() -> str:
        """Generate a cryptographically secure 32-character Base32 secret."""
        return pyotp.random_base32()

    @staticmethod
    def derive_secret(master_key: str, room_code: str, session_id: Union[str, uuid.UUID]) -> str:
        """Deterministically derive a per-room/per-session Base32 secret from a master key.

        Enables stateless multi-instance verification without distributed key synchronization.
        """
        seed = f"{room_code.strip()}:{str(session_id).strip()}".encode("utf-8")
        raw_mac = hmac.new(master_key.encode("utf-8"), seed, hashlib.sha256).digest()
        # Encode first 20 bytes (160 bits) to Base32 (32 characters without padding)
        return base64.b32encode(raw_mac[:20]).decode("ascii").rstrip("=")

    def get_totp_instance(self, secret: str) -> pyotp.TOTP:
        """Create a configured pyotp.TOTP instance with HMAC-SHA256 and 15s interval."""
        return pyotp.TOTP(
            s=secret,
            digits=self.digits,
            digest=self.digest,
            interval=self.interval,
        )

    def generate_token(self, secret: str, for_time: Optional[Union[int, float]] = None) -> str:
        """Generate the current 6-digit zero-padded TOTP token.

        Args:
            secret: Base32 secret string.
            for_time: Optional epoch timestamp (defaults to current time).
        """
        t = int(for_time if for_time is not None else time.time())
        totp = self.get_totp_instance(secret)
        return totp.at(t)

    def verify_token(
        self,
        secret: str,
        token: str,
        for_time: Optional[Union[int, float]] = None,
        valid_window: int = 1,
    ) -> bool:
        """Verify a 6-digit TOTP token against the ±valid_window tolerance.

        With valid_window=1 and interval=15s, tokens from the prior 15s window,
        current window, and immediate next window are accepted (30s effective tolerance).
        Tokens older than 30s are strictly rejected.
        """
        if not token:
            return False
        cleaned_token = str(token).strip()
        if len(cleaned_token) != self.digits or not cleaned_token.isdigit():
            return False

        t = int(for_time if for_time is not None else time.time())
        totp = self.get_totp_instance(secret)
        return bool(totp.verify(cleaned_token, for_time=t, valid_window=valid_window))

    def time_remaining(self, for_time: Optional[Union[int, float]] = None) -> int:
        """Return the number of seconds remaining in the current 15-second window (1-15)."""
        t = int(for_time if for_time is not None else time.time())
        rem = self.interval - (t % self.interval)
        return rem if rem != 0 else self.interval

    def current_step(self, for_time: Optional[Union[int, float]] = None) -> int:
        """Return the integer step counter floor(t / interval)."""
        t = int(for_time if for_time is not None else time.time())
        return t // self.interval

    def generate_qr_payload(
        self,
        room_code: str,
        session_id: Union[str, uuid.UUID],
        secret: str,
        for_time: Optional[Union[int, float]] = None,
    ) -> Dict[str, Any]:
        """Generate the dynamic QR payload dictionary.

        Output format: {"room": room_code, "session": session_id, "totp": token, "ts": epoch_seconds}
        """
        t = int(for_time if for_time is not None else time.time())
        token = self.generate_token(secret, for_time=t)
        return {
            "room": room_code,
            "session": str(session_id),
            "totp": token,
            "ts": t,
        }

    def generate_qr_payload_json(
        self,
        room_code: str,
        session_id: Union[str, uuid.UUID],
        secret: str,
        for_time: Optional[Union[int, float]] = None,
    ) -> str:
        """Serialize the QR payload into compact JSON format with zero redundant whitespace."""
        payload = self.generate_qr_payload(
            room_code=room_code,
            session_id=session_id,
            secret=secret,
            for_time=for_time,
        )
        return json.dumps(payload, separators=(",", ":"))


class SessionSecretManager:
    """Thread-safe in-memory session registry for COMLAB active sessions and secrets."""

    def __init__(self, default_master_key: str = "classync-presence-master-secret-2026"):
        self.master_key = default_master_key
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self.generator = TOTPGenerator()

    def create_session(
        self,
        room_code: str,
        session_id: Optional[Union[str, uuid.UUID]] = None,
        secret: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create or register an active instructional session for a room."""
        sess_id = uuid.UUID(str(session_id)) if session_id else uuid.uuid4()
        chosen_secret = secret or self.generator.generate_secret()

        record = {
            "room_code": room_code,
            "session_id": sess_id,
            "secret": chosen_secret,
            "created_at": time.time(),
            "metadata": metadata or {},
        }

        with self._lock:
            self._sessions[room_code] = record

        return record

    def get_session(self, room_code: str) -> Optional[Dict[str, Any]]:
        """Retrieve the active session record for a room."""
        with self._lock:
            return self._sessions.get(room_code)

    def get_secret(self, room_code: str) -> Optional[str]:
        """Retrieve the active TOTP secret for a room."""
        sess = self.get_session(room_code)
        return sess["secret"] if sess else None

    def end_session(self, room_code: str) -> bool:
        """Terminate and deregister the active session for a room."""
        with self._lock:
            if room_code in self._sessions:
                del self._sessions[room_code]
                return True
            return False

    def is_session_active(self, room_code: str, session_id: Optional[Union[str, uuid.UUID]] = None) -> bool:
        """Check if an active session exists for a room and matches session_id if provided."""
        sess = self.get_session(room_code)
        if not sess:
            return False
        if session_id:
            return str(sess["session_id"]) == str(session_id)
        return True
