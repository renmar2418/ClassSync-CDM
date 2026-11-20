"""Google OR-Tools CP-SAT Master Model Builder for ClassSync.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Enforces:
1. Exact CP-SAT model setup with cp_model.CpModel()
2. Start, Duration, End, Interval variables (I_o)
3. Optional room interval variables (I_{o, r}) linked to room presence indicators (x_{o, r})
4. Room non-overlap constraint (model.AddNoOverlap per schedulable room)
5. Faculty non-overlap constraint (model.AddNoOverlap per 100% full-time faculty)
6. Section non-overlap constraint (model.AddNoOverlap per unified student cohort)
7. Day boundary constraint: start_slot + duration_slots <= 24
8. Academic operational horizon: Mon-Sat 07:00-19:00 (Days 0-5, Slots 0-23)
9. Sunday Civic Space Allocation & Function Hall partitioning (ROTC, buffer, NSTP)
10. Quarantined spaces exclusion (NB 204, NB 304, NB 308, PROPERTY_OFFICE, CAMPUS_CANTEEN)
11. Room exclusivity: PRRC 108 locked exclusively to BSED_SCIENCE offerings
"""

from __future__ import annotations
import hashlib
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any

from ortools.sat.python import cp_model

from classync_contracts.enums import RoomType, DayOfWeek, CohortMode, SolverStatus
from classync_contracts.schemas import (
    RoomSchema,
    CourseOfferingDetail,
    TimetableEntrySchema,
    SolverRunResponse,
)
from services.scheduling.solver.objective_weights import (
    SolverObjectiveWeights,
    add_all_objective_weights,
)
from services.scheduling.solver.sunday_rules import (
    DAY_SUNDAY,
    FUNCTION_HALL_ROOM_CODE,
    ROTC_START_SLOT,
    ROTC_DURATION_SLOTS,
    NSTP_START_SLOT,
    NSTP_DURATION_SLOTS,
    is_rotc_subject,
    is_nstp_subject,
    is_pathfit_subject,
    is_civic_subject,
    is_outdoor_ground,
    apply_sunday_constraints,
)


@dataclass
class OfferingData:
    """Normalized offering payload consumed by CP-SAT Model Builder."""
    id: uuid.UUID
    subject_code: str
    section_id: uuid.UUID
    section_code: str
    faculty_id: uuid.UUID
    faculty_name: str
    required_room_type: str
    duration_slots: int
    enrolled_student_count: int
    program: Optional[str] = None
    is_locked: bool = False
    locked_day: Optional[int] = None
    locked_start_slot: Optional[int] = None
    locked_room_code: Optional[str] = None


@dataclass
class RoomData:
    """Normalized room payload consumed by CP-SAT Model Builder."""
    room_code: str
    building_name: str
    floor_level: int
    room_type: str
    capacity: int
    is_schedulable: bool
    has_aircon: bool = False
    has_projector: bool = False
    exclusive_program: Optional[str] = None


@dataclass
class SectionData:
    """Normalized section payload consumed by CP-SAT Model Builder."""
    id: uuid.UUID
    section_code: str
    year_level: int
    enrolled_student_count: int


@dataclass
class ScheduleSolutionEntry:
    """Single scheduled class assignment in the resulting timetable."""
    offering_id: uuid.UUID
    room_code: str
    day_of_week: int
    start_slot: int
    duration_slots: int
    cohort_mode: str = "UNIFIED"
    is_locked: bool = False
    revision_hash: str = ""
    id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass
class SolverResult:
    """Overall CP-SAT solver execution response."""
    status: SolverStatus
    solve_time_seconds: float
    total_conflicts: int
    entries: List[ScheduleSolutionEntry]
    objective_value: Optional[float] = None
    diagnostics: Optional[str] = None


@dataclass
class SolverVariables:
    """Container holding CP-SAT mathematical decision variables."""
    d_vars: Dict[uuid.UUID, cp_model.IntVar]
    slot_vars: Dict[uuid.UUID, cp_model.IntVar]
    start_vars: Dict[uuid.UUID, cp_model.IntVar]
    end_vars: Dict[uuid.UUID, cp_model.IntVar]
    interval_vars: Dict[uuid.UUID, cp_model.IntervalVar]
    x_vars: Dict[Tuple[uuid.UUID, str], cp_model.BoolVar]
    room_opt_intervals: Dict[str, List[cp_model.IntervalVar]]
    sec_intervals: Dict[uuid.UUID, List[cp_model.IntervalVar]]
    fac_intervals: Dict[uuid.UUID, List[cp_model.IntervalVar]]
    candidate_rooms: Dict[uuid.UUID, List[str]]


def normalize_offering(item: Any) -> OfferingData:
    """Converts a CourseOfferingDetail, OfferingData, or dict into OfferingData."""
    if isinstance(item, OfferingData):
        return item

    if hasattr(item, "id"):
        off_id = item.id
        subj_code = getattr(item.subject, "subject_code", "") if hasattr(item, "subject") and item.subject else getattr(item, "subject_code", "")
        sec_id = getattr(item, "section_id", uuid.uuid4())
        sec_code = getattr(item.section, "section_code", "") if hasattr(item, "section") and item.section else getattr(item, "section_code", "")
        fac_id = getattr(item, "faculty_id", uuid.uuid4())
        fac_name = getattr(item.faculty, "full_name", "") if hasattr(item, "faculty") and item.faculty else getattr(item, "faculty_name", "")

        # Room type
        req_rt = "LECTURE"
        if hasattr(item, "subject") and item.subject:
            req_rt = item.subject.required_room_type
        elif hasattr(item, "required_room_type"):
            req_rt = item.required_room_type
        if hasattr(req_rt, "value"):
            req_rt = req_rt.value
        req_rt = str(req_rt)

        # Duration
        dur = 0
        if hasattr(item, "duration_slots") and item.duration_slots:
            dur = item.duration_slots
        elif hasattr(item, "subject") and item.subject:
            lec = getattr(item.subject, "lecture_hours", 0) or 0
            lab = getattr(item.subject, "lab_hours", 0) or 0
            dur = (lec + lab) * 2

        if is_rotc_subject(subj_code):
            dur = ROTC_DURATION_SLOTS
        elif is_nstp_subject(subj_code):
            dur = NSTP_DURATION_SLOTS
        elif is_pathfit_subject(subj_code) and dur == 0:
            dur = 4

        if dur <= 0:
            dur = 6  # 3 hours default

        # Student count
        enrolled = 60
        if hasattr(item, "section") and item.section:
            enrolled = getattr(item.section, "enrolled_student_count", 60)
        elif hasattr(item, "enrolled_student_count"):
            enrolled = getattr(item, "enrolled_student_count", 60)

        # Program extraction
        program = getattr(item, "program", None)
        if not program:
            if "BSED" in sec_code or "BSED-SCI" in sec_code or "BSED" in subj_code:
                program = "BSED_SCIENCE"
            elif "BSIT" in sec_code:
                program = "BSIT"
            elif "BSCPE" in sec_code:
                program = "BSCPE"

        return OfferingData(
            id=off_id,
            subject_code=subj_code,
            section_id=sec_id,
            section_code=sec_code,
            faculty_id=fac_id,
            faculty_name=fac_name,
            required_room_type=req_rt,
            duration_slots=dur,
            enrolled_student_count=enrolled,
            program=program,
            is_locked=getattr(item, "is_locked", False),
            locked_day=getattr(item, "locked_day", None),
            locked_start_slot=getattr(item, "locked_start_slot", None),
            locked_room_code=getattr(item, "locked_room_code", None),
        )

    # Dict fallback
    return OfferingData(
        id=item.get("id", uuid.uuid4()),
        subject_code=item.get("subject_code", ""),
        section_id=item.get("section_id", uuid.uuid4()),
        section_code=item.get("section_code", ""),
        faculty_id=item.get("faculty_id", uuid.uuid4()),
        faculty_name=item.get("faculty_name", ""),
        required_room_type=str(item.get("required_room_type", "LECTURE")),
        duration_slots=item.get("duration_slots", 6),
        enrolled_student_count=item.get("enrolled_student_count", 60),
        program=item.get("program"),
        is_locked=item.get("is_locked", False),
        locked_day=item.get("locked_day"),
        locked_start_slot=item.get("locked_start_slot"),
        locked_room_code=item.get("locked_room_code"),
    )


def normalize_room(item: Any) -> RoomData:
    """Converts a RoomSchema, Room model, RoomData, or dict into RoomData."""
    if isinstance(item, RoomData):
        return item

    if hasattr(item, "room_code"):
        rt = item.room_type
        if hasattr(rt, "value"):
            rt = rt.value
        return RoomData(
            room_code=item.room_code,
            building_name=item.building_name,
            floor_level=item.floor_level,
            room_type=str(rt),
            capacity=item.capacity,
            is_schedulable=item.is_schedulable,
            has_aircon=getattr(item, "has_aircon", False),
            has_projector=getattr(item, "has_projector", False),
            exclusive_program=getattr(item, "exclusive_program", None),
        )

    return RoomData(
        room_code=item["room_code"],
        building_name=item.get("building_name", ""),
        floor_level=item.get("floor_level", 1),
        room_type=str(item.get("room_type", "LECTURE")),
        capacity=item.get("capacity", 50),
        is_schedulable=item.get("is_schedulable", True),
        has_aircon=item.get("has_aircon", False),
        has_projector=item.get("has_projector", False),
        exclusive_program=item.get("exclusive_program"),
    )


class CPSATMasterModelBuilder:
    """Master Constraint Programming model builder powered by Google OR-Tools CP-SAT."""

    def __init__(
        self,
        offerings: List[Any],
        rooms: List[Any],
        sections: Optional[List[SectionData]] = None,
        weights: Optional[SolverObjectiveWeights] = None,
    ) -> None:
        self.offerings: List[OfferingData] = [normalize_offering(o) for o in offerings]
        self.rooms: List[RoomData] = [normalize_room(r) for r in rooms]
        self.weights = weights or SolverObjectiveWeights()

        # Deduce sections if not provided explicitly
        if sections is not None:
            self.sections = sections
        else:
            sec_dict: Dict[uuid.UUID, SectionData] = {}
            for o in self.offerings:
                if o.section_id not in sec_dict:
                    sec_dict[o.section_id] = SectionData(
                        id=o.section_id,
                        section_code=o.section_code,
                        year_level=3,
                        enrolled_student_count=o.enrolled_student_count,
                    )
            self.sections = list(sec_dict.values())

        # Spatial Quarantine filter: strictly schedulable rooms
        self.schedulable_rooms = [r for r in self.rooms if r.is_schedulable]
        self.room_map = {r.room_code: r for r in self.schedulable_rooms}

    def filter_eligible_rooms(self, offering: OfferingData) -> List[RoomData]:
        """Filters candidate rooms enforcing quarantine, room type, capacity, and exclusivity."""
        eligible: List[RoomData] = []
        is_pathfit = is_pathfit_subject(offering.subject_code)

        for r in self.schedulable_rooms:
            # 1. PATHFIT outdoor grounds rule
            if is_pathfit:
                if not is_outdoor_ground(r.room_code):
                    continue
            else:
                # Non-PATHFIT forbidden from outdoor grounds
                if is_outdoor_ground(r.room_code):
                    continue

                # 2. Room type match (LECTURE vs COMPUTER_LAB vs FUNCTION_HALL)
                if r.room_type != offering.required_room_type:
                    continue

            # 3. Capacity match
            if r.capacity < offering.enrolled_student_count:
                continue

            # 4. Room exclusivity (PRRC 108 locked to BSED_SCIENCE)
            if r.exclusive_program is not None:
                if offering.program != r.exclusive_program:
                    continue
            elif r.room_code == "PRRC 108" and offering.program != "BSED_SCIENCE":
                continue

            eligible.append(r)
        return eligible

    def build_model(self) -> Tuple[cp_model.CpModel, SolverVariables]:
        """Constructs the full mathematical CP-SAT model with hard and soft constraints."""
        model = cp_model.CpModel()

        d_vars: Dict[uuid.UUID, cp_model.IntVar] = {}
        slot_vars: Dict[uuid.UUID, cp_model.IntVar] = {}
        start_vars: Dict[uuid.UUID, cp_model.IntVar] = {}
        end_vars: Dict[uuid.UUID, cp_model.IntVar] = {}
        interval_vars: Dict[uuid.UUID, cp_model.IntervalVar] = {}
        x_vars: Dict[Tuple[uuid.UUID, str], cp_model.BoolVar] = {}
        room_opt_intervals: Dict[str, List[cp_model.IntervalVar]] = {
            r.room_code: [] for r in self.schedulable_rooms
        }
        sec_intervals: Dict[uuid.UUID, List[cp_model.IntervalVar]] = {}
        fac_intervals: Dict[uuid.UUID, List[cp_model.IntervalVar]] = {}
        candidate_rooms: Dict[uuid.UUID, List[str]] = {}

        # 1. Variable creation per offering
        for o in self.offerings:
            dur = o.duration_slots
            if dur < 1 or dur > 24:
                raise ValueError(f"Invalid duration {dur} for offering {o.id}")

            # Day variable: Mon-Sun (0 to 6)
            d = model.NewIntVar(0, 6, f"d_{o.id}")
            # Slot variable: 0 to 24 - dur (guarantees slot + dur <= 24)
            slot = model.NewIntVar(0, 24 - dur, f"slot_{o.id}")
            # Global start and end slots: 0 to 168 (7 days * 24 slots)
            start = model.NewIntVar(0, 168 - dur, f"start_{o.id}")
            end = model.NewIntVar(dur, 168, f"end_{o.id}")

            model.Add(start == d * 24 + slot)
            model.Add(end == start + dur)

            # Primary interval variable
            inv = model.NewIntervalVar(start, dur, end, f"inv_{o.id}")

            d_vars[o.id] = d
            slot_vars[o.id] = slot
            start_vars[o.id] = start
            end_vars[o.id] = end
            interval_vars[o.id] = inv

            sec_intervals.setdefault(o.section_id, []).append(inv)
            fac_intervals.setdefault(o.faculty_id, []).append(inv)

            # Manual locking support
            if o.is_locked:
                if o.locked_day is not None:
                    model.Add(d == o.locked_day)
                if o.locked_start_slot is not None:
                    model.Add(slot == o.locked_start_slot)

            # Candidate rooms
            cands = self.filter_eligible_rooms(o)
            if not cands:
                raise ValueError(
                    f"Infeasible offering {o.subject_code} ({o.id}): zero eligible schedulable rooms "
                    f"for room_type={o.required_room_type}, capacity={o.enrolled_student_count}, program={o.program}"
                )
            candidate_rooms[o.id] = [r.room_code for r in cands]

            x_list: List[cp_model.BoolVar] = []
            for r in cands:
                rcode = r.room_code
                x = model.NewBoolVar(f"x_{o.id}_{rcode}")
                x_vars[o.id, rcode] = x
                x_list.append(x)

                opt_inv = model.NewOptionalIntervalVar(start, dur, end, x, f"opt_{o.id}_{rcode}")
                room_opt_intervals[rcode].append(opt_inv)

                if o.is_locked and o.locked_room_code == rcode:
                    model.Add(x == 1)

            # Exactly one room assigned per offering
            model.AddExactlyOne(x_list)

        # 2. Hard Constraints: Room Non-Overlap
        # (Will be committed after adding Sunday reservations)

        # 3. Apply Sunday Civic Space Allocation & Outdoor Grounds Rules
        apply_sunday_constraints(
            model=model,
            offerings=self.offerings,
            d_vars=d_vars,
            start_vars=start_vars,
            x_vars=x_vars,
            room_opt_intervals=room_opt_intervals,
            candidate_rooms=candidate_rooms,
            schedulable_rooms=self.schedulable_rooms,
        )

        # Commit Room Non-Overlap
        for rcode, opt_invs in room_opt_intervals.items():
            if opt_invs:
                model.AddNoOverlap(opt_invs)

        # 4. Hard Constraints: Faculty Non-Overlap (100% full-time faculty)
        for fid, f_invs in fac_intervals.items():
            if len(f_invs) > 1:
                model.AddNoOverlap(f_invs)

        # 5. Soft Constraints & Objective Weights (injects Lunch into section non-overlap)
        add_all_objective_weights(
            model=model,
            offerings=self.offerings,
            sections=self.sections,
            d_vars=d_vars,
            start_vars=start_vars,
            end_vars=end_vars,
            section_intervals=sec_intervals,
            x_vars=x_vars,
            candidate_rooms=candidate_rooms,
            weights=self.weights,
        )

        variables = SolverVariables(
            d_vars=d_vars,
            slot_vars=slot_vars,
            start_vars=start_vars,
            end_vars=end_vars,
            interval_vars=interval_vars,
            x_vars=x_vars,
            room_opt_intervals=room_opt_intervals,
            sec_intervals=sec_intervals,
            fac_intervals=fac_intervals,
            candidate_rooms=candidate_rooms,
        )
        return model, variables

    def solve(
        self,
        time_limit_seconds: int = 120,
        num_workers: int = 8,
    ) -> SolverResult:
        """Executes the Google OR-Tools CP-SAT solver and formats the output entries."""
        start_time = time.time()
        try:
            model, variables = self.build_model()
        except ValueError as exc:
            return SolverResult(
                status=SolverStatus.INFEASIBLE,
                solve_time_seconds=time.time() - start_time,
                total_conflicts=1,
                entries=[],
                diagnostics=str(exc),
            )

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = float(time_limit_seconds)
        solver.parameters.num_search_workers = num_workers
        solver.parameters.log_search_progress = False

        status_code = solver.Solve(model)
        elapsed_seconds = time.time() - start_time

        if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            status = SolverStatus.OPTIMAL if status_code == cp_model.OPTIMAL else SolverStatus.FEASIBLE
            entries: List[ScheduleSolutionEntry] = []

            for o in self.offerings:
                day_val = solver.Value(variables.d_vars[o.id])
                slot_val = solver.Value(variables.slot_vars[o.id])

                # Determine chosen room
                chosen_room = ""
                for rcode in variables.candidate_rooms[o.id]:
                    if solver.Value(variables.x_vars[o.id, rcode]) == 1:
                        chosen_room = rcode
                        break

                # Cryptographic revision hash over sorted tuple
                digest_input = f"{o.id}:{chosen_room}:{day_val}:{slot_val}:{o.duration_slots}:UNIFIED"
                rev_hash = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()

                entry = ScheduleSolutionEntry(
                    id=uuid.uuid4(),
                    offering_id=o.id,
                    room_code=chosen_room,
                    day_of_week=day_val,
                    start_slot=slot_val,
                    duration_slots=o.duration_slots,
                    cohort_mode="UNIFIED",
                    is_locked=o.is_locked,
                    revision_hash=rev_hash,
                )
                entries.append(entry)

            return SolverResult(
                status=status,
                solve_time_seconds=elapsed_seconds,
                total_conflicts=0,
                entries=entries,
                objective_value=solver.ObjectiveValue(),
            )
        else:
            return SolverResult(
                status=SolverStatus.INFEASIBLE,
                solve_time_seconds=elapsed_seconds,
                total_conflicts=len(self.offerings),
                entries=[],
                diagnostics="CP-SAT solver returned INFEASIBLE or TIMED_OUT under given constraints.",
            )


class MasterCPSATSolver:
    """Production Adapter wrapping CPSATMasterModelBuilder.
    
    Accepts CourseOfferingDetail/OfferingData and RoomSchema/RoomData lists and
    returns a SolverRunResponse containing TimetableEntrySchema entries.
    """

    def __init__(
        self,
        rooms: List[Any],
        offerings: List[Any],
        sections: Optional[List[Any]] = None,
        weights: Optional[SolverObjectiveWeights] = None,
        time_limit_seconds: int = 120,
        num_workers: int = 8,
    ) -> None:
        self.rooms = rooms
        self.offerings = offerings
        self.sections = sections
        self.weights = weights
        self.time_limit_seconds = time_limit_seconds
        self.num_workers = num_workers

        self.builder = CPSATMasterModelBuilder(
            offerings=offerings,
            rooms=rooms,
            sections=sections,
            weights=weights,
        )

    def solve(self) -> SolverRunResponse:
        """Executes solve and maps output to SolverRunResponse."""
        result = self.builder.solve(
            time_limit_seconds=self.time_limit_seconds,
            num_workers=self.num_workers,
        )

        # Convert ScheduleSolutionEntry list to TimetableEntrySchema list
        timetable_entries: List[TimetableEntrySchema] = []
        for e in result.entries:
            schema_entry = TimetableEntrySchema(
                id=e.id,
                offering_id=e.offering_id,
                room_code=e.room_code,
                day_of_week=DayOfWeek(e.day_of_week),
                start_slot=e.start_slot,
                duration_slots=e.duration_slots,
                cohort_mode=CohortMode.UNIFIED,
                is_locked=e.is_locked,
                revision_hash=e.revision_hash,
            )
            timetable_entries.append(schema_entry)

        return SolverRunResponse(
            status=result.status,
            total_conflicts=result.total_conflicts,
            solve_time_seconds=result.solve_time_seconds,
            timetable_entries=timetable_entries,
        )
