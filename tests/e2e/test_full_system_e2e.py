"""End-to-End Integration and System Acceptance Test Suite for ClassSync.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Full Pipeline Verification:
1. Multi-Role Gateway Authentication (Admin, Faculty, Student, Freshie First-Time Setup).
2. Spatial Quarantine Filtering & Facility Directory Invariants (D-05, D-06, PRRC 108 Lock).
3. Google OR-Tools CP-SAT Master Timetable Batch Solve & Sunday Civic Space Allocation.
4. Emergency Localized Delta Re-Solver (<100ms SLA, Variable Freezing).
5. COMLAB 15-second RFC 6238 TOTP Ingress, Atomic Workstation Claim & Empathetic Collision (D-04, D-12).
6. CQRS Cloud Firestore Read Model Projection Pipeline.
7. AST Invariant Verification (Decision Log D-02: Zero 're' module imports in ingress/validation paths).
"""

from __future__ import annotations

import ast
import os
import time
import uuid
from typing import Any, Dict, List
import pytest
from fastapi.testclient import TestClient

from classync_contracts.enums import UserRole, RoomType, DayOfWeek, SolverStatus, EmploymentTier
from classync_contracts.schemas import (
    RoomSchema,
    CurriculumSubjectSchema,
    SectionSchema,
    FacultyProfileSchema,
    CourseOfferingDetail,
    TimetableEntrySchema,
    CheckInRequest,
    CheckOutRequest,
    LocalLoginRequest,
    PasswordSetupRequest,
    DeltaSolveRequest,
)

# Services apps
from services.gateway.main import app as gateway_app
from services.academic.main import app as academic_app
from services.scheduling.main import app as scheduling_app
from services.presence.main import app as presence_app

# Core solver & sync components
from services.scheduling.solver.model_builder import MasterCPSATSolver
from services.scheduling.solver.delta_resolver import LocalizedDeltaResolver, OfferingMetadata
from services.scheduling.solver.conflict_auditor import ConflictAuditor
from services.scheduling.firestore_sync import FirestoreProjectionPipeline
from services.gateway.auth.routes import reset_user_db
from services.presence.totp.generator import TOTPGenerator


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture(autouse=True)
def setup_teardown_state():
    reset_user_db()
    yield
    reset_user_db()


@pytest.fixture
def gateway_client():
    return TestClient(gateway_app)


@pytest.fixture
def academic_client():
    return TestClient(academic_app)


@pytest.fixture
def scheduling_client():
    return TestClient(scheduling_app)


@pytest.fixture
def presence_client():
    return TestClient(presence_app)


# ===========================================================================
# 1. Multi-Role Gateway Authentication & ASVS 4.0 Token Lifecycle
# ===========================================================================

class TestE2EGatewayAuthentication:
    """Verifies complete multi-role auth flow from role .txt and OWASP ASVS 4.0 guidelines."""

    TURNSTILE_TEST_TOKEN = "test-turnstile-token-pass"

    def test_admin_login_with_role_credentials(self, gateway_client):
        """Admin logs in with official institutional credentials (role .txt) and Turnstile."""
        resp = gateway_client.post(
            "/api/v1/auth/login",
            json={
                "identifier": "admin@pnm.edu.ph",
                "password": "CdMAdmin2026!",
                "turnstile_token": self.TURNSTILE_TEST_TOKEN,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["role"] == "ADMIN"
        assert data["user"]["identifier"] == "admin@pnm.edu.ph"
        assert data["user"]["requires_password_change"] is False

        # Verify security headers are injected
        assert resp.headers["x-frame-options"] == "DENY"
        assert resp.headers["x-content-type-options"] == "nosniff"
        assert "default-src 'self'" in resp.headers["content-security-policy"]

    def test_faculty_login_with_role_credentials(self, gateway_client):
        """Faculty logs in with official credentials (role .txt)."""
        resp = gateway_client.post(
            "/api/v1/auth/login",
            json={
                "identifier": "teacher@pnm.edu.ph",
                "password": "FacultyPass2026!",
                "turnstile_token": self.TURNSTILE_TEST_TOKEN,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["user"]["role"] == "FACULTY"
        assert data["user"]["identifier"] == "teacher@pnm.edu.ph"

    def test_student_login_with_email_and_student_id(self, gateway_client):
        """Student logs in using both institutional email and raw 24-XXXXX ID."""
        # 1. Using institutional email
        resp_email = gateway_client.post(
            "/api/v1/auth/login",
            json={
                "identifier": "24-00123@student.pnm.edu.ph",
                "password": "StudentPass2026!",
                "turnstile_token": "test-turnstile-token-pass",
            },
        )
        assert resp_email.status_code == 200, resp_email.text
        assert resp_email.json()["user"]["role"] == "STUDENT"

        # 2. Using raw deterministic student ID
        resp_id = gateway_client.post(
            "/api/v1/auth/login",
            json={
                "identifier": "24-00123",
                "password": "StudentPass2026!",
                "turnstile_token": "test-turnstile-token-pass",
            },
        )
        assert resp_id.status_code == 200, resp_id.text
        assert resp_id.json()["user"]["role"] == "STUDENT"

    def test_freshie_first_time_password_setup_flow(self, gateway_client):
        """Freshman student with requires_password_change=True completes ASVS 4.0 setup."""
        # Weak password attempt (violates campus dictionary rule)
        weak_resp = gateway_client.post(
            "/api/v1/auth/setup-password",
            json={
                "student_or_employee_id": "24-00999",
                "new_password": "Cdmmontalban2026!",
                "confirm_password": "Cdmmontalban2026!",
            },
        )
        assert weak_resp.status_code == 422
        assert "predictable" in weak_resp.json()["detail"].lower() or "campus" in weak_resp.json()["detail"].lower()

        # Strong ASVS 4.0 compliant password
        strong_resp = gateway_client.post(
            "/api/v1/auth/setup-password",
            json={
                "student_or_employee_id": "24-00999",
                "new_password": "FreshieSecurePass2026!#",
                "confirm_password": "FreshieSecurePass2026!#",
            },
        )
        assert strong_resp.status_code == 200, strong_resp.text
        data = strong_resp.json()
        assert data["user"]["requires_password_change"] is False

        # Subsequent login works with new password
        login_resp = gateway_client.post(
            "/api/v1/auth/login",
            json={
                "identifier": "24-00999",
                "password": "FreshieSecurePass2026!#",
                "turnstile_token": "test-turnstile-token-pass",
            },
        )
        assert login_resp.status_code == 200, login_resp.text
        assert login_resp.json()["user"]["requires_password_change"] is False


# ===========================================================================
# 2. Academic Spatial Directory & Spatial Quarantine Filtering (D-05, D-06)
# ===========================================================================

class TestE2EAcademicSpatialDirectory:
    """Verifies facility directory rules: quarantined spaces hidden, PRRC 108 locked."""

    def test_spatial_quarantine_default_omission(self, academic_client):
        """Quarantined spaces (NB 204, NB 304, NB 308) MUST NOT appear in default room list."""
        resp = academic_client.get("/api/v1/academic/rooms")
        assert resp.status_code == 200
        rooms = resp.json()
        room_codes = [r["room_code"] for r in rooms]

        # Quarantined rooms must be absent
        assert "NB 204" not in room_codes
        assert "NB 304" not in room_codes
        assert "NB 308" not in room_codes

        # Schedulable rooms must be present
        assert "PRRC 108" in room_codes
        assert "PRRC 301" in room_codes
        assert "PRRC 201" in room_codes
        assert "Function Hall" in room_codes

        # All returned rooms must have is_schedulable=True
        for r in rooms:
            assert r["is_schedulable"] is True

    def test_prrc_108_exclusive_lock_invariant(self, academic_client):
        """PRRC 108 is strictly locked to BSED_SCIENCE."""
        resp = academic_client.get("/api/v1/academic/rooms")
        assert resp.status_code == 200
        prrc_108 = next((r for r in resp.json() if r["room_code"] == "PRRC 108"), None)
        assert prrc_108 is not None
        assert prrc_108["exclusive_program"] == "BSED_SCIENCE"
        assert prrc_108["room_type"] == "SCIENCE_LAB"

    def test_function_hall_capacity_and_type(self, academic_client):
        """Function Hall has >= 300 capacity and room_type FUNCTION_HALL."""
        resp = academic_client.get("/api/v1/academic/rooms")
        assert resp.status_code == 200
        func_hall = next((r for r in resp.json() if r["room_code"] == "Function Hall"), None)
        assert func_hall is not None
        assert func_hall["room_type"] == "FUNCTION_HALL"
        assert func_hall["capacity"] >= 300

    def test_admin_quarantine_inspection_view(self, academic_client):
        """Admin passing include_quarantined=True can view quarantined spaces."""
        resp = academic_client.get("/api/v1/academic/rooms?include_quarantined=true")
        assert resp.status_code == 200
        rooms = resp.json()
        room_codes = [r["room_code"] for r in rooms]

        assert "NB 204" in room_codes
        assert "NB 304" in room_codes
        assert "NB 308" in room_codes

        nb_204 = next(r for r in rooms if r["room_code"] == "NB 204")
        assert nb_204["is_schedulable"] is False


# ===========================================================================
# 3. Master CP-SAT Batch Timetable Solve & Conflict Audit (D-03, D-06)
# ===========================================================================

class TestE2EMasterCPSATSolver:
    """Verifies OR-Tools CP-SAT batch solve, zero collisions, and Sunday rules."""

    @pytest.fixture
    def institutional_dataset(self):
        period_id = uuid.uuid4()
        rooms = [
            RoomSchema(
                room_code="PRRC 301",
                building_name="PRRC Building",
                floor_level=3,
                room_type=RoomType.COMPUTER_LAB,
                capacity=70,
                is_schedulable=True,
                has_aircon=True,
                has_projector=True,
            ),
            RoomSchema(
                room_code="PRRC 201",
                building_name="PRRC Building",
                floor_level=2,
                room_type=RoomType.LECTURE,
                capacity=70,
                is_schedulable=True,
                has_aircon=True,
                has_projector=True,
            ),
            RoomSchema(
                room_code="PRRC 202",
                building_name="PRRC Building",
                floor_level=2,
                room_type=RoomType.LECTURE,
                capacity=70,
                is_schedulable=True,
                has_aircon=True,
                has_projector=True,
            ),
            RoomSchema(
                room_code="PRRC 108",
                building_name="PRRC Building",
                floor_level=1,
                room_type=RoomType.SCIENCE_LAB,
                capacity=65,
                is_schedulable=True,
                has_aircon=True,
                has_projector=True,
                exclusive_program="BSED_SCIENCE",
            ),
            RoomSchema(
                room_code="FUNCTION_HALL",
                building_name="Main Complex",
                floor_level=1,
                room_type=RoomType.FUNCTION_HALL,
                capacity=300,
                is_schedulable=True,
                has_aircon=True,
                has_projector=True,
            ),
        ]

        # Subjects
        subj_ipt2 = CurriculumSubjectSchema(
            id=uuid.uuid4(),
            subject_code="CC-IPT2",
            descriptive_title="Integrative Programming 2",
            lecture_hours=2,
            lab_hours=3,
            units=3,
            required_room_type=RoomType.COMPUTER_LAB,
        )
        subj_ias = CurriculumSubjectSchema(
            id=uuid.uuid4(),
            subject_code="CC-IAS",
            descriptive_title="Information Assurance & Security",
            lecture_hours=2,
            lab_hours=3,
            units=3,
            required_room_type=RoomType.COMPUTER_LAB,
        )
        subj_sci = CurriculumSubjectSchema(
            id=uuid.uuid4(),
            subject_code="BSED-SCI101",
            descriptive_title="Inorganic Chemistry",
            lecture_hours=3,
            lab_hours=0,
            units=3,
            required_room_type=RoomType.SCIENCE_LAB,
        )
        subj_rotc = CurriculumSubjectSchema(
            id=uuid.uuid4(),
            subject_code="ROTC-1",
            descriptive_title="ROTC Civic Training 1",
            lecture_hours=5,
            lab_hours=0,
            units=3,
            required_room_type=RoomType.FUNCTION_HALL,
        )
        subj_nstp = CurriculumSubjectSchema(
            id=uuid.uuid4(),
            subject_code="NSTP-1",
            descriptive_title="NSTP Civic Training 1",
            lecture_hours=4,
            lab_hours=0,
            units=3,
            required_room_type=RoomType.FUNCTION_HALL,
        )

        # Sections
        sec_3a = SectionSchema(id=uuid.uuid4(), academic_period_id=period_id, section_code="BSIT-3A", year_level=3, enrolled_student_count=65)
        sec_3b = SectionSchema(id=uuid.uuid4(), academic_period_id=period_id, section_code="BSIT-3B", year_level=3, enrolled_student_count=68)
        sec_sci = SectionSchema(id=uuid.uuid4(), academic_period_id=period_id, section_code="BSED_SCI-2A", year_level=2, enrolled_student_count=60)
        sec_rotc = SectionSchema(id=uuid.uuid4(), academic_period_id=period_id, section_code="ROTC-ALPHA", year_level=1, enrolled_student_count=150)
        sec_nstp = SectionSchema(id=uuid.uuid4(), academic_period_id=period_id, section_code="NSTP-BRAVO", year_level=1, enrolled_student_count=140)

        # Faculty
        fac_nat = FacultyProfileSchema(id=uuid.uuid4(), institutional_email="nat@pnm.edu.ph", full_name="Prof. Nat", employment_tier=EmploymentTier.FULL_TIME, role=UserRole.FACULTY, is_active=True, requires_password_change=False)
        fac_mades = FacultyProfileSchema(id=uuid.uuid4(), institutional_email="mades@pnm.edu.ph", full_name="Prof. Mades", employment_tier=EmploymentTier.FULL_TIME, role=UserRole.FACULTY, is_active=True, requires_password_change=False)
        fac_sci = FacultyProfileSchema(id=uuid.uuid4(), institutional_email="science@pnm.edu.ph", full_name="Prof. Science Lead", employment_tier=EmploymentTier.FULL_TIME, role=UserRole.FACULTY, is_active=True, requires_password_change=False)
        fac_rotc = FacultyProfileSchema(id=uuid.uuid4(), institutional_email="rotc@pnm.edu.ph", full_name="Col. ROTC Commander", employment_tier=EmploymentTier.FULL_TIME, role=UserRole.FACULTY, is_active=True, requires_password_change=False)
        fac_nstp = FacultyProfileSchema(id=uuid.uuid4(), institutional_email="nstp@pnm.edu.ph", full_name="Prof. NSTP Coordinator", employment_tier=EmploymentTier.FULL_TIME, role=UserRole.FACULTY, is_active=True, requires_password_change=False)

        offerings = [
            CourseOfferingDetail(
                id=uuid.uuid4(),
                academic_period_id=period_id,
                subject_id=subj_ipt2.id,
                section_id=sec_3a.id,
                faculty_id=fac_nat.id,
                subject=subj_ipt2,
                section=sec_3a,
                faculty=fac_nat,
            ),
            CourseOfferingDetail(
                id=uuid.uuid4(),
                academic_period_id=period_id,
                subject_id=subj_ias.id,
                section_id=sec_3b.id,
                faculty_id=fac_mades.id,
                subject=subj_ias,
                section=sec_3b,
                faculty=fac_mades,
            ),
            CourseOfferingDetail(
                id=uuid.uuid4(),
                academic_period_id=period_id,
                subject_id=subj_sci.id,
                section_id=sec_sci.id,
                faculty_id=fac_sci.id,
                subject=subj_sci,
                section=sec_sci,
                faculty=fac_sci,
            ),
            CourseOfferingDetail(
                id=uuid.uuid4(),
                academic_period_id=period_id,
                subject_id=subj_rotc.id,
                section_id=sec_rotc.id,
                faculty_id=fac_rotc.id,
                subject=subj_rotc,
                section=sec_rotc,
                faculty=fac_rotc,
            ),
            CourseOfferingDetail(
                id=uuid.uuid4(),
                academic_period_id=period_id,
                subject_id=subj_nstp.id,
                section_id=sec_nstp.id,
                faculty_id=fac_nstp.id,
                subject=subj_nstp,
                section=sec_nstp,
                faculty=fac_nstp,
            ),
        ]
        return {"period_id": period_id, "rooms": rooms, "offerings": offerings}

    def test_batch_solve_zero_conflicts_and_sunday_partition(self, institutional_dataset):
        """Batch CP-SAT solve must produce zero collisions and partition Sunday civic spaces."""
        rooms = institutional_dataset["rooms"]
        offerings = institutional_dataset["offerings"]

        solver = MasterCPSATSolver(rooms=rooms, offerings=offerings, time_limit_seconds=30)
        result = solver.solve()

        assert result.status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)
        assert len(result.timetable_entries) > 0

        # Independent audit
        auditor = ConflictAuditor(rooms=rooms, offerings=offerings)
        audit_report = auditor.audit(result.timetable_entries)
        assert audit_report.is_valid is True
        assert audit_report.total_violations == 0
        assert audit_report.room_collisions == 0
        assert audit_report.faculty_collisions == 0
        assert audit_report.section_collisions == 0

        # Verify Sunday Civic Partition (D-06):
        # Sunday is day 6. ROTC in morning (slots 0-9), NSTP in afternoon (slots 12-19).
        rotc_entries = [e for e in result.timetable_entries if e.offering_id == offerings[3].id]
        nstp_entries = [e for e in result.timetable_entries if e.offering_id == offerings[4].id]

        assert len(rotc_entries) > 0
        for e in rotc_entries:
            day_val = e.day_of_week.value if hasattr(e.day_of_week, "value") else int(e.day_of_week)
            assert day_val == DayOfWeek.SUNDAY.value
            assert e.room_code == "FUNCTION_HALL"
            assert e.start_slot >= 0
            assert e.start_slot + e.duration_slots <= 10  # 07:00 to 12:00

        assert len(nstp_entries) > 0
        for e in nstp_entries:
            day_val = e.day_of_week.value if hasattr(e.day_of_week, "value") else int(e.day_of_week)
            assert day_val == DayOfWeek.SUNDAY.value
            assert e.room_code == "FUNCTION_HALL"
            assert e.start_slot >= 12  # 13:00 to 17:00
            assert e.start_slot + e.duration_slots <= 20


# ===========================================================================
# 4. Emergency Localized Delta Re-Solver SLA (<100ms)
# ===========================================================================

class TestE2EDeltaResolver:
    """Verifies sub-second emergency room reallocation executes under <100ms SLA."""

    def test_emergency_room_failure_reassignment_speed_and_isolation(self):
        """Simulates sudden facility outage: reallocates disrupted offerings under 100ms."""
        period_id = uuid.uuid4()
        offering1_id = uuid.uuid4()
        offering2_id = uuid.uuid4()
        offering3_id = uuid.uuid4()

        rooms = [
            RoomSchema(
                room_code="PRRC 201",
                building_name="PRRC Building",
                floor_level=2,
                room_type=RoomType.LECTURE,
                capacity=70,
                is_schedulable=True,
                has_aircon=True,
                has_projector=True,
            ),
            RoomSchema(
                room_code="PRRC 202",
                building_name="PRRC Building",
                floor_level=2,
                room_type=RoomType.LECTURE,
                capacity=70,
                is_schedulable=True,
                has_aircon=True,
                has_projector=True,
            ),
        ]

        # Baseline: offering 1 in PRRC 201 on Tuesday (day 1), slots 2-6 (08:00-10:00)
        # Baseline: offering 2 in PRRC 202 on Tuesday, slots 8-12 (11:00-13:00)
        # Baseline: offering 3 in PRRC 201 on Wednesday (day 2), slots 2-6
        baseline_entries = [
            TimetableEntrySchema(
                id=uuid.uuid4(),
                academic_period_id=period_id,
                offering_id=offering1_id,
                room_code="PRRC 201",
                day_of_week=DayOfWeek.TUESDAY,
                start_slot=2,
                end_slot=6,
                duration_slots=4,
            ),
            TimetableEntrySchema(
                id=uuid.uuid4(),
                academic_period_id=period_id,
                offering_id=offering2_id,
                room_code="PRRC 202",
                day_of_week=DayOfWeek.TUESDAY,
                start_slot=8,
                end_slot=12,
                duration_slots=4,
            ),
            TimetableEntrySchema(
                id=uuid.uuid4(),
                academic_period_id=period_id,
                offering_id=offering3_id,
                room_code="PRRC 201",
                day_of_week=DayOfWeek.WEDNESDAY,
                start_slot=2,
                end_slot=6,
                duration_slots=4,
            ),
        ]

        offerings_map = {
            offering1_id: OfferingMetadata(
                offering_id=offering1_id,
                required_room_type="LECTURE",
                enrolled_student_count=65,
                section_id=uuid.uuid4(),
                faculty_id=uuid.uuid4(),
            ),
            offering2_id: OfferingMetadata(
                offering_id=offering2_id,
                required_room_type="LECTURE",
                enrolled_student_count=60,
                section_id=uuid.uuid4(),
                faculty_id=uuid.uuid4(),
            ),
            offering3_id: OfferingMetadata(
                offering_id=offering3_id,
                required_room_type="LECTURE",
                enrolled_student_count=60,
                section_id=uuid.uuid4(),
                faculty_id=uuid.uuid4(),
            ),
        }

        request = DeltaSolveRequest(
            disrupted_room_code="PRRC 201",
            day_of_week=DayOfWeek.TUESDAY,
            start_slot=0,
            duration_slots=24,
        )

        resolver = LocalizedDeltaResolver(rooms=rooms)

        # Measure latency
        start_time = time.perf_counter()
        delta_response = resolver.resolve(
            baseline_entries=baseline_entries,
            request=request,
            offerings_map=offerings_map,
        )
        elapsed_seconds = time.perf_counter() - start_time

        # Strict SLA requirement: delta re-solve MUST execute under 0.10s (100ms)
        assert elapsed_seconds < 0.10, f"Delta re-solve exceeded SLA: {elapsed_seconds:.4f}s"
        assert delta_response.delta_solved is True

        # Reassigned entry must have moved from PRRC 201 to PRRC 202
        assert len(delta_response.reassigned_entries) == 1
        reassigned = delta_response.reassigned_entries[0]
        assert reassigned.offering_id == offering1_id
        assert reassigned.room_code == "PRRC 202"


# ===========================================================================
# 5. COMLAB Presence & 15s RFC 6238 TOTP Workstation Ingress (D-04, D-12)
# ===========================================================================

class TestE2EPresenceIngress:
    """Verifies rotating 15s TOTP QR stream, zero-regex ID, and seat collision detection."""

    def test_totp_generation_and_valid_checkin(self, presence_client):
        """Fetches active 15s TOTP for PRRC 301 and successfully checks in on Workstation 14."""
        # 1. Fetch live TOTP
        totp_resp = presence_client.get("/api/v1/presence/totp/PRRC 301")
        assert totp_resp.status_code == 200
        totp_data = totp_resp.json()
        assert len(totp_data["totp"]) == 6
        assert totp_data["remaining_seconds"] <= 15

        # 2. Student 24-00123 checks in to Workstation 14
        checkin_resp = presence_client.post(
            "/api/v1/presence/checkin",
            json={
                "room_code": "PRRC 301",
                "workstation_number": 14,
                "student_id": "24-00123",
                "totp_token": totp_data["totp"],
            },
        )
        assert checkin_resp.status_code == 200, checkin_resp.text
        claim_data = checkin_resp.json()
        assert claim_data["success"] is True
        assert claim_data["workstation_number"] == 14
        assert claim_data["student_id"] == "24-00123"

        # 3. Workstation occupancy check
        occ_resp = presence_client.get("/api/v1/presence/rooms/PRRC 301/occupancy")
        assert occ_resp.status_code == 200
        occ_data = occ_resp.json()
        assert occ_data["occupied_count"] >= 1

    def test_workstation_collision_returns_d12_empathetic_recommendation(self, presence_client):
        """Second student attempting to claim same workstation triggers 409 with adjacent recommendation."""
        totp_resp = presence_client.get("/api/v1/presence/totp/PRRC 302")
        totp_token = totp_resp.json()["totp"]

        # Student A claims Workstation 14
        res_a = presence_client.post(
            "/api/v1/presence/checkin",
            json={
                "room_code": "PRRC 302",
                "workstation_number": 14,
                "student_id": "24-00111",
                "totp_token": totp_token,
            },
        )
        assert res_a.status_code == 200

        # Student B tries to claim Workstation 14
        res_b = presence_client.post(
            "/api/v1/presence/checkin",
            json={
                "room_code": "PRRC 302",
                "workstation_number": 14,
                "student_id": "24-00222",
                "totp_token": totp_token,
            },
        )
        assert res_b.status_code == 409
        err_msg = res_b.json()["detail"]

        # D-12 requirement: No '409 Conflict' system jargon; friendly adjacent recommendation
        assert "just claimed" in err_msg.lower()
        assert "pc-15" in err_msg.lower()

    def test_checkout_and_circular_audit_buffer(self, presence_client):
        """Checkout frees the station and in-memory circular buffer logs the event."""
        totp_resp = presence_client.get("/api/v1/presence/totp/PRRC 303")
        totp_token = totp_resp.json()["totp"]

        # Checkin
        presence_client.post(
            "/api/v1/presence/checkin",
            json={
                "room_code": "PRRC 303",
                "workstation_number": 20,
                "student_id": "24-00333",
                "totp_token": totp_token,
            },
        )

        # Checkout
        checkout_resp = presence_client.post(
            "/api/v1/presence/checkout",
            json={
                "room_code": "PRRC 303",
                "workstation_number": 20,
                "student_id": "24-00333",
            },
        )
        assert checkout_resp.status_code == 200
        assert checkout_resp.json()["success"] is True

        # Circular buffer log check
        logs_resp = presence_client.get("/api/v1/presence/rooms/PRRC 303/recent-logs")
        assert logs_resp.status_code == 200
        logs = logs_resp.json()
        assert len(logs) >= 1
        assert logs[0]["student_id"] == "24-00333"


# ===========================================================================
# 6. CQRS Cloud Firestore Read Model Projection Pipeline (D-08)
# ===========================================================================

class TestE2ECQRSFirestoreProjection:
    """Verifies relational-to-document read model projection for client PWA & Mobile."""

    def test_firestore_timetable_and_occupancy_projection(self):
        pipeline = FirestoreProjectionPipeline(project_id="classync-pnm-test")

        # 1. Project timetable batch
        period_id = uuid.uuid4()
        entries = [
            {"day": 1, "room": "PRRC 301", "subject": "CC-IPT2", "start": 2, "end": 6},
            {"day": 3, "room": "PRRC 201", "subject": "CC-ADMS", "start": 8, "end": 12},
        ]
        tt_proj = pipeline.project_timetable_entries(
            academic_period_id=period_id,
            entries=entries,
            revision_hash="a1b2c3d4e5f6",
        )
        assert tt_proj["academic_period_id"] == str(period_id)
        assert tt_proj["entry_count"] == 2
        assert tt_proj["revision_hash"] == "a1b2c3d4e5f6"

        # 2. Project workstation presence
        stations_state = {14: {"occupied": True, "student_id": "24-00123"}}
        occ_proj = pipeline.project_workstation_occupancy(
            room_code="PRRC 301",
            occupied_count=1,
            total_stations=45,
            occupancy_rate=1 / 45,
            stations_state=stations_state,
        )
        assert occ_proj["room_code"] == "PRRC 301"
        assert occ_proj["occupied_count"] == 1
        assert occ_proj["vacant_count"] == 44
        assert occ_proj["occupancy_rate"] > 0

        # 3. Project facility directory (ensuring quarantined spaces are omitted)
        rooms = [
            {"room_code": "PRRC 301", "is_schedulable": True},
            {"room_code": "NB 204", "is_schedulable": False},
        ]
        fac_proj = pipeline.project_facility_directory(rooms)
        assert fac_proj["total_schedulable_rooms"] == 1
        assert len(fac_proj["rooms"]) == 1
        assert fac_proj["rooms"][0]["room_code"] == "PRRC 301"


# ===========================================================================
# 7. Zero-Regex AST Security Invariant Audit across Microservices
# ===========================================================================

class TestE2EZeroRegexSecurityInvariant:
    """Verifies that the 're' module is strictly banned in student ID and token processing."""

    def test_zero_regex_module_imports_across_critical_paths(self):
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        critical_dirs = [
            os.path.join(root_dir, "services", "presence", "ingress"),
            os.path.join(root_dir, "services", "gateway", "auth"),
            os.path.join(root_dir, "packages", "contracts-py", "classync_contracts"),
        ]

        banned_modules = {"re"}

        for target_dir in critical_dirs:
            assert os.path.exists(target_dir), f"Directory {target_dir} not found"
            for root, _, files in os.walk(target_dir):
                for file in files:
                    if not file.endswith(".py") or file == "__init__.py":
                        continue
                    filepath = os.path.join(root, file)
                    with open(filepath, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read(), filename=filepath)

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                assert alias.name not in banned_modules, (
                                    f"Security Invariant D-02 Violated: '{alias.name}' imported in {filepath} at line {node.lineno}"
                                )
                        elif isinstance(node, ast.ImportFrom):
                            assert node.module not in banned_modules, (
                                f"Security Invariant D-02 Violated: from '{node.module}' imported in {filepath} at line {node.lineno}"
                            )
