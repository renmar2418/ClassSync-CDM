"""Objective Weights & Soft Constraint Penalties for ClassSync CP-SAT Solver.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Implements mathematical penalty terms per SYSTEM_DESIGN_BLUEPRINT.md:
- W_lunch = 100: continuous 60-min (2 slots) lunch break between 11:00 and 14:00 (slots 8-13)
- W_gap = 50: minimizing idle gap slots between scheduled classes for each section
- W_compact = 20: minimizing daily span (max end - min start) for full-time faculty
- W_room_stability = 10: consecutive classes of a section in the same room
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional
import uuid

from ortools.sat.python import cp_model


@dataclass(frozen=True)
class SolverObjectiveWeights:
    """Configurable penalty weights for soft constraints."""
    w_lunch: int = 100
    w_gap: int = 50
    w_compact: int = 20
    w_room_stability: int = 10


def add_lunch_break_penalty(
    model: cp_model.CpModel,
    sections: List[Any],
    section_intervals: Dict[uuid.UUID, List[cp_model.IntervalVar]],
    w_lunch: int = 100,
) -> Tuple[List[cp_model.LinearExpr], Dict[Tuple[uuid.UUID, int], cp_model.BoolVar]]:
    """Enforces continuous 60-minute lunch break between 11:00 and 14:00 (slots 8-13).

    For each section and each day d in [0..5], creates an optional 2-slot interval in [8..14].
    Adds it to the section's non-overlap constraint. If classes occupy all slots,
    has_lunch is forced to 0, incurring w_lunch penalty.
    """
    penalties: List[cp_model.LinearExpr] = []
    has_lunch_map: Dict[Tuple[uuid.UUID, int], cp_model.BoolVar] = {}

    for sec in sections:
        sec_id = sec.id if hasattr(sec, "id") else sec["id"]
        for d in range(6):
            l_start = model.NewIntVar(d * 24 + 8, d * 24 + 12, f"l_start_{sec_id}_{d}")
            l_end = model.NewIntVar(d * 24 + 10, d * 24 + 14, f"l_end_{sec_id}_{d}")
            model.Add(l_end == l_start + 2)
            has_lunch = model.NewBoolVar(f"has_lunch_{sec_id}_{d}")
            l_inv = model.NewOptionalIntervalVar(l_start, 2, l_end, has_lunch, f"l_inv_{sec_id}_{d}")

            # Section intervals must not overlap with lunch
            existing = section_intervals.get(sec_id, [])
            model.AddNoOverlap(existing + [l_inv])

            has_lunch_map[(sec_id, d)] = has_lunch
            penalties.append(w_lunch * (1 - has_lunch))

    return penalties, has_lunch_map


def add_section_idle_gap_penalty(
    model: cp_model.CpModel,
    offerings: List[Any],
    d_vars: Dict[uuid.UUID, cp_model.IntVar],
    start_vars: Dict[uuid.UUID, cp_model.IntVar],
    end_vars: Dict[uuid.UUID, cp_model.IntVar],
    has_lunch_map: Optional[Dict[Tuple[uuid.UUID, int], cp_model.BoolVar]] = None,
    w_gap: int = 50,
) -> List[cp_model.LinearExpr]:
    """Minimizes idle gaps between scheduled classes for each section on each day."""
    penalties: List[cp_model.LinearExpr] = []

    # Group offerings by section
    sec_offerings: Dict[uuid.UUID, List[Any]] = {}
    for o in offerings:
        sec_id = o.section_id if hasattr(o, "section_id") else o["section_id"]
        sec_offerings.setdefault(sec_id, []).append(o)

    for sec_id, off_list in sec_offerings.items():
        if len(off_list) <= 1:
            continue
        for d in range(6):
            on_day_vars = []
            for o in off_list:
                oid = o.id if hasattr(o, "id") else o["id"]
                b = model.NewBoolVar(f"sec_on_{sec_id}_{oid}_{d}")
                model.Add(d_vars[oid] == d).OnlyEnforceIf(b)
                model.Add(d_vars[oid] != d).OnlyEnforceIf(b.Not())
                on_day_vars.append((o, b))

            day_active = model.NewBoolVar(f"sec_day_active_{sec_id}_{d}")
            model.AddBoolOr([b for _, b in on_day_vars]).OnlyEnforceIf(day_active)
            model.AddBoolAnd([b.Not() for _, b in on_day_vars]).OnlyEnforceIf(day_active.Not())

            span = model.NewIntVar(0, 24, f"sec_span_{sec_id}_{d}")
            model.Add(span == 0).OnlyEnforceIf(day_active.Not())

            for o, b in on_day_vars:
                dur = o.duration_slots if hasattr(o, "duration_slots") else o["duration_slots"]
                model.Add(span >= dur).OnlyEnforceIf(b)

            for i in range(len(on_day_vars)):
                for j in range(i + 1, len(on_day_vars)):
                    o1, b1 = on_day_vars[i]
                    o2, b2 = on_day_vars[j]
                    oid1 = o1.id if hasattr(o1, "id") else o1["id"]
                    oid2 = o2.id if hasattr(o2, "id") else o2["id"]
                    model.Add(span >= end_vars[oid1] - start_vars[oid2]).OnlyEnforceIf([b1, b2])
                    model.Add(span >= end_vars[oid2] - start_vars[oid1]).OnlyEnforceIf([b1, b2])

            active_slots = sum(
                (o.duration_slots if hasattr(o, "duration_slots") else o["duration_slots"]) * b
                for o, b in on_day_vars
            )
            raw_gap = model.NewIntVar(0, 24, f"raw_gap_{sec_id}_{d}")
            model.Add(raw_gap == span - active_slots)

            net_gap = model.NewIntVar(0, 24, f"net_gap_{sec_id}_{d}")
            if has_lunch_map and (sec_id, d) in has_lunch_map:
                hl = has_lunch_map[(sec_id, d)]
                model.Add(net_gap >= raw_gap - 2 * hl)
            else:
                model.Add(net_gap >= raw_gap)
            model.Add(net_gap >= 0)

            penalties.append(w_gap * net_gap)

    return penalties


def add_faculty_compactness_penalty(
    model: cp_model.CpModel,
    offerings: List[Any],
    d_vars: Dict[uuid.UUID, cp_model.IntVar],
    start_vars: Dict[uuid.UUID, cp_model.IntVar],
    end_vars: Dict[uuid.UUID, cp_model.IntVar],
    w_compact: int = 20,
) -> List[cp_model.LinearExpr]:
    """Minimizes daily teaching span for full-time faculty across Mon-Sat."""
    penalties: List[cp_model.LinearExpr] = []

    fac_offerings: Dict[uuid.UUID, List[Any]] = {}
    for o in offerings:
        fid = o.faculty_id if hasattr(o, "faculty_id") else o["faculty_id"]
        fac_offerings.setdefault(fid, []).append(o)

    for fid, off_list in fac_offerings.items():
        if len(off_list) <= 1:
            continue
        for d in range(6):
            on_day_vars = []
            for o in off_list:
                oid = o.id if hasattr(o, "id") else o["id"]
                b = model.NewBoolVar(f"fac_on_{fid}_{oid}_{d}")
                model.Add(d_vars[oid] == d).OnlyEnforceIf(b)
                model.Add(d_vars[oid] != d).OnlyEnforceIf(b.Not())
                on_day_vars.append((o, b))

            day_active = model.NewBoolVar(f"fac_day_active_{fid}_{d}")
            model.AddBoolOr([b for _, b in on_day_vars]).OnlyEnforceIf(day_active)
            model.AddBoolAnd([b.Not() for _, b in on_day_vars]).OnlyEnforceIf(day_active.Not())

            span = model.NewIntVar(0, 24, f"fac_span_{fid}_{d}")
            model.Add(span == 0).OnlyEnforceIf(day_active.Not())

            for o, b in on_day_vars:
                dur = o.duration_slots if hasattr(o, "duration_slots") else o["duration_slots"]
                model.Add(span >= dur).OnlyEnforceIf(b)

            for i in range(len(on_day_vars)):
                for j in range(i + 1, len(on_day_vars)):
                    o1, b1 = on_day_vars[i]
                    o2, b2 = on_day_vars[j]
                    oid1 = o1.id if hasattr(o1, "id") else o1["id"]
                    oid2 = o2.id if hasattr(o2, "id") else o2["id"]
                    model.Add(span >= end_vars[oid1] - start_vars[oid2]).OnlyEnforceIf([b1, b2])
                    model.Add(span >= end_vars[oid2] - start_vars[oid1]).OnlyEnforceIf([b1, b2])

            penalties.append(w_compact * span)

    return penalties


def add_room_stability_penalty(
    model: cp_model.CpModel,
    offerings: List[Any],
    start_vars: Dict[uuid.UUID, cp_model.IntVar],
    end_vars: Dict[uuid.UUID, cp_model.IntVar],
    x_vars: Dict[Tuple[uuid.UUID, str], cp_model.BoolVar],
    candidate_rooms: Dict[uuid.UUID, List[str]],
    w_room_stability: int = 10,
) -> List[cp_model.LinearExpr]:
    """Penalizes room changes for consecutive classes belonging to the same section."""
    penalties: List[cp_model.LinearExpr] = []

    sec_offerings: Dict[uuid.UUID, List[Any]] = {}
    for o in offerings:
        sec_id = o.section_id if hasattr(o, "section_id") else o["section_id"]
        sec_offerings.setdefault(sec_id, []).append(o)

    for sec_id, off_list in sec_offerings.items():
        if len(off_list) <= 1:
            continue
        for i in range(len(off_list)):
            for j in range(i + 1, len(off_list)):
                o1 = off_list[i]
                o2 = off_list[j]
                oid1 = o1.id if hasattr(o1, "id") else o1["id"]
                oid2 = o2.id if hasattr(o2, "id") else o2["id"]

                common_rooms = set(candidate_rooms.get(oid1, [])) & set(candidate_rooms.get(oid2, []))
                if not common_rooms:
                    continue

                c12 = model.NewBoolVar(f"c12_{oid1}_{oid2}")
                model.Add(start_vars[oid2] == end_vars[oid1]).OnlyEnforceIf(c12)
                model.Add(start_vars[oid2] != end_vars[oid1]).OnlyEnforceIf(c12.Not())

                c21 = model.NewBoolVar(f"c21_{oid1}_{oid2}")
                model.Add(start_vars[oid1] == end_vars[oid2]).OnlyEnforceIf(c21)
                model.Add(start_vars[oid1] != end_vars[oid2]).OnlyEnforceIf(c21.Not())

                is_consec = model.NewBoolVar(f"consec_{oid1}_{oid2}")
                model.AddBoolOr([c12, c21]).OnlyEnforceIf(is_consec)
                model.AddBoolAnd([c12.Not(), c21.Not()]).OnlyEnforceIf(is_consec.Not())

                same_room_terms = []
                for rcode in common_rooms:
                    b_r = model.NewBoolVar(f"same_r_{oid1}_{oid2}_{rcode}")
                    model.AddBoolAnd([x_vars[oid1, rcode], x_vars[oid2, rcode]]).OnlyEnforceIf(b_r)
                    model.AddBoolOr([x_vars[oid1, rcode].Not(), x_vars[oid2, rcode].Not()]).OnlyEnforceIf(b_r.Not())
                    same_room_terms.append(b_r)

                same_room = model.NewBoolVar(f"same_room_{oid1}_{oid2}")
                model.AddBoolOr(same_room_terms).OnlyEnforceIf(same_room)
                model.AddBoolAnd([b.Not() for b in same_room_terms]).OnlyEnforceIf(same_room.Not())

                room_change = model.NewBoolVar(f"room_change_{oid1}_{oid2}")
                model.AddBoolAnd([is_consec, same_room.Not()]).OnlyEnforceIf(room_change)
                model.AddBoolOr([is_consec.Not(), same_room]).OnlyEnforceIf(room_change.Not())

                penalties.append(w_room_stability * room_change)

    return penalties


def add_all_objective_weights(
    model: cp_model.CpModel,
    offerings: List[Any],
    sections: List[Any],
    d_vars: Dict[uuid.UUID, cp_model.IntVar],
    start_vars: Dict[uuid.UUID, cp_model.IntVar],
    end_vars: Dict[uuid.UUID, cp_model.IntVar],
    section_intervals: Dict[uuid.UUID, List[cp_model.IntervalVar]],
    x_vars: Dict[Tuple[uuid.UUID, str], cp_model.BoolVar],
    candidate_rooms: Dict[uuid.UUID, List[str]],
    weights: Optional[SolverObjectiveWeights] = None,
) -> Optional[cp_model.LinearExpr]:
    """Combines all 4 objective components and attaches minimization to model."""
    w = weights or SolverObjectiveWeights()
    all_penalties: List[cp_model.LinearExpr] = []

    # 1. Lunch penalty (W=100)
    lunch_penalties, has_lunch_map = add_lunch_break_penalty(
        model, sections, section_intervals, w_lunch=w.w_lunch
    )
    all_penalties.extend(lunch_penalties)

    # 2. Section idle gaps (W=50)
    gap_penalties = add_section_idle_gap_penalty(
        model, offerings, d_vars, start_vars, end_vars, has_lunch_map, w_gap=w.w_gap
    )
    all_penalties.extend(gap_penalties)

    # 3. Faculty compactness (W=20)
    compact_penalties = add_faculty_compactness_penalty(
        model, offerings, d_vars, start_vars, end_vars, w_compact=w.w_compact
    )
    all_penalties.extend(compact_penalties)

    # 4. Room stability (W=10)
    stability_penalties = add_room_stability_penalty(
        model, offerings, start_vars, end_vars, x_vars, candidate_rooms, w_room_stability=w.w_room_stability
    )
    all_penalties.extend(stability_penalties)

    if all_penalties:
        total_objective = sum(all_penalties)
        model.Minimize(total_objective)
        return total_objective
    return None
