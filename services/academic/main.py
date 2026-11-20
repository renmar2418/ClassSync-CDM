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
import csv
import io
import os
import uuid
from typing import List, Dict, Optional, Any, Union
from fastapi import FastAPI, HTTPException, status, Query, Header, UploadFile, File, Body, Request
from pydantic import BaseModel, Field

from classync_contracts.models import (
    AcademicPeriod,
    Room,
    CurriculumSubject,
    FacultyProfile,
    Section,
    CourseOffering,
    StudentProfile,
)
from classync_contracts.schemas import (
    RoomSchema,
    AcademicPeriodSchema,
    CurriculumSubjectSchema,
    FacultyProfileSchema,
    SectionSchema,
    CourseOfferingDetail,
    validate_student_id_deterministic,
    StudentProfileCreate,
    StudentProfileUpdate,
    StudentProfileSchema,
    StudentImportResult,
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


# ---------------------------------------------------------------------------
# Student Roster Store & Helpers
# ---------------------------------------------------------------------------

STUDENTS_DB: Dict[str, Dict[str, Any]] = {
    "24-00123": {
        "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "student_id": "24-00123",
        "institutional_email": "24-00123@student.pnm.edu.ph",
        "full_name": "Juan Dela Cruz",
        "section_code": "BSIT-3A",
        "curriculum_version_id": None,
        "year_level": 3,
        "is_active": True,
        "requires_password_change": False,
    },
    "24-00999": {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "student_id": "24-00999",
        "institutional_email": "24-00999@student.pnm.edu.ph",
        "full_name": "Freshie Student",
        "section_code": "BSIT-3A",
        "curriculum_version_id": None,
        "year_level": 1,
        "is_active": True,
        "requires_password_change": True,
    },
}

_ACADEMIC_ENGINE = None

def _get_academic_engine():
    global _ACADEMIC_ENGINE
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None
    if _ACADEMIC_ENGINE is None:
        from sqlalchemy import create_engine
        _ACADEMIC_ENGINE = create_engine(db_url, pool_pre_ping=True)
    return _ACADEMIC_ENGINE


# ---------------------------------------------------------------------------
# Student & Roster Management Endpoints (Phase 11)
# ---------------------------------------------------------------------------

@app.get("/api/v1/academic/students", tags=["Students"])
def list_students(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    section_code: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    year_level: Optional[int] = Query(default=None),
) -> List[Dict[str, Any]]:
    """Retrieve paginated student list with optional section and text search."""
    engine = _get_academic_engine()
    if engine is not None:
        try:
            from sqlalchemy import select
            from sqlalchemy.orm import Session
            with Session(engine) as session:
                query = select(StudentProfile)
                if section_code:
                    query = query.where(StudentProfile.section_code == section_code)
                if year_level:
                    query = query.where(StudentProfile.year_level == year_level)
                if search:
                    term = f"%{search.strip().lower()}%"
                    query = query.where(
                        (StudentProfile.student_id.ilike(term)) |
                        (StudentProfile.full_name.ilike(term)) |
                        (StudentProfile.institutional_email.ilike(term))
                    )
                query = query.offset(skip).limit(limit)
                rows = session.scalars(query).all()
                if rows:
                    return [
                        {
                            "id": r.id,
                            "student_id": r.student_id,
                            "institutional_email": r.institutional_email,
                            "full_name": r.full_name,
                            "section_code": r.section_code,
                            "curriculum_version_id": r.curriculum_version_id,
                            "year_level": r.year_level,
                            "is_active": r.is_active,
                            "requires_password_change": r.requires_password_change,
                            "created_at": r.created_at.isoformat() if r.created_at else None,
                        }
                        for r in rows
                    ]
        except Exception:
            pass

    res = list(STUDENTS_DB.values())
    if section_code:
        res = [s for s in res if s.get("section_code") == section_code]
    if year_level:
        res = [s for s in res if s.get("year_level") == year_level]
    if search:
        s_term = search.strip().lower()
        res = [
            s for s in res
            if s_term in s.get("student_id", "").lower()
            or s_term in s.get("full_name", "").lower()
            or s_term in s.get("institutional_email", "").lower()
        ]
    return res[skip : skip + limit]


@app.post("/api/v1/academic/admin/students", status_code=status.HTTP_201_CREATED, tags=["Admin"])
def create_student(body: StudentProfileCreate) -> Dict[str, Any]:
    """Admin single student entry."""
    validated_id = validate_student_id_deterministic(body.student_id)

    if validated_id in STUDENTS_DB:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Student ID '{validated_id}' already exists in roster.",
        )

    engine = _get_academic_engine()
    new_uuid = uuid.uuid4()
    if engine is not None:
        try:
            from sqlalchemy import select
            from sqlalchemy.orm import Session
            with Session(engine) as session:
                existing = session.scalar(
                    select(StudentProfile).where(
                        (StudentProfile.student_id == validated_id) |
                        (StudentProfile.institutional_email == body.institutional_email)
                    )
                )
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Student record already exists in database.",
                    )
                new_student = StudentProfile(
                    id=new_uuid,
                    student_id=validated_id,
                    institutional_email=body.institutional_email,
                    full_name=body.full_name,
                    section_code=body.section_code,
                    curriculum_version_id=body.curriculum_version_id,
                    year_level=body.year_level,
                    is_active=body.is_active,
                    requires_password_change=True,
                )
                session.add(new_student)
                session.commit()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database write error: {str(e)}")

    record = {
        "id": new_uuid,
        "student_id": validated_id,
        "institutional_email": body.institutional_email,
        "full_name": body.full_name,
        "section_code": body.section_code,
        "curriculum_version_id": body.curriculum_version_id,
        "year_level": body.year_level,
        "is_active": body.is_active,
        "requires_password_change": True,
    }
    STUDENTS_DB[validated_id] = record
    return record


@app.get("/api/v1/academic/admin/students/{identifier}", tags=["Admin"])
def get_student(identifier: str) -> Dict[str, Any]:
    """Retrieve single student by ID or student_id."""
    clean_id = identifier.strip().lower()
    engine = _get_academic_engine()
    if engine is not None:
        try:
            from sqlalchemy import select
            from sqlalchemy.orm import Session
            with Session(engine) as session:
                is_uuid = False
                u_id = None
                try:
                    u_id = uuid.UUID(clean_id)
                    is_uuid = True
                except ValueError:
                    pass
                stu = session.scalar(
                    select(StudentProfile).where(
                        (StudentProfile.student_id == clean_id) |
                        ((StudentProfile.id == u_id) if is_uuid else False)
                    )
                )
                if stu:
                    return {
                        "id": stu.id,
                        "student_id": stu.student_id,
                        "institutional_email": stu.institutional_email,
                        "full_name": stu.full_name,
                        "section_code": stu.section_code,
                        "curriculum_version_id": stu.curriculum_version_id,
                        "year_level": stu.year_level,
                        "is_active": stu.is_active,
                        "requires_password_change": stu.requires_password_change,
                    }
        except Exception:
            pass

    for s in STUDENTS_DB.values():
        if s.get("student_id", "").lower() == clean_id or str(s.get("id", "")).lower() == clean_id:
            return s
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student '{identifier}' not found.")


@app.put("/api/v1/academic/admin/students/{identifier}", tags=["Admin"])
def update_student(identifier: str, body: StudentProfileUpdate) -> Dict[str, Any]:
    """Update student profile attributes."""
    student = get_student(identifier)
    updates = body.model_dump(exclude_unset=True)

    engine = _get_academic_engine()
    if engine is not None:
        try:
            from sqlalchemy.orm import Session
            with Session(engine) as session:
                stu = session.get(StudentProfile, student["id"])
                if stu:
                    for k, v in updates.items():
                        setattr(stu, k, v)
                    session.commit()
        except Exception:
            pass

    student.update(updates)
    STUDENTS_DB[student["student_id"]] = student
    return student


@app.delete("/api/v1/academic/admin/students/{identifier}", tags=["Admin"])
def deactivate_student(identifier: str) -> Dict[str, Any]:
    """Soft-deactivate student from active roster."""
    student = get_student(identifier)
    student["is_active"] = False

    engine = _get_academic_engine()
    if engine is not None:
        try:
            from sqlalchemy.orm import Session
            with Session(engine) as session:
                stu = session.get(StudentProfile, student["id"])
                if stu:
                    stu.is_active = False
                    session.commit()
        except Exception:
            pass

    STUDENTS_DB[student["student_id"]] = student
    return {"status": "deactivated", "student_id": student["student_id"]}


@app.post("/api/v1/academic/admin/students/bulk-import", tags=["Admin"])
async def bulk_import_students(request: Request) -> Dict[str, Any]:
    """Bulk import student roster via CSV file, raw CSV string, or JSON array."""
    rows_to_process: List[Dict[str, str]] = []
    content_type = request.headers.get("content-type", "").lower()

    if "multipart/form-data" in content_type:
        form = await request.form()
        file = form.get("file")
        if file and hasattr(file, "read"):
            content_bytes = await file.read()
            try:
                text_content = content_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                text_content = content_bytes.decode("latin-1")
            reader = csv.DictReader(io.StringIO(text_content))
            for r in reader:
                rows_to_process.append(r)
    else:
        try:
            body = await request.json()
        except Exception:
            body = {}
        raw_csv = body.get("raw_csv")
        students = body.get("students")
        if raw_csv:
            reader = csv.DictReader(io.StringIO(raw_csv.strip()))
            for r in reader:
                rows_to_process.append(r)
        elif students:
            for item in students:
                rows_to_process.append({k: str(v) for k, v in item.items()})

    if not rows_to_process:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either a CSV file upload, raw_csv text, or a JSON students array.",
        )

    total_processed = len(rows_to_process)
    imported = 0
    skipped = 0
    errors: List[str] = []

    engine = _get_academic_engine()
    db_session = None
    if engine is not None:
        from sqlalchemy.orm import Session
        db_session = Session(engine)

    try:
        for idx, row in enumerate(rows_to_process, start=1):
            normalized = {k.strip().lower().replace(" ", "_"): (v or "").strip() for k, v in row.items()}
            raw_id = normalized.get("student_id") or normalized.get("id") or normalized.get("student")
            if not raw_id:
                errors.append(f"Row {idx}: Missing student_id.")
                skipped += 1
                continue

            try:
                valid_id = validate_student_id_deterministic(raw_id)
            except ValueError as ve:
                errors.append(f"Row {idx} ({raw_id}): {str(ve)}")
                skipped += 1
                continue

            email = (
                normalized.get("institutional_email")
                or normalized.get("email")
                or f"{valid_id}@student.pnm.edu.ph"
            ).lower()
            name = normalized.get("full_name") or normalized.get("name") or f"Student {valid_id}"
            section = normalized.get("section_code") or normalized.get("section")
            raw_year = normalized.get("year_level") or normalized.get("year") or "1"
            try:
                year_lvl = int(raw_year)
                if not (1 <= year_lvl <= 5):
                    year_lvl = 1
            except ValueError:
                year_lvl = 1

            if db_session is not None:
                from sqlalchemy import select
                existing = db_session.scalar(
                    select(StudentProfile).where(StudentProfile.student_id == valid_id)
                )
                if existing:
                    existing.full_name = name
                    existing.institutional_email = email
                    if section:
                        existing.section_code = section
                    existing.year_level = year_lvl
                else:
                    new_stu = StudentProfile(
                        id=uuid.uuid4(),
                        student_id=valid_id,
                        institutional_email=email,
                        full_name=name,
                        section_code=section,
                        year_level=year_lvl,
                        is_active=True,
                        requires_password_change=True,
                    )
                    db_session.add(new_stu)

            STUDENTS_DB[valid_id] = {
                "id": uuid.uuid4(),
                "student_id": valid_id,
                "institutional_email": email,
                "full_name": name,
                "section_code": section,
                "year_level": year_lvl,
                "is_active": True,
                "requires_password_change": True,
            }
            imported += 1

        if db_session is not None:
            db_session.commit()
    finally:
        if db_session is not None:
            db_session.close()

    return {
        "total_processed": total_processed,
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
    }
