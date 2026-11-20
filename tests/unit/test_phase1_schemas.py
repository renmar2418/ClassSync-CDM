"""Unit Test Suite for ClassSync Phase 1: Contracts & Database Schemas.
Official Project Title: ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System

Verifies:
1. Pydantic V2 schema validation and constraints.
2. Deterministic zero-regex student ID parsing (strictly 24-XXXXX, no '@').
3. Faculty institutional email validation (@pnm.edu.ph, rejecting @cdm.edu.ph and @gmail.com).
4. 100% full-time faculty mandate (rejection of part-time, adjunct).
5. Strictly UNIFIED cohort mode (rejection of sub-batch splitting).
6. Discrete 30-minute interval slot bounds (0-23, duration >= 1, start + duration <= 24).
7. PostgreSQL 16 / SQLAlchemy 2.0 declarative models and relational mapping.
8. Spatial quarantine filter (exclusion of NB 204, NB 304, NB 308 from is_schedulable=True).
9. Room exclusivity (PRRC 108 locked to BSED_SCIENCE).
10. Idempotent institutional seed data execution.
"""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from classync_contracts.enums import (
    RoomType,
    DayOfWeek,
    CohortMode,
    EmploymentTier,
    UserRole,
    WorkstationStatus,
    LaboratorySessionState,
    SolverStatus,
)
from classync_contracts.security import (
    hash_password,
    verify_password,
)
from classync_contracts.schemas import (
    validate_student_id_deterministic,
    validate_faculty_institutional_email,
    AcademicPeriodBase,
    AcademicPeriodCreate,
    AcademicPeriodSchema,
    RoomBase,
    RoomCreate,
    RoomSchema,
    RoomFilterQuery,
    CurriculumSubjectBase,
    CurriculumSubjectCreate,
    CurriculumSubjectSchema,
    FacultyProfileBase,
    FacultyProfileCreate,
    FacultyProfileSchema,
    SectionBase,
    SectionCreate,
    SectionSchema,
    CourseOfferingBase,
    CourseOfferingCreate,
    CourseOfferingSchema,
    TimetableEntryBase,
    TimetableEntryCreate,
    TimetableEntrySchema,
    TimetableGridSlot,
    WorkstationBase,
    WorkstationCreate,
    WorkstationSchema,
    WorkstationClaim,
    PresenceLogBase,
    PresenceLogCreate,
    PresenceLogSchema,
    CheckInRequest,
    CheckOutRequest,
    TurnstileVerifyRequest,
    TurnstileVerifyResponse,
    GoogleOAuthTokenRequest,
    GoogleTokenClaims,
    PasswordSetupRequest,
    PasswordIntegrityResponse,
    LocalLoginRequest,
    AuthTokenResponse,
    SessionUser,
    LiveRoomVacancyEvent,
    WorkstationStateEvent,
    SolverRunRequest,
    SolverRunResponse,
    DeltaSolveRequest,
    DeltaSolveResponse,
    ConflictReport,
)
from classync_contracts.models import (
    Base,
    AcademicPeriod,
    Room,
    CurriculumSubject,
    FacultyProfile,
    Section,
    CourseOffering,
    TimetableEntry,
    Workstation,
    PresenceLog,
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


# ===========================================================================
# 1. Zero-Regex Deterministic Student ID Validator Tests
# ===========================================================================

class TestZeroRegexStudentIdValidation:
    """Verifies Decision Log D-02: Zero-Regex deterministic validation for student ID (24-XXXXX)."""

    def test_valid_student_ids(self):
        valid_ids = ["24-00123", "24-99999", "24-00001", "24-12345", "22-00001", "23-00123", "25-00123", "26-00123"]
        for sid in valid_ids:
            assert validate_student_id_deterministic(sid) == sid

    def test_invalid_prefix_rejected(self):
        with pytest.raises(ValueError, match="Student IDs must look like 24-00123"):
            validate_student_id_deterministic("19-00123")
        with pytest.raises(ValueError, match="Student IDs must look like 24-00123"):
            validate_student_id_deterministic("AB-00123")

    def test_invalid_length_too_short(self):
        with pytest.raises(ValueError, match="Student IDs must look like 24-00123"):
            validate_student_id_deterministic("24-123")

    def test_invalid_length_too_long(self):
        with pytest.raises(ValueError, match="Student IDs must look like 24-00123"):
            validate_student_id_deterministic("24-000123")

    def test_email_symbol_rejected(self):
        with pytest.raises(ValueError, match="Student IDs must look like 24-00123"):
            validate_student_id_deterministic("24-00123@student.pnm.edu.ph")

    def test_non_digit_suffix_rejected(self):
        with pytest.raises(ValueError, match="Student IDs must look like 24-00123"):
            validate_student_id_deterministic("24-0012A")

    def test_empty_string_rejected(self):
        with pytest.raises(ValueError, match="Student IDs must look like 24-00123"):
            validate_student_id_deterministic("")

    def test_check_in_request_validates_student_id(self):
        valid_req = CheckInRequest(
            room_code="PRRC 301",
            workstation_number=14,
            student_id="24-00123",
            totp_token="123456",
        )
        assert valid_req.student_id == "24-00123"

        with pytest.raises(ValueError, match="Student IDs must look like 24-00123"):
            CheckInRequest(
                room_code="PRRC 301",
                workstation_number=14,
                student_id="invalid-id",
                totp_token="123456",
            )

    def test_arabic_indic_digits_rejected(self):
        with pytest.raises(ValueError, match="Student IDs must look like 24-00123"):
            validate_student_id_deterministic("24-\u0661\u0662\u0663\u0664\u0665")

    def test_fullwidth_digits_rejected(self):
        with pytest.raises(ValueError, match="Student IDs must look like 24-00123"):
            validate_student_id_deterministic("24-\uff11\uff12\uff13\uff14\uff15")

    def test_superscript_digits_rejected(self):
        with pytest.raises(ValueError, match="Student IDs must look like 24-00123"):
            validate_student_id_deterministic("24-\u00b9\u00b2\u00b3\u2074\u2075")

    def test_devanagari_digits_rejected(self):
        with pytest.raises(ValueError, match="Student IDs must look like 24-00123"):
            validate_student_id_deterministic("24-\u0967\u0968\u0969\u096a\u096b")

    def test_circled_digits_rejected(self):
        with pytest.raises(ValueError, match="Student IDs must look like 24-00123"):
            validate_student_id_deterministic("24-\u2460\u2461\u2462\u2463\u2464")

    def test_check_in_request_rejects_unicode_digits(self):
        with pytest.raises(ValueError, match="Student IDs must look like 24-00123"):
            CheckInRequest(
                room_code="PRRC 301",
                workstation_number=14,
                student_id="24-\u0661\u0662\u0663\u0664\u0665",
                totp_token="123456",
            )


# ===========================================================================
# 2. Institutional Email & 100% Full-Time Faculty Tests
# ===========================================================================

class TestFacultyProfileConstraints:
    """Verifies institutional faculty rules: @pnm.edu.ph domain and 100% FULL_TIME tier."""

    def test_valid_faculty_email(self):
        assert validate_faculty_institutional_email("teacher@pnm.edu.ph") == "teacher@pnm.edu.ph"
        assert validate_faculty_institutional_email("ADMIN@PNM.EDU.PH") == "admin@pnm.edu.ph"

    def test_deprecated_cdm_domain_rejected(self):
        with pytest.raises(ValueError, match="Please select your official school Google account"):
            validate_faculty_institutional_email("teacher@cdm.edu.ph")

    def test_personal_gmail_domain_rejected(self):
        with pytest.raises(ValueError, match="Please select your official school Google account"):
            validate_faculty_institutional_email("teacher@gmail.com")

    def test_empty_username_rejected(self):
        with pytest.raises(ValueError, match="Please select your official school Google account"):
            validate_faculty_institutional_email("@pnm.edu.ph")

    def test_multiple_at_symbols_rejected(self):
        with pytest.raises(ValueError, match="Please select your official school Google account"):
            validate_faculty_institutional_email("foo@evil.com@pnm.edu.ph")

    def test_null_byte_in_username_rejected(self):
        with pytest.raises(ValueError, match="Please provide a valid institutional email address"):
            validate_faculty_institutional_email("user\x00@pnm.edu.ph")
        with pytest.raises(ValueError):
            validate_faculty_institutional_email("user@test\x00@pnm.edu.ph")

    def test_whitespace_and_control_chars_in_username_rejected(self):
        invalid_emails = [
            "user name@pnm.edu.ph",
            "user\tname@pnm.edu.ph",
            "user\n@pnm.edu.ph",
            "user\r@pnm.edu.ph",
        ]
        for bad in invalid_emails:
            with pytest.raises(ValueError):
                validate_faculty_institutional_email(bad)

    def test_cyrillic_homoglyphs_in_faculty_email_rejected(self):
        """Deterministically rejects Cyrillic homoglyphs impersonating ASCII characters."""
        bad_emails = [
            "\u0430dmin@pnm.edu.ph",   # Cyrillic small letter a
            "t\u0435acher@pnm.edu.ph", # Cyrillic small letter e
            "pr\u043ef@pnm.edu.ph",    # Cyrillic small letter o
            "f\u0430culty@pnm.edu.ph", # Cyrillic small letter a
        ]
        for bad in bad_emails:
            with pytest.raises(ValueError, match="Please provide a valid institutional email address"):
                validate_faculty_institutional_email(bad)

    def test_zero_width_and_unicode_whitespace_rejected(self):
        """Deterministically rejects zero-width spaces, joiners, and non-breaking spaces."""
        bad_emails = [
            "prof\u200bname@pnm.edu.ph",  # zero-width space
            "prof\xa0name@pnm.edu.ph",   # non-breaking space
            "prof\u200cname@pnm.edu.ph",  # zero-width non-joiner
            "prof\u200dname@pnm.edu.ph",  # zero-width joiner
            "prof\ufeffname@pnm.edu.ph",  # zero-width no-break space (BOM)
        ]
        for bad in bad_emails:
            with pytest.raises(ValueError, match="Please provide a valid institutional email address"):
                validate_faculty_institutional_email(bad)

    def test_html_and_script_injection_in_faculty_email_rejected(self):
        """Deterministically rejects HTML tags and script injections."""
        bad_emails = [
            "user<script>@pnm.edu.ph",
            "user</script>@pnm.edu.ph",
            "user'or'1'='1@pnm.edu.ph",
            'user"test"@pnm.edu.ph',
            "user`test`@pnm.edu.ph",
        ]
        for bad in bad_emails:
            with pytest.raises(ValueError, match="Please provide a valid institutional email address"):
                validate_faculty_institutional_email(bad)

    def test_symbol_boundaries_and_invalid_chars_in_faculty_email_rejected(self):
        """Deterministically rejects usernames starting/ending with symbols or with unapproved characters."""
        bad_emails = [
            ".user@pnm.edu.ph",
            "user.@pnm.edu.ph",
            "_user@pnm.edu.ph",
            "user_@pnm.edu.ph",
            "-user@pnm.edu.ph",
            "user-@pnm.edu.ph",
            "user+tag@pnm.edu.ph",
            "user#admin@pnm.edu.ph",
            "user!test@pnm.edu.ph",
            "user%40@pnm.edu.ph",
        ]
        for bad in bad_emails:
            with pytest.raises(ValueError, match="Please provide a valid institutional email address"):
                validate_faculty_institutional_email(bad)

    def test_valid_faculty_emails_with_allowed_symbols(self):
        """Accepts valid ASCII alphanumeric emails with dots, underscores, and hyphens."""
        valid_emails = [
            "john.doe@pnm.edu.ph",
            "john_doe@pnm.edu.ph",
            "john-doe@pnm.edu.ph",
            "j.d.prof-2@pnm.edu.ph",
        ]
        for valid in valid_emails:
            assert validate_faculty_institutional_email(valid) == valid

    def test_faculty_profile_creation_valid(self):
        fac = FacultyProfileBase(
            institutional_email="prof.nat@pnm.edu.ph",
            full_name="Prof. Nathaniel Nat",
            employment_tier=EmploymentTier.FULL_TIME,
            role=UserRole.FACULTY,
        )
        assert fac.employment_tier == "FULL_TIME"
        assert fac.institutional_email == "prof.nat@pnm.edu.ph"

    def test_part_time_faculty_rejected(self):
        with pytest.raises(ValueError):
            FacultyProfileBase(
                institutional_email="prof.parttime@pnm.edu.ph",
                full_name="Prof. Part Time",
                employment_tier="PART_TIME",  # type: ignore
                role=UserRole.FACULTY,
            )

    def test_adjunct_faculty_rejected(self):
        with pytest.raises(ValueError):
            FacultyProfileBase(
                institutional_email="prof.adjunct@pnm.edu.ph",
                full_name="Prof. Adjunct",
                employment_tier="ADJUNCT",  # type: ignore
                role=UserRole.FACULTY,
            )

    def test_invalid_role_on_faculty_profile_rejected(self):
        with pytest.raises(ValueError):
            FacultyProfileBase(
                institutional_email="user@pnm.edu.ph",
                full_name="Student User",
                employment_tier=EmploymentTier.FULL_TIME,
                role=UserRole.STUDENT,  # Faculty profile must be ADMIN or FACULTY
            )


# ===========================================================================
# 3. Timetable Continuous Slot Interval & Unified Cohort Tests
# ===========================================================================

class TestTimetableSlotAndCohortConstraints:
    """Verifies continuous 30-min interval boundaries (0-23) and UNIFIED cohort mode."""

    def test_valid_timetable_slot_entry(self):
        entry = TimetableEntryBase(
            offering_id=uuid.uuid4(),
            room_code="PRRC 301",
            day_of_week=DayOfWeek.MONDAY,
            start_slot=0,       # 07:00
            duration_slots=6,   # 3 hours (07:00 - 10:00)
            cohort_mode=CohortMode.UNIFIED,
            revision_hash="abc123sha",
        )
        assert entry.start_slot == 0
        assert entry.duration_slots == 6
        assert entry.cohort_mode == "UNIFIED"

    def test_boundary_slot_sum_24_valid(self):
        # 17:00 to 19:00 = slot 20 to slot 24 (duration = 4)
        entry = TimetableEntryBase(
            offering_id=uuid.uuid4(),
            room_code="PRRC 201",
            day_of_week=DayOfWeek.FRIDAY,
            start_slot=20,
            duration_slots=4,
            cohort_mode=CohortMode.UNIFIED,
            revision_hash="revhash",
        )
        assert entry.start_slot + entry.duration_slots == 24

    def test_slot_overflow_exceeding_19_00_rejected(self):
        # start_slot 22 (18:00) + duration 4 (2 hours) = 26 > 24
        with pytest.raises(ValueError, match="exceed operating window"):
            TimetableEntryBase(
                offering_id=uuid.uuid4(),
                room_code="PRRC 201",
                day_of_week=DayOfWeek.WEDNESDAY,
                start_slot=22,
                duration_slots=4,
                cohort_mode=CohortMode.UNIFIED,
                revision_hash="revhash",
            )

    def test_invalid_start_slot_negative(self):
        with pytest.raises(ValueError):
            TimetableEntryBase(
                offering_id=uuid.uuid4(),
                room_code="PRRC 201",
                day_of_week=DayOfWeek.MONDAY,
                start_slot=-1,
                duration_slots=2,
                cohort_mode=CohortMode.UNIFIED,
                revision_hash="hash",
            )

    def test_invalid_start_slot_greater_than_23(self):
        with pytest.raises(ValueError):
            TimetableEntryBase(
                offering_id=uuid.uuid4(),
                room_code="PRRC 201",
                day_of_week=DayOfWeek.MONDAY,
                start_slot=24,
                duration_slots=2,
                cohort_mode=CohortMode.UNIFIED,
                revision_hash="hash",
            )

    def test_invalid_duration_zero(self):
        with pytest.raises(ValueError):
            TimetableEntryBase(
                offering_id=uuid.uuid4(),
                room_code="PRRC 201",
                day_of_week=DayOfWeek.MONDAY,
                start_slot=10,
                duration_slots=0,
                cohort_mode=CohortMode.UNIFIED,
                revision_hash="hash",
            )

    def test_split_cohort_prohibited(self):
        with pytest.raises(ValueError):
            TimetableEntryBase(
                offering_id=uuid.uuid4(),
                room_code="PRRC 201",
                day_of_week=DayOfWeek.MONDAY,
                start_slot=10,
                duration_slots=4,
                cohort_mode="SPLIT_BATCH",  # type: ignore
                revision_hash="hash",
            )


# ===========================================================================
# 4. Security & Turnstile DTO Tests
# ===========================================================================

class TestSecurityContracts:
    """Verifies Turnstile, password matching, and session DTOs."""

    def test_turnstile_response(self):
        resp_success = TurnstileVerifyResponse(success=True)
        assert resp_success.success is True

        resp_fail = TurnstileVerifyResponse(success=False, error_codes=["invalid-input-response"])
        assert resp_fail.success is False
        assert "invalid-input-response" in resp_fail.error_codes

    def test_password_setup_mismatch_rejected(self):
        with pytest.raises(ValueError, match="do not match"):
            PasswordSetupRequest(
                student_or_employee_id="24-00123",
                new_password="SuperSecretPassword2026!",
                confirm_password="DifferentPassword2026!",
            )

    def test_password_setup_matching_valid(self):
        req = PasswordSetupRequest(
            student_or_employee_id="24-00123",
            new_password="SuperSecretPassword2026!",
            confirm_password="SuperSecretPassword2026!",
        )
        assert req.new_password == req.confirm_password

    def test_hash_password_asvs_conformance(self):
        """Verifies hash_password produces OWASP ASVS 4.0 compliant Argon2id hashes."""
        plain = "PassSync2026!#Strong"
        hashed = hash_password(plain)
        assert hashed.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
        assert len(hashed) > 50

    def test_verify_password_standard_flow(self):
        """Verifies verify_password with correct, incorrect, and empty passwords."""
        plain = "CdMClassSync2026$#@"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True
        assert verify_password("WrongPassword123!", hashed) is False
        assert verify_password("", hashed) is False

    def test_verify_password_bidirectional_signature(self):
        """Verifies that verify_password supports both (plain, hash) and (hash, plain) parameter orders."""
        plain = "BidirectionalCheck2026!"
        hashed = hash_password(plain)
        assert verify_password(plain_password=plain, hashed_password=hashed) is True
        assert verify_password(plain_password=hashed, hashed_password=plain) is True

    def test_verify_password_seed_hashes(self):
        """Verifies pre-generated seed hashes for admin and faculty credentials."""
        admin_hash = _seed_module.ADMIN_ARGON2_HASH
        faculty_hash = _seed_module.FACULTY_ARGON2_HASH
        assert verify_password("CdMAdmin2026!", admin_hash) is True
        assert verify_password("IncorrectAdminPass", admin_hash) is False
        assert verify_password("FacultyPass2026!", faculty_hash) is True
        assert verify_password("IncorrectFacultyPass", faculty_hash) is False

    def test_verify_password_edge_cases_and_invalid_inputs(self):
        """Verifies verify_password safely rejects invalid hashes and non-string inputs."""
        assert verify_password("password", "not_a_valid_argon2_hash") is False
        assert verify_password("password", "$argon2id$v=19$m=65536,t=3,p=4$corrupted$salt") is False
        assert verify_password(None, "$argon2id$v=19$m=65536,t=3,p=4$abc$def") is False  # type: ignore
        assert verify_password("password", None) is False  # type: ignore


# ===========================================================================
# 5. SQLAlchemy 2.0 ORM & Database Relational Mapping Tests
# ===========================================================================

@pytest.fixture
def db_session():
    """Provides a fresh in-memory SQLite database session configured with ClassSync metadata."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()
    yield session
    session.close()


class TestSQLAlchemyDeclarativeModels:
    """Verifies SQLAlchemy 2.0 models, relationships, spatial quarantine, and seed execution."""

    def test_all_9_tables_exist_in_metadata(self):
        expected_tables = {
            "academic_period",
            "room",
            "curriculum_subject",
            "faculty_profile",
            "section",
            "course_offering",
            "timetable_entry",
            "workstation",
            "presence_log",
            "curriculum_version",
            "student_curriculum_override",
            "student_profile",
        }
        assert expected_tables == set(Base.metadata.tables.keys())

    def test_insert_and_query_academic_period(self, db_session: Session):
        period = AcademicPeriod(
            id=uuid.uuid4(),
            academic_year="2026-2027",
            semester=1,
            is_active=True,
        )
        db_session.add(period)
        db_session.commit()

        retrieved = db_session.get(AcademicPeriod, period.id)
        assert retrieved is not None
        assert retrieved.academic_year == "2026-2027"
        assert retrieved.semester == 1
        assert retrieved.is_active is True

    def test_spatial_quarantine_exclusion_query(self, db_session: Session):
        """Verifies Decision Log D-05: NB 204, NB 304, NB 308 are flagged is_schedulable=False."""
        # Insert schedulable rooms
        schedulable_room = Room(
            room_code="PRRC 301",
            building_name="PRRC Building",
            floor_level=3,
            room_type="COMPUTER_LAB",
            capacity=50,
            is_schedulable=True,
        )
        # Insert quarantined administrative rooms
        nb204 = Room(
            room_code="NB 204",
            building_name="New Building",
            floor_level=2,
            room_type="LECTURE",
            capacity=15,
            is_schedulable=False,  # Quarantined
        )
        nb304 = Room(
            room_code="NB 304",
            building_name="New Building",
            floor_level=3,
            room_type="LECTURE",
            capacity=15,
            is_schedulable=False,  # Quarantined
        )
        nb308 = Room(
            room_code="NB 308",
            building_name="New Building",
            floor_level=3,
            room_type="LECTURE",
            capacity=20,
            is_schedulable=False,  # Quarantined
        )
        db_session.add_all([schedulable_room, nb204, nb304, nb308])
        db_session.commit()

        # Execute quarantine directory filter query
        schedulable_query = select(Room.room_code).where(Room.is_schedulable.is_(True))
        visible_rooms = db_session.scalars(schedulable_query).all()

        assert "PRRC 301" in visible_rooms
        assert "NB 204" not in visible_rooms
        assert "NB 304" not in visible_rooms
        assert "NB 308" not in visible_rooms

    def test_prrc_108_exclusivity_lock(self, db_session: Session):
        """Verifies room PRRC 108 exclusivity locked to BSED_SCIENCE."""
        prrc108 = Room(
            room_code="PRRC 108",
            building_name="PRRC Building",
            floor_level=1,
            room_type="LECTURE",
            capacity=70,
            is_schedulable=True,
            exclusive_program="BSED_SCIENCE",
        )
        db_session.add(prrc108)
        db_session.commit()

        retrieved = db_session.get(Room, "PRRC 108")
        assert retrieved is not None
        assert retrieved.exclusive_program == "BSED_SCIENCE"
        assert retrieved.is_schedulable is True

    def test_seed_database_execution_and_idempotency(self, db_session: Session):
        """Verifies institutional seed populates all entities idempotently."""
        counts_first_run = seed_database(db_session)
        assert counts_first_run["academic_periods"] == 1
        assert counts_first_run["rooms"] == 55
        assert counts_first_run["workstations"] == 270
        assert counts_first_run["subjects"] == 10
        assert counts_first_run["faculty"] == 7
        assert counts_first_run["sections"] == 3
        assert counts_first_run["offerings"] == 4
        assert counts_first_run["students"] == 6

        # Verify quarantined spaces are strictly excluded from schedulable queries
        schedulable_rooms = db_session.scalars(
            select(Room.room_code).where(Room.is_schedulable.is_(True))
        ).all()
        quarantined_rooms = ["NB 204", "NB 304", "NB 308", "PROPERTY_OFFICE", "CAMPUS_CANTEEN"]
        for qroom in quarantined_rooms:
            assert qroom not in schedulable_rooms

        # Second seed run must be idempotent (0 new records added)
        counts_second_run = seed_database(db_session)
        for key, val in counts_second_run.items():
            assert val == 0, f"Expected 0 additions on second run for {key}, got {val}"

    def test_presence_log_relationship_cascade(self, db_session: Session):
        """Verifies Workstation and Room mapping to PresenceLog."""
        room = Room(
            room_code="PRRC 301",
            building_name="PRRC Building",
            floor_level=3,
            room_type="COMPUTER_LAB",
            capacity=50,
            is_schedulable=True,
        )
        db_session.add(room)
        db_session.flush()

        ws = Workstation(
            id=uuid.uuid4(),
            room_code="PRRC 301",
            workstation_number=14,
            is_operational=True,
        )
        db_session.add(ws)
        db_session.flush()

        presence = PresenceLog(
            id=uuid.uuid4(),
            room_code="PRRC 301",
            workstation_number=14,
            student_id="24-00123",
            session_id=uuid.uuid4(),
            totp_verified=True,
        )
        db_session.add(presence)
        db_session.commit()

        retrieved_presence = db_session.get(PresenceLog, presence.id)
        assert retrieved_presence is not None
        assert retrieved_presence.student_id == "24-00123"
        assert retrieved_presence.room.room_code == "PRRC 301"
        assert retrieved_presence.workstation.workstation_number == 14

    def test_database_check_constraint_semester(self, db_session: Session):
        """Database check constraint rejects semester outside (1, 2, 3)."""
        from sqlalchemy.exc import IntegrityError
        invalid_period = AcademicPeriod(
            id=uuid.uuid4(),
            academic_year="2026-2027",
            semester=4,  # Invalid: only 1, 2, 3 allowed
            is_active=False,
        )
        db_session.add(invalid_period)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_database_check_constraint_employment_tier(self, db_session: Session):
        """Database check constraint rejects non-FULL_TIME faculty."""
        from sqlalchemy.exc import IntegrityError
        invalid_fac = FacultyProfile(
            id=uuid.uuid4(),
            institutional_email="adjunct@pnm.edu.ph",
            full_name="Adjunct Faculty",
            employment_tier="ADJUNCT",  # Invalid
            password_hash="argon2hash",
            requires_password_change=True,
            is_active=True,
            role="FACULTY",
        )
        db_session.add(invalid_fac)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_database_check_constraint_timetable_slot_boundary(self, db_session: Session):
        """Database check constraint rejects timetable entries exceeding slot boundary 24."""
        from sqlalchemy.exc import IntegrityError
        # First create valid dependencies
        period = AcademicPeriod(id=uuid.uuid4(), academic_year="2026-2027", semester=1)
        room = Room(room_code="PRRC 201", building_name="PRRC", floor_level=2, room_type="LECTURE", capacity=60)
        subj = CurriculumSubject(id=uuid.uuid4(), subject_code="TEST-101", descriptive_title="Test", required_room_type="LECTURE")
        fac = FacultyProfile(id=uuid.uuid4(), institutional_email="testfac@pnm.edu.ph", full_name="Test Fac", password_hash="hash")
        sec = Section(id=uuid.uuid4(), academic_period_id=period.id, section_code="TEST-SEC", year_level=1, enrolled_student_count=60)
        offering = CourseOffering(id=uuid.uuid4(), academic_period_id=period.id, subject_id=subj.id, section_id=sec.id, faculty_id=fac.id)
        db_session.add_all([period, room, subj, fac, sec, offering])
        db_session.flush()

        # Slot 22 + duration 4 = 26 > 24
        invalid_entry = TimetableEntry(
            id=uuid.uuid4(),
            offering_id=offering.id,
            room_code=room.room_code,
            day_of_week=0,
            start_slot=22,
            duration_slots=4,
            cohort_mode="UNIFIED",
            revision_hash="hash",
        )
        db_session.add(invalid_entry)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_database_check_constraint_student_id_format(self, db_session: Session):
        """Database check constraint rejects presence log with invalid student ID format on SQLite."""
        from sqlalchemy.exc import IntegrityError
        room = Room(room_code="PRRC 301", building_name="PRRC", floor_level=3, room_type="COMPUTER_LAB", capacity=50)
        ws = Workstation(id=uuid.uuid4(), room_code="PRRC 301", workstation_number=1, is_operational=True)
        db_session.add_all([room, ws])
        db_session.flush()

        # Test various invalid student IDs: alphabetic, short, long, wrong prefix, mixed
        invalid_ids = [
            "invalid-id",
            "24-abcde",
            "24-1234a",
            "24-a2345",
            "24-1a345",
            "24-12a45",
            "24-123a5",
            "24-1234",
            "24-123456",
            "X4-12345",
            "2X-12345",
            "24/12345",
            "24- 1234",
        ]
        for bad_id in invalid_ids:
            invalid_presence = PresenceLog(
                id=uuid.uuid4(),
                room_code="PRRC 301",
                workstation_number=1,
                student_id=bad_id,
                session_id=uuid.uuid4(),
                totp_verified=True,
            )
            db_session.add(invalid_presence)
            with pytest.raises(IntegrityError):
                db_session.commit()
            db_session.rollback()

        # Test valid student IDs succeed (boundaries 00000, 99999, multi-year 22, 23, 24, 25, 26)
        for valid_id in ["24-00000", "24-12345", "24-99999", "22-00001", "23-54321", "25-11111", "26-99999"]:
            valid_presence = PresenceLog(
                id=uuid.uuid4(),
                room_code="PRRC 301",
                workstation_number=1,
                student_id=valid_id,
                session_id=uuid.uuid4(),
                totp_verified=True,
            )
            db_session.add(valid_presence)
            db_session.commit()
            retrieved = db_session.get(PresenceLog, valid_presence.id)
            assert retrieved is not None
            assert retrieved.student_id == valid_id

    def test_database_check_constraint_postgresql_ddl_compilation(self):
        """Verifies that PresenceLog DDL generates valid ANSI SQL on PostgreSQL dialect without SQLite GLOB."""
        from sqlalchemy.schema import CreateTable
        from sqlalchemy.dialects import postgresql

        table = PresenceLog.__table__
        ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))
        assert "GLOB" not in ddl
        assert "substr(student_id, 3, 1) = '-'" in ddl
        assert "substr(student_id, 4, 1) BETWEEN '0' AND '9'" in ddl
        assert "substr(student_id, 8, 1) BETWEEN '0' AND '9'" in ddl
        assert "chk_presence_student_id_format" in ddl


# ===========================================================================
# 6. TypeScript Contract Parity Verification Test
# ===========================================================================

class TestTypeScriptContractParity:
    """Verifies that TypeScript definitions in packages/shared-types-ts reflect 1:1 schema parity."""

    def test_typescript_models_file_exists_and_contains_core_interfaces(self):
        ts_models_path = Path(__file__).resolve().parents[2] / "packages" / "shared-types-ts" / "src" / "models.ts"
        assert ts_models_path.exists(), f"models.ts not found at {ts_models_path}"
        content = ts_models_path.read_text(encoding="utf-8")

        # Check core interfaces
        core_interfaces = [
            "interface AcademicPeriod",
            "interface Room",
            "interface CurriculumSubject",
            "interface FacultyProfile",
            "interface Section",
            "interface CourseOffering",
            "interface TimetableEntry",
            "interface Workstation",
            "interface PresenceLog",
            "interface CheckInRequest",
            "interface TurnstileVerifyRequest",
            "interface TurnstileVerifyResponse",
            "interface GoogleTokenClaims",
            "interface SessionUser",
            "interface LiveRoomVacancyEvent",
            "interface WorkstationStateEvent",
            "interface SolverRunRequest",
            "interface SolverRunResponse",
            "interface DeltaSolveRequest",
            "interface DeltaSolveResponse",
        ]
        for iface in core_interfaces:
            assert iface in content, f"Expected {iface} in TypeScript models"

        # Check core enum literals
        core_types = [
            "type RoomType =",
            "type CohortMode = 'UNIFIED'",
            "type EmploymentTier = 'FULL_TIME'",
            "type UserRole = 'ADMIN' | 'FACULTY' | 'STUDENT'",
        ]
        for tdef in core_types:
            assert tdef in content, f"Expected {tdef} in TypeScript models"

    def test_typescript_errors_file_exists_and_contains_jargon_free_messages(self):
        ts_errors_path = Path(__file__).resolve().parents[2] / "packages" / "shared-types-ts" / "src" / "errors.ts"
        assert ts_errors_path.exists(), f"errors.ts not found at {ts_errors_path}"
        content = ts_errors_path.read_text(encoding="utf-8")

        # Check empathetic plain-language copy from Section 7.2 of SYSTEM_DESIGN_BLUEPRINT.md
        assert "was just claimed by a classmate!" in content
        assert "The QR code just refreshed!" in content
        assert "Student IDs must look like 24-00123" in content
        assert "Please select your official school Google account" in content
        assert "Offline Mode • Showing your saved schedule" in content

