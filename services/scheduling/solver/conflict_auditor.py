"""Independent Conflict & Collision Auditor for ClassSync.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Provides an authoritative, multi-pass validation engine that independently audits
timetable entries post-solve, detects any hard constraint collisions, validates
Sunday civic allocation and spatial quarantines, and computes a deterministic
cryptographic SHA-256 revision hash when total collisions == 0.
"""

from __future__ import annotations
import uuid
import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional, Set, Sequence
from pydantic import Field

from classync_contracts.enums import DayOfWeek, CohortMode
from classync_contracts.schemas import BaseContract, ConflictReport
from services.scheduling.solver.sunday_rules import (
    DAY_SUNDAY,
    FUNCTION_HALL_ROOM_CODE,
    BUFFER_START_SLOT,
    BUFFER_END_SLOT,
    POST_CIVIC_START_SLOT,
    POST_CIVIC_END_SLOT,
    is_rotc_subject,
    is_nstp_subject,
    is_pathfit_subject,
    is_civic_subject,
    is_outdoor_ground,
)

# ---------------------------------------------------------------------------
# Default Quarantined Facilities (Decision Log D-05)
# ---------------------------------------------------------------------------
DEFAULT_QUARANTINED_ROOMS: frozenset[str] = frozenset({
    "NB 204",
    "NB 304",
    "NB 308",
    "PROPERTY_OFFICE",
    "CAMPUS_CANTEEN",
    "CANTEEN",
})

EXCLUSIVE_ROOM_CODE: str = "PRRC 108"
EXCLUSIVE_PROGRAM_CODE: str = "BSED_SCIENCE"


# ---------------------------------------------------------------------------
# Auditor Domain Models
# ---------------------------------------------------------------------------

class CollisionCategory(str, Enum):
    """Categorization of scheduling integrity violations."""
    ROOM_DOUBLE_BOOKING = "ROOM_DOUBLE_BOOKING"
    FACULTY_COLLISION = "FACULTY_COLLISION"
    SECTION_COLLISION = "SECTION_COLLISION"
    SPATIAL_QUARANTINE_LEAK = "SPATIAL_QUARANTINE_LEAK"
    ROOM_EXCLUSIVITY_LEAK = "ROOM_EXCLUSIVITY_LEAK"
    OPERATIONAL_BOUNDARY_VIOLATION = "OPERATIONAL_BOUNDARY_VIOLATION"
    SUNDAY_RULE_VIOLATION = "SUNDAY_RULE_VIOLATION"
    COHORT_MODE_VIOLATION = "COHORT_MODE_VIOLATION"


class CollisionRecord(BaseContract):
    """Structured record of an identified constraint violation."""
    category: CollisionCategory
    severity: str = "HARD_CONSTRAINT"
    entry_id: Optional[str] = None
    offering_id: Optional[str] = None
    colliding_offering_id: Optional[str] = None
    room_code: Optional[str] = None
    day_of_week: Optional[int] = None
    start_slot: Optional[int] = None
    duration_slots: Optional[int] = None
    message: str


class AuditReport(BaseContract):
    """Comprehensive audit report returned by ConflictAuditor."""
    is_valid: bool
    total_violations: int = 0
    room_collisions: int = 0
    faculty_collisions: int = 0
    section_collisions: int = 0
    quarantine_violations: int = 0
    exclusivity_violations: int = 0
    boundary_violations: int = 0
    sunday_violations: int = 0
    cohort_mode_violations: int = 0
    revision_hash: Optional[str] = None
    details: List[str] = Field(default_factory=list)
    collision_records: List[CollisionRecord] = Field(default_factory=list)
    audited_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_entries_audited: int = 0

    @property
    def has_conflict(self) -> bool:
        """Parity property with contracts ConflictReport schema."""
        return not self.is_valid

    def to_conflict_report(self) -> ConflictReport:
        """Converts AuditReport to contracts-py ConflictReport."""
        return ConflictReport(
            has_conflict=self.has_conflict,
            room_collisions=self.room_collisions,
            faculty_collisions=self.faculty_collisions,
            section_collisions=self.section_collisions,
            quarantine_violations=self.quarantine_violations,
            details=list(self.details),
        )


# ---------------------------------------------------------------------------
# Independent Conflict Auditor Class
# ---------------------------------------------------------------------------

class ConflictAuditor:
    """Authoritative post-solve collision and integrity auditor for ClassSync.

    Performs 8 independent validation passes over timetable entries and generates
    a tamper-evident cryptographic SHA-256 revision hash upon 100% collision-free certification.
    """

    def __init__(
        self,
        offerings_map: Optional[Dict[uuid.UUID, Any]] = None,
        rooms_map: Optional[Dict[str, Any]] = None,
        quarantined_rooms: Optional[Set[str]] = None,
        rooms: Optional[List[Any]] = None,
        offerings: Optional[List[Any]] = None,
    ) -> None:
        """Initializes the ConflictAuditor.

        Args:
            offerings_map: Optional mapping from offering UUID to CourseOffering model/schema.
            rooms_map: Optional mapping from room_code to Room model/schema.
            quarantined_rooms: Set of quarantined room codes. Defaults to institutional set.
            rooms: Optional list of rooms (converted to rooms_map).
            offerings: Optional list of offerings (converted to offerings_map).
        """
        self.offerings_map: Dict[uuid.UUID, Any] = {}
        if offerings_map:
            self.offerings_map.update(offerings_map)
        if offerings:
            for o in offerings:
                oid = getattr(o, "id", None) or (o.get("id") if isinstance(o, dict) else None)
                if oid:
                    if isinstance(oid, str):
                        try:
                            oid = uuid.UUID(oid)
                        except ValueError:
                            pass
                    self.offerings_map[oid] = o

        self.rooms_map: Dict[str, Any] = {}
        if rooms_map:
            self.rooms_map.update(rooms_map)
        if rooms:
            for r in rooms:
                rcode = getattr(r, "room_code", None) or (r.get("room_code") if isinstance(r, dict) else None)
                if rcode:
                    self.rooms_map[str(rcode)] = r

        self.quarantined_rooms = set(quarantined_rooms) if quarantined_rooms is not None else set(DEFAULT_QUARANTINED_ROOMS)

        # Incorporate rooms marked is_schedulable=False from rooms_map
        for r_code, r_obj in self.rooms_map.items():
            if hasattr(r_obj, "is_schedulable") and not r_obj.is_schedulable:
                self.quarantined_rooms.add(r_code)
            elif isinstance(r_obj, dict) and not r_obj.get("is_schedulable", True):
                self.quarantined_rooms.add(r_code)

    def _resolve_offering(self, offering_id: Any) -> Optional[Any]:
        """Resolves offering object from offering_id."""
        if not offering_id:
            return None
        if isinstance(offering_id, str):
            try:
                offering_id = uuid.UUID(offering_id)
            except ValueError:
                pass
        return self.offerings_map.get(offering_id)

    def audit(
        self,
        entries: Sequence[Any],
        stamp_hash: bool = True,
    ) -> AuditReport:
        """Alias for audit_timetable to support multiple calling conventions."""
        return self.audit_timetable(entries, stamp_revision_hash=stamp_hash)

    def audit_timetable(
        self,
        entries: Sequence[Any],
        stamp_revision_hash: bool = True,
    ) -> AuditReport:
        """Audits a collection of TimetableEntry instances across all institutional rules.

        Args:
            entries: Sequence of TimetableEntry models, schemas, or dicts.
            stamp_revision_hash: If True, writes the SHA-256 hash into entry.revision_hash when valid.

        Returns:
            AuditReport with pass/fail status, violation counts, records, and revision hash.
        """
        records: List[CollisionRecord] = []
        details: List[str] = []

        room_collisions = 0
        faculty_collisions = 0
        section_collisions = 0
        quarantine_violations = 0
        exclusivity_violations = 0
        boundary_violations = 0
        sunday_violations = 0
        cohort_mode_violations = 0

        # Pass 1: Operational Boundary & Slot Contiguity Check
        for entry in entries:
            e_id = str(getattr(entry, "id", "") or (entry.get("id") if isinstance(entry, dict) else ""))
            s_slot = int(getattr(entry, "start_slot", 0) if not isinstance(entry, dict) else entry.get("start_slot", 0))
            d_slots = int(getattr(entry, "duration_slots", 0) if not isinstance(entry, dict) else entry.get("duration_slots", 0))
            raw_day = getattr(entry, "day_of_week", 0) if not isinstance(entry, dict) else entry.get("day_of_week", 0)
            day = int(raw_day.value if hasattr(raw_day, "value") else raw_day)

            if s_slot < 0 or s_slot > 23 or d_slots < 1 or (s_slot + d_slots) > 24:
                boundary_violations += 1
                msg = (
                    f"Operational boundary violated for entry {e_id}: start_slot={s_slot}, "
                    f"duration={d_slots}, end={s_slot + d_slots}. Must be within 0-23 and end <= 24."
                )
                details.append(msg)
                records.append(CollisionRecord(
                    category=CollisionCategory.OPERATIONAL_BOUNDARY_VIOLATION,
                    entry_id=e_id,
                    day_of_week=day,
                    start_slot=s_slot,
                    duration_slots=d_slots,
                    message=msg,
                ))

            if day < 0 or day > 6:
                boundary_violations += 1
                msg = f"Invalid day of week {day} for entry {e_id}. Must be between 0 (Mon) and 6 (Sun)."
                details.append(msg)
                records.append(CollisionRecord(
                    category=CollisionCategory.OPERATIONAL_BOUNDARY_VIOLATION,
                    entry_id=e_id,
                    day_of_week=day,
                    message=msg,
                ))

        # Pass 2: Unified Cohort Mode Enforcement
        for entry in entries:
            e_id = str(getattr(entry, "id", "") or (entry.get("id") if isinstance(entry, dict) else ""))
            raw_mode = getattr(entry, "cohort_mode", CohortMode.UNIFIED) if not isinstance(entry, dict) else entry.get("cohort_mode", CohortMode.UNIFIED)
            c_mode = raw_mode.value if hasattr(raw_mode, "value") else str(raw_mode)

            if c_mode != CohortMode.UNIFIED.value:
                cohort_mode_violations += 1
                msg = (
                    f"Illegal cohort mode '{c_mode}' on entry {e_id}. "
                    f"Institutional mandate strictly requires UNIFIED mode (zero sub-batch splitting)."
                )
                details.append(msg)
                records.append(CollisionRecord(
                    category=CollisionCategory.COHORT_MODE_VIOLATION,
                    entry_id=e_id,
                    message=msg,
                ))

        # Pass 3: Spatial Quarantine Leakage
        for entry in entries:
            e_id = str(getattr(entry, "id", "") or (entry.get("id") if isinstance(entry, dict) else ""))
            r_code = str(getattr(entry, "room_code", "") if not isinstance(entry, dict) else entry.get("room_code", "")).strip()

            if r_code in self.quarantined_rooms:
                quarantine_violations += 1
                msg = (
                    f"Quarantine leakage detected: Entry {e_id} is scheduled in quarantined "
                    f"space '{r_code}'. Administrative offices and faculty lounges must never be scheduled."
                )
                details.append(msg)
                records.append(CollisionRecord(
                    category=CollisionCategory.SPATIAL_QUARANTINE_LEAK,
                    entry_id=e_id,
                    room_code=r_code,
                    message=msg,
                ))

        # Pass 4: Room Exclusivity Leakage (PRRC 108 locked to BSED_SCIENCE)
        for entry in entries:
            e_id = str(getattr(entry, "id", "") or (entry.get("id") if isinstance(entry, dict) else ""))
            r_code = str(getattr(entry, "room_code", "") if not isinstance(entry, dict) else entry.get("room_code", "")).strip()
            off_id = getattr(entry, "offering_id", None) if not isinstance(entry, dict) else entry.get("offering_id")
            offering = self._resolve_offering(off_id)

            if r_code == EXCLUSIVE_ROOM_CODE:
                is_bsed_science = False
                if offering is not None:
                    sec_code = getattr(offering.section, "section_code", "") if hasattr(offering, "section") and offering.section else getattr(offering, "section_code", "")
                    subj_code = getattr(offering.subject, "subject_code", "") if hasattr(offering, "subject") and offering.subject else getattr(offering, "subject_code", "")
                    prog = getattr(offering, "program", "") or getattr(offering, "program_code", "")

                    if (
                        "BSED_SCI" in sec_code
                        or "BSED-SCI" in sec_code
                        or "BSED" in sec_code
                        or "BSED-SCI" in subj_code
                        or "BSED" in subj_code
                        or prog == EXCLUSIVE_PROGRAM_CODE
                    ):
                        is_bsed_science = True

                if not is_bsed_science:
                    exclusivity_violations += 1
                    msg = (
                        f"Room exclusivity violation: Entry {e_id} scheduled in '{EXCLUSIVE_ROOM_CODE}' "
                        f"does not belong to {EXCLUSIVE_PROGRAM_CODE} program."
                    )
                    details.append(msg)
                    records.append(CollisionRecord(
                        category=CollisionCategory.ROOM_EXCLUSIVITY_LEAK,
                        entry_id=e_id,
                        room_code=r_code,
                        offering_id=str(off_id) if off_id else None,
                        message=msg,
                    ))

        # Pass 5: Sunday Civic Space Allocation & Buffer Verification
        for entry in entries:
            e_id = str(getattr(entry, "id", "") or (entry.get("id") if isinstance(entry, dict) else ""))
            r_code = str(getattr(entry, "room_code", "") if not isinstance(entry, dict) else entry.get("room_code", "")).strip()
            raw_day = getattr(entry, "day_of_week", 0) if not isinstance(entry, dict) else entry.get("day_of_week", 0)
            day = int(raw_day.value if hasattr(raw_day, "value") else raw_day)
            s_slot = int(getattr(entry, "start_slot", 0) if not isinstance(entry, dict) else entry.get("start_slot", 0))
            d_slots = int(getattr(entry, "duration_slots", 0) if not isinstance(entry, dict) else entry.get("duration_slots", 0))
            e_end = s_slot + d_slots
            off_id = getattr(entry, "offering_id", None) if not isinstance(entry, dict) else entry.get("offering_id")
            offering = self._resolve_offering(off_id)

            subj_code = ""
            if offering is not None:
                if hasattr(offering, "subject") and offering.subject:
                    subj_code = getattr(offering.subject, "subject_code", "")
                elif hasattr(offering, "subject_code"):
                    subj_code = offering.subject_code or ""
                elif isinstance(offering, dict):
                    subj_code = offering.get("subject_code", "")

            # 5a. Sunday Academic Offering Prohibition
            if day == DAY_SUNDAY:
                if not is_civic_subject(subj_code) and not is_pathfit_subject(subj_code):
                    sunday_violations += 1
                    msg = (
                        f"Academic offering {subj_code} (Offering {off_id}) is scheduled on Sunday (d=6). "
                        f"Standard academic curriculum is strictly forbidden on Sundays."
                    )
                    details.append(msg)
                    records.append(CollisionRecord(
                        category=CollisionCategory.SUNDAY_RULE_VIOLATION,
                        entry_id=e_id,
                        offering_id=str(off_id) if off_id else None,
                        day_of_week=day,
                        start_slot=s_slot,
                        duration_slots=d_slots,
                        message=msg,
                    ))

                # 5b. Function Hall Sunday turnover buffer check [10, 12)
                if r_code == FUNCTION_HALL_ROOM_CODE:
                    # Check overlap with turnover buffer [10, 12)
                    if max(s_slot, BUFFER_START_SLOT) < min(e_end, BUFFER_END_SLOT):
                        sunday_violations += 1
                        msg = (
                            f"Sunday Function Hall turnover buffer encroachment: Entry {e_id} overlaps "
                            f"mandatory clearance window (12:00-13:00, slots 10-11)."
                        )
                        details.append(msg)
                        records.append(CollisionRecord(
                            category=CollisionCategory.SUNDAY_RULE_VIOLATION,
                            entry_id=e_id,
                            room_code=r_code,
                            day_of_week=day,
                            start_slot=s_slot,
                            duration_slots=d_slots,
                            message=msg,
                        ))

                    # Check overlap with post-17:00 closed window [20, 24)
                    if max(s_slot, POST_CIVIC_START_SLOT) < min(e_end, POST_CIVIC_END_SLOT):
                        sunday_violations += 1
                        msg = (
                            f"Sunday Function Hall post-civic closure violation: Entry {e_id} overlaps "
                            f"closed window (17:00-19:00, slots 20-23)."
                        )
                        details.append(msg)
                        records.append(CollisionRecord(
                            category=CollisionCategory.SUNDAY_RULE_VIOLATION,
                            entry_id=e_id,
                            room_code=r_code,
                            day_of_week=day,
                            start_slot=s_slot,
                            duration_slots=d_slots,
                            message=msg,
                        ))

            # 5c. PATHFIT Dedicated Outdoor Grounds Check
            if is_pathfit_subject(subj_code):
                if not is_outdoor_ground(r_code):
                    sunday_violations += 1
                    msg = (
                        f"PATHFIT course {subj_code} (Entry {e_id}) is scheduled in indoor room '{r_code}'. "
                        f"PATHFIT is restricted exclusively to Athletic Oval / Sports Complex / Open Grounds."
                    )
                    details.append(msg)
                    records.append(CollisionRecord(
                        category=CollisionCategory.SUNDAY_RULE_VIOLATION,
                        entry_id=e_id,
                        offering_id=str(off_id) if off_id else None,
                        room_code=r_code,
                        message=msg,
                    ))
            elif is_outdoor_ground(r_code):
                sunday_violations += 1
                msg = (
                    f"Non-PATHFIT offering {subj_code} (Entry {e_id}) is scheduled in outdoor sports grounds '{r_code}'."
                )
                details.append(msg)
                records.append(CollisionRecord(
                    category=CollisionCategory.SUNDAY_RULE_VIOLATION,
                    entry_id=e_id,
                    offering_id=str(off_id) if off_id else None,
                    room_code=r_code,
                    message=msg,
                ))

        # Pass 6: Room Double-Booking Verification
        room_day_groups: Dict[tuple, List[Any]] = {}
        for entry in entries:
            r_code = str(getattr(entry, "room_code", "") if not isinstance(entry, dict) else entry.get("room_code", "")).strip()
            raw_day = getattr(entry, "day_of_week", 0) if not isinstance(entry, dict) else entry.get("day_of_week", 0)
            day = int(raw_day.value if hasattr(raw_day, "value") else raw_day)
            room_day_groups.setdefault((r_code, day), []).append(entry)

        for (r_code, day), group in room_day_groups.items():
            sorted_group = sorted(
                group,
                key=lambda e: int(getattr(e, "start_slot", 0) if not isinstance(e, dict) else e.get("start_slot", 0))
            )
            for i in range(len(sorted_group) - 1):
                e1, e2 = sorted_group[i], sorted_group[i + 1]
                s1 = int(getattr(e1, "start_slot", 0) if not isinstance(e1, dict) else e1.get("start_slot", 0))
                d1 = int(getattr(e1, "duration_slots", 0) if not isinstance(e1, dict) else e1.get("duration_slots", 0))
                s2 = int(getattr(e2, "start_slot", 0) if not isinstance(e2, dict) else e2.get("start_slot", 0))
                d2 = int(getattr(e2, "duration_slots", 0) if not isinstance(e2, dict) else e2.get("duration_slots", 0))

                if max(s1, s2) < min(s1 + d1, s2 + d2):
                    room_collisions += 1
                    msg = (
                        f"Room double-booking collision in '{r_code}' on day {day}: "
                        f"Entry {getattr(e1, 'id', '')} (slots {s1}-{s1 + d1}) overlaps with "
                        f"Entry {getattr(e2, 'id', '')} (slots {s2}-{s2 + d2})."
                    )
                    details.append(msg)
                    records.append(CollisionRecord(
                        category=CollisionCategory.ROOM_DOUBLE_BOOKING,
                        entry_id=str(getattr(e1, "id", "")),
                        colliding_offering_id=str(getattr(e2, "offering_id", "")),
                        room_code=r_code,
                        day_of_week=day,
                        start_slot=s2,
                        duration_slots=min(s1 + d1, s2 + d2) - s2,
                        message=msg,
                    ))

        # Pass 7: Faculty Collision Verification
        faculty_day_groups: Dict[tuple, List[Any]] = {}
        for entry in entries:
            off_id = getattr(entry, "offering_id", None) if not isinstance(entry, dict) else entry.get("offering_id")
            offering = self._resolve_offering(off_id)
            fac_id = None
            if offering is not None:
                fac_id = getattr(offering, "faculty_id", None)
            elif hasattr(entry, "faculty_id"):
                fac_id = getattr(entry, "faculty_id")
            elif isinstance(entry, dict) and "faculty_id" in entry:
                fac_id = entry["faculty_id"]

            if fac_id:
                raw_day = getattr(entry, "day_of_week", 0) if not isinstance(entry, dict) else entry.get("day_of_week", 0)
                day = int(raw_day.value if hasattr(raw_day, "value") else raw_day)
                faculty_day_groups.setdefault((str(fac_id), day), []).append(entry)

        for (fac_id_str, day), group in faculty_day_groups.items():
            sorted_group = sorted(
                group,
                key=lambda e: int(getattr(e, "start_slot", 0) if not isinstance(e, dict) else e.get("start_slot", 0))
            )
            for i in range(len(sorted_group) - 1):
                e1, e2 = sorted_group[i], sorted_group[i + 1]
                s1 = int(getattr(e1, "start_slot", 0) if not isinstance(e1, dict) else e1.get("start_slot", 0))
                d1 = int(getattr(e1, "duration_slots", 0) if not isinstance(e1, dict) else e1.get("duration_slots", 0))
                s2 = int(getattr(e2, "start_slot", 0) if not isinstance(e2, dict) else e2.get("start_slot", 0))
                d2 = int(getattr(e2, "duration_slots", 0) if not isinstance(e2, dict) else e2.get("duration_slots", 0))

                if max(s1, s2) < min(s1 + d1, s2 + d2):
                    faculty_collisions += 1
                    msg = (
                        f"Faculty collision for faculty {fac_id_str} on day {day}: "
                        f"Entry {getattr(e1, 'id', '')} (slots {s1}-{s1 + d1}) overlaps with "
                        f"Entry {getattr(e2, 'id', '')} (slots {s2}-{s2 + d2})."
                    )
                    details.append(msg)
                    records.append(CollisionRecord(
                        category=CollisionCategory.FACULTY_COLLISION,
                        entry_id=str(getattr(e1, "id", "")),
                        colliding_offering_id=str(getattr(e2, "offering_id", "")),
                        day_of_week=day,
                        start_slot=s2,
                        duration_slots=min(s1 + d1, s2 + d2) - s2,
                        message=msg,
                    ))

        # Pass 8: Section Collision Verification
        section_day_groups: Dict[tuple, List[Any]] = {}
        for entry in entries:
            off_id = getattr(entry, "offering_id", None) if not isinstance(entry, dict) else entry.get("offering_id")
            offering = self._resolve_offering(off_id)
            sec_id = None
            if offering is not None:
                sec_id = getattr(offering, "section_id", None)
            elif hasattr(entry, "section_id"):
                sec_id = getattr(entry, "section_id")
            elif isinstance(entry, dict) and "section_id" in entry:
                sec_id = entry["section_id"]

            if sec_id:
                raw_day = getattr(entry, "day_of_week", 0) if not isinstance(entry, dict) else entry.get("day_of_week", 0)
                day = int(raw_day.value if hasattr(raw_day, "value") else raw_day)
                section_day_groups.setdefault((str(sec_id), day), []).append(entry)

        for (sec_id_str, day), group in section_day_groups.items():
            sorted_group = sorted(
                group,
                key=lambda e: int(getattr(e, "start_slot", 0) if not isinstance(e, dict) else e.get("start_slot", 0))
            )
            for i in range(len(sorted_group) - 1):
                e1, e2 = sorted_group[i], sorted_group[i + 1]
                s1 = int(getattr(e1, "start_slot", 0) if not isinstance(e1, dict) else e1.get("start_slot", 0))
                d1 = int(getattr(e1, "duration_slots", 0) if not isinstance(e1, dict) else e1.get("duration_slots", 0))
                s2 = int(getattr(e2, "start_slot", 0) if not isinstance(e2, dict) else e2.get("start_slot", 0))
                d2 = int(getattr(e2, "duration_slots", 0) if not isinstance(e2, dict) else e2.get("duration_slots", 0))

                if max(s1, s2) < min(s1 + d1, s2 + d2):
                    section_collisions += 1
                    msg = (
                        f"Section collision for section cohort {sec_id_str} on day {day}: "
                        f"Entry {getattr(e1, 'id', '')} (slots {s1}-{s1 + d1}) overlaps with "
                        f"Entry {getattr(e2, 'id', '')} (slots {s2}-{s2 + d2})."
                    )
                    details.append(msg)
                    records.append(CollisionRecord(
                        category=CollisionCategory.SECTION_COLLISION,
                        entry_id=str(getattr(e1, "id", "")),
                        colliding_offering_id=str(getattr(e2, "offering_id", "")),
                        day_of_week=day,
                        start_slot=s2,
                        duration_slots=min(s1 + d1, s2 + d2) - s2,
                        message=msg,
                    ))

        # Aggregate total violations
        total_violations = (
            room_collisions
            + faculty_collisions
            + section_collisions
            + quarantine_violations
            + exclusivity_violations
            + boundary_violations
            + sunday_violations
            + cohort_mode_violations
        )
        is_valid = (total_violations == 0)

        # Cryptographic Revision Hash
        revision_hash = None
        if is_valid:
            entry_tuples = []
            for e in entries:
                off_val = str(getattr(e, "offering_id", "") if not isinstance(e, dict) else e.get("offering_id", ""))
                r_val = str(getattr(e, "room_code", "") if not isinstance(e, dict) else e.get("room_code", "")).strip()
                raw_d = getattr(e, "day_of_week", 0) if not isinstance(e, dict) else e.get("day_of_week", 0)
                d_val = int(raw_d.value if hasattr(raw_d, "value") else raw_d)
                s_val = int(getattr(e, "start_slot", 0) if not isinstance(e, dict) else e.get("start_slot", 0))
                dur_val = int(getattr(e, "duration_slots", 0) if not isinstance(e, dict) else e.get("duration_slots", 0))
                entry_tuples.append((off_val, r_val, d_val, s_val, dur_val))

            # Canonical sort order: day_of_week, start_slot, room_code, offering_id
            sorted_tuples = sorted(entry_tuples, key=lambda t: (t[2], t[3], t[1], t[0]))
            canonical_string = "\n".join(f"{t[0]}|{t[1]}|{t[2]}|{t[3]}|{t[4]}" for t in sorted_tuples)
            revision_hash = hashlib.sha256(canonical_string.encode("utf-8")).hexdigest()

            # Stamp revision_hash into objects if requested
            if stamp_revision_hash:
                for entry in entries:
                    if hasattr(entry, "revision_hash"):
                        try:
                            setattr(entry, "revision_hash", revision_hash)
                        except Exception:
                            pass
                    elif isinstance(entry, dict):
                        entry["revision_hash"] = revision_hash

        return AuditReport(
            is_valid=is_valid,
            total_violations=total_violations,
            room_collisions=room_collisions,
            faculty_collisions=faculty_collisions,
            section_collisions=section_collisions,
            quarantine_violations=quarantine_violations,
            exclusivity_violations=exclusivity_violations,
            boundary_violations=boundary_violations,
            sunday_violations=sunday_violations,
            cohort_mode_violations=cohort_mode_violations,
            revision_hash=revision_hash,
            details=details,
            collision_records=records,
            total_entries_audited=len(entries),
        )


def audit_timetable_entries(
    entries: Sequence[Any],
    offerings_map: Optional[Dict[uuid.UUID, Any]] = None,
    rooms_map: Optional[Dict[str, Any]] = None,
    stamp_hash: bool = True,
) -> AuditReport:
    """Convenience functional wrapper around ConflictAuditor."""
    auditor = ConflictAuditor(offerings_map=offerings_map, rooms_map=rooms_map)
    return auditor.audit_timetable(entries, stamp_revision_hash=stamp_hash)
