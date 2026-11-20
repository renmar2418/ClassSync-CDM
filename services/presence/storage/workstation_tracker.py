"""COMLAB 45-Workstation Occupancy Tracking Engine.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Enforces Decision Logs D-04 and D-12:
- Models 45 workstations per standard CdM/PNM COMLAB (PRRC 301, PRRC 302, PRRC 303, PRRC 304).
- Tracks operational state (is_operational) and occupancy state (is_occupied, active_student_id).
- Atomic collision detection with nearest vacant workstation recommendation.
- Empathetic plain-language collision copy.
- Thread-safe state transitions using reentrant locks (threading.RLock).
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from classync_contracts.enums import WorkstationStatus


class WorkstationError(Exception):
    """Base exception for workstation tracking operations."""

    pass


class WorkstationOutOfBoundsError(WorkstationError):
    """Raised when workstation number is outside valid range (1..45)."""

    pass


class WorkstationConflictError(WorkstationError):
    """Raised on seat collision with plain-language recommendation."""

    def __init__(
        self,
        message: str,
        claimed_station: int,
        suggested_station: Optional[int] = None,
    ):
        super().__init__(message)
        self.message = message
        self.claimed_station = claimed_station
        self.suggested_station = suggested_station


class WorkstationMaintenanceError(WorkstationError):
    """Raised when claiming a workstation currently marked non-operational."""

    def __init__(
        self,
        message: str,
        claimed_station: int,
        suggested_station: Optional[int] = None,
    ):
        super().__init__(message)
        self.message = message
        self.claimed_station = claimed_station
        self.suggested_station = suggested_station


@dataclass
class WorkstationSlot:
    """State of an individual laboratory workstation."""

    room_code: str
    workstation_number: int
    is_operational: bool = True
    is_occupied: bool = False
    active_student_id: Optional[str] = None
    check_in_time: Optional[datetime] = None
    session_id: Optional[uuid.UUID] = None

    @property
    def status(self) -> WorkstationStatus:
        if not self.is_operational:
            return WorkstationStatus.MAINTENANCE
        if self.is_occupied:
            return WorkstationStatus.OCCUPIED
        return WorkstationStatus.VACANT

    def to_dict(self) -> dict:
        return {
            "room_code": self.room_code,
            "workstation_number": self.workstation_number,
            "is_operational": self.is_operational,
            "is_occupied": self.is_occupied,
            "status": self.status.value,
            "active_student_id": self.active_student_id,
            "check_in_time": self.check_in_time.isoformat() if self.check_in_time else None,
            "session_id": str(self.session_id) if self.session_id else None,
        }


@dataclass
class ClaimResult:
    """Result of an atomic workstation claim."""

    success: bool
    workstation: WorkstationSlot
    message: str
    relocated_from_station: Optional[int] = None


@dataclass
class ReleaseResult:
    """Result of an atomic workstation release."""

    success: bool
    workstation_number: int
    was_occupied: bool
    student_id: Optional[str] = None


@dataclass
class RoomOccupancySummary:
    """Aggregated occupancy telemetry for a laboratory room."""

    room_code: str
    total_stations: int
    operational_count: int
    occupied_count: int
    vacant_count: int
    occupancy_rate: float
    active_session_id: Optional[uuid.UUID]
    stations: List[WorkstationSlot]

    @property
    def vacant_rate(self) -> float:
        return (self.vacant_count / self.total_stations) if self.total_stations > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "room_code": self.room_code,
            "total_stations": self.total_stations,
            "operational_count": self.operational_count,
            "occupied_count": self.occupied_count,
            "vacant_count": self.vacant_count,
            "occupancy_rate": round(self.occupancy_rate, 4),
            "vacant_rate": round(self.vacant_rate, 4),
            "active_session_id": str(self.active_session_id) if self.active_session_id else None,
            "stations": [s.to_dict() for s in self.stations],
        }


class RoomWorkstationTracker:
    """Tracks the 45 workstations of a single COMLAB room."""

    def __init__(
        self,
        room_code: str,
        total_workstations: int = 45,
        non_operational_stations: Optional[Set[int]] = None,
    ):
        self.room_code = room_code
        self.total_workstations = total_workstations
        self._lock = threading.RLock()
        self.active_session_id: Optional[uuid.UUID] = None

        non_op = non_operational_stations or set()
        self._stations: Dict[int, WorkstationSlot] = {
            num: WorkstationSlot(
                room_code=room_code,
                workstation_number=num,
                is_operational=(num not in non_op),
            )
            for num in range(1, total_workstations + 1)
        }

    def find_nearest_vacant(self, target_station: int) -> Optional[int]:
        """Finds the nearest vacant operational workstation to target_station.

        Radiates outward with priority given to k+d over k-d to match
        D-12 copy ('PC-14 claimed -> PC-15 is open').
        """
        with self._lock:
            for d in range(1, self.total_workstations):
                right = target_station + d
                if right <= self.total_workstations:
                    st = self._stations[right]
                    if st.is_operational and not st.is_occupied:
                        return right

                left = target_station - d
                if left >= 1:
                    st = self._stations[left]
                    if st.is_operational and not st.is_occupied:
                        return left

            return None

    def find_student_workstation(self, student_id: str) -> Optional[int]:
        """Locates the workstation currently occupied by a student in this room."""
        with self._lock:
            for num, st in self._stations.items():
                if st.is_occupied and st.active_student_id == student_id:
                    return num
            return None

    def claim_workstation(
        self,
        workstation_number: int,
        student_id: str,
        session_id: Optional[uuid.UUID] = None,
    ) -> ClaimResult:
        """Atomically claims a workstation for a verified student."""
        with self._lock:
            if workstation_number < 1 or workstation_number > self.total_workstations:
                raise WorkstationOutOfBoundsError(
                    f"Workstation PC-{workstation_number} does not exist in {self.room_code}. "
                    f"Valid stations are 1 to {self.total_workstations}."
                )

            slot = self._stations[workstation_number]

            # Case 1: Workstation is marked under maintenance
            if not slot.is_operational:
                suggested = self.find_nearest_vacant(workstation_number)
                if suggested:
                    msg = (
                        f"Seat PC-{workstation_number} is currently undergoing maintenance. "
                        f"PC-{suggested} is open right next to it."
                    )
                else:
                    msg = (
                        f"Seat PC-{workstation_number} is currently undergoing maintenance. "
                        f"All other stations are occupied."
                    )
                raise WorkstationMaintenanceError(msg, workstation_number, suggested)

            # Case 2: Workstation is occupied by another student (Collision)
            if slot.is_occupied and slot.active_student_id != student_id:
                suggested = self.find_nearest_vacant(workstation_number)
                if suggested:
                    msg = (
                        f"Seat PC-{workstation_number} was just claimed by a classmate! "
                        f"PC-{suggested} is open right next to it."
                    )
                else:
                    msg = (
                        f"All {self.total_workstations} workstations in {self.room_code} "
                        f"are currently occupied. Please consult your instructor."
                    )
                raise WorkstationConflictError(msg, workstation_number, suggested)

            # Case 3: Student already occupies this exact workstation (Idempotent scan)
            if slot.is_occupied and slot.active_student_id == student_id:
                return ClaimResult(
                    success=True,
                    workstation=slot,
                    message=f"You are already checked in at PC-{workstation_number}.",
                )

            # Case 4: Student is relocating from another workstation in this room
            relocated_from = self.find_student_workstation(student_id)
            if relocated_from and relocated_from != workstation_number:
                prev_slot = self._stations[relocated_from]
                prev_slot.is_occupied = False
                prev_slot.active_student_id = None
                prev_slot.check_in_time = None
                prev_slot.session_id = None

            # Claim slot
            now = datetime.now(timezone.utc)
            slot.is_occupied = True
            slot.active_student_id = student_id
            slot.check_in_time = now
            slot.session_id = session_id or self.active_session_id

            msg = f"Seat PC-{workstation_number} successfully claimed."
            if relocated_from:
                msg += f" (Relocated from PC-{relocated_from})"

            return ClaimResult(
                success=True,
                workstation=slot,
                message=msg,
                relocated_from_station=relocated_from,
            )

    def release_workstation(
        self,
        workstation_number: int,
        student_id: Optional[str] = None,
    ) -> ReleaseResult:
        """Atomically releases a workstation."""
        with self._lock:
            if workstation_number < 1 or workstation_number > self.total_workstations:
                raise WorkstationOutOfBoundsError(
                    f"Workstation PC-{workstation_number} is out of bounds (1..{self.total_workstations})."
                )

            slot = self._stations[workstation_number]
            if not slot.is_occupied:
                return ReleaseResult(success=True, workstation_number=workstation_number, was_occupied=False)

            if student_id and slot.active_student_id != student_id:
                raise WorkstationConflictError(
                    f"Cannot release PC-{workstation_number}: occupied by another student.",
                    claimed_station=workstation_number,
                )

            freed_student = slot.active_student_id
            slot.is_occupied = False
            slot.active_student_id = None
            slot.check_in_time = None
            slot.session_id = None

            return ReleaseResult(
                success=True,
                workstation_number=workstation_number,
                was_occupied=True,
                student_id=freed_student,
            )

    def set_maintenance_status(self, workstation_number: int, is_operational: bool) -> WorkstationSlot:
        """Flags a workstation as operational or under maintenance."""
        with self._lock:
            if workstation_number < 1 or workstation_number > self.total_workstations:
                raise WorkstationOutOfBoundsError(
                    f"Workstation PC-{workstation_number} is out of bounds."
                )
            slot = self._stations[workstation_number]
            slot.is_operational = is_operational
            if not is_operational and slot.is_occupied:
                slot.is_occupied = False
                slot.active_student_id = None
                slot.check_in_time = None
                slot.session_id = None
            return slot

    def get_summary(self) -> RoomOccupancySummary:
        """Returns snapshot summary of the room's workstation occupancy."""
        with self._lock:
            stations_list = [self._stations[i] for i in range(1, self.total_workstations + 1)]
            operational = sum(1 for s in stations_list if s.is_operational)
            occupied = sum(1 for s in stations_list if s.is_occupied)
            vacant = sum(1 for s in stations_list if s.is_operational and not s.is_occupied)
            rate = (occupied / operational) if operational > 0 else 0.0

            return RoomOccupancySummary(
                room_code=self.room_code,
                total_stations=self.total_workstations,
                operational_count=operational,
                occupied_count=occupied,
                vacant_count=vacant,
                occupancy_rate=rate,
                active_session_id=self.active_session_id,
                stations=stations_list,
            )

    def reset_room(self, new_session_id: Optional[uuid.UUID] = None) -> None:
        """Resets all workstations to vacant state for a new laboratory session."""
        with self._lock:
            self.active_session_id = new_session_id
            for slot in self._stations.values():
                slot.is_occupied = False
                slot.active_student_id = None
                slot.check_in_time = None
                slot.session_id = None


class COMLABWorkstationManager:
    """Registry managing multi-room COMLAB workstation trackers."""

    STANDARD_COMLABS = ("PRRC 301", "PRRC 302", "PRRC 303", "PRRC 304")

    def __init__(self, auto_init_standard: bool = True):
        self._rooms: Dict[str, RoomWorkstationTracker] = {}
        self._lock = threading.RLock()
        if auto_init_standard:
            for room in self.STANDARD_COMLABS:
                self._rooms[room] = RoomWorkstationTracker(room_code=room, total_workstations=45)

    def get_room_tracker(self, room_code: str, auto_create: bool = True) -> RoomWorkstationTracker:
        """Retrieves or dynamically creates a tracker for room_code."""
        with self._lock:
            if room_code not in self._rooms:
                if auto_create:
                    self._rooms[room_code] = RoomWorkstationTracker(room_code=room_code, total_workstations=45)
                else:
                    raise KeyError(f"Room {room_code} not initialized.")
            return self._rooms[room_code]

    def reset_all_rooms(self) -> None:
        """Resets all rooms (useful in tests and daily rollover)."""
        with self._lock:
            for tracker in self._rooms.values():
                tracker.reset_room()
