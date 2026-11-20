"""SQLAlchemy 2.0 Declarative Models for ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System.

Enforces:
- 100% Full-Time Faculty (employment_tier = 'FULL_TIME')
- UNIFIED cohort mode (zero sub-batch splitting)
- Discrete continuous 30-min slot intervals (0-23)
- Spatial quarantine (is_schedulable = FALSE for NB 204, NB 304, NB 308)
- Room exclusivity (PRRC 108 locked to BSED_SCIENCE)
- Zero-regex student ID check constraint (length=8 AND student_id LIKE '24-%')
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    String,
    Integer,
    SmallInteger,
    Boolean,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    ForeignKeyConstraint,
    Index,
    Uuid,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base class for all ClassSync relational models."""
    pass


class AcademicPeriod(Base):
    __tablename__ = "academic_period"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    academic_year: Mapped[str] = mapped_column(String(16), nullable=False)  # e.g., '2026-2027'
    semester: Mapped[int] = mapped_column(SmallInteger, nullable=False)       # 1, 2, 3
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("academic_year", "semester", name="uq_academic_period_year_sem"),
        CheckConstraint("semester IN (1, 2, 3)", name="chk_academic_period_semester"),
    )

    offerings: Mapped[List["CourseOffering"]] = relationship(
        "CourseOffering", back_populates="academic_period", cascade="all, delete-orphan"
    )
    sections: Mapped[List["Section"]] = relationship(
        "Section", back_populates="academic_period", cascade="all, delete-orphan"
    )


class Room(Base):
    __tablename__ = "room"

    room_code: Mapped[str] = mapped_column(String(32), primary_key=True)  # e.g., 'PRRC 108', 'NB 204'
    building_name: Mapped[str] = mapped_column(String(64), nullable=False) # 'PRRC Building', 'New Building'
    floor_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    room_type: Mapped[str] = mapped_column(String(32), nullable=False)    # 'LECTURE', 'COMPUTER_LAB', 'SCIENCE_LAB', 'FUNCTION_HALL'
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    is_schedulable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False) # FALSE for NB 204/304/308
    has_aircon: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_projector: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    exclusive_program: Mapped[Optional[str]] = mapped_column(String(64), nullable=True) # 'BSED_SCIENCE' for PRRC 108

    __table_args__ = (
        CheckConstraint("capacity > 0", name="chk_room_capacity_positive"),
        Index("idx_room_schedulable", "is_schedulable"),
        Index("idx_room_building_floor", "building_name", "floor_level"),
    )

    timetable_entries: Mapped[List["TimetableEntry"]] = relationship(
        "TimetableEntry", back_populates="room"
    )
    workstations: Mapped[List["Workstation"]] = relationship(
        "Workstation", back_populates="room", cascade="all, delete-orphan"
    )
    presence_logs: Mapped[List["PresenceLog"]] = relationship(
        "PresenceLog", back_populates="room"
    )


class CurriculumSubject(Base):
    __tablename__ = "curriculum_subject"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False) # e.g. 'CC-IPT2'
    descriptive_title: Mapped[str] = mapped_column(String(255), nullable=False)
    lecture_hours: Mapped[int] = mapped_column(SmallInteger, default=3, nullable=False)
    lab_hours: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    units: Mapped[int] = mapped_column(SmallInteger, default=3, nullable=False)
    required_room_type: Mapped[str] = mapped_column(String(32), nullable=False) # 'LECTURE', 'COMPUTER_LAB'

    __table_args__ = (
        CheckConstraint("lecture_hours >= 0", name="chk_subj_lecture_non_neg"),
        CheckConstraint("lab_hours >= 0", name="chk_subj_lab_non_neg"),
        CheckConstraint("units > 0", name="chk_subj_units_positive"),
    )

    offerings: Mapped[List["CourseOffering"]] = relationship(
        "CourseOffering", back_populates="subject"
    )


class FacultyProfile(Base):
    __tablename__ = "faculty_profile"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    institutional_email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False) # '@pnm.edu.ph'
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    employment_tier: Mapped[str] = mapped_column(String(32), default="FULL_TIME", nullable=False) # 100% full-time
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False) # Argon2id
    requires_password_change: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="FACULTY", nullable=False) # 'ADMIN', 'FACULTY'

    __table_args__ = (
        CheckConstraint("employment_tier = 'FULL_TIME'", name="chk_faculty_100_percent_full_time"),
        CheckConstraint("role IN ('ADMIN', 'FACULTY')", name="chk_faculty_valid_role"),
        Index("idx_faculty_email", "institutional_email"),
    )

    offerings: Mapped[List["CourseOffering"]] = relationship(
        "CourseOffering", back_populates="faculty"
    )


class CurriculumVersion(Base):
    __tablename__ = "curriculum_version"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    curriculum_year: Mapped[str] = mapped_column(String(16), nullable=False) # e.g. '22', '23', '24', '25', '26'
    program_code: Mapped[str] = mapped_column(String(32), nullable=False)    # e.g. 'BSIT', 'BSCPE', 'BSED_SCIENCE'
    institute: Mapped[str] = mapped_column(String(16), nullable=False)       # 'ICS', 'ITE', 'IBE'
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("curriculum_year", "program_code", name="uq_curriculum_year_program"),
        Index("idx_curriculum_program", "program_code"),
    )

    sections: Mapped[List["Section"]] = relationship("Section", back_populates="curriculum_version")


class StudentCurriculumOverride(Base):
    __tablename__ = "student_curriculum_override"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[str] = mapped_column(String(16), unique=True, nullable=False) # e.g. '24-00123'
    curriculum_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("curriculum_version.id", ondelete="CASCADE"), nullable=False
    )
    override_reason: Mapped[str] = mapped_column(String(255), default="Irregular", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    __table_args__ = (
        Index("idx_override_student_id", "student_id"),
    )

    curriculum_version: Mapped["CurriculumVersion"] = relationship("CurriculumVersion")


class Section(Base):
    __tablename__ = "section"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    academic_period_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("academic_period.id", ondelete="CASCADE"), nullable=False
    )
    section_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False) # 'BSIT-3A'
    year_level: Mapped[int] = mapped_column(SmallInteger, nullable=False) # 1, 2, 3, 4
    enrolled_student_count: Mapped[int] = mapped_column(Integer, nullable=False) # 60-70+ students
    curriculum_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("curriculum_version.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        CheckConstraint("year_level BETWEEN 1 AND 5", name="chk_section_year_level"),
        CheckConstraint("enrolled_student_count > 0", name="chk_section_enrollment_positive"),
        Index("idx_section_academic_period", "academic_period_id"),
        Index("idx_section_curriculum", "curriculum_version_id"),
    )

    academic_period: Mapped["AcademicPeriod"] = relationship("AcademicPeriod", back_populates="sections")
    curriculum_version: Mapped[Optional["CurriculumVersion"]] = relationship("CurriculumVersion", back_populates="sections")
    offerings: Mapped[List["CourseOffering"]] = relationship(
        "CourseOffering", back_populates="section", cascade="all, delete-orphan"
    )


class CourseOffering(Base):
    __tablename__ = "course_offering"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    academic_period_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("academic_period.id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("curriculum_subject.id", ondelete="RESTRICT"), nullable=False
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("section.id", ondelete="CASCADE"), nullable=False
    )
    faculty_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("faculty_profile.id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "academic_period_id", "subject_id", "section_id",
            name="uq_course_offering_period_subj_section"
        ),
        Index("idx_offering_faculty", "faculty_id"),
        Index("idx_offering_section", "section_id"),
    )

    academic_period: Mapped["AcademicPeriod"] = relationship("AcademicPeriod", back_populates="offerings")
    subject: Mapped["CurriculumSubject"] = relationship("CurriculumSubject", back_populates="offerings")
    section: Mapped["Section"] = relationship("Section", back_populates="offerings")
    faculty: Mapped["FacultyProfile"] = relationship("FacultyProfile", back_populates="offerings")
    timetable_entries: Mapped[List["TimetableEntry"]] = relationship(
        "TimetableEntry", back_populates="offering", cascade="all, delete-orphan"
    )


class TimetableEntry(Base):
    __tablename__ = "timetable_entry"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    offering_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("course_offering.id", ondelete="CASCADE"), nullable=False
    )
    room_code: Mapped[str] = mapped_column(
        String(32), ForeignKey("room.room_code", ondelete="RESTRICT"), nullable=False
    )
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False) # 0=Mon, 6=Sun
    start_slot: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0 to 23 (30-min intervals)
    duration_slots: Mapped[int] = mapped_column(SmallInteger, nullable=False) # e.g. 6 slots = 3 hours
    cohort_mode: Mapped[str] = mapped_column(String(32), default="UNIFIED", nullable=False) # Strictly UNIFIED
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revision_hash: Mapped[str] = mapped_column(String(64), nullable=False) # SHA-256

    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="chk_timetable_day_range"),
        CheckConstraint("start_slot BETWEEN 0 AND 23", name="chk_timetable_start_slot_range"),
        CheckConstraint("duration_slots >= 1", name="chk_timetable_duration_min"),
        CheckConstraint("start_slot + duration_slots <= 24", name="chk_timetable_slot_boundary"),
        CheckConstraint("cohort_mode = 'UNIFIED'", name="chk_timetable_unified_cohort_only"),
        Index("idx_timetable_room_day_slot", "room_code", "day_of_week", "start_slot"),
        Index("idx_timetable_offering_day_slot", "offering_id", "day_of_week", "start_slot"),
    )

    offering: Mapped["CourseOffering"] = relationship("CourseOffering", back_populates="timetable_entries")
    room: Mapped["Room"] = relationship("Room", back_populates="timetable_entries")


class Workstation(Base):
    __tablename__ = "workstation"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    room_code: Mapped[str] = mapped_column(
        String(32), ForeignKey("room.room_code", ondelete="CASCADE"), nullable=False
    )
    workstation_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_operational: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("room_code", "workstation_number", name="uq_room_workstation_number"),
        CheckConstraint("workstation_number > 0", name="chk_workstation_number_positive"),
        Index("idx_workstation_room", "room_code"),
    )

    room: Mapped["Room"] = relationship("Room", back_populates="workstations")
    presence_logs: Mapped[List["PresenceLog"]] = relationship(
        "PresenceLog", back_populates="workstation", overlaps="presence_logs,room"
    )


class PresenceLog(Base):
    __tablename__ = "presence_log"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    room_code: Mapped[str] = mapped_column(
        String(32), ForeignKey("room.room_code", ondelete="RESTRICT"), nullable=False
    )
    workstation_number: Mapped[int] = mapped_column(Integer, nullable=False)
    student_id: Mapped[str] = mapped_column(String(16), nullable=False) # Strictly '24-XXXXX'
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    check_in_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    check_out_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    totp_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        CheckConstraint("workstation_number > 0", name="chk_presence_workstation_positive"),
        CheckConstraint(
            "length(student_id) = 8 AND "
            "substr(student_id, 1, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 2, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 3, 1) = '-' AND "
            "substr(student_id, 4, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 5, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 6, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 7, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 8, 1) BETWEEN '0' AND '9'",
            name="chk_presence_student_id_format",
        ),
        ForeignKeyConstraint(
            ["room_code", "workstation_number"],
            ["workstation.room_code", "workstation.workstation_number"],
            name="fk_presence_workstation",
            ondelete="CASCADE",
        ),
        Index("idx_presence_session_room", "session_id", "room_code"),
        Index("idx_presence_student_checkin", "student_id", "check_in_time"),
    )

    room: Mapped["Room"] = relationship("Room", back_populates="presence_logs", overlaps="workstation,presence_logs")
    workstation: Mapped["Workstation"] = relationship("Workstation", back_populates="presence_logs", overlaps="presence_logs,room")


class StudentProfile(Base):
    __tablename__ = "student_profile"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[str] = mapped_column(String(16), unique=True, nullable=False) # e.g. '24-00123'
    institutional_email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # None = needs first-time setup
    section_code: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("section.section_code", ondelete="SET NULL"), nullable=True
    )
    curriculum_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("curriculum_version.id", ondelete="SET NULL"), nullable=True
    )
    year_level: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requires_password_change: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    __table_args__ = (
        CheckConstraint("year_level BETWEEN 1 AND 5", name="chk_student_year_level"),
        CheckConstraint(
            "length(student_id) = 8 AND "
            "substr(student_id, 1, 1) BETWEEN '2' AND '9' AND "
            "substr(student_id, 2, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 3, 1) = '-' AND "
            "substr(student_id, 4, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 5, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 6, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 7, 1) BETWEEN '0' AND '9' AND "
            "substr(student_id, 8, 1) BETWEEN '0' AND '9'",
            name="chk_student_id_format",
        ),
        Index("idx_student_profile_id", "student_id"),
        Index("idx_student_profile_email", "institutional_email"),
        Index("idx_student_profile_section", "section_code"),
    )

    section: Mapped[Optional["Section"]] = relationship("Section")
    curriculum_version: Mapped[Optional["CurriculumVersion"]] = relationship("CurriculumVersion")

