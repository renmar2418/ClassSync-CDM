"""OWASP ASVS 4.0 Password Entropy Validator and Argon2id Hashing Engine.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Strictly enforces:
- Decision Log D-02: Zero-Regex deterministic validation (no 're' module imports).
- Decision Log D-07: Mandatory first-time password setup with OWASP ASVS 4.0 entropy enforcement.
- Decision Log D-12: Human-centered plain-language error messages without technical jargon.
- OWASP ASVS 4.0: Argon2id configuration (Memory 64 MiB / m=65536, t=3, p=4, hash_len=32, salt_len=16).
"""

from __future__ import annotations

import math
from typing import Any, List, Optional, Tuple

from argon2 import PasswordHasher
from argon2.exceptions import (
    Argon2Error,
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

from classync_contracts.schemas import PasswordIntegrityResponse


# ===========================================================================
# 1. Institutional Constants & Blacklists
# ===========================================================================

# Forbidden campus and easily guessed keywords (case-insensitive)
CAMPUS_DICTIONARY_BLACKLIST: Tuple[str, ...] = (
    "cdm",
    "montalban",
    "pnm",
    "classsync",
    "password",
    "123456",
    "admin",
    "faculty",
    "student",
    "college",
    "pamantasan",
    "colegio",
)

CAMPUS_BLACKLIST = CAMPUS_DICTIONARY_BLACKLIST

# Reference sequences for sliding-window sequence detection (length >= 4)
# Contains alphabetical, numerical, and standard QWERTY keyboard rows
REFERENCE_SEQUENCES: Tuple[str, ...] = (
    "abcdefghijklmnopqrstuvwxyz",
    "0123456789",
    "qwertyuiop",
    "asdfghjkl",
    "zxcvbnm",
    "!@#$%^&*()_+",
)

# All forward and backward patterns
ALL_SEQUENTIAL_PATTERNS: Tuple[str, ...] = (
    REFERENCE_SEQUENCES + tuple(s[::-1] for s in REFERENCE_SEQUENCES)
)

SEQUENTIAL_STRINGS: Tuple[str, ...] = (
    "0123", "1234", "2345", "3456", "4567", "5678", "6789",
    "abcd", "bcde", "cdef", "defg", "efgh", "fghi", "ghij", "qwerty",
    "3210", "4321", "5432", "6543", "7654", "8765", "9876",
    "dcba", "edcb", "fedc", "gfed", "hgfe", "ihgf", "jihg", "ytrewq",
)

# Leetspeak substitution map for evasive dictionary word detection
LEETSPEAK_MAP = str.maketrans({
    "@": "a",
    "0": "o",
    "1": "i",
    "3": "e",
    "5": "s",
    "$": "s",
    "7": "t",
})

# Standardized OWASP ASVS 4.0 Argon2id Parameters
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 65536  # 64 MiB in KiB
ARGON2_PARALLELISM = 4
ARGON2_HASH_LEN = 32
ARGON2_SALT_LEN = 16

_hasher = PasswordHasher(
    time_cost=ARGON2_TIME_COST,
    memory_cost=ARGON2_MEMORY_COST,
    parallelism=ARGON2_PARALLELISM,
    hash_len=ARGON2_HASH_LEN,
    salt_len=ARGON2_SALT_LEN,
)


# ===========================================================================
# 2. Custom Exception Classes
# ===========================================================================

class PasswordEntropyError(ValueError):
    """Raised when a password fails OWASP ASVS 4.0 entropy or institutional rules."""

    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.message = message
        self.errors = errors or [message]


# ===========================================================================
# 3. Zero-Regex Validation & Entropy Analysis Helpers
# ===========================================================================

def calculate_entropy_bits(password: str) -> float:
    """Calculate the theoretical information entropy of a password string in bits.

    Formula: E = L * log2(R), where L is password length and R is character pool size.
    Zero-regex execution using character ordinals.
    """
    if not isinstance(password, str) or not password:
        return 0.0

    pool_size = 0
    # Lowercase characters (ord 97-122)
    if any(97 <= ord(c) <= 122 for c in password):
        pool_size += 26
    # Uppercase characters (ord 65-90)
    if any(65 <= ord(c) <= 90 for c in password):
        pool_size += 26
    # Decimal digits (ord 48-57)
    if any(48 <= ord(c) <= 57 for c in password):
        pool_size += 10
    # Printable symbols / punctuation (ord 33-47, 58-64, 91-96, 123-126)
    if any(
        (33 <= ord(c) <= 47)
        or (58 <= ord(c) <= 64)
        or (91 <= ord(c) <= 96)
        or (123 <= ord(c) <= 126)
        for c in password
    ):
        pool_size += 32

    if pool_size == 0:
        return 0.0

    return round(len(password) * math.log2(pool_size), 2)


def detect_forbidden_campus_keyword(password: str) -> Optional[str]:
    """Check for forbidden campus dictionary keywords using case-insensitivity and leetspeak.

    Returns the matched forbidden keyword if found, None otherwise.
    Zero-regex execution using pure Python string lower and translate.
    """
    lower_pwd = password.lower()
    norm_pwd = lower_pwd.translate(LEETSPEAK_MAP)

    for keyword in CAMPUS_DICTIONARY_BLACKLIST:
        if keyword in lower_pwd or keyword in norm_pwd:
            return keyword
    return None


def detect_sequential_sequence(password: str, min_length: int = 4) -> Optional[str]:
    """Detect forward and backward sequences of length >= 4 (alphabetical, numerical, or keyboard).

    Also detects repeated identical character sequences (e.g. 'aaaa', '1111').
    Zero-regex execution using sliding window checks.
    """
    if len(password) < min_length:
        return None

    lower_pwd = password.lower()

    for idx in range(len(lower_pwd) - min_length + 1):
        window = lower_pwd[idx : idx + min_length]

        # 1. Check repeated character sequence
        if window[0] == window[1] == window[2] == window[3]:
            return password[idx : idx + min_length]

        # 2. Check sliding window against forward and reversed patterns
        for pattern in ALL_SEQUENTIAL_PATTERNS:
            if window in pattern:
                return password[idx : idx + min_length]

    return None


def assess_password_entropy(
    password: Any,
    identifier: Optional[str] = None,
) -> Tuple[bool, float, List[str]]:
    """Comprehensively assess password compliance against OWASP ASVS 4.0 and CdM/PNM rules.

    Zero-regex execution using character ordinals and pure string methods.

    Returns:
        Tuple of (is_valid: bool, entropy_bits: float, failure_reasons: List[str])
    """
    reasons: List[str] = []

    if not isinstance(password, str) or not password:
        return False, 0.0, ["Please enter a password."]

    entropy_bits = calculate_entropy_bits(password)

    # 1. Whitespace padding check
    if password != password.strip():
        reasons.append("Your password cannot begin or end with spaces.")

    # 2. Control character check (ord < 32 or ord == 127)
    for char in password:
        if ord(char) < 32 or ord(char) == 127:
            reasons.append("Your password contains invalid or invisible control characters.")
            break

    # 3. Minimum length of 10 characters
    if len(password) < 10:
        reasons.append("Your password must be at least 10 characters long.")

    # 4. Uppercase letter check (ord 65-90)
    if not any(65 <= ord(c) <= 90 for c in password):
        reasons.append("Your password must include at least one capital letter (A–Z).")

    # 5. Lowercase letter check (ord 97-122)
    if not any(97 <= ord(c) <= 122 for c in password):
        reasons.append("Your password must include at least one lowercase letter (a–z).")

    # 6. Digit check (ord 48-57)
    if not any(48 <= ord(c) <= 57 for c in password):
        reasons.append("Your password must include at least one number (0–9).")

    # 7. Special character / symbol check (ord 33-47, 58-64, 91-96, 123-126)
    if not any(
        (33 <= ord(c) <= 47)
        or (58 <= ord(c) <= 64)
        or (91 <= ord(c) <= 96)
        or (123 <= ord(c) <= 126)
        for c in password
    ):
        reasons.append("Your password must include at least one special symbol (e.g. !@#$%^&*).")

    # 8. Campus dictionary blacklist check
    matched_keyword = detect_forbidden_campus_keyword(password)
    if matched_keyword:
        reasons.append(
            f"Your password cannot contain campus names or common terms like '{matched_keyword}'."
        )

    # 9. Sequential pattern check (length >= 4)
    matched_seq = detect_sequential_sequence(password)
    if matched_seq:
        reasons.append(
            f"Your password cannot contain predictable sequences of letters, numbers, or keyboard patterns (like '{matched_seq}')."
        )

    # 10. Student ID or username inclusion check
    if identifier:
        cleaned_id = str(identifier).strip().lower().replace("-", "")
        lower_pass = password.lower()
        if len(cleaned_id) >= 4 and cleaned_id in lower_pass:
            reasons.append(
                "Your password cannot contain parts of your Student ID or institutional username."
            )

    is_valid = len(reasons) == 0
    return is_valid, entropy_bits, reasons


def validate_password_entropy(password: Any, identifier: Optional[str] = None) -> None:
    """Strictly validate password entropy and institutional rules, raising on failure.

    Raises:
        PasswordEntropyError with plain-language, jargon-free message per D-12.
    """
    is_valid, _, reasons = assess_password_entropy(password, identifier=identifier)
    if not is_valid:
        primary_message = reasons[0] if reasons else "Password does not meet security criteria."
        raise PasswordEntropyError(message=primary_message, errors=reasons)


def check_password_integrity(
    password: Any, identifier: Optional[str] = None
) -> PasswordIntegrityResponse:
    """Non-raising evaluation returning the standard PasswordIntegrityResponse DTO."""
    is_valid, entropy_bits, reasons = assess_password_entropy(password, identifier=identifier)
    if is_valid:
        message = "Your password meets all institutional security criteria."
    else:
        message = reasons[0] if reasons else "Password does not meet security criteria."

    return PasswordIntegrityResponse(
        valid=is_valid,
        entropy_bits=entropy_bits,
        message=message,
    )


class PasswordEntropyValidator:
    """Class wrapper providing static methods for password entropy validation."""

    calculate_entropy = staticmethod(calculate_entropy_bits)

    @classmethod
    def validate_password(
        cls, password: str, identifier: Optional[str] = None
    ) -> Tuple[bool, str, float]:
        is_valid, entropy_bits, reasons = assess_password_entropy(password, identifier=identifier)
        if is_valid:
            return True, "Password meets OWASP ASVS 4.0 entropy requirements.", entropy_bits
        primary_message = reasons[0] if reasons else "Password does not meet security criteria."
        return False, primary_message, entropy_bits


# ===========================================================================
# 4. Argon2id Password Hashing Engine
# ===========================================================================

def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using Argon2id with OWASP ASVS 4.0 parameters.

    Memory: 64 MiB (m=65536)
    Time cost: 3 iterations
    Parallelism: 4 threads
    Hash length: 32 bytes
    Salt length: 16 bytes

    Returns:
        Standard encoded Argon2id hash string starting with $argon2id$v=19$m=65536,t=3,p=4$
    """
    if not isinstance(plain_password, str) or not plain_password:
        raise TypeError("plain_password must be a non-empty string")
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against an Argon2id hash string in constant time.

    Supports bidirectional argument order for robust interoperability across services.
    Safely returns False on corrupted hashes or non-string types without raising unhandled errors.
    """
    if not isinstance(plain_password, str) or not isinstance(hashed_password, str):
        return False

    try:
        if plain_password.startswith("$argon2") and not hashed_password.startswith("$argon2"):
            return _hasher.verify(plain_password, hashed_password)
        return _hasher.verify(hashed_password, plain_password)
    except (Argon2Error, InvalidHashError, VerificationError, VerifyMismatchError, ValueError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Determine whether an existing hash was generated with older or different parameters."""
    if not isinstance(hashed_password, str) or not hashed_password.startswith("$argon2"):
        return True
    try:
        return _hasher.check_needs_rehash(hashed_password)
    except Exception:
        return True
