"""Dual-Tier In-Memory Token Bucket Rate Limiter.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Tiers:
1. General API: 60 requests per minute per IP (capacity=60, fill_rate=1.0 token/s).
2. Auth Endpoints: 5 attempts per 15 minutes per IP (capacity=5, fill_rate=5/900 token/s).

Features:
- High performance in-memory token bucket
- Retry-After HTTP response header calculation
- Zero 're' module imports (strictly enforced per D-02)
- Empathetic plain-language copy per D-12
"""

from __future__ import annotations

import math
import threading
import time
from typing import Dict, Tuple
from fastapi import HTTPException, Request, status

RATE_LIMIT_ERROR_MESSAGE = "Too many requests. Please wait a moment before trying again."


class TokenBucket:
    """Individual leaky token bucket."""

    def __init__(self, capacity: float, fill_rate: float):
        self.capacity = float(capacity)
        self.fill_rate = float(fill_rate)
        self.tokens = float(capacity)
        self.last_update = time.time()
        self._lock = threading.Lock()

    def consume(self, amount: float = 1.0) -> Tuple[bool, int]:
        """Attempt to consume tokens.

        Returns (allowed: bool, retry_after_seconds: int).
        """
        with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)

            if self.tokens >= amount:
                self.tokens -= amount
                return True, 0
            else:
                deficit = amount - self.tokens
                retry_after = (
                    max(1, math.ceil(deficit / self.fill_rate))
                    if self.fill_rate > 0
                    else 60
                )
                return False, retry_after


class InMemoryRateLimiter:
    """Dual-tier IP-based token bucket rate limiter."""

    def __init__(self):
        self._general_buckets: Dict[str, TokenBucket] = {}
        self._auth_buckets: Dict[str, TokenBucket] = {}
        self._lock = threading.RLock()

    def reset(self) -> None:
        """Reset all rate limiter state (useful for tests)."""
        with self._lock:
            self._general_buckets.clear()
            self._auth_buckets.clear()

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP with zero-regex string splitting."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # First IP in comma-separated list
            parts = forwarded.split(",")
            return parts[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    def check_request(self, request: Request) -> None:
        """Check both Auth tier and General tier. Raises HTTPException(429) if exceeded."""
        client_ip = self._get_client_ip(request)
        path = request.url.path

        # 1. Auth Endpoint Tier (5 requests per 15 minutes)
        if path.startswith("/api/v1/auth/login") or path.startswith("/api/v1/auth/google-sso"):
            with self._lock:
                bucket = self._auth_buckets.get(client_ip)
                if bucket is None:
                    # 5 tokens, refilled over 900 seconds (15 min)
                    bucket = TokenBucket(capacity=5.0, fill_rate=5.0 / 900.0)
                    self._auth_buckets[client_ip] = bucket

            allowed, retry_after = bucket.consume(1.0)
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=RATE_LIMIT_ERROR_MESSAGE,
                    headers={"Retry-After": str(retry_after)},
                )

        # 2. General API Tier (60 requests per minute)
        with self._lock:
            bucket = self._general_buckets.get(client_ip)
            if bucket is None:
                # 60 tokens, 1 token per second
                bucket = TokenBucket(capacity=60.0, fill_rate=1.0)
                self._general_buckets[client_ip] = bucket

        allowed, retry_after = bucket.consume(1.0)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=RATE_LIMIT_ERROR_MESSAGE,
                headers={"Retry-After": str(retry_after)},
            )
