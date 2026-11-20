"""FastAPI Application for ClassSync Academic Microservice.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Port: 8001
Routes:
- GET  /health
- GET  /api/v1/academic/rooms (with spatial quarantine filter WHERE is_schedulable=TRUE)
- POST /api/v1/academic/rooms
- GET  /api/v1/academic/subjects
- POST /api/v1/academic/subjects
- GET  /api/v1/academic/faculty
- POST /api/v1/academic/faculty
- GET  /api/v1/academic/sections
- POST /api/v1/academic/sections
- GET  /api/v1/academic/offerings
- POST /api/v1/academic/offerings
"""

from __future__ import annotations
import uuid
from typing import List, Dict, Optional, Any
from fastapi import FastAPI, HTTPException, status, Query, Header
from pydantic import BaseModel, Field

from classync_contracts.models import (
    AcademicPeriod,
    Room,
    CurriculumSubject,
    FacultyProfile,
    Section,
    CourseOffering,
)
from classync_contracts.schemas import (
    RoomSchema,
    AcademicPeriodSchema,
    CurriculumSubjectSchema,
    FacultyProfileSchema,
    SectionSchema,
    CourseOfferingDetail,
)
from classync_contracts.enums import RoomType, EmploymentTier

app = FastAPI(
    title="ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System - Academic Service",
    description="Microservice managing Curricula, Spatial Facility Directory (with quarantine filter), Sections, Faculty Profiles, and Course Offerings on Port 8001.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# In-Memory Database Store (Initialized with Institutional Data)
# ---------------------------------------------------------------------------

DEFAULT_PERIOD_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")

PERIODS_DB: Dict[uuid.UUID, Dict[str, Any]] = {
    DEFAULT_PERIOD_ID: {
        "id": DEFAULT_PERIOD_ID,
        "academic_year": "2026-2027",
        "semester": 1,
        "is_active": True,
    }
}

ROOMS_DB: Dict[str, Dict[str, Any]] = {
    # PRRC Computer Labs
    "PRRC 301": {
        "room_code": "PRRC 301",
        "building_name": "PRRC Building",
        "floor_level": 3,
        "room_type": "COMPUTER_LAB",
        "capacity": 70,
        "is_schedulable": True,
        "has_aircon": True,
        "has_projector": True,
        "exclusive_program": None,
    },
    "PRRC 302": {
        "room_code": "PRRC 302",
        "building_name": "PRRC Building",
        "floor_level": 3,
        "room_type": "COMPUTER_LAB",
        "capacity": 70,
        "is_schedulable": True,
        "has_aircon": True,
        "has_projector": True,
        "exclusive_program": None,
    },
    # PRRC 108: Locked to BSEd Science
    "PRRC 108": {
        "room_code": "PRRC 108",
        "building_name": "PRRC Building",
        "floor_level": 1,
        "room_type": "SCIENCE_LAB",
        "capacity": 65,
        "is_schedulable": True,
        "has_aircon": True,
        "has_projector": True,
        "exclusive_program": "BSED_SCIENCE",
    },
    # Lecture Rooms
    "PRRC 201": {
        "room_code": "PRRC 201",
        "building_name": "PRRC Building",
        "floor_level": 2,
        "room_type": "LECTURE",
        "capacity": 70,
        "is_schedulable": True,
        "has_aircon": True,
        "has_projector": True,
        "exclusive_program": None,
    },
    "PRRC 202": {
        "room_code": "PRRC 202",
        "building_name": "PRRC Building",
        "floor_level": 2,
        "room_type": "LECTURE",
        "capacity": 70,
        "is_schedulable": True,
        "has_aircon": True,
        "has_projector": True,
        "exclusive_program": None,
    },
    # Civic Training / Large Venues
    "Function Hall": {
        "room_code": "Function Hall",
        "building_name": "Main Building",
        "floor_level": 1,
        "room_type": "FUNCTION_HALL",
        "capacity": 300,
        "is_schedulable": True,
        "has_aircon": True,
        "has_projector": True,
        "exclusive_program": None,
    },
    "Athletic Oval": {
        "room_code": "Athletic Oval",
        "building_name": "Sports Complex",
        "floor_level": 0,
        "room_type": "COURT",
        "capacity": 500,
        "is_schedulable": True,
        "has_aircon": False,
        "has_projector": False,
        "exclusive_program": None,
    },
    # Quarantined Spaces (is_schedulable = FALSE, Decision Log D-05)
    "NB 204": {
        "room_code": "NB 204",
        "building_name": "New Building",
        "floor_level": 2,
        "room_type": "LECTURE",
        "capacity": 0,
        "is_schedulable": False,
        "has_aircon": True,
        "has_projector": False,
        "exclusive_program": None,
    },
    "NB 304": {
        "room_code": "NB 304",
        "building_name": "New Building",
        "floor_level": 3,
        "room_type": "LECTURE",
        "capacity": 0,
        "is_schedulable": False,
        "has_aircon": True,
        "has_projector": False,
        "exclusive_program": None,
    },
    "NB 308": {
        "room_code": "NB 308",
        "building_name": "New Building",
        "floor_level": 3,
        "room_type": "LECTURE",
        "capacity": 0,
        "is_schedulable": False,
        "has_aircon": True,
        "has_projector": False,
        "exclusive_program": None,
    },
}

FACULTY_DB: Dict[uuid.UUID, Dict[str, Any]] = {
    uuid.UUID("22222222-2222-2222-2222-222222222221"): {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222221"),
        "institutional_email": "mades.faculty@pnm.edu.ph",
        "full_name": "Prof. Mades (IAS Lead)",
        "employment_tier": "FULL_TIME",
        "requires_password_change": False,
        "is_active": True,
    },
    uuid.UUID("22222222-2222-2222-2222-222222222222"): {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "institutional_email": "nat.faculty@pnm.edu.ph",
        "full_name": "Prof. Nat (IPT2 Lead)",
        "employment_tier": "FULL_TIME",
        "requires_password_change": False,
        "is_active": True,
    },
    uuid.UUID("22222222-2222-2222-2222-222222222223"): {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222223"),
        "institutional_email": "gretchen.faculty@pnm.edu.ph",
        "full_name": "Prof. Gretchen (ADBMS / AppDev Lead)",
        "employment_tier": "FULL_TIME",
        "requires_password_change": False,
        "is_active": True,
    },
    uuid.UUID("22222222-2222-2222-2222-222222222224"): {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222224"),
        "institutional_email": "teacher@pnm.edu.ph",
        "full_name": "Test Faculty Member",
        "employment_tier": "FULL_TIME",
        "requires_password_change": False,
        "is_active": True,
    },
}

SECTIONS_DB: Dict[uuid.UUID, Dict[str, Any]] = {
    uuid.UUID("33333333-3333-3333-3333-333333333331"): {
        "id": uuid.UUID("33333333-3333-3333-3333-333333333331"),
        "academic_period_id": DEFAULT_PERIOD_ID,
        "section_code": "BSIT-3A",
        "year_level": 3,
        "enrolled_student_count": 65,
    },
    uuid.UUID("33333333-3333-3333-3333-333333333332"): {
        "id": uuid.UUID("33333333-3333-3333-3333-333333333332"),
        "academic_period_id": DEFAULT_PERIOD_ID,
        "section_code": "BSIT-3B",
        "year_level": 3,
        "enrolled_student_count": 68,
    },
}

SUBJECTS_DB: Dict[uuid.UUID, Dict[str, Any]] = {
    uuid.UUID("44444444-4444-4444-4444-444444444441"): {
        "id": uuid.UUID("44444444-4444-4444-4444-444444444441"),
        "subject_code": "IPT-201",
        "descriptive_title": "Integrative Programming and Technologies 2",
        "lecture_hours": 2,
        "lab_hours": 3,
        "units": 3,
        "required_room_type": "COMPUTER_LAB",
    },
    uuid.UUID("44444444-4444-4444-4444-444444444442"): {
        "id": uuid.UUID("44444444-4444-4444-4444-444444444442"),
        "subject_code": "IAS-301",
        "descriptive_title": "Information Assurance and Security",
        "lecture_hours": 3,
        "lab_hours": 0,
        "units": 3,
        "required_room_type": "LECTURE",
    },
}

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Monitoring"])
def health_check() -> Dict[str, Any]:
    """Health monitor for Academic service."""
    return {
        "status": "healthy",
        "service": "academic",
        "port": 8001,
        "title": "ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System",
    }


@app.get("/api/v1/academic/rooms", tags=["Rooms"])
def get_rooms(
    include_quarantined: bool = Query(
        default=False,
        description="Whether to include quarantined administrative rooms (NB 204, NB 304, NB 308). Default FALSE.",
    )
) -> List[Dict[str, Any]]:
    """Retrieves spatial room inventory.
    
    Decision Log D-05: By default, WHERE is_schedulable = TRUE hiding
    non-schedulable administrative offices, storage, and canteen.
    """
    rooms = list(ROOMS_DB.values())
    if not include_quarantined:
        rooms = [r for r in rooms if r["is_schedulable"]]
    return rooms


@app.get("/api/v1/academic/rooms/{room_code}", tags=["Rooms"])
def get_room(room_code: str) -> Dict[str, Any]:
    """Retrieves a single room by its unique room code."""
    if room_code not in ROOMS_DB:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room '{room_code}' not found in campus facility directory.",
        )
    return ROOMS_DB[room_code]


@app.get("/api/v1/academic/faculty", tags=["Faculty"])
def get_faculty() -> List[Dict[str, Any]]:
    """Retrieves all 100% full-time faculty profiles."""
    return list(FACULTY_DB.values())


@app.get("/api/v1/academic/sections", tags=["Sections"])
def get_sections() -> List[Dict[str, Any]]:
    """Retrieves all student cohorts (60-70+ students, UNIFIED cohort mode)."""
    return list(SECTIONS_DB.values())


@app.get("/api/v1/academic/subjects", tags=["Subjects"])
def get_subjects() -> List[Dict[str, Any]]:
    """Retrieves all curriculum subjects."""
    return list(SUBJECTS_DB.values())
