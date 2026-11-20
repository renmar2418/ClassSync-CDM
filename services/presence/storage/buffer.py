"""In-Memory Circular Ring Buffer for Presence Telemetry.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Enforces Decision Logs D-04 and D-12:
- Thread-safe ring buffer strictly capped at maxlen=50.
- O(1) instantaneous append with automatic FIFO eviction of the 51st entry.
- Sub-microsecond list serialization for teacher dashboard and SSE push streams.
- Preserves check-in records: id, student_id, room_code, workstation_number, check_in_time, totp_verified.
"""

from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class PresenceLogEntry:
    """Immutable presence log record stored in the circular ring buffer."""

    id: uuid.UUID
    student_id: str
    room_code: str
    workstation_number: int
    check_in_time: datetime
    totp_verified: bool = True
    session_id: Optional[uuid.UUID] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize snapshot to dictionary."""
        return {
            "id": str(self.id),
            "student_id": self.student_id,
            "room_code": self.room_code,
            "workstation_number": self.workstation_number,
            "check_in_time": self.check_in_time.isoformat(),
            "totp_verified": self.totp_verified,
            "session_id": str(self.session_id) if self.session_id else None,
        }


class PresenceCircularBuffer:
    """Thread-safe bounded ring buffer holding strictly the last 50 events."""

    DEFAULT_CAPACITY = 50

    def __init__(self, capacity: int = DEFAULT_CAPACITY):
        self._capacity = capacity
        self._buffer: deque[PresenceLogEntry] = deque(maxlen=capacity)
        self._lock = threading.RLock()

    @property
    def capacity(self) -> int:
        return self._capacity

    def __len__(self) -> int:
        with self._lock:
            return len(self._buffer)

    @property
    def is_full(self) -> bool:
        with self._lock:
            return len(self._buffer) == self._capacity

    def append(self, entry: PresenceLogEntry) -> None:
        """Appends a new check-in entry in O(1). Oldest entry automatically evicted if full."""
        with self._lock:
            self._buffer.append(entry)

    def get_recent(self, limit: Optional[int] = None, reverse: bool = True) -> List[PresenceLogEntry]:
        """Returns recent log entries.

        Parameters
        ----------
        limit : Optional[int]
            Max number of records to return. If None or > len, returns all.
        reverse : bool
            If True (default), returns newest records first (index 0 = most recent).
            If False, returns chronological order (index 0 = oldest).
        """
        with self._lock:
            items = list(self._buffer)
            if reverse:
                items.reverse()
            if limit is not None and limit >= 0:
                return items[:limit]
            return items

    def get_recent_logs(self, limit: Optional[int] = None) -> List[PresenceLogEntry]:
        """Returns recent log entries in reverse chronological order (newest first)."""
        return self.get_recent(limit=limit, reverse=True)

    def get_by_student(self, student_id: str) -> Optional[PresenceLogEntry]:
        """Finds the most recent entry for student_id."""
        with self._lock:
            for entry in reversed(self._buffer):
                if entry.student_id == student_id:
                    return entry
            return None

    def get_by_workstation(self, workstation_number: int) -> Optional[PresenceLogEntry]:
        """Finds the most recent entry for a given workstation number."""
        with self._lock:
            for entry in reversed(self._buffer):
                if entry.workstation_number == workstation_number:
                    return entry
            return None

    def clear(self) -> None:
        """Flushes all entries from the buffer."""
        with self._lock:
            self._buffer.clear()

    def snapshot(self) -> List[Dict[str, Any]]:
        """Exports snapshot serialization of all buffer entries in reverse chronological order."""
        return [entry.to_dict() for entry in self.get_recent(reverse=True)]


class PresenceBufferManager:
    """Manages circular buffers separated per COMLAB room plus global event stream."""

    def __init__(self, room_capacity: int = 50, global_capacity: int = 100):
        self._room_capacity = room_capacity
        self._global_buffer = PresenceCircularBuffer(capacity=global_capacity)
        self._room_buffers: Dict[str, PresenceCircularBuffer] = {}
        self._lock = threading.RLock()

    def get_room_buffer(self, room_code: str) -> PresenceCircularBuffer:
        """Returns or creates the dedicated 50-item circular buffer for a room."""
        with self._lock:
            if room_code not in self._room_buffers:
                self._room_buffers[room_code] = PresenceCircularBuffer(capacity=self._room_capacity)
            return self._room_buffers[room_code]

    def record_check_in(self, entry: PresenceLogEntry) -> None:
        """Records a check-in in both the room-specific buffer and global buffer."""
        room_buf = self.get_room_buffer(entry.room_code)
        room_buf.append(entry)
        with self._lock:
            self._global_buffer.append(entry)

    def get_recent_room_logs(
        self,
        room_code: str,
        limit: int = 50,
        reverse: bool = True,
    ) -> List[PresenceLogEntry]:
        """Returns newest logs for a specific room."""
        buf = self.get_room_buffer(room_code)
        return buf.get_recent(limit=limit, reverse=reverse)

    def get_global_recent_logs(self, limit: int = 50, reverse: bool = True) -> List[PresenceLogEntry]:
        """Returns newest logs across all laboratory rooms."""
        with self._lock:
            return self._global_buffer.get_recent(limit=limit, reverse=reverse)

    def clear_all(self) -> None:
        """Clears all buffers."""
        with self._lock:
            self._global_buffer.clear()
            for buf in self._room_buffers.values():
                buf.clear()
