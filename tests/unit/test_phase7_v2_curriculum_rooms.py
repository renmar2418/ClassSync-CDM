"""Unit tests for ClassSync V2 Schema Evolution:
- Multi-Year Student IDs (22-XXXXX to 26-XXXXX)
- Authoritative 53 Room Inventory Verification
- Curriculum Versioning & Irregular Student Overrides
"""

import uuid
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from classync_contracts.enums import RoomType, UserRole
from classync_contracts.models import (
    Base,
    Room,
    Workstation,
    CurriculumVersion,
    StudentCurriculumOverride,
    Section,
)
from classync_contracts.schemas import (
    validate_student_id_deterministic,
    CurriculumVersionCreate,
    CurriculumVersionSchema,
    StudentCurriculumOverrideCreate,
    StudentCurriculumOverrideSchema,
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


@pytest.fixture
def memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    seed_database(session)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


class TestMultiYearStudentIdValidation:
    """Verifies student ID validation across cohorts 2022 to 2026+."""

    def test_cohorts_22_to_26_valid(self):
        valid_ids = [
            "22-00001",
            "23-12345",
            "24-00123",
            "25-99999",
            "26-00001",
        ]
        for sid in valid_ids:
            assert validate_student_id_deterministic(sid) == sid

    def test_invalid_cohort_year_below_20_rejected(self):
        with pytest.raises(ValueError, match="Student IDs must look like 24-00123"):
            validate_student_id_deterministic("19-00123")

    def test_alphabetic_cohort_prefix_rejected(self):
        with pytest.raises(ValueError, match="Student IDs must look like 24-00123"):
            validate_student_id_deterministic("AB-00123")

    def test_invalid_length_rejected(self):
        with pytest.raises(ValueError, match="Student IDs must look like 24-00123"):
            validate_student_id_deterministic("24-123")
        with pytest.raises(ValueError, match="Student IDs must look like 24-00123"):
            validate_student_id_deterministic("24-123456")

    def test_at_symbol_rejected(self):
        with pytest.raises(ValueError, match="Student IDs must look like 24-00123"):
            validate_student_id_deterministic("24-00123@student.pnm.edu.ph")


class TestAuthoritativeRoomInventory:
    """Verifies the 53-space verified inventory from cdm-room-inventory.md."""

    def test_total_rooms_count(self, memory_db):
        rooms = memory_db.scalars(select(Room)).all()
        # 53 cataloged rooms + 2 legacy backward-compatibility entries = 55 in seed
        assert len(rooms) >= 53

    def test_schedulable_lecture_rooms(self, memory_db):
        # Verify PRRC lecture classrooms
        for code in ["PRRC 103", "PRRC 105", "PRRC 106", "PRRC 107", "PRRC 201", "PRRC 202", "PRRC 203", "PRRC 206", "PRRC 207", "PRRC 208", "PRRC 209", "PRRC 309", "PRRC 310"]:
            r = memory_db.get(Room, code)
            assert r is not None, f"Room {code} should exist"
            assert r.is_schedulable is True
            assert r.room_type == RoomType.LECTURE

        # Verify New Building lecture classrooms
        for code in ["NB 101", "NB 102", "NB 103", "NB 104", "NB 105", "NB 106", "NB 107", "NB 201", "NB 202", "NB 203", "NB 205", "NB 206", "NB 207", "NB 208", "NB 301", "NB 302", "NB 303", "NB 305", "NB 306", "NB 307"]:
            r = memory_db.get(Room, code)
            assert r is not None, f"Room {code} should exist"
            assert r.is_schedulable is True
            assert r.room_type == RoomType.LECTURE

    def test_quarantined_spaces_are_non_schedulable(self, memory_db):
        """NB 204 (ITE Faculty Room), NB 304 (Joint Faculty Room), NB 308 (Faculty Lounge) must be non-schedulable."""
        for code in ["NB 204", "NB 304", "NB 308"]:
            r = memory_db.get(Room, code)
            assert r is not None, f"Quarantined space {code} must exist in inventory"
            assert r.is_schedulable is False, f"Room {code} must have is_schedulable=False"

        # Specialized PRRC non-schedulable spaces
        for code in ["PRRC 101", "PRRC 102", "PRRC 104", "PRRC 204", "PRRC 205", "PRRC 305", "PRRC 306"]:
            r = memory_db.get(Room, code)
            assert r is not None, f"Space {code} must exist"
            assert r.is_schedulable is False

    def test_prrc108_locked_to_bsed_science(self, memory_db):
        prrc108 = memory_db.get(Room, "PRRC 108")
        assert prrc108 is not None
        assert prrc108.room_type == RoomType.SCIENCE_LAB
        assert prrc108.exclusive_program == "BSED_SCIENCE"
        assert prrc108.is_schedulable is True

    def test_athletic_spaces_cataloged(self, memory_db):
        court = memory_db.get(Room, "Court")
        assert court is not None
        assert court.room_type == RoomType.SPORTS_COURT
        assert court.is_schedulable is True

        oval = memory_db.get(Room, "Oval")
        assert oval is not None
        assert oval.room_type == RoomType.SPORTS_OVAL
        assert oval.is_schedulable is True

    def test_comlab_workstations_seeded(self, memory_db):
        for code in ["PRRC 302", "PRRC 304", "PRRC 307", "PRRC 308"]:
            ws_list = memory_db.scalars(
                select(Workstation).where(Workstation.room_code == code)
            ).all()
            assert len(ws_list) == 45, f"COMLAB {code} should have 45 operational workstations"


class TestCurriculumVersioningAndOverrides:
    """Verifies curriculum versions and irregular student override resolution."""

    def test_curriculum_versions_seeded_across_institutes(self, memory_db):
        cvs = memory_db.scalars(select(CurriculumVersion)).all()
        assert len(cvs) >= 30

        # Check ICS
        bsit_23 = memory_db.scalar(
            select(CurriculumVersion).where(
                CurriculumVersion.program_code == "BSIT",
                CurriculumVersion.curriculum_year == "23",
            )
        )
        assert bsit_23 is not None
        assert bsit_23.institute == "ICS"

        # Check ITE
        bsed_sci_25 = memory_db.scalar(
            select(CurriculumVersion).where(
                CurriculumVersion.program_code == "BSED_SCIENCE",
                CurriculumVersion.curriculum_year == "25",
            )
        )
        assert bsed_sci_25 is not None
        assert bsed_sci_25.institute == "ITE"
        assert bsed_sci_25.is_current is True

        # Check IBE
        bsba_hrm_24 = memory_db.scalar(
            select(CurriculumVersion).where(
                CurriculumVersion.program_code == "BSBA_HRM",
                CurriculumVersion.curriculum_year == "24",
            )
        )
        assert bsba_hrm_24 is not None
        assert bsba_hrm_24.institute == "IBE"

    def test_section_curriculum_inheritance(self, memory_db):
        sec = memory_db.scalar(select(Section).where(Section.section_code == "BSIT-3A"))
        assert sec is not None
        assert sec.curriculum_version is not None
        assert sec.curriculum_version.curriculum_year == "23"
        assert sec.curriculum_version.program_code == "BSIT"

    def test_irregular_student_curriculum_override(self, memory_db):
        """Irregular student enrolled in cohort 24 overrides default to Curriculum 22."""
        cv_22_bsit = memory_db.scalar(
            select(CurriculumVersion).where(
                CurriculumVersion.program_code == "BSIT",
                CurriculumVersion.curriculum_year == "22",
            )
        )
        assert cv_22_bsit is not None

        # Create student override
        override = StudentCurriculumOverride(
            id=uuid.uuid4(),
            student_id="24-00555",
            curriculum_version_id=cv_22_bsit.id,
            override_reason="Transferee from other university with credited units",
        )
        memory_db.add(override)
        memory_db.commit()

        # Query and resolve effective curriculum
        student_id = "24-00555"
        student_override = memory_db.scalar(
            select(StudentCurriculumOverride).where(StudentCurriculumOverride.student_id == student_id)
        )
        assert student_override is not None
        assert student_override.curriculum_version.curriculum_year == "22"
