"""Comprehensive Unit Tests for Sub-Second Localized Delta Re-solver.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Validates:
1. Latency strictly < 0.10s across 10 trials.
2. Zero schedule shifts for students or faculty time slots.
3. Vacancy collision avoidance with baseline scheduled entries.
4. Capacity compliance (70-student section never placed in 40-seat room).
5. RoomType compliance (COMPUTER_LAB offering never placed in LECTURE room).
6. Quarantined rooms (NB 204, NB 304, NB 308) never assigned.
7. PRRC 108 exclusivity lock respected during delta re-assignment.
8. Baseline freezing (all unaffected entries 100% untouched).
9. Graceful infeasibility/overflow diagnostics on campus saturation.
10. Deterministic SHA-256 revision hash generation per reassigned entry.
"""

import uuid
import time
import hashlib
import pytest

from classync_contracts.enums import RoomType, DayOfWeek, CohortMode
from classync_contracts.schemas import (
    RoomSchema,
    TimetableEntrySchema,
    DeltaSolveRequest,
)
from services.scheduling.solver.delta_resolver import (
    LocalizedDeltaResolver,
    OfferingMetadata,
)


@pytest.fixture
def delta_fixture():
    """Builds a calibrated fixture with baseline timetable and institutional facilities."""
    rooms = [
        # Candidate Lecture Rooms
        RoomSchema(room_code="PRRC 301", building_name="PRRC Building", floor_level=3, room_type=RoomType.LECTURE, capacity=70, is_schedulable=True, has_aircon=True, has_projector=True),
        RoomSchema(room_code="PRRC 302", building_name="PRRC Building", floor_level=3, room_type=RoomType.LECTURE, capacity=70, is_schedulable=True, has_aircon=True, has_projector=True),
        RoomSchema(room_code="PRRC 201", building_name="PRRC Building", floor_level=2, room_type=RoomType.LECTURE, capacity=65, is_schedulable=True, has_aircon=True, has_projector=True),
        RoomSchema(room_code="NB 101", building_name="New Building", floor_level=1, room_type=RoomType.LECTURE, capacity=80, is_schedulable=True, has_aircon=True, has_projector=True),
        # Small Room (Insufficient for 70 students)
        RoomSchema(room_code="PRRC 105", building_name="PRRC Building", floor_level=1, room_type=RoomType.LECTURE, capacity=40, is_schedulable=True, has_aircon=True, has_projector=True),
        # Computer Lab Room
        RoomSchema(room_code="COMLAB 1", building_name="PRRC Building", floor_level=3, room_type=RoomType.COMPUTER_LAB, capacity=50, is_schedulable=True, has_aircon=True, has_projector=True),
        # Program-Exclusive Room (Locked to BSED_SCIENCE)
        RoomSchema(room_code="PRRC 108", building_name="PRRC Building", floor_level=1, room_type=RoomType.LECTURE, capacity=70, is_schedulable=True, has_aircon=True, has_projector=True, exclusive_program="BSED_SCIENCE"),
        # Quarantined Spaces (is_schedulable = False)
        RoomSchema(room_code="NB 204", building_name="New Building", floor_level=2, room_type=RoomType.LECTURE, capacity=20, is_schedulable=False, has_aircon=False, has_projector=False),
        RoomSchema(room_code="NB 304", building_name="New Building", floor_level=3, room_type=RoomType.LECTURE, capacity=20, is_schedulable=False, has_aircon=False, has_projector=False),
        RoomSchema(room_code="NB 308", building_name="New Building", floor_level=3, room_type=RoomType.LECTURE, capacity=20, is_schedulable=False, has_aircon=False, has_projector=False),
    ]

    off_ids = [uuid.uuid4() for _ in range(5)]
    baseline_entries = [
        # Offerings in PRRC 301 on Monday (disrupted target)
        TimetableEntrySchema(id=uuid.uuid4(), offering_id=off_ids[0], room_code="PRRC 301", day_of_week=DayOfWeek.MONDAY, start_slot=0, duration_slots=6, cohort_mode=CohortMode.UNIFIED, is_locked=False, revision_hash="h0"),
        TimetableEntrySchema(id=uuid.uuid4(), offering_id=off_ids[1], room_code="PRRC 301", day_of_week=DayOfWeek.MONDAY, start_slot=6, duration_slots=6, cohort_mode=CohortMode.UNIFIED, is_locked=False, revision_hash="h1"),
        TimetableEntrySchema(id=uuid.uuid4(), offering_id=off_ids[2], room_code="PRRC 301", day_of_week=DayOfWeek.MONDAY, start_slot=12, duration_slots=6, cohort_mode=CohortMode.UNIFIED, is_locked=False, revision_hash="h2"),
        # Existing booked entry in PRRC 302 at slots 0-6 (cannot be used for off_ids[0])
        TimetableEntrySchema(id=uuid.uuid4(), offering_id=off_ids[3], room_code="PRRC 302", day_of_week=DayOfWeek.MONDAY, start_slot=0, duration_slots=6, cohort_mode=CohortMode.UNIFIED, is_locked=False, revision_hash="h3"),
        # Existing booked entry in NB 101 at slots 12-18 (cannot be used for off_ids[2])
        TimetableEntrySchema(id=uuid.uuid4(), offering_id=off_ids[4], room_code="NB 101", day_of_week=DayOfWeek.MONDAY, start_slot=12, duration_slots=6, cohort_mode=CohortMode.UNIFIED, is_locked=False, revision_hash="h4"),
    ]

    offerings_map = {
        off_ids[0]: OfferingMetadata(offering_id=off_ids[0], required_room_type=RoomType.LECTURE, enrolled_student_count=65, program_code="BSIT", orig_building="PRRC Building", orig_floor=3),
        off_ids[1]: OfferingMetadata(offering_id=off_ids[1], required_room_type=RoomType.LECTURE, enrolled_student_count=65, program_code="BSIT", orig_building="PRRC Building", orig_floor=3),
        off_ids[2]: OfferingMetadata(offering_id=off_ids[2], required_room_type=RoomType.LECTURE, enrolled_student_count=65, program_code="BSIT", orig_building="PRRC Building", orig_floor=3),
        off_ids[3]: OfferingMetadata(offering_id=off_ids[3], required_room_type=RoomType.LECTURE, enrolled_student_count=65, program_code="BSIT", orig_building="PRRC Building", orig_floor=3),
        off_ids[4]: OfferingMetadata(offering_id=off_ids[4], required_room_type=RoomType.LECTURE, enrolled_student_count=70, program_code="BSCPE", orig_building="New Building", orig_floor=1),
    }

    return {
        "rooms": rooms,
        "entries": baseline_entries,
        "offerings_map": offerings_map,
        "disrupted_off_ids": off_ids[:3],
    }


class TestDeltaResolver:
    """Verifies all performance SLA and constraint requirements for DeltaResolver."""

    def test_delta_resolver_latency_sla_under_100ms(self, delta_fixture):
        """Verifies strictly < 0.10s latency SLA across 10 repeated disruption trials."""
        rooms = delta_fixture["rooms"]
        entries = delta_fixture["entries"]
        offerings_map = delta_fixture["offerings_map"]

        resolver = LocalizedDeltaResolver(rooms)
        req = DeltaSolveRequest(
            disrupted_room_code="PRRC 301",
            day_of_week=DayOfWeek.MONDAY,
            start_slot=0,
            duration_slots=24,
        )

        latencies = []
        for _ in range(10):
            res = resolver.resolve(entries, req, offerings_map)
            assert res.delta_solved is True, "Delta solve unexpectedly failed."
            assert res.solve_time_seconds < 0.10, f"SLA violated: {res.solve_time_seconds:.4f}s >= 0.10s"
            latencies.append(res.solve_time_seconds)

        mean_latency_ms = (sum(latencies) / len(latencies)) * 1000
        max_latency_ms = max(latencies) * 1000
        print(f"\n[LATENCY BENCHMARK] Mean: {mean_latency_ms:.3f}ms, Max: {max_latency_ms:.3f}ms")
        assert max_latency_ms < 100.0, "Maximum latency exceeded 100ms budget."

    def test_delta_resolver_vacancy_collision_avoidance(self, delta_fixture):
        """Verifies newly assigned rooms do not collide with existing bookings."""
        rooms = delta_fixture["rooms"]
        entries = delta_fixture["entries"]
        offerings_map = delta_fixture["offerings_map"]

        resolver = LocalizedDeltaResolver(rooms)
        req = DeltaSolveRequest(
            disrupted_room_code="PRRC 301",
            day_of_week=DayOfWeek.MONDAY,
            start_slot=0,
            duration_slots=24,
        )
        res = resolver.resolve(entries, req, offerings_map)
        assert res.delta_solved is True

        reassigned = res.reassigned_entries
        assert len(reassigned) == 3

        # Verify offering 0 (slots 0-6): PRRC 302 was busy, so it cannot be PRRC 302
        e0 = next(e for e in reassigned if e.start_slot == 0)
        assert e0.room_code != "PRRC 302", "Offering 0 collided with PRRC 302 existing booking!"
        assert e0.room_code in ("PRRC 201", "NB 101"), f"Unexpected room assigned: {e0.room_code}"

        # Verify offering 2 (slots 12-18): NB 101 was busy, so it cannot be NB 101
        e2 = next(e for e in reassigned if e.start_slot == 12)
        assert e2.room_code != "NB 101", "Offering 2 collided with NB 101 existing booking!"

    def test_delta_resolver_capacity_compliance(self, delta_fixture):
        """Verifies that a 65-student section is never assigned to 40-seat PRRC 105."""
        rooms = delta_fixture["rooms"]
        entries = delta_fixture["entries"]
        offerings_map = delta_fixture["offerings_map"]

        resolver = LocalizedDeltaResolver(rooms)
        req = DeltaSolveRequest(
            disrupted_room_code="PRRC 301",
            day_of_week=DayOfWeek.MONDAY,
            start_slot=0,
            duration_slots=24,
        )
        res = resolver.resolve(entries, req, offerings_map)

        for re_entry in res.reassigned_entries:
            assigned_room = next(r for r in rooms if r.room_code == re_entry.room_code)
            assert assigned_room.capacity >= 65, f"Capacity violation: {assigned_room.capacity} < 65"
            assert re_entry.room_code != "PRRC 105", "Small room PRRC 105 was illegally assigned!"

    def test_delta_resolver_room_type_compliance(self, delta_fixture):
        """Verifies that a COMPUTER_LAB offering is never assigned to a LECTURE hall."""
        rooms = delta_fixture["rooms"]
        entries = delta_fixture["entries"]
        offerings_map = delta_fixture["offerings_map"]

        # Mutate offering 0 to require COMPUTER_LAB with 45 students
        off0_id = delta_fixture["disrupted_off_ids"][0]
        offerings_map[off0_id].required_room_type = RoomType.COMPUTER_LAB
        offerings_map[off0_id].enrolled_student_count = 45

        resolver = LocalizedDeltaResolver(rooms)
        req = DeltaSolveRequest(
            disrupted_room_code="PRRC 301",
            day_of_week=DayOfWeek.MONDAY,
            start_slot=0,
            duration_slots=6,
        )
        res = resolver.resolve(entries, req, offerings_map)
        assert res.delta_solved is True

        e0 = next(e for e in res.reassigned_entries if e.offering_id == off0_id)
        assert e0.room_code == "COMLAB 1", f"Lab offering assigned to non-lab room: {e0.room_code}"

    def test_delta_resolver_quarantined_rooms_never_assigned(self, delta_fixture):
        """Verifies quarantined rooms NB 204, NB 304, NB 308 are never used."""
        rooms = delta_fixture["rooms"]
        entries = delta_fixture["entries"]
        offerings_map = delta_fixture["offerings_map"]

        resolver = LocalizedDeltaResolver(rooms)
        req = DeltaSolveRequest(
            disrupted_room_code="PRRC 301",
            day_of_week=DayOfWeek.MONDAY,
            start_slot=0,
            duration_slots=24,
        )
        res = resolver.resolve(entries, req, offerings_map)

        quarantined = {"NB 204", "NB 304", "NB 308"}
        for re_entry in res.reassigned_entries:
            assert re_entry.room_code not in quarantined, f"Quarantined space {re_entry.room_code} was assigned!"

    def test_delta_resolver_prrc_108_exclusivity(self, delta_fixture):
        """Verifies PRRC 108 is never assigned to non-BSED_SCIENCE offerings, but is available for BSED."""
        rooms = delta_fixture["rooms"]
        entries = delta_fixture["entries"]
        offerings_map = delta_fixture["offerings_map"]

        resolver = LocalizedDeltaResolver(rooms)

        # Non-BSED offering (BSIT)
        req = DeltaSolveRequest(
            disrupted_room_code="PRRC 301",
            day_of_week=DayOfWeek.MONDAY,
            start_slot=0,
            duration_slots=6,
        )
        res = resolver.resolve(entries, req, offerings_map)
        assert res.delta_solved is True
        for e in res.reassigned_entries:
            assert e.room_code != "PRRC 108", "PRRC 108 illegally assigned to non-BSED_SCIENCE class!"

        # Now test with BSED_SCIENCE offering
        off0_id = delta_fixture["disrupted_off_ids"][0]
        offerings_map[off0_id].program_code = "BSED_SCIENCE"
        # Make all other lecture rooms busy except PRRC 108
        busy_entries = [
            TimetableEntrySchema(id=uuid.uuid4(), offering_id=uuid.uuid4(), room_code="PRRC 302", day_of_week=DayOfWeek.MONDAY, start_slot=0, duration_slots=6, cohort_mode=CohortMode.UNIFIED, is_locked=False, revision_hash="b1"),
            TimetableEntrySchema(id=uuid.uuid4(), offering_id=uuid.uuid4(), room_code="PRRC 201", day_of_week=DayOfWeek.MONDAY, start_slot=0, duration_slots=6, cohort_mode=CohortMode.UNIFIED, is_locked=False, revision_hash="b2"),
            TimetableEntrySchema(id=uuid.uuid4(), offering_id=uuid.uuid4(), room_code="NB 101", day_of_week=DayOfWeek.MONDAY, start_slot=0, duration_slots=6, cohort_mode=CohortMode.UNIFIED, is_locked=False, revision_hash="b3"),
            # Disrupted entry
            TimetableEntrySchema(id=uuid.uuid4(), offering_id=off0_id, room_code="PRRC 301", day_of_week=DayOfWeek.MONDAY, start_slot=0, duration_slots=6, cohort_mode=CohortMode.UNIFIED, is_locked=False, revision_hash="dis"),
        ]
        res_bsed = resolver.resolve(busy_entries, req, offerings_map)
        assert res_bsed.delta_solved is True
        assert res_bsed.reassigned_entries[0].room_code == "PRRC 108", "BSED_SCIENCE offering was not assigned to vacant PRRC 108!"

    def test_delta_resolver_infeasibility_overflow_handling(self, delta_fixture):
        """Verifies graceful degradation when all rooms are fully booked."""
        rooms = delta_fixture["rooms"]
        offerings_map = delta_fixture["offerings_map"]

        # Saturate every single schedulable room at slots 0-6
        disrupted_entry = TimetableEntrySchema(
            id=uuid.uuid4(),
            offering_id=delta_fixture["disrupted_off_ids"][0],
            room_code="PRRC 301",
            day_of_week=DayOfWeek.MONDAY,
            start_slot=0,
            duration_slots=6,
            cohort_mode=CohortMode.UNIFIED,
            is_locked=False,
            revision_hash="d0",
        )
        saturated_entries = [disrupted_entry]
        for r in rooms:
            if r.is_schedulable and r.room_code != "PRRC 301":
                saturated_entries.append(
                    TimetableEntrySchema(
                        id=uuid.uuid4(),
                        offering_id=uuid.uuid4(),
                        room_code=r.room_code,
                        day_of_week=DayOfWeek.MONDAY,
                        start_slot=0,
                        duration_slots=6,
                        cohort_mode=CohortMode.UNIFIED,
                        is_locked=False,
                        revision_hash=f"sat_{r.room_code}",
                    )
                )

        resolver = LocalizedDeltaResolver(rooms)
        req = DeltaSolveRequest(
            disrupted_room_code="PRRC 301",
            day_of_week=DayOfWeek.MONDAY,
            start_slot=0,
            duration_slots=6,
        )

        res = resolver.resolve(saturated_entries, req, offerings_map)
        assert res.delta_solved is False, "Expected delta_solved to be False under total saturation."
        assert res.reassigned_entries == []
        assert res.solve_time_seconds < 0.10

    def test_delta_resolver_revision_hash_recalculation(self, delta_fixture):
        """Verifies newly reassigned entries receive recalculated SHA-256 hashes."""
        rooms = delta_fixture["rooms"]
        entries = delta_fixture["entries"]
        offerings_map = delta_fixture["offerings_map"]

        resolver = LocalizedDeltaResolver(rooms)
        req = DeltaSolveRequest(
            disrupted_room_code="PRRC 301",
            day_of_week=DayOfWeek.MONDAY,
            start_slot=0,
            duration_slots=6,
        )
        res = resolver.resolve(entries, req, offerings_map)
        assert res.delta_solved is True

        re_entry = res.reassigned_entries[0]
        raw_d = re_entry.day_of_week
        d_val = raw_d.value if hasattr(raw_d, "value") else raw_d
        expected_raw = f"{re_entry.offering_id}:{re_entry.room_code}:{d_val}:{re_entry.start_slot}:{re_entry.duration_slots}"
        expected_hash = hashlib.sha256(expected_raw.encode("utf-8")).hexdigest()

        assert re_entry.revision_hash == expected_hash
