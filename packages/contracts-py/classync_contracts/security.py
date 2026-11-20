"""Standardized Argon2id cryptographic helpers for ClassSync.
Official Project Title: ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System

Conforms strictly to OWASP ASVS 4.0:
- Memory cost: 65536 KiB (64 MiB)
- Time cost: 3 iterations
- Parallelism: 4 threads
- Salt length: 16 bytes
- Hash length: 32 bytes
"""

from __future__ import annotations
from argon2 import PasswordHasher
from argon2.exceptions import (
    Argon2Error,
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

# Standardized OWASP ASVS 4.0 Argon2id Hasher
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using Argon2id with OWASP ASVS 4.0 parameters.

    Args:
        plain_password: The plaintext password string to hash.

    Returns:
        The encoded Argon2id hash string.
    """
    if not isinstance(plain_password, str):
        raise TypeError("plain_password must be a string")
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against an Argon2id hash string.

    Supports both (plain_password, hashed_password) and (hash_str, password)
    calling conventions for robust interoperability across microservices.

    Args:
        plain_password: Plaintext password or hash string.
        hashed_password: Encoded hash string or plaintext password.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    if not isinstance(plain_password, str) or not isinstance(hashed_password, str):
        return False

    try:
        # Detect if the first argument is actually the argon2 hash
        if plain_password.startswith("$argon2") and not hashed_password.startswith("$argon2"):
            return _hasher.verify(plain_password, hashed_password)
        # Standard signature: verify(hash=hashed_password, password=plain_password)
        return _hasher.verify(hashed_password, plain_password)
    except (Argon2Error, InvalidHashError, VerificationError, VerifyMismatchError, ValueError):
        return False
