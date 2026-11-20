"""Presence Ingress Package for ClassSync.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System
"""

from services.presence.ingress.validator import (
    STUDENT_ID_ERROR_MESSAGE,
    StudentIDValidationError,
    is_valid_student_id,
    validate_student_id,
)

__all__ = [
    "STUDENT_ID_ERROR_MESSAGE",
    "StudentIDValidationError",
    "is_valid_student_id",
    "validate_student_id",
]
