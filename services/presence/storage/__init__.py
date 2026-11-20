"""Presence Storage Package for ClassSync.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System
"""

from services.presence.storage.buffer import (
    PresenceBufferManager,
    PresenceCircularBuffer,
    PresenceLogEntry,
)
from services.presence.storage.workstation_tracker import (
    ClaimResult,
    COMLABWorkstationManager,
    ReleaseResult,
    RoomOccupancySummary,
    RoomWorkstationTracker,
    WorkstationConflictError,
    WorkstationError,
    WorkstationMaintenanceError,
    WorkstationOutOfBoundsError,
    WorkstationSlot,
)

__all__ = [
    "PresenceCircularBuffer",
    "PresenceBufferManager",
    "PresenceLogEntry",
    "RoomWorkstationTracker",
    "COMLABWorkstationManager",
    "WorkstationSlot",
    "ClaimResult",
    "ReleaseResult",
    "RoomOccupancySummary",
    "WorkstationError",
    "WorkstationOutOfBoundsError",
    "WorkstationConflictError",
    "WorkstationMaintenanceError",
]
