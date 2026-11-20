"""Faculty In-Room Presence Manager for ClassSync.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Tracks real-time faculty presence per room across the campus:
- Supports manual Professor Check-In / Check-Out ("Professor Present" marker).
- Thread-safe state transitions using reentrant locks.
- Broadcast-ready status payloads for SSE and REST endpoints.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


@dataclass
class FacultyPresenceRecord:
    room_code: str
    faculty_name: str
    faculty_id: Optional[str] = None
    faculty_email: Optional[str] = None
    session_id: Optional[str] = None
    subject_code: Optional[str] = None
    section_code: Optional[str] = None
    checked_in_at: Optional[datetime] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "room_code": self.room_code,
            "faculty_name": self.faculty_name,
            "faculty_id": self.faculty_id,
            "faculty_email": self.faculty_email,
            "session_id": self.session_id,
            "subject_code": self.subject_code,
            "section_code": self.section_code,
            "checked_in_at": self.checked_in_at.isoformat() if self.checked_in_at else None,
            "notes": self.notes,
        }


class FacultyPresenceManager:
    """Thread-safe in-memory manager tracking active faculty presence per room."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._active_presences: Dict[str, FacultyPresenceRecord] = {}

    def check_in(
        self,
        room_code: str,
        faculty_name: str,
        faculty_id: Optional[str] = None,
        faculty_email: Optional[str] = None,
        session_id: Optional[str] = None,
        subject_code: Optional[str] = None,
        section_code: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> FacultyPresenceRecord:
        """Atomically checks a faculty member into a room."""
        with self._lock:
            record = FacultyPresenceRecord(
                room_code=room_code,
                faculty_name=faculty_name,
                faculty_id=faculty_id,
                faculty_email=faculty_email,
                session_id=session_id,
                subject_code=subject_code,
                section_code=section_code,
                checked_in_at=datetime.now(timezone.utc),
                notes=notes,
            )
            self._active_presences[room_code] = record
            return record

    def check_out(
        self,
        room_code: str,
        faculty_id: Optional[str] = None,
        faculty_email: Optional[str] = None,
    ) -> Optional[FacultyPresenceRecord]:
        """Atomically checks faculty out of a room."""
        with self._lock:
            existing = self._active_presences.get(room_code)
            if existing is None:
                return None
            # If an identifier is passed, verify match or allow admin override
            if faculty_id and existing.faculty_id and existing.faculty_id != faculty_id:
                pass
            if faculty_email and existing.faculty_email and existing.faculty_email.lower() != faculty_email.lower():
                pass
            return self._active_presences.pop(room_code, None)

    def get_presence(self, room_code: str) -> Optional[FacultyPresenceRecord]:
        """Retrieves faculty presence record for a room, or None."""
        with self._lock:
            return self._active_presences.get(room_code)

    def is_faculty_present(self, room_code: str) -> bool:
        """Checks if a faculty member is currently checked in to the room."""
        with self._lock:
            return room_code in self._active_presences

    def get_all_presences(self) -> Dict[str, FacultyPresenceRecord]:
        """Retrieves a shallow snapshot of all active faculty presences."""
        with self._lock:
            return dict(self._active_presences)

    def clear(self) -> None:
        """Clears all active faculty presences (test cleanup)."""
        with self._lock:
            self._active_presences.clear()
