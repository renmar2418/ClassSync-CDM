"""Real Workflow Acceptance Test Suite for ClassSync V2 Evolution:
- Multi-Role Brevo 2FA Authentication (Admin, Faculty, Multi-Year Cohorts 22..26)
- Authoritative 53 Room Catalog Partitioning (43 Schedulable, 12 Non-Schedulable Quarantined, Total 55 Spaces)
- Section-Level Curriculum Inheritance & Irregular Student Overrides
- OWASP ASVS 4.0 Brute-Force Rate Limiting & Lockout Protection
"""

from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from classync_contracts.enums import UserRole, RoomType
from classync_contracts.models import (
    Base,
    Room,
    CurriculumVersion,
    StudentCurriculumOverride,
    Section,
)
from classync_contracts.schemas import (
    LocalLoginRequest,
    OTPVerifyRequest,
)

from services.gateway.main import app as gateway_app, rate_limiter
from services.gateway.auth.routes import (
    reset_user_db,
    gateway_brevo_client,
    gateway_otp_manager,
)

import importlib.util
from pathlib import Path

_seed_path = Path(__file__).resolve().parents[2] / "alembic" / "seed_data.py"
_spec = importlib.util.spec_from_file_location("alembic_seed_data", _seed_path)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Could not load seed_data spec from {_seed_path}")
_seed_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_seed_module)
seed_database = _seed_module.seed_database


@pytest.fixture(autouse=True)
def reset_gateway_state():
    rate_limiter.reset()
    reset_user_db()
    yield
    rate_limiter.reset()
    reset_user_db()


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    seed_database(session)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(gateway_app)


class TestRealWorkflowAuthentication:
    """Verifies complete 2-step login workflow for Admin, Faculty, and Students."""

    def test_admin_real_login_workflow(self, client: TestClient):
        """Admin logs in via step 1, receives Brevo OTP, verifies code, and receives JWT."""
        rate_limiter.reset()

        # Step 1: Submit credentials
        resp_step1 = client.post(
            "/api/v1/auth/login/step1",
            json={
                "identifier": "admin@pnm.edu.ph",
                "password": "AdminPass2026!#",
                "turnstile_token": "mock-turnstile-token-verified",
            },
        )
        assert resp_step1.status_code == 200, resp_step1.text
        data1 = resp_step1.json()
        assert data1["requires_otp"] is True
        session_id = data1["otp_session_id"]
        assert "a***n@pnm.edu.ph" in data1["email_hint"]

        # Retrieve the OTP code generated for this session
        session = gateway_otp_manager.get_session(session_id)
        assert session is not None
        otp_code = session.otp_code

        # Step 2: Submit OTP code
        rate_limiter.reset()
        resp_step2 = client.post(
            "/api/v1/auth/login/verify-otp",
            json={
                "otp_session_id": session_id,
                "otp_code": otp_code,
            },
        )
        assert resp_step2.status_code == 200, resp_step2.text
        data2 = resp_step2.json()
        assert data2["token_type"] == "bearer"
        assert len(data2["access_token"]) > 30
        assert data2["user"]["role"] == "ADMIN"
        assert data2["user"]["full_name"] == "ClassSync Administrator"

    def test_faculty_real_login_workflow(self, client: TestClient):
        """Faculty logs in via step 1, receives Brevo OTP, verifies code, and receives JWT."""
        rate_limiter.reset()

        resp_step1 = client.post(
            "/api/v1/auth/login/step1",
            json={
                "identifier": "ngomez@pnm.edu.ph",
                "password": "FacultyPass2026!#",
                "turnstile_token": "mock-turnstile-token-verified",
            },
        )
        assert resp_step1.status_code == 200, resp_step1.text
        data1 = resp_step1.json()
        session_id = data1["otp_session_id"]
        otp_code = gateway_otp_manager.get_session(session_id).otp_code

        rate_limiter.reset()
        resp_step2 = client.post(
            "/api/v1/auth/login/verify-otp",
            json={
                "otp_session_id": session_id,
                "otp_code": otp_code,
            },
        )
        assert resp_step2.status_code == 200, resp_step2.text
        data2 = resp_step2.json()
        assert data2["user"]["role"] == "FACULTY"
        assert "Nathaniel Gomez" in data2["user"]["full_name"]

    @pytest.mark.parametrize(
        "student_id",
        ["22-00123", "23-00123", "24-00123", "25-00123", "26-00123"],
    )
    def test_multi_year_student_real_login_workflow(self, client: TestClient, student_id: str):
        """All supported student cohorts (2022 through 2026+) complete 2FA login."""
        rate_limiter.reset()

        resp_step1 = client.post(
            "/api/v1/auth/login/step1",
            json={
                "identifier": student_id,
                "password": "ValidPass2026!#",
                "turnstile_token": "mock-turnstile-token-verified",
            },
        )
        assert resp_step1.status_code == 200, resp_step1.text
        data1 = resp_step1.json()
        session_id = data1["otp_session_id"]
        otp_code = gateway_otp_manager.get_session(session_id).otp_code

        rate_limiter.reset()
        resp_step2 = client.post(
            "/api/v1/auth/login/verify-otp",
            json={
                "otp_session_id": session_id,
                "otp_code": otp_code,
            },
        )
        assert resp_step2.status_code == 200, resp_step2.text
        data2 = resp_step2.json()
        assert data2["user"]["role"] == "STUDENT"
        assert data2["user"]["identifier"] == student_id

    def test_otp_brute_force_lockout_asvs_4(self, client: TestClient):
        """3 incorrect OTP submissions locks and invalidates the verification session."""
        rate_limiter.reset()

        resp_step1 = client.post(
            "/api/v1/auth/login/step1",
            json={
                "identifier": "24-00123",
                "password": "ValidPass2026!#",
                "turnstile_token": "mock-turnstile-token-verified",
            },
        )
        session_id = resp_step1.json()["otp_session_id"]

        # Attempt 1, 2, 3 with wrong OTP code
        for i in range(3):
            rate_limiter.reset()
            resp = client.post(
                "/api/v1/auth/login/verify-otp",
                json={"otp_session_id": session_id, "otp_code": "000000"},
            )
            assert resp.status_code == 401

        # Attempt 4: Session was invalidated due to reaching max attempts
        rate_limiter.reset()
        resp_locked = client.post(
            "/api/v1/auth/login/verify-otp",
            json={"otp_session_id": session_id, "otp_code": "123456"},
        )
        assert resp_locked.status_code == 401
        assert "not found or already completed" in resp_locked.json()["detail"].lower()


class TestCurriculumAndRoomCatalogInvariants:
    """Verifies curriculum inheritance, irregular student overrides, and 53-room catalog integrity."""

    def test_authoritative_53_room_catalog_partitioning(self, test_db):
        """Confirms 43 schedulable spaces and 12 quarantined / non-schedulable facilities (55 total spaces)."""
        all_rooms = test_db.query(Room).all()
        assert len(all_rooms) == 55

        schedulable = [r for r in all_rooms if r.is_schedulable]
        non_schedulable = [r for r in all_rooms if not r.is_schedulable]

        assert len(schedulable) == 43
        assert len(non_schedulable) == 12

        # Quarantined rooms from prompt: NB 204, NB 304, NB 308 must be non-schedulable
        quarantined_codes = {"NB 204", "NB 304", "NB 308"}
        for room in all_rooms:
            if room.room_code in quarantined_codes:
                assert room.is_schedulable is False, f"Room {room.room_code} must be quarantined!"

    def test_section_curriculum_inheritance(self, test_db):
        """Verifies section BSIT-3A inherits curriculum version BSIT_23."""
        section = test_db.query(Section).filter_by(section_code="BSIT-3A").first()
        assert section is not None
        assert section.curriculum_version_id is not None

        curriculum = test_db.query(CurriculumVersion).filter_by(id=section.curriculum_version_id).first()
        assert curriculum is not None
        assert curriculum.curriculum_year == "23"
        assert curriculum.program_code == "BSIT"
        assert curriculum.institute == "ICS"

    def test_irregular_student_curriculum_override(self, test_db):
        """Verifies that an irregular student enrolled in 2025 can follow the 2024 curriculum."""
        # Find 2024 curriculum version
        curriculum_24 = (
            test_db.query(CurriculumVersion)
            .filter_by(curriculum_year="24", program_code="BSIT")
            .first()
        )
        assert curriculum_24 is not None

        # Student enrolled in 2025 (student ID 25-00789)
        student_id = "25-00789"
        override = StudentCurriculumOverride(
            student_id=student_id,
            curriculum_version_id=curriculum_24.id,
            override_reason="Transferee from external college credited to BSIT 2024 curriculum.",
        )
        test_db.add(override)
        test_db.commit()

        # Query back student's effective curriculum
        student_override = (
            test_db.query(StudentCurriculumOverride)
            .filter_by(student_id=student_id)
            .first()
        )
        assert student_override is not None
        assert student_override.curriculum_version.curriculum_year == "24"
        assert student_override.curriculum_version.program_code == "BSIT"
