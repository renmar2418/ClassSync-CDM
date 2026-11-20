"""Zero-Regex Student ID Ingress Validator.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Enforces Decision Log D-02 and D-12:
- Deterministic bounds checking without regular expression engines.
- O(1) constant-time execution.
- Zero 're' module imports (strictly forbidden).
- Rejection of Unicode digit homoglyphs (Arabic-Indic, Fullwidth, Superscript, Devanagari, Circled).
- Empathetic plain-language error reporting.
"""

from typing import Any

# Strictly enforced plain-language error message per D-12
STUDENT_ID_ERROR_MESSAGE = "Student IDs must look like 24-00123 (numbers only, no emails)."


class StudentIDValidationError(ValueError):
    """Raised when a Student ID violates CdM/PNM institutional format."""

    def __init__(self, message: str = STUDENT_ID_ERROR_MESSAGE):
        super().__init__(message)
        self.message = message


def validate_student_id(raw_id: Any) -> str:
    """Deterministically validates a CdM/PNM Student ID with zero regex engines.

    Validation Rules:
    1. Input must be a string.
    2. Whitespace is stripped; length must be exactly 8 characters.
    3. Characters 0..2 must strictly match '24-'.
    4. Characters 3..7 must each be ASCII decimal digits ('0' <= c <= '9', ord 48..57).
    5. Rejects email symbols ('@'), letters, spaces, hyphens, and Unicode numeric homoglyphs.

    Parameters
    ----------
    raw_id : Any
        Input student ID to validate.

    Returns
    -------
    str
        Cleaned, uppercase 8-character student ID string (e.g., '24-00123').

    Raises
    ------
    StudentIDValidationError
        If format requirements are not strictly satisfied.
    """
    if not isinstance(raw_id, str):
        raise StudentIDValidationError()

    cleaned = raw_id.strip()

    # Rule 1: Exact length must be 8 characters
    if len(cleaned) != 8:
        raise StudentIDValidationError()

    # Rule 2: Prefix must strictly equal '24-'
    if cleaned[0] != "2" or cleaned[1] != "4" or cleaned[2] != "-":
        raise StudentIDValidationError()

    # Rule 3: Remaining 5 characters must strictly be ASCII digits '0'-'9' (ord 48..57)
    for idx in range(3, 8):
        char_code = ord(cleaned[idx])
        if char_code < 48 or char_code > 57:
            raise StudentIDValidationError()

    return cleaned


def is_valid_student_id(raw_id: Any) -> bool:
    """Non-raising predicate for fast conditional student ID checks."""
    try:
        validate_student_id(raw_id)
        return True
    except StudentIDValidationError:
        return False
