"""Comprehensive Phase 2 Test Suite: Google OR-Tools CP-SAT Solver Calibration.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Validates:
1. Zero room double-booking.
2. Zero faculty clash (100% full-time faculty).
3. Zero section clash (unified 60-70+ student cohorts).
4. Continuous 30-min slot day boundary adherence (0-23, finishing by 19:00).
5. Quarantined rooms (NB 204, NB 304, NB 308, canteen, property office) strictly excluded.
6. PRRC 108 exclusivity lock dedicated to BSED_SCIENCE.
7. Sunday Function Hall rigid partition: ROTC (07:00-12:00), NSTP (13:00-17:00), buffer (12:00-13:00) empty.
8. Sunday PATHFIT restricted to Athletic Oval / Sports Grounds.
9. Standard curriculum ban on Sunday.
10. Lunch hour soft penalty gap optimization (slots 8-13).
11. Independent Conflict Auditor SHA-256 verification and collision detection.
"""

import uuid
import pytest
from datetime import datetime, timezone

from classync_contracts.enums import (
    RoomType,
    DayOfWeek,
    CohortMode,
    EmploymentTier,
    UserRole,
    SolverStatus,
)
from classync_contracts.schemas import (
    AcademicPeriodSchema,
    RoomSchema,
    CurriculumSubjectSchema,
    FacultyProfileSchema,
    SectionSchema,
    CourseOfferingDetail,
    TimetableEntrySchema,
)
from services.scheduling.solver.model_builder import MasterCPSATSolver, CPSATMasterModelBuilder
from services.scheduling.solver.conflict_auditor import ConflictAuditor, CollisionCategory


@pytest.fixture
def phase2_synthetic_dataset():
    """Generates a complete, realistic CdM institutional scheduling dataset."""
    period = AcademicPeriodSchema(
        id=uuid.uuid4(),
        academic_year="2026-2027",
        semester=1,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    # Physical room inventory
    rooms = [
        # Schedulable Lecture Halls
        RoomSchema(room_code="PRRC 201", building_name="PRRC Building", floor_level=2, room_type=RoomType.LECTURE, capacity=75, is_schedulable=True, has_aircon=True, has_projector=True),
        RoomSchema(room_code="PRRC 202", building_name="PRRC Building", floor_level=2, room_type=RoomType.LECTURE, capacity=75, is_schedulable=True, has_aircon=True, has_projector=True),
        RoomSchema(room_code="PRRC 301", building_name="PRRC Building", floor_level=3, room_type=RoomType.LECTURE, capacity=70, is_schedulable=True, has_aircon=True, has_projector=True),
        RoomSchema(room_code="NB 101", building_name="New Building", floor_level=1, room_type=RoomType.LECTURE, capacity=80, is_schedulable=True, has_aircon=True, has_projector=True),
        RoomSchema(room_code="NB 102", building_name="New Building", floor_level=1, room_type=RoomType.LECTURE, capacity=80, is_schedulable=True, has_aircon=True, has_projector=True),
        # Computer Laboratories
        RoomSchema(room_code="COMLAB 1", building_name="PRRC Building", floor_level=3, room_type=RoomType.COMPUTER_LAB, capacity=70, is_schedulable=True, has_aircon=True, has_projector=True),
        RoomSchema(room_code="COMLAB 2", building_name="PRRC Building", floor_level=3, room_type=RoomType.COMPUTER_LAB, capacity=70, is_schedulable=True, has_aircon=True, has_projector=True),
        # Program-Exclusive Space
        RoomSchema(room_code="PRRC 108", building_name="PRRC Building", floor_level=1, room_type=RoomType.LECTURE, capacity=70, is_schedulable=True, has_aircon=True, has_projector=True, exclusive_program="BSED_SCIENCE"),
        # Sunday Civic Facilities
        RoomSchema(room_code="FUNCTION_HALL", building_name="Main Assembly", floor_level=1, room_type=RoomType.FUNCTION_HALL, capacity=500, is_schedulable=True, has_aircon=True, has_projector=True),
        RoomSchema(room_code="ATHLETIC_OVAL", building_name="Open Grounds", floor_level=1, room_type=RoomType.LECTURE, capacity=1000, is_schedulable=True, has_aircon=False, has_projector=False),
        # Quarantined Administrative & Service Spaces
        RoomSchema(room_code="NB 204", building_name="New Building", floor_level=2, room_type=RoomType.LECTURE, capacity=15, is_schedulable=False, has_aircon=False, has_projector=False),
        RoomSchema(room_code="NB 304", building_name="New Building", floor_level=3, room_type=RoomType.LECTURE, capacity=15, is_schedulable=False, has_aircon=False, has_projector=False),
        RoomSchema(room_code="NB 308", building_name="New Building", floor_level=3, room_type=RoomType.LECTURE, capacity=20, is_schedulable=False, has_aircon=False, has_projector=False),
        RoomSchema(room_code="PROPERTY_OFFICE", building_name="Admin Annex", floor_level=1, room_type=RoomType.LECTURE, capacity=10, is_schedulable=False, has_aircon=False, has_projector=False),
        RoomSchema(room_code="CANTEEN", building_name="Student Center", floor_level=1, room_type=RoomType.LECTURE, capacity=100, is_schedulable=False, has_aircon=False, has_projector=False),
    ]

    # Full-time faculty (100% full-time, @pnm.edu.ph)
    fac_ids = [uuid.uuid4() for _ in range(6)]
    faculty = [
        FacultyProfileSchema(id=fac_ids[0], institutional_email="nmades@pnm.edu.ph", full_name="Nat Mades", employment_tier=EmploymentTier.FULL_TIME, role=UserRole.FACULTY, is_active=True, requires_password_change=False),
        FacultyProfileSchema(id=fac_ids[1], institutional_email="gdecastro@pnm.edu.ph", full_name="Gretchen De Castro", employment_tier=EmploymentTier.FULL_TIME, role=UserRole.FACULTY, is_active=True, requires_password_change=False),
        FacultyProfileSchema(id=fac_ids[2], institutional_email="elamadora@pnm.edu.ph", full_name="Evelyn Lamadora", employment_tier=EmploymentTier.FULL_TIME, role=UserRole.FACULTY, is_active=True, requires_password_change=False),
        FacultyProfileSchema(id=fac_ids[3], institutional_email="acaparas@pnm.edu.ph", full_name="Andrea Caparas", employment_tier=EmploymentTier.FULL_TIME, role=UserRole.FACULTY, is_active=True, requires_password_change=False),
        FacultyProfileSchema(id=fac_ids[4], institutional_email="jdelacruz@pnm.edu.ph", full_name="Juan Dela Cruz", employment_tier=EmploymentTier.FULL_TIME, role=UserRole.FACULTY, is_active=True, requires_password_change=False),
        FacultyProfileSchema(id=fac_ids[5], institutional_email="msantos@pnm.edu.ph", full_name="Maria Santos", employment_tier=EmploymentTier.FULL_TIME, role=UserRole.FACULTY, is_active=True, requires_password_change=False),
    ]

    # Unified student cohorts (60-70+ students)
    sec_ids = [uuid.uuid4() for _ in range(5)]
    sections = [
        SectionSchema(id=sec_ids[0], academic_period_id=period.id, section_code="BSIT-3A", year_level=3, enrolled_student_count=65),
        SectionSchema(id=sec_ids[1], academic_period_id=period.id, section_code="BSIT-3B", year_level=3, enrolled_student_count=65),
        SectionSchema(id=sec_ids[2], academic_period_id=period.id, section_code="BSED-SCI-1A", year_level=1, enrolled_student_count=60),
        SectionSchema(id=sec_ids[3], academic_period_id=period.id, section_code="BSED-SCI-2A", year_level=2, enrolled_student_count=62),
        SectionSchema(id=sec_ids[4], academic_period_id=period.id, section_code="BSCPE-2A", year_level=2, enrolled_student_count=70),
    ]

    # Curriculum subjects
    subj_ids = [uuid.uuid4() for _ in range(7)]
    subjects = [
        CurriculumSubjectSchema(id=subj_ids[0], subject_code="CC-IPT2", descriptive_title="Integrative Programming 2", lecture_hours=3, lab_hours=0, units=3, required_room_type=RoomType.LECTURE),
        CurriculumSubjectSchema(id=subj_ids[1], subject_code="IT-NETLAB", descriptive_title="Advanced Networking Lab", lecture_hours=0, lab_hours=3, units=1, required_room_type=RoomType.COMPUTER_LAB),
        CurriculumSubjectSchema(id=subj_ids[2], subject_code="BSED-BIO", descriptive_title="Biological Sciences", lecture_hours=3, lab_hours=0, units=3, required_room_type=RoomType.LECTURE),
        CurriculumSubjectSchema(id=subj_ids[3], subject_code="CS-ALG", descriptive_title="Design and Analysis of Algorithms", lecture_hours=3, lab_hours=0, units=3, required_room_type=RoomType.LECTURE),
        CurriculumSubjectSchema(id=subj_ids[4], subject_code="ROTC-1", descriptive_title="Civic Military Training", lecture_hours=5, lab_hours=0, units=3, required_room_type=RoomType.FUNCTION_HALL),
        CurriculumSubjectSchema(id=subj_ids[5], subject_code="NSTP-1", descriptive_title="National Service Training", lecture_hours=4, lab_hours=0, units=3, required_room_type=RoomType.FUNCTION_HALL),
        CurriculumSubjectSchema(id=subj_ids[6], subject_code="PATHFIT-1", descriptive_title="Physical Activity", lecture_hours=2, lab_hours=0, units=2, required_room_type=RoomType.LECTURE),
    ]

    # Course offerings
    offerings: List[CourseOfferingDetail] = [
        CourseOfferingDetail(id=uuid.uuid4(), academic_period_id=period.id, subject_id=subj_ids[0], section_id=sec_ids[0], faculty_id=fac_ids[0], subject=subjects[0], section=sections[0], faculty=faculty[0]),
        CourseOfferingDetail(id=uuid.uuid4(), academic_period_id=period.id, subject_id=subj_ids[1], section_id=sec_ids[0], faculty_id=fac_ids[1], subject=subjects[1], section=sections[0], faculty=faculty[1]),
        CourseOfferingDetail(id=uuid.uuid4(), academic_period_id=period.id, subject_id=subj_ids[3], section_id=sec_ids[1], faculty_id=fac_ids[0], subject=subjects[3], section=sections[1], faculty=faculty[0]),
        CourseOfferingDetail(id=uuid.uuid4(), academic_period_id=period.id, subject_id=subj_ids[2], section_id=sec_ids[2], faculty_id=fac_ids[4], subject=subjects[2], section=sections[2], faculty=faculty[4]),
        CourseOfferingDetail(id=uuid.uuid4(), academic_period_id=period.id, subject_id=subj_ids[2], section_id=sec_ids[3], faculty_id=fac_ids[5], subject=subjects[2], section=sections[3], faculty=faculty[5]),
        # Sunday Civic offerings
        CourseOfferingDetail(id=uuid.uuid4(), academic_period_id=period.id, subject_id=subj_ids[4], section_id=sec_ids[0], faculty_id=fac_ids[2], subject=subjects[4], section=sections[0], faculty=faculty[2]),
        CourseOfferingDetail(id=uuid.uuid4(), academic_period_id=period.id, subject_id=subj_ids[5], section_id=sec_ids[1], faculty_id=fac_ids[3], subject=subjects[5], section=sections[1], faculty=faculty[3]),
        CourseOfferingDetail(id=uuid.uuid4(), academic_period_id=period.id, subject_id=subj_ids[6], section_id=sec_ids[4], faculty_id=fac_ids[3], subject=subjects[6], section=sections[4], faculty=faculty[3]),
    ]

    return {
        "period": period,
        "rooms": rooms,
        "faculty": faculty,
        "sections": sections,
        "subjects": subjects,
        "offerings": offerings,
    }


class TestPhase2MasterSolver:
    """Verifies that the Master CP-SAT Model satisfies all institutional constraints."""

    def test_master_solver_hard_constraints_and_audit(self, phase2_synthetic_dataset):
        data = phase2_synthetic_dataset
        solver = MasterCPSATSolver(
            rooms=data["rooms"],
            offerings=data["offerings"],
            time_limit_seconds=60,
        )
        response = solver.solve()

        # Gate 1: Solver Feasibility
        assert response.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE), "CP-SAT failed to find a valid solution."
        assert len(response.timetable_entries) > 0, "No timetable entries produced."

        entries = response.timetable_entries

        # Gate 2: Room Non-Overlap
        room_day_map = {}
        for e in entries:
            raw_d = e.day_of_week
            day_int = int(raw_d.value if hasattr(raw_d, "value") else raw_d)
            key = (e.room_code, day_int)
            room_day_map.setdefault(key, []).append(e)

        for (r_code, day), day_entries in room_day_map.items():
            for i in range(len(day_entries)):
                for j in range(i + 1, len(day_entries)):
                    e1, e2 = day_entries[i], day_entries[j]
                    assert max(e1.start_slot, e2.start_slot) >= min(
                        e1.start_slot + e1.duration_slots, e2.start_slot + e2.duration_slots
                    ), f"Double-booking collision detected in room {r_code} on day {day}: {e1.id} vs {e2.id}"

        # Gate 3: Quarantined Room Exclusion (D-05)
        quarantined = {"NB 204", "NB 304", "NB 308", "PROPERTY_OFFICE", "CANTEEN", "CAMPUS_CANTEEN"}
        for e in entries:
            assert e.room_code not in quarantined, f"Quarantined room {e.room_code} was scheduled!"

        # Gate 4: PRRC 108 Exclusivity Lock (BSED_SCIENCE only)
        off_map = {o.id: o for o in data["offerings"]}
        for e in entries:
            if e.room_code == "PRRC 108":
                off = off_map[e.offering_id]
                sec_code = off.section.section_code
                assert "BSED" in sec_code, f"Non-BSED offering {sec_code} scheduled in PRRC 108!"

        # Gate 5: Sunday Civic Space Partition (D-06)
        sunday_entries = [e for e in entries if int(e.day_of_week.value if hasattr(e.day_of_week, "value") else e.day_of_week) == DayOfWeek.SUNDAY.value]
        for e in sunday_entries:
            off = off_map[e.offering_id]
            if off.subject.subject_code == "ROTC-1":
                assert e.room_code == "FUNCTION_HALL"
                assert e.start_slot == 0 and e.duration_slots == 10, "ROTC must be 07:00-12:00 (slots 0-9)"
            elif off.subject.subject_code == "NSTP-1":
                assert e.room_code == "FUNCTION_HALL"
                assert e.start_slot == 12 and e.duration_slots == 8, "NSTP must be 13:00-17:00 (slots 12-19)"
            elif off.subject.subject_code == "PATHFIT-1":
                assert e.room_code in ("ATHLETIC_OVAL", "MONTALBAN_SPORTS_COMPLEX", "OPEN_GROUNDS"), "PATHFIT must be on outdoor athletic oval"
            else:
                pytest.fail(f"Standard academic subject {off.subject.subject_code} scheduled on Sunday!")

        # Gate 6: Function Hall Buffer Vacancy (12:00-13:00, slots 10-11)
        fh_sunday = [
            e for e in sunday_entries if e.room_code == "FUNCTION_HALL"
        ]
        for e in fh_sunday:
            # Overlaps with turnover buffer [10, 12)?
            assert max(e.start_slot, 10) >= min(e.start_slot + e.duration_slots, 12), \
                "Function Hall 12:00-13:00 turnover buffer violated!"

        # Gate 7: Independent Conflict Auditor Verification
        auditor = ConflictAuditor(rooms=data["rooms"], offerings=data["offerings"])
        audit_report = auditor.audit(entries)
        assert audit_report.has_conflict is False, f"Auditor found conflicts: {audit_report.details}"
        assert audit_report.room_collisions == 0
        assert audit_report.faculty_collisions == 0
        assert audit_report.section_collisions == 0
        assert audit_report.revision_hash is not None and len(audit_report.revision_hash) == 64, "Auditor did not emit 64-char SHA-256 hash"

    def test_conflict_auditor_negative_detections(self, phase2_synthetic_dataset):
        """Verifies that the ConflictAuditor catches every category of constraint violation."""
        data = phase2_synthetic_dataset
        auditor = ConflictAuditor(rooms=data["rooms"], offerings=data["offerings"])

        off_ids = [o.id for o in data["offerings"]]

        # Negative test 1: Room double-booking
        colliding_entries = [
            TimetableEntrySchema(
                id=uuid.uuid4(),
                offering_id=off_ids[0],
                room_code="PRRC 201",
                day_of_week=DayOfWeek.MONDAY,
                start_slot=0,
                duration_slots=6,
                cohort_mode=CohortMode.UNIFIED,
            ),
            TimetableEntrySchema(
                id=uuid.uuid4(),
                offering_id=off_ids[1],
                room_code="PRRC 201",
                day_of_week=DayOfWeek.MONDAY,
                start_slot=4,  # Overlaps 4-10 with 0-6
                duration_slots=6,
                cohort_mode=CohortMode.UNIFIED,
            ),
        ]
        report = auditor.audit(colliding_entries)
        assert report.has_conflict is True
        assert report.room_collisions >= 1
        assert any(r.category == CollisionCategory.ROOM_DOUBLE_BOOKING for r in report.collision_records)

        # Negative test 2: Quarantined room leak
        quarantine_leak_entry = [
            TimetableEntrySchema(
                id=uuid.uuid4(),
                offering_id=off_ids[0],
                room_code="NB 204",  # Quarantined!
                day_of_week=DayOfWeek.MONDAY,
                start_slot=0,
                duration_slots=6,
                cohort_mode=CohortMode.UNIFIED,
            )
        ]
        report_q = auditor.audit(quarantine_leak_entry)
        assert report_q.has_conflict is True
        assert report_q.quarantine_violations >= 1

        # Negative test 3: PRRC 108 exclusivity violation (BSIT offering in PRRC 108)
        bsit_off_id = off_ids[0]  # BSIT-3A
        prrc_leak_entry = [
            TimetableEntrySchema(
                id=uuid.uuid4(),
                offering_id=bsit_off_id,
                room_code="PRRC 108",
                day_of_week=DayOfWeek.MONDAY,
                start_slot=0,
                duration_slots=6,
                cohort_mode=CohortMode.UNIFIED,
            )
        ]
        report_prrc = auditor.audit(prrc_leak_entry)
        assert report_prrc.has_conflict is True
        assert report_prrc.exclusivity_violations >= 1

        # Negative test 4: Academic class scheduled on Sunday
        academic_sunday_entry = [
            TimetableEntrySchema(
                id=uuid.uuid4(),
                offering_id=bsit_off_id,
                room_code="PRRC 201",
                day_of_week=DayOfWeek.SUNDAY,
                start_slot=0,
                duration_slots=6,
                cohort_mode=CohortMode.UNIFIED,
            )
        ]
        report_sun = auditor.audit(academic_sunday_entry)
        assert report_sun.has_conflict is True
        assert report_sun.sunday_violations >= 1

        # Negative test 5: Sunday Function Hall buffer breach (12:00-13:00, slots 10-11)
        rotc_off_id = next(o.id for o in data["offerings"] if "ROTC" in o.subject.subject_code)
        buffer_breach_entry = [
            TimetableEntrySchema(
                id=uuid.uuid4(),
                offering_id=rotc_off_id,
                room_code="FUNCTION_HALL",
                day_of_week=DayOfWeek.SUNDAY,
                start_slot=9,
                duration_slots=3,  # slots 9, 10, 11 (breaches 10-12)
                cohort_mode=CohortMode.UNIFIED,
            )
        ]
        report_buf = auditor.audit(buffer_breach_entry)
        assert report_buf.has_conflict is True
        assert report_buf.sunday_violations >= 1


class TestSundayRulesClassification:
    """Tests the classification and domain rules for Sunday civic and sports activities."""

    def test_civic_and_pathfit_classification(self):
        from services.scheduling.solver.sunday_rules import (
            is_rotc_subject,
            is_nstp_subject,
            is_pathfit_subject,
            is_civic_subject,
            is_academic_subject,
            is_outdoor_ground,
            get_sunday_civic_reservations,
        )

        assert is_rotc_subject("ROTC-1") is True
        assert is_rotc_subject("ROTC-2") is True
        assert is_rotc_subject("CC-IPT2") is False

        assert is_nstp_subject("NSTP-1") is True
        assert is_nstp_subject("CWTS-1") is True
        assert is_nstp_subject("LTS-2") is True
        assert is_nstp_subject("CS-ALG") is False

        assert is_pathfit_subject("PATHFIT-1") is True
        assert is_pathfit_subject("PATHFIT-3") is True
        assert is_pathfit_subject("PE-101") is True
        assert is_pathfit_subject("BSED-BIO") is False

        assert is_civic_subject("ROTC-1") is True
        assert is_civic_subject("NSTP-1") is True
        assert is_civic_subject("CC-IPT2") is False

        assert is_academic_subject("CC-IPT2") is True
        assert is_academic_subject("ROTC-1") is False

        assert is_outdoor_ground("ATHLETIC_OVAL") is True
        assert is_outdoor_ground("MONTALBAN_SPORTS_COMPLEX") is True
        assert is_outdoor_ground("OPEN_GROUNDS") is True
        assert is_outdoor_ground("PRRC 301") is False

        reservations = get_sunday_civic_reservations()
        assert len(reservations) == 4
        assert reservations[0]["activity"] == "ROTC"
        assert reservations[1]["activity"] == "TURNOVER_BUFFER"
        assert reservations[2]["activity"] == "NSTP"
        assert reservations[3]["activity"] == "FACILITY_CLOSED"


class TestSoftPenaltyObjectives:
    """Verifies that the soft penalty terms are correctly constructed."""

    def test_objective_weights_initialization(self):
        from services.scheduling.solver.objective_weights import SolverObjectiveWeights
        weights = SolverObjectiveWeights()
        assert weights.w_lunch == 100
        assert weights.w_gap == 50
        assert weights.w_compact == 20
        assert weights.w_room_stability == 10


class TestFastAPISchedulingEndpoints:
    """Verifies the FastAPI HTTP endpoints exposed on Port 8002."""

    def test_health_endpoint(self):
        from fastapi.testclient import TestClient
        from services.scheduling.main import app

        client = TestClient(app)
        res = client.get("/health")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "healthy"
        assert body["port"] == 8002
        assert "ClassSync" in body["title"]

    def test_audit_endpoint(self, phase2_synthetic_dataset):
        from fastapi.testclient import TestClient
        from services.scheduling.main import app

        data = phase2_synthetic_dataset
        client = TestClient(app)

        entry = TimetableEntrySchema(
            id=uuid.uuid4(),
            offering_id=data["offerings"][0].id,
            room_code="PRRC 201",
            day_of_week=DayOfWeek.MONDAY,
            start_slot=0,
            duration_slots=6,
            cohort_mode=CohortMode.UNIFIED,
        )

        payload = {
            "entries": [entry.model_dump(mode="json")],
            "offerings": [o.model_dump(mode="json") for o in data["offerings"]],
            "rooms": [r.model_dump(mode="json") for r in data["rooms"]],
            "stamp_hash": True,
        }

        res = client.post("/api/v1/scheduling/audit", json=payload)
        assert res.status_code == 200
        body = res.json()
        assert body["is_valid"] is True
        assert body["total_violations"] == 0
        assert body["revision_hash"] is not None
        assert len(body["revision_hash"]) == 64

