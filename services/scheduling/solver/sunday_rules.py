"""Sunday Civic Space Allocation Rules for ClassSync.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Enforces Decision Log D-06:
- Sunday Function Hall partitioned into ROTC (07:00-12:00, slots 0-9) and NSTP (13:00-17:00, slots 12-19).
- Compulsory turnover buffer (12:00-13:00, slots 10-11) strictly empty and locked against any scheduling.
- Post-17:00 complex closure (17:00-19:00, slots 20-23) locked.
- PATHFIT courses restricted exclusively to Athletic Oval / Montalban Sports Complex / Open Grounds.
- Standard academic curriculum offerings strictly forbidden on Sunday (d=6).
"""

from __future__ import annotations
import uuid
from typing import Dict, List, Any, Optional, Set, FrozenSet
from ortools.sat.python import cp_model

from classync_contracts.enums import DayOfWeek

# ---------------------------------------------------------------------------
# Canonical Constants
# ---------------------------------------------------------------------------
DAY_SUNDAY: int = DayOfWeek.SUNDAY.value  # 6
ACADEMIC_DAYS: List[int] = [
    DayOfWeek.MONDAY.value,
    DayOfWeek.TUESDAY.value,
    DayOfWeek.WEDNESDAY.value,
    DayOfWeek.THURSDAY.value,
    DayOfWeek.FRIDAY.value,
    DayOfWeek.SATURDAY.value,
]  # [0, 1, 2, 3, 4, 5]

FUNCTION_HALL_ROOM_CODE: str = "FUNCTION_HALL"

# Shift slot ranges (30-min intervals, 0 = 07:00)
ROTC_START_SLOT: int = 0          # 07:00
ROTC_DURATION_SLOTS: int = 10     # 5.0 hours (07:00 - 12:00, slots 0-9)
ROTC_END_SLOT: int = 10           # 12:00

BUFFER_START_SLOT: int = 10       # 12:00
BUFFER_DURATION_SLOTS: int = 2     # 1.0 hour (12:00 - 13:00, slots 10-11)
BUFFER_END_SLOT: int = 12          # 13:00

NSTP_START_SLOT: int = 12         # 13:00
NSTP_DURATION_SLOTS: int = 8       # 4.0 hours (13:00 - 17:00, slots 12-19)
NSTP_END_SLOT: int = 20           # 17:00

POST_CIVIC_START_SLOT: int = 20   # 17:00
POST_CIVIC_DURATION_SLOTS: int = 4  # 2.0 hours (17:00 - 19:00, slots 20-23)
POST_CIVIC_END_SLOT: int = 24      # 19:00

# Canonical outdoor sports grounds
OUTDOOR_GROUNDS_ROOM_CODES: FrozenSet[str] = frozenset({
    "ATHLETIC_OVAL",
    "MONTALBAN_SPORTS_COMPLEX",
    "OPEN_GROUNDS",
    "Athletic Oval",
    "Montalban Sports Complex",
    "Open Grounds",
})

# Subject prefix categorizations
ROTC_PREFIXES: tuple = ("ROTC",)
NSTP_PREFIXES: tuple = ("NSTP", "CWTS", "LTS")
PATHFIT_PREFIXES: tuple = ("PATHFIT", "PE")


# ---------------------------------------------------------------------------
# Classification Helpers
# ---------------------------------------------------------------------------

def is_rotc_subject(subject_code: str) -> bool:
    """Checks whether the subject code corresponds to ROTC civic training."""
    if not subject_code:
        return False
    clean = subject_code.strip().upper()
    return any(clean.startswith(prefix) for prefix in ROTC_PREFIXES)


def is_nstp_subject(subject_code: str) -> bool:
    """Checks whether the subject code corresponds to NSTP (CWTS/LTS) civic training."""
    if not subject_code:
        return False
    clean = subject_code.strip().upper()
    return any(clean.startswith(prefix) for prefix in NSTP_PREFIXES)


def is_pathfit_subject(subject_code: str) -> bool:
    """Checks whether the subject code corresponds to physical education / PATHFIT."""
    if not subject_code:
        return False
    clean = subject_code.strip().upper()
    return any(clean.startswith(prefix) for prefix in PATHFIT_PREFIXES)


def is_civic_subject(subject_code: str) -> bool:
    """Checks whether the subject code is Sunday civic training (ROTC or NSTP)."""
    return is_rotc_subject(subject_code) or is_nstp_subject(subject_code)


def is_academic_subject(subject_code: str) -> bool:
    """Returns True if the subject is standard academic curriculum (not civic training)."""
    return not is_civic_subject(subject_code)


def is_outdoor_ground(room_code: str) -> bool:
    """Checks whether a room identifier corresponds to outdoor athletic grounds."""
    if not room_code:
        return False
    clean = room_code.strip()
    return clean in OUTDOOR_GROUNDS_ROOM_CODES or clean.upper() in OUTDOOR_GROUNDS_ROOM_CODES


def get_sunday_civic_reservations() -> List[Dict[str, Any]]:
    """Generates the authoritative static reservation schedule for Function Hall on Sunday."""
    return [
        {
            "name": "SUNDAY_ROTC_DRILL",
            "room_code": FUNCTION_HALL_ROOM_CODE,
            "day_of_week": DAY_SUNDAY,
            "start_slot": ROTC_START_SLOT,
            "duration_slots": ROTC_DURATION_SLOTS,
            "end_slot": ROTC_END_SLOT,
            "activity": "ROTC",
            "is_locked": True,
        },
        {
            "name": "SUNDAY_TURNOVER_BUFFER",
            "room_code": FUNCTION_HALL_ROOM_CODE,
            "day_of_week": DAY_SUNDAY,
            "start_slot": BUFFER_START_SLOT,
            "duration_slots": BUFFER_DURATION_SLOTS,
            "end_slot": BUFFER_END_SLOT,
            "activity": "TURNOVER_BUFFER",
            "is_locked": True,
        },
        {
            "name": "SUNDAY_NSTP_TRAINING",
            "room_code": FUNCTION_HALL_ROOM_CODE,
            "day_of_week": DAY_SUNDAY,
            "start_slot": NSTP_START_SLOT,
            "duration_slots": NSTP_DURATION_SLOTS,
            "end_slot": NSTP_END_SLOT,
            "activity": "NSTP",
            "is_locked": True,
        },
        {
            "name": "SUNDAY_POST_CIVIC_LOCKOUT",
            "room_code": FUNCTION_HALL_ROOM_CODE,
            "day_of_week": DAY_SUNDAY,
            "start_slot": POST_CIVIC_START_SLOT,
            "duration_slots": POST_CIVIC_DURATION_SLOTS,
            "end_slot": POST_CIVIC_END_SLOT,
            "activity": "FACILITY_CLOSED",
            "is_locked": True,
        },
    ]


# ---------------------------------------------------------------------------
# CP-SAT Constraint Binder
# ---------------------------------------------------------------------------

def apply_sunday_constraints(
    model: cp_model.CpModel,
    offerings: List[Any],
    d_vars: Dict[uuid.UUID, cp_model.IntVar],
    start_vars: Dict[uuid.UUID, cp_model.IntVar],
    x_vars: Dict[tuple, cp_model.BoolVar],
    room_opt_intervals: Dict[str, List[cp_model.IntervalVar]],
    candidate_rooms: Dict[uuid.UUID, List[str]],
    schedulable_rooms: List[Any],
) -> None:
    """Applies Sunday civic space allocation and outdoor grounds constraints to the CP-SAT model.

    Rules applied:
    1. Academic offerings are locked to Monday-Saturday (day <= 5).
    2. Function Hall on Sunday has fixed zero-occupancy intervals for the turnover buffer (12:00-13:00)
       and post-17:00 lockout (17:00-19:00).
    3. ROTC offerings are pinned to Sunday 07:00-12:00 in the Function Hall.
    4. NSTP offerings are pinned to Sunday 13:00-17:00 in the Function Hall.
    5. PATHFIT offerings are strictly restricted to outdoor grounds.
    6. Non-PATHFIT offerings are strictly forbidden from outdoor grounds.
    """
    has_rotc_offering = False
    has_nstp_offering = False

    # 1. Turnover buffer interval in Function Hall on Sunday [10, 12)
    # Global slot index: day 6 * 24 + 10 = 144 + 10 = 154
    buffer_start = DAY_SUNDAY * 24 + BUFFER_START_SLOT
    buffer_end = buffer_start + BUFFER_DURATION_SLOTS
    buf_interval = model.NewIntervalVar(
        start=buffer_start,
        size=BUFFER_DURATION_SLOTS,
        end=buffer_end,
        name="fixed_sun_function_hall_turnover_buffer",
    )
    if FUNCTION_HALL_ROOM_CODE in room_opt_intervals:
        room_opt_intervals[FUNCTION_HALL_ROOM_CODE].append(buf_interval)

    # Post-17:00 closure interval in Function Hall on Sunday [20, 24)
    # Global slot index: day 6 * 24 + 20 = 144 + 20 = 164
    closure_start = DAY_SUNDAY * 24 + POST_CIVIC_START_SLOT
    closure_end = closure_start + POST_CIVIC_DURATION_SLOTS
    close_interval = model.NewIntervalVar(
        start=closure_start,
        size=POST_CIVIC_DURATION_SLOTS,
        end=closure_end,
        name="fixed_sun_function_hall_post_civic_closure",
    )
    if FUNCTION_HALL_ROOM_CODE in room_opt_intervals:
        room_opt_intervals[FUNCTION_HALL_ROOM_CODE].append(close_interval)

    # 2. Offerings iteration
    for offering in offerings:
        off_id = offering.id if hasattr(offering, "id") else offering["id"]
        subj_code = ""
        if hasattr(offering, "subject_code"):
            subj_code = offering.subject_code or ""
        elif hasattr(offering, "subject") and hasattr(offering.subject, "subject_code"):
            subj_code = offering.subject.subject_code or ""
        elif isinstance(offering, dict) and "subject_code" in offering:
            subj_code = offering["subject_code"] or ""

        # PATHFIT outdoor grounds rule
        if is_pathfit_subject(subj_code):
            # Forbid indoor rooms
            for r in schedulable_rooms:
                rcode = r.room_code if hasattr(r, "room_code") else r["room_code"]
                if not is_outdoor_ground(rcode):
                    if (off_id, rcode) in x_vars:
                        model.Add(x_vars[off_id, rcode] == 0)
        else:
            # Non-PATHFIT cannot use outdoor grounds
            for r in schedulable_rooms:
                rcode = r.room_code if hasattr(r, "room_code") else r["room_code"]
                if is_outdoor_ground(rcode):
                    if (off_id, rcode) in x_vars:
                        model.Add(x_vars[off_id, rcode] == 0)

        # ROTC Civic Offering
        if is_rotc_subject(subj_code):
            has_rotc_offering = True
            model.Add(d_vars[off_id] == DAY_SUNDAY)
            model.Add(start_vars[off_id] == DAY_SUNDAY * 24 + ROTC_START_SLOT)
            if (off_id, FUNCTION_HALL_ROOM_CODE) in x_vars:
                model.Add(x_vars[off_id, FUNCTION_HALL_ROOM_CODE] == 1)

        # NSTP Civic Offering
        elif is_nstp_subject(subj_code):
            has_nstp_offering = True
            model.Add(d_vars[off_id] == DAY_SUNDAY)
            model.Add(start_vars[off_id] == DAY_SUNDAY * 24 + NSTP_START_SLOT)
            if (off_id, FUNCTION_HALL_ROOM_CODE) in x_vars:
                model.Add(x_vars[off_id, FUNCTION_HALL_ROOM_CODE] == 1)

        # Standard Academic Offering
        else:
            # Forbid Sunday scheduling: day must be Monday (0) to Saturday (5)
            model.Add(d_vars[off_id] <= DayOfWeek.SATURDAY.value)

    # If ROTC is not present as a course offering, lock Function Hall 07:00-12:00 as an external block
    if not has_rotc_offering and FUNCTION_HALL_ROOM_CODE in room_opt_intervals:
        rotc_start = DAY_SUNDAY * 24 + ROTC_START_SLOT
        rotc_end = rotc_start + ROTC_DURATION_SLOTS
        rotc_fixed = model.NewIntervalVar(
            start=rotc_start,
            size=ROTC_DURATION_SLOTS,
            end=rotc_end,
            name="fixed_sun_function_hall_rotc_external",
        )
        room_opt_intervals[FUNCTION_HALL_ROOM_CODE].append(rotc_fixed)

    # If NSTP is not present as a course offering, lock Function Hall 13:00-17:00 as an external block
    if not has_nstp_offering and FUNCTION_HALL_ROOM_CODE in room_opt_intervals:
        nstp_start = DAY_SUNDAY * 24 + NSTP_START_SLOT
        nstp_end = nstp_start + NSTP_DURATION_SLOTS
        nstp_fixed = model.NewIntervalVar(
            start=nstp_start,
            size=NSTP_DURATION_SLOTS,
            end=nstp_end,
            name="fixed_sun_function_hall_nstp_external",
        )
        room_opt_intervals[FUNCTION_HALL_ROOM_CODE].append(nstp_fixed)
