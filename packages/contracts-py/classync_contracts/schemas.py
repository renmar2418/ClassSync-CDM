"""Pydantic V2 Schemas for ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System.

Enforces zero-regex deterministic student ID parsing, institutional hosted domain validation,
Argon2id password entropy, 100% full-time faculty tier, strictly UNIFIED cohort mode,
continuous 30-min slot boundaries (0-23), and spatial quarantine contracts.
"""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


def validate_student_id_deterministic(v: str) -> str:
    """Zero-Regex deterministic O(n) validator for CdM/PNM Student IDs.

    Rules:
    - Length must be exactly 8 characters.
    - Must start with 2-digit cohort prefix >= '20' followed by '-' (e.g. '22-' through '99-').
    - Must contain no '@' symbol (prevent email confusion).
    - Remaining 5 characters must strictly be ASCII numeric digits '0'-'9'.
      (Rejects Arabic-Indic, fullwidth, superscript, circled, and non-ASCII numerals).
    """
    if not isinstance(v, str):
        raise ValueError("Student IDs must look like 24-00123 (numbers only, no emails).")
    cleaned = v.strip()
    if len(cleaned) != 8:
        raise ValueError("Student IDs must look like 24-00123 (numbers only, no emails).")
    if "@" in cleaned:
        raise ValueError("Student IDs must look like 24-00123 (numbers only, no emails).")
    prefix = cleaned[:2]
    hyphen = cleaned[2]
    suffix = cleaned[3:]
    if (
        not prefix.isascii()
        or not all("0" <= c <= "9" for c in prefix)
        or hyphen != "-"
        or len(suffix) != 5
        or not suffix.isascii()
        or not all("0" <= c <= "9" for c in suffix)
    ):
        raise ValueError("Student IDs must look like 24-00123 (numbers only, no emails).")
    if int(prefix) < 20:
        raise ValueError("Student IDs must look like 24-00123 (numbers only, no emails).")
    return cleaned


def validate_faculty_institutional_email(v: str) -> str:
    """Deterministic validator for faculty institutional email.

    Must end with '@pnm.edu.ph'. Rejects personal '@gmail.com', deprecated '@cdm.edu.ph',
    empty usernames, multiple '@' symbols, control/whitespace characters, non-ASCII homoglyphs,
    and invalid symbols.
    """
    if not isinstance(v, str):
        raise ValueError("Please provide a valid institutional email address.")
    cleaned = v.strip().lower()
    parts = cleaned.split("@")
    if len(parts) != 2:
        raise ValueError("Please select your official school Google account (@pnm.edu.ph) to sign in.")
    user_part, domain_part = parts[0], parts[1]
    if not user_part or domain_part != "pnm.edu.ph":
        raise ValueError("Please select your official school Google account (@pnm.edu.ph) to sign in.")
    if any(ord(c) <= 32 or ord(c) == 127 for c in user_part) or "\x00" in user_part:
        raise ValueError("Please provide a valid institutional email address.")
    if not user_part.isascii():
        raise ValueError("Please provide a valid institutional email address.")
    if not all(c.isalnum() or c in "._-" for c in user_part):
        raise ValueError("Please provide a valid institutional email address.")
    if user_part.startswith((".", "_", "-")) or user_part.endswith((".", "_", "-")):
        raise ValueError("Please provide a valid institutional email address.")
    return cleaned


class BaseContract(BaseModel):
    """Base Pydantic configuration for all ClassSync contracts."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
        use_enum_values=True,
    )


# ---------------------------------------------------------------------------
# Academic Period
# ---------------------------------------------------------------------------

class AcademicPeriodBase(BaseContract):
    academic_year: str = Field(..., description="Academic year representation, e.g. '2026-2027'")
    semester: int = Field(..., ge=1, le=3, description="Semester term (1=First, 2=Second, 3=Midyear/Summer)")
    is_active: bool = Field(default=False, description="Whether this term is currently active")


class AcademicPeriodCreate(AcademicPeriodBase):
    pass


class AcademicPeriodSchema(AcademicPeriodBase):
    id: uuid.UUID
    created_at: datetime


# ---------------------------------------------------------------------------
# Room & Physical Facilities
# ---------------------------------------------------------------------------

class RoomBase(BaseContract):
    room_code: str = Field(..., max_length=32, description="Authoritative natural room identifier, e.g. 'PRRC 108', 'NB 204'")
    building_name: str = Field(..., max_length=64, description="Building name, e.g. 'PRRC Building', 'New Building'")
    floor_level: int = Field(..., description="Floor level integer")
    room_type: RoomType = Field(default=RoomType.LECTURE, description="Facility operational type")
    capacity: int = Field(..., gt=0, description="Maximum seated room capacity")
    is_schedulable: bool = Field(default=True, description="False for quarantined spaces: NB 204, NB 304, NB 308")
    has_aircon: bool = Field(default=False, description="Air conditioning equipped")
    has_projector: bool = Field(default=False, description="Digital projector equipped")
    exclusive_program: Optional[str] = Field(default=None, max_length=64, description="Exclusivity lock, e.g. 'BSED_SCIENCE' for PRRC 108")


class RoomCreate(RoomBase):
    pass


class RoomSchema(RoomBase):
    pass


class RoomFilterQuery(BaseContract):
    is_schedulable: Optional[bool] = None
    building_name: Optional[str] = None
    room_type: Optional[RoomType] = None


# ---------------------------------------------------------------------------
# Curriculum Subject
# ---------------------------------------------------------------------------

class CurriculumSubjectBase(BaseContract):
    subject_code: str = Field(..., max_length=32, description="Institutional subject code, e.g. 'CC-IPT2'")
    descriptive_title: str = Field(..., max_length=255, description="Full descriptive course title")
    lecture_hours: int = Field(default=3, ge=0, description="Weekly lecture contact hours")
    lab_hours: int = Field(default=0, ge=0, description="Weekly laboratory contact hours")
    units: int = Field(default=3, gt=0, description="Credit unit load")
    required_room_type: RoomType = Field(default=RoomType.LECTURE, description="Required facility room type")


class CurriculumSubjectCreate(CurriculumSubjectBase):
    pass


class CurriculumSubjectSchema(CurriculumSubjectBase):
    id: uuid.UUID


# ---------------------------------------------------------------------------
# Faculty Profile
# ---------------------------------------------------------------------------

class FacultyProfileBase(BaseContract):
    institutional_email: str = Field(..., max_length=255, description="Faculty institutional email ending with @pnm.edu.ph")
    full_name: str = Field(..., max_length=255, description="Full legal faculty name")
    employment_tier: EmploymentTier = Field(
        default=EmploymentTier.FULL_TIME,
        description="Mandatory 100% full-time faculty employment tier"
    )
    role: UserRole = Field(default=UserRole.FACULTY, description="User RBAC role (ADMIN or FACULTY)")
    is_active: bool = Field(default=True, description="Faculty active status")

    @field_validator("institutional_email")
    @classmethod
    def check_institutional_email(cls, v: str) -> str:
        return validate_faculty_institutional_email(v)

    @field_validator("employment_tier")
    @classmethod
    def check_employment_tier_full_time(cls, v: EmploymentTier | str) -> str:
        tier_str = v.value if isinstance(v, EmploymentTier) else str(v)
        if tier_str != "FULL_TIME":
            raise ValueError("All faculty must be 100% FULL_TIME per institutional parameters.")
        return tier_str

    @field_validator("role")
    @classmethod
    def check_faculty_role(cls, v: UserRole | str) -> str:
        role_str = v.value if isinstance(v, UserRole) else str(v)
        if role_str not in ("ADMIN", "FACULTY"):
            raise ValueError("Faculty profile role must be either ADMIN or FACULTY.")
        return role_str


class FacultyProfileCreate(FacultyProfileBase):
    password: Optional[str] = Field(default=None, min_length=8, description="Initial plain password (hashed via Argon2id)")


class FacultyProfileSchema(FacultyProfileBase):
    id: uuid.UUID
    requires_password_change: bool = Field(default=True, description="Enforces first-login password creation")


# ---------------------------------------------------------------------------
# Section
# ---------------------------------------------------------------------------

class SectionBase(BaseContract):
    academic_period_id: uuid.UUID = Field(..., description="Associated academic period UUID")
    section_code: str = Field(..., max_length=64, description="Section code, e.g. 'BSIT-3A'")
    year_level: int = Field(..., ge=1, le=5, description="Academic year level (1 to 5)")
    enrolled_student_count: int = Field(..., gt=0, description="Enrolled cohort count (60-70+ students)")
    curriculum_version_id: Optional[uuid.UUID] = Field(
        default=None, description="Optional curriculum version UUID bound to section"
    )


class SectionCreate(SectionBase):
    pass


class SectionSchema(SectionBase):
    id: uuid.UUID


# ---------------------------------------------------------------------------
# Course Offering
# ---------------------------------------------------------------------------

class CourseOfferingBase(BaseContract):
    academic_period_id: uuid.UUID = Field(..., description="Academic period UUID")
    subject_id: uuid.UUID = Field(..., description="Curriculum subject UUID")
    section_id: uuid.UUID = Field(..., description="Student section UUID")
    faculty_id: uuid.UUID = Field(..., description="Assigned full-time faculty UUID")


class CourseOfferingCreate(CourseOfferingBase):
    pass


class CourseOfferingSchema(CourseOfferingBase):
    id: uuid.UUID


class CourseOfferingDetail(CourseOfferingSchema):
    subject: Optional[CurriculumSubjectSchema] = None
    section: Optional[SectionSchema] = None
    faculty: Optional[FacultyProfileSchema] = None


# ---------------------------------------------------------------------------
# Timetable Entry
# ---------------------------------------------------------------------------

class TimetableEntryBase(BaseContract):
    offering_id: uuid.UUID = Field(..., description="Course offering UUID")
    room_code: str = Field(..., max_length=32, description="Assigned room natural code")
    day_of_week: DayOfWeek = Field(..., description="0=Monday, 6=Sunday")
    start_slot: int = Field(..., ge=0, le=23, description="Continuous 30-min slot interval (0=07:00, 23=18:30)")
    duration_slots: int = Field(..., ge=1, le=24, description="Duration in 30-min intervals (e.g. 6 slots = 3h)")
    cohort_mode: CohortMode = Field(
        default=CohortMode.UNIFIED,
        description="Strictly UNIFIED cohort mode. Sub-batch splitting is prohibited."
    )
    is_locked: bool = Field(default=False, description="Manual lock flag to prevent solver reallocation")
    revision_hash: str = Field(default="", max_length=64, description="SHA-256 audit digest")

    @field_validator("cohort_mode")
    @classmethod
    def check_unified_cohort_mode(cls, v: CohortMode | str) -> str:
        mode_str = v.value if isinstance(v, CohortMode) else str(v)
        if mode_str != "UNIFIED":
            raise ValueError("Cohort mode must be UNIFIED. Zero sub-batch splitting is permitted.")
        return mode_str

    @model_validator(mode="after")
    def check_slot_boundary(self) -> TimetableEntryBase:
        if self.start_slot + self.duration_slots > 24:
            raise ValueError(
                f"Class slots exceed operating window: start_slot ({self.start_slot}) + "
                f"duration_slots ({self.duration_slots}) = {self.start_slot + self.duration_slots} > 24."
            )
        return self


class TimetableEntryCreate(TimetableEntryBase):
    pass


class TimetableEntrySchema(TimetableEntryBase):
    id: uuid.UUID


class TimetableGridSlot(BaseContract):
    day_of_week: int
    slot_index: int
    time_label: str  # e.g. "07:00 - 07:30"
    is_occupied: bool
    entry: Optional[TimetableEntrySchema] = None


# ---------------------------------------------------------------------------
# Workstation
# ---------------------------------------------------------------------------

class WorkstationBase(BaseContract):
    room_code: str = Field(..., max_length=32, description="Associated COMLAB room code")
    workstation_number: int = Field(..., gt=0, description="1-indexed physical seat number (1 to 45+)")
    is_operational: bool = Field(default=True, description="Hardware health status")


class WorkstationCreate(WorkstationBase):
    pass


class WorkstationSchema(WorkstationBase):
    id: uuid.UUID


class WorkstationClaim(BaseContract):
    room_code: str = Field(..., max_length=32)
    workstation_number: int = Field(..., gt=0)
    student_id: str
    totp_token: str = Field(..., min_length=6, max_length=6)

    @field_validator("student_id")
    @classmethod
    def check_student_id(cls, v: str) -> str:
        return validate_student_id_deterministic(v)


# ---------------------------------------------------------------------------
# Presence Log & Ingress
# ---------------------------------------------------------------------------

class PresenceLogBase(BaseContract):
    room_code: str = Field(..., max_length=32)
    workstation_number: int = Field(..., gt=0)
    student_id: str
    session_id: uuid.UUID
    totp_verified: bool = Field(default=True)

    @field_validator("student_id")
    @classmethod
    def check_student_id(cls, v: str) -> str:
        return validate_student_id_deterministic(v)


class PresenceLogCreate(PresenceLogBase):
    pass


class PresenceLogSchema(PresenceLogBase):
    id: uuid.UUID
    check_in_time: datetime
    check_out_time: Optional[datetime] = None


class CheckInRequest(BaseContract):
    room_code: str = Field(..., max_length=32)
    workstation_number: int = Field(..., gt=0)
    student_id: str
    totp_token: str = Field(..., min_length=6, max_length=6)

    @field_validator("student_id")
    @classmethod
    def check_student_id(cls, v: str) -> str:
        return validate_student_id_deterministic(v)


class CheckOutRequest(BaseContract):
    room_code: str = Field(..., max_length=32)
    workstation_number: int = Field(..., gt=0)
    student_id: str

    @field_validator("student_id")
    @classmethod
    def check_student_id(cls, v: str) -> str:
        return validate_student_id_deterministic(v)


# ---------------------------------------------------------------------------
# Security, Auth & Cloudflare Turnstile
# ---------------------------------------------------------------------------

class TurnstileVerifyRequest(BaseContract):
    token: str = Field(..., description="Cloudflare Turnstile client verification token")


class TurnstileVerifyResponse(BaseContract):
    success: bool
    error_codes: Optional[List[str]] = None


class GoogleOAuthTokenRequest(BaseContract):
    id_token: str = Field(..., description="Cryptographically signed Google OAuth JWT")


class GoogleTokenClaims(BaseContract):
    sub: str
    email: str
    email_verified: bool
    hd: Optional[str] = None
    name: Optional[str] = None


class PasswordSetupRequest(BaseContract):
    student_or_employee_id: str
    current_password: Optional[str] = None
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @model_validator(mode="after")
    def check_passwords_match(self) -> PasswordSetupRequest:
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirmation do not match.")
        return self


class PasswordIntegrityResponse(BaseContract):
    valid: bool
    entropy_bits: float
    message: str


class LocalLoginRequest(BaseContract):
    identifier: str = Field(..., description="Email address or 24-XXXXX Student ID")
    password: str
    turnstile_token: str


class SessionUser(BaseContract):
    id: uuid.UUID
    identifier: str
    full_name: str
    role: UserRole
    requires_password_change: bool


class AuthTokenResponse(BaseContract):
    access_token: str
    token_type: str = "bearer"
    user: SessionUser


class LoginStep1Response(BaseContract):
    otp_session_id: str = Field(..., description="Opaque session identifier for OTP verification")
    message: str = Field(..., description="User guidance message")
    email_hint: str = Field(..., description="Masked destination email hint")
    requires_otp: bool = True


class OTPVerifyRequest(BaseContract):
    otp_session_id: str = Field(..., description="Session identifier received from step 1")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")


class SendOTPRequest(BaseContract):
    email: str = Field(..., description="Destination email address")
    full_name: Optional[str] = Field(default=None, description="Recipient full name")
    purpose: str = Field(default="login", description="Reason for OTP dispatch")


class SendOTPResponse(BaseContract):
    otp_session_id: str
    success: bool
    message: str


# ---------------------------------------------------------------------------
# Curriculum Versioning & Overrides
# ---------------------------------------------------------------------------

class CurriculumVersionBase(BaseContract):
    curriculum_year: str = Field(..., max_length=16, description="Curriculum year, e.g. '22', '23', '24', '25', '26'")
    program_code: str = Field(..., max_length=32, description="Degree program, e.g. 'BSIT', 'BSCPE', 'BSED_SCIENCE'")
    institute: str = Field(..., max_length=16, description="Institute code: 'ICS', 'ITE', 'IBE'")
    is_current: bool = Field(default=False, description="Whether this version is the latest active default")


class CurriculumVersionCreate(CurriculumVersionBase):
    pass


class CurriculumVersionSchema(CurriculumVersionBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None


class StudentCurriculumOverrideBase(BaseContract):
    student_id: str = Field(..., description="Student ID e.g. '24-00123'")
    curriculum_version_id: uuid.UUID = Field(..., description="Curriculum version UUID to bind")
    override_reason: str = Field(default="Irregular", max_length=255, description="Administrative override reason")

    @field_validator("student_id")
    @classmethod
    def check_student_id(cls, v: str) -> str:
        return validate_student_id_deterministic(v)


class StudentCurriculumOverrideCreate(StudentCurriculumOverrideBase):
    pass


class StudentCurriculumOverrideSchema(StudentCurriculumOverrideBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Real-Time Presence & Telemetry Events
# ---------------------------------------------------------------------------

class LiveRoomVacancyEvent(BaseContract):
    room_code: str
    occupied_count: int
    vacant_count: int
    total_stations: int
    active_session_id: Optional[uuid.UUID] = None
    timestamp: int


class WorkstationStateEvent(BaseContract):
    room_code: str
    workstation_number: int
    status: WorkstationStatus
    student_id: Optional[str] = None
    timestamp: int


# ---------------------------------------------------------------------------
# Solver & Optimization DTOs
# ---------------------------------------------------------------------------

class SolverRunRequest(BaseContract):
    academic_period_id: uuid.UUID
    time_limit_seconds: int = Field(default=120, ge=5, le=600)


class SolverRunResponse(BaseContract):
    status: SolverStatus
    total_conflicts: int
    solve_time_seconds: float
    timetable_entries: List[TimetableEntrySchema]


class DeltaSolveRequest(BaseContract):
    disrupted_room_code: str
    day_of_week: DayOfWeek
    start_slot: int = Field(..., ge=0, le=23)
    duration_slots: int = Field(..., ge=1, le=24)


class DeltaSolveResponse(BaseContract):
    delta_solved: bool
    solve_time_seconds: float
    reassigned_entries: List[TimetableEntrySchema]


class ConflictReport(BaseContract):
    has_conflict: bool
    room_collisions: int = 0
    faculty_collisions: int = 0
    section_collisions: int = 0
    quarantine_violations: int = 0
    details: List[str] = Field(default_factory=list)
