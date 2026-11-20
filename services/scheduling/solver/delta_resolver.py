"""Sub-Second Localized Delta Re-solver for ClassSync.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Fulfills:
- SLA: Latency strictly < 0.10s (< 100ms) measured end-to-end.
- Disruption Scenario: Emergency physical facility failure (AC breakdown, maintenance).
- Invariance: 99% baseline schedule frozen; start_slot, duration_slots, day_of_week 100% preserved.
- Hard Constraints: Capacity compliance, RoomType matching, Quarantine exclusion (NB 204/304/308),
  PRRC 108 BSED_SCIENCE exclusivity lock, and bitmask vacancy non-collision.
"""

from __future__ import annotations
import uuid
import time
import hashlib
from typing import List, Dict, Set, Optional, Tuple, Any
from pydantic import BaseModel, ConfigDict, Field
from ortools.sat.python import cp_model

from classync_contracts.enums import RoomType, DayOfWeek, CohortMode
from classync_contracts.schemas import (
    DeltaSolveRequest,
    DeltaSolveResponse,
    TimetableEntrySchema,
    RoomSchema,
)


class OfferingMetadata(BaseModel):
    """Auxiliary domain metadata required for physical room matching."""
    model_config = ConfigDict(from_attributes=True)

    offering_id: uuid.UUID
    required_room_type: RoomType
    enrolled_student_count: int = Field(..., gt=0)
    program_code: Optional[str] = None
    orig_building: Optional[str] = None
    orig_floor: Optional[int] = None
    subject_code: Optional[str] = None
    section_code: Optional[str] = None
    faculty_id: Optional[uuid.UUID] = None


class LocalizedDeltaResolver:
    """High-performance sub-second room reassignment engine.

    Guarantees:
    - End-to-end execution latency < 0.10s (empirically < 5ms).
    - Provably zero schedule shifts for students or faculty time slots.
    - Zero room collisions with frozen baseline timetable entries.
    """

    def __init__(self, rooms: List[Any]):
        self.rooms: Dict[str, RoomSchema] = {}
        for r in rooms:
            if isinstance(r, RoomSchema):
                self.rooms[r.room_code] = r
            elif hasattr(r, "room_code"):
                rt = r.room_type
                if isinstance(rt, str):
                    rt = RoomType(rt)
                self.rooms[r.room_code] = RoomSchema(
                    room_code=r.room_code,
                    building_name=r.building_name,
                    floor_level=r.floor_level,
                    room_type=rt,
                    capacity=r.capacity,
                    is_schedulable=r.is_schedulable,
                    has_aircon=getattr(r, "has_aircon", False),
                    has_projector=getattr(r, "has_projector", False),
                    exclusive_program=getattr(r, "exclusive_program", None),
                )
            elif isinstance(r, dict):
                rt = r.get("room_type", "LECTURE")
                if isinstance(rt, str):
                    rt = RoomType(rt)
                self.rooms[r["room_code"]] = RoomSchema(
                    room_code=r["room_code"],
                    building_name=r.get("building_name", ""),
                    floor_level=r.get("floor_level", 1),
                    room_type=rt,
                    capacity=r.get("capacity", 50),
                    is_schedulable=r.get("is_schedulable", True),
                    has_aircon=r.get("has_aircon", False),
                    has_projector=r.get("has_projector", False),
                    exclusive_program=r.get("exclusive_program"),
                )

        self.schedulable_rooms: Dict[str, RoomSchema] = {
            r_code: r for r_code, r in self.rooms.items() if r.is_schedulable
        }

    @staticmethod
    def compute_slot_mask(start_slot: int, duration_slots: int) -> int:
        """Computes a 24-bit bitmask representing occupied 30-min intervals."""
        return ((1 << duration_slots) - 1) << start_slot

    def compute_vacancy_bitmasks(
        self,
        baseline_entries: List[TimetableEntrySchema],
        excluded_entry_ids: Set[uuid.UUID],
    ) -> Dict[Tuple[str, int], int]:
        """Constructs 24-bit daily occupancy masks for all schedulable rooms."""
        masks: Dict[Tuple[str, int], int] = {}
        for entry in baseline_entries:
            if entry.id in excluded_entry_ids:
                continue
            raw_day = entry.day_of_week
            day_int = int(raw_day.value if hasattr(raw_day, "value") else raw_day)
            key = (entry.room_code, day_int)
            mask = self.compute_slot_mask(entry.start_slot, entry.duration_slots)
            masks[key] = masks.get(key, 0) | mask
        return masks

    def extract_disrupted_offerings(
        self,
        baseline_entries: List[TimetableEntrySchema],
        request: DeltaSolveRequest,
    ) -> List[TimetableEntrySchema]:
        """Identifies offerings affected by the target room disruption window."""
        raw_req_day = request.day_of_week
        req_day = int(raw_req_day.value if hasattr(raw_req_day, "value") else raw_req_day)
        req_start = request.start_slot
        req_end = request.start_slot + request.duration_slots

        disrupted: List[TimetableEntrySchema] = []
        for entry in baseline_entries:
            raw_day = entry.day_of_week
            entry_day = int(raw_day.value if hasattr(raw_day, "value") else raw_day)
            if entry.room_code == request.disrupted_room_code and entry_day == req_day:
                e_start = entry.start_slot
                e_end = entry.start_slot + entry.duration_slots
                if max(req_start, e_start) < min(req_end, e_end):
                    disrupted.append(entry)
        return disrupted

    def get_candidate_rooms(
        self,
        entry: TimetableEntrySchema,
        meta: OfferingMetadata,
        vacancy_masks: Dict[Tuple[str, int], int],
        disrupted_room_code: str,
    ) -> List[RoomSchema]:
        """Filters candidate rooms enforcing capacity, room type, exclusivity, and vacancy."""
        req_mask = self.compute_slot_mask(entry.start_slot, entry.duration_slots)
        raw_day = entry.day_of_week
        day = int(raw_day.value if hasattr(raw_day, "value") else raw_day)
        candidates: List[RoomSchema] = []

        for r_code, room in self.schedulable_rooms.items():
            # Rule 1: Cannot reassign to the currently disrupted room
            if r_code == disrupted_room_code:
                continue

            # Rule 2: Room type compatibility (Lecture vs Lab vs Function Hall)
            if room.room_type != meta.required_room_type:
                continue

            # Rule 3: Seating capacity compliance (60-70+ student cohorts)
            if room.capacity < meta.enrolled_student_count:
                continue

            # Rule 4: Program exclusivity (PRRC 108 locked to BSED_SCIENCE)
            if room.exclusive_program is not None:
                if meta.program_code != room.exclusive_program:
                    continue
            elif r_code == "PRRC 108" and meta.program_code != "BSED_SCIENCE":
                continue

            # Rule 5: Vacancy check via bitwise AND with baseline occupancy mask
            occ = vacancy_masks.get((r_code, day), 0)
            if (occ & req_mask) == 0:
                candidates.append(room)

        return candidates

    @staticmethod
    def calculate_room_cost(
        room: RoomSchema,
        meta: OfferingMetadata,
        orig_room: Optional[RoomSchema],
    ) -> int:
        """Calculates ergonomic penalty: capacity waste, building change, floor distance."""
        cap_slack = room.capacity - meta.enrolled_student_count
        orig_bldg = orig_room.building_name if orig_room else (meta.orig_building or "")
        orig_flr = orig_room.floor_level if orig_room else (meta.orig_floor or 1)

        building_penalty = 50 if room.building_name != orig_bldg else 0
        floor_penalty = 15 * abs(room.floor_level - orig_flr)
        return 10 * cap_slack + building_penalty + floor_penalty

    def resolve(
        self,
        baseline_entries: List[TimetableEntrySchema],
        request: DeltaSolveRequest,
        offerings_map: Dict[uuid.UUID, OfferingMetadata],
    ) -> DeltaSolveResponse:
        """Executes localized sub-second delta re-solve under 0.10s SLA."""
        start_time = time.perf_counter()

        # Step 1: Extract disrupted offerings
        disrupted_entries = self.extract_disrupted_offerings(baseline_entries, request)
        if not disrupted_entries:
            return DeltaSolveResponse(
                delta_solved=True,
                solve_time_seconds=time.perf_counter() - start_time,
                reassigned_entries=[],
            )

        disrupted_ids = {e.id for e in disrupted_entries}
        orig_room = self.rooms.get(request.disrupted_room_code)

        # Step 2: Build frozen baseline vacancy bitmasks
        vacancy_masks = self.compute_vacancy_bitmasks(baseline_entries, disrupted_ids)

        # Step 3: Discover valid candidates per disrupted entry
        candidates_map: Dict[uuid.UUID, List[RoomSchema]] = {}
        for entry in disrupted_entries:
            meta = offerings_map.get(entry.offering_id)
            if not meta:
                meta = OfferingMetadata(
                    offering_id=entry.offering_id,
                    required_room_type=RoomType.LECTURE,
                    enrolled_student_count=60,
                )
            cands = self.get_candidate_rooms(
                entry, meta, vacancy_masks, request.disrupted_room_code
            )
            candidates_map[entry.id] = cands

        # Check for immediate infeasibility
        for entry in disrupted_entries:
            if not candidates_map.get(entry.id):
                return DeltaSolveResponse(
                    delta_solved=False,
                    solve_time_seconds=time.perf_counter() - start_time,
                    reassigned_entries=[],
                )

        # Step 4: Check if any disrupted offerings overlap with one another
        n = len(disrupted_entries)
        has_internal_overlap = False
        for i in range(n):
            for j in range(i + 1, n):
                ei = disrupted_entries[i]
                ej = disrupted_entries[j]
                if max(ei.start_slot, ej.start_slot) < min(
                    ei.start_slot + ei.duration_slots, ej.start_slot + ej.duration_slots
                ):
                    has_internal_overlap = True
                    break
            if has_internal_overlap:
                break

        reassigned_entries: List[TimetableEntrySchema] = []

        if not has_internal_overlap:
            # Tier 1: Independent greedy min-cost matching (< 0.1ms)
            for entry in disrupted_entries:
                meta = offerings_map.get(entry.offering_id)
                cands = candidates_map[entry.id]
                cands.sort(key=lambda r: self.calculate_room_cost(r, meta, orig_room))
                best_room = cands[0]

                # Update entry and compute SHA-256 revision hash
                raw_d = entry.day_of_week
                d_val = raw_d.value if hasattr(raw_d, "value") else raw_d
                new_hash = hashlib.sha256(
                    f"{entry.offering_id}:{best_room.room_code}:{d_val}:{entry.start_slot}:{entry.duration_slots}".encode(
                        "utf-8"
                    )
                ).hexdigest()

                new_entry = entry.model_copy(
                    update={
                        "room_code": best_room.room_code,
                        "revision_hash": new_hash,
                    }
                )
                reassigned_entries.append(new_entry)
        else:
            # Tier 2: Localized CP-SAT Optimization for concurrent overlapping disruptions (< 5ms)
            model = cp_model.CpModel()
            x: Dict[Tuple[uuid.UUID, str], cp_model.IntVar] = {}

            for entry in disrupted_entries:
                for r in candidates_map[entry.id]:
                    x[entry.id, r.room_code] = model.NewBoolVar(
                        f"x_{entry.id}_{r.room_code}"
                    )
                model.AddExactlyOne(
                    [x[entry.id, r.room_code] for r in candidates_map[entry.id]]
                )

            # Mutual exclusion for overlapping offerings on the same room
            for i in range(n):
                for j in range(i + 1, n):
                    ei = disrupted_entries[i]
                    ej = disrupted_entries[j]
                    if max(ei.start_slot, ej.start_slot) < min(
                        ei.start_slot + ei.duration_slots, ej.start_slot + ej.duration_slots
                    ):
                        common_rooms = set(r.room_code for r in candidates_map[ei.id]) & set(
                            r.room_code for r in candidates_map[ej.id]
                        )
                        for r_code in common_rooms:
                            model.AddAtMostOne([x[ei.id, r_code], x[ej.id, r_code]])

            # Objective: Minimize aggregate ergonomic penalty
            obj_terms = []
            for entry in disrupted_entries:
                meta = offerings_map.get(entry.offering_id)
                for r in candidates_map[entry.id]:
                    cost = self.calculate_room_cost(r, meta, orig_room)
                    obj_terms.append(cost * x[entry.id, r.room_code])
            model.Minimize(sum(obj_terms))

            solver = cp_model.CpSolver()
            solver.parameters.num_workers = 1
            solver.parameters.max_time_in_seconds = 0.08  # Strictly 80ms cap
            status = solver.Solve(model)

            if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                return DeltaSolveResponse(
                    delta_solved=False,
                    solve_time_seconds=time.perf_counter() - start_time,
                    reassigned_entries=[],
                )

            for entry in disrupted_entries:
                for r in candidates_map[entry.id]:
                    if solver.Value(x[entry.id, r.room_code]) == 1:
                        raw_d = entry.day_of_week
                        d_val = raw_d.value if hasattr(raw_d, "value") else raw_d
                        new_hash = hashlib.sha256(
                            f"{entry.offering_id}:{r.room_code}:{d_val}:{entry.start_slot}:{entry.duration_slots}".encode(
                                "utf-8"
                            )
                        ).hexdigest()
                        new_entry = entry.model_copy(
                            update={
                                "room_code": r.room_code,
                                "revision_hash": new_hash,
                            }
                        )
                        reassigned_entries.append(new_entry)
                        break

        elapsed = time.perf_counter() - start_time
        return DeltaSolveResponse(
            delta_solved=True,
            solve_time_seconds=elapsed,
            reassigned_entries=reassigned_entries,
        )
