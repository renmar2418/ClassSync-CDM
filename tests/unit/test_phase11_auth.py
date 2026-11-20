"""Unit & Integration Tests for Phase 11 — Real Database-Backed Authentication & Student Roster System.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Tests:
1. StudentProfile model constraints and zero-regex deterministic validation
2. Admin student CRUD operations via academic service
3. Admin CSV bulk-import with zero-regex validation and error reporting
4. Gateway DB user resolution for StudentProfile and FacultyProfile
5. First-time student password setup and persistence
6. Full 2FA OTP flow for newly imported/created student
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from classync_contracts.enums import UserRole
from classync_contracts.models import Base, StudentProfile, FacultyProfile
from classync_contracts.schemas import validate_student_id_deterministic
from classync_contracts.security import hash_password, verify_password

from services.gateway.main import app as gateway_app, jwt_manager, rate_limiter
from services.gateway.auth.routes import (
    get_user_record,
    save_user_password,
    gateway_otp_manager,
    gateway_brevo_client,
    USER_DB,
    reset_user_db,
)
from services.academic.main import app as academic_app, STUDENTS_DB


@pytest.fixture(scope="module")
def test_db_engine():
    """In-memory SQLite database engine for testing Phase 11 schema."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(test_db_engine):
    """Provides a transactional database session."""
    SessionLocal = sessionmaker(bind=test_db_engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def gateway_client():
    """TestClient for Security Gateway."""
    return TestClient(gateway_app)


@pytest.fixture
def academic_client():
    """TestClient for Academic Service."""
    return TestClient(academic_app)


# ---------------------------------------------------------------------------
# 1. Model & Validation Tests
# ---------------------------------------------------------------------------

class TestStudentProfileModel:
    def test_student_id_deterministic_validator(self):
        """Zero-regex O(n) validator accepts valid cohorts 20-99 and rejects invalid."""
        assert validate_student_id_deterministic("24-00123") == "24-00123"
        assert validate_student_id_deterministic("20-99999") == "20-99999"
        assert validate_student_id_deterministic("26-00001") == "26-00001"

        # Rejects legacy/under-20, non-ascii, emails, wrong lengths
        with pytest.raises(ValueError):
            validate_student_id_deterministic("19-00123")
        with pytest.raises(ValueError):
            validate_student_id_deterministic("24-0012")
        with pytest.raises(ValueError):
            validate_student_id_deterministic("24-001234")
        with pytest.raises(ValueError):
            validate_student_id_deterministic("24-0012a")
        with pytest.raises(ValueError):
            validate_student_id_deterministic("24-00123@student.pnm.edu.ph")

    def test_student_profile_persistence(self, db_session: Session):
        """StudentProfile persists to database with correct defaults."""
        stu = StudentProfile(
            id=uuid.uuid4(),
            student_id="25-12345",
            institutional_email="25-12345@student.pnm.edu.ph",
            full_name="Maria Santos",
            section_code="BSIT-2A",
            year_level=2,
            is_active=True,
            requires_password_change=True,
        )
        db_session.add(stu)
        db_session.commit()

        retrieved = db_session.scalar(select(StudentProfile).where(StudentProfile.student_id == "25-12345"))
        assert retrieved is not None
        assert retrieved.full_name == "Maria Santos"
        assert retrieved.requires_password_change is True
        assert retrieved.password_hash is None


# ---------------------------------------------------------------------------
# 2. Academic Admin Student CRUD & CSV Bulk Import Tests
# ---------------------------------------------------------------------------

class TestAcademicStudentRoster:
    def test_list_students(self, academic_client: TestClient):
        """Academic service lists students with pagination and filtering."""
        resp = academic_client.get("/api/v1/academic/students?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(s["student_id"] == "24-00123" for s in data)

    def test_create_and_get_student(self, academic_client: TestClient):
        """Admin creates single student and retrieves it."""
        payload = {
            "student_id": "25-98765",
            "institutional_email": "25-98765@student.pnm.edu.ph",
            "full_name": "Pedro Penduko",
            "section_code": "BSIT-2B",
            "year_level": 2,
        }
        res_create = academic_client.post("/api/v1/academic/admin/students", json=payload)
        assert res_create.status_code == 201
        created = res_create.json()
        assert created["student_id"] == "25-98765"
        assert created["requires_password_change"] is True

        # Duplicate ID rejection
        res_dup = academic_client.post("/api/v1/academic/admin/students", json=payload)
        assert res_dup.status_code == 409

        # Get student
        res_get = academic_client.get("/api/v1/academic/admin/students/25-98765")
        assert res_get.status_code == 200
        assert res_get.json()["full_name"] == "Pedro Penduko"

    def test_update_and_deactivate_student(self, academic_client: TestClient):
        """Admin updates and soft-deactivates student."""
        res_update = academic_client.put(
            "/api/v1/academic/admin/students/25-98765",
            json={"full_name": "Pedro Penduko Jr.", "year_level": 3},
        )
        assert res_update.status_code == 200
        assert res_update.json()["full_name"] == "Pedro Penduko Jr."
        assert res_update.json()["year_level"] == 3

        res_del = academic_client.delete("/api/v1/academic/admin/students/25-98765")
        assert res_del.status_code == 200
        assert res_del.json()["status"] == "deactivated"

    def test_bulk_import_students_csv(self, academic_client: TestClient):
        """Admin bulk imports student roster via CSV text with validation."""
        csv_data = (
            "student_id,institutional_email,full_name,section_code,year_level\n"
            "25-00001,25-00001@student.pnm.edu.ph,Alice Ramos,BSIT-2A,2\n"
            "25-00002,25-00002@student.pnm.edu.ph,Bob Tan,BSIT-2A,2\n"
            "19-00003,invalid@student.pnm.edu.ph,Invalid Cohort,BSIT-2A,2\n"  # Invalid cohort (< 20)
            "25-00004,,Charlie Garcia,BSIT-2A,2\n"  # Missing email -> auto-defaults
        )
        resp = academic_client.post(
            "/api/v1/academic/admin/students/bulk-import",
            json={"raw_csv": csv_data},
        )
        assert resp.status_code == 200
        res = resp.json()
        assert res["total_processed"] == 4
        assert res["imported"] == 3
        assert res["skipped"] == 1
        assert len(res["errors"]) == 1
        assert "Row 3" in res["errors"][0]

        # Verify auto-defaulted email for 25-00004
        check = academic_client.get("/api/v1/academic/admin/students/25-00004")
        assert check.status_code == 200
        assert check.json()["institutional_email"] == "25-00004@student.pnm.edu.ph"


# ---------------------------------------------------------------------------
# 3. Gateway Hybrid DB User Lookup & 2FA Tests
# ---------------------------------------------------------------------------

class TestGatewayDBAuthWorkflow:
    def test_gateway_user_record_resolution(self):
        """Gateway resolves users from memory or database fallback."""
        reset_user_db()
        # juan dela cruz
        u = get_user_record("24-00123")
        assert u is not None
        assert u.identifier == "24-00123"
        assert u.role == UserRole.STUDENT

        # admin
        admin = get_user_record("admin@pnm.edu.ph")
        assert admin is not None
        assert admin.role == UserRole.ADMIN

    def test_first_time_password_setup_and_login_flow(self, gateway_client: TestClient):
        """Student with requires_password_change=True completes setup, then logs in with 2FA."""
        rate_limiter.reset()

        # Step A: Setup password for 24-00999 (Freshie Student)
        resp_setup = gateway_client.post(
            "/api/v1/auth/setup-password",
            json={
                "student_or_employee_id": "24-00999",
                "new_password": "NewFreshiePass2026!#",
                "confirm_password": "NewFreshiePass2026!#",
            },
        )
        assert resp_setup.status_code == 200
        setup_data = resp_setup.json()
        assert setup_data["user"]["identifier"] == "24-00999"
        assert setup_data["user"]["requires_password_change"] is False

        # Step B: Perform Step 1 Login with new password
        rate_limiter.reset()
        resp_step1 = gateway_client.post(
            "/api/v1/auth/login/step1",
            json={
                "identifier": "24-00999",
                "password": "NewFreshiePass2026!#",
                "turnstile_token": "mock-turnstile-token-verified",
            },
        )
        assert resp_step1.status_code == 200
        step1_data = resp_step1.json()
        assert step1_data["requires_otp"] is True
        session_id = step1_data["otp_session_id"]

        # Step C: Verify OTP and receive JWT
        session = gateway_otp_manager.get_session(session_id)
        assert session is not None
        otp_code = session.otp_code

        rate_limiter.reset()
        resp_step2 = gateway_client.post(
            "/api/v1/auth/login/verify-otp",
            json={
                "otp_session_id": session_id,
                "otp_code": otp_code,
            },
        )
        assert resp_step2.status_code == 200
        auth_data = resp_step2.json()
        assert auth_data["user"]["identifier"] == "24-00999"
        assert auth_data["user"]["role"] == "STUDENT"
        assert len(auth_data["access_token"]) > 30

        # Step D: Test /me endpoint with received bearer token
        resp_me = gateway_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {auth_data['access_token']}"},
        )
        assert resp_me.status_code == 200
        assert resp_me.json()["identifier"] == "24-00999"
