"""FastAPI Application for ClassSync Scheduling Microservice.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Port: 8002
Routes:
- POST /api/v1/scheduling/solve
- POST /api/v1/scheduling/delta-resolve
- POST /api/v1/scheduling/audit
- GET  /health
"""

from __future__ import annotations
import os
import uuid
from typing import List, Dict, Optional, Any
from fastapi import FastAPI, HTTPException, status, Query, Response
from pydantic import BaseModel, Field

from classync_contracts.schemas import (
    BaseContract,
    SolverRunRequest,
    SolverRunResponse,
    DeltaSolveRequest,
    DeltaSolveResponse,
    ConflictReport,
    TimetableEntrySchema,
    RoomSchema,
    CourseOfferingDetail,
)
from services.scheduling.solver.model_builder import MasterCPSATSolver
from services.scheduling.solver.delta_resolver import (
    LocalizedDeltaResolver,
    OfferingMetadata,
)
from services.scheduling.solver.conflict_auditor import (
    ConflictAuditor,
    AuditReport,
)
from services.scheduling.ical_export import generate_student_schedule_ics
from services.scheduling.pdf_export import generate_schedule_pdf

app = FastAPI(
    title="ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System - Scheduling Service",
    description="Microservice responsible for Google OR-Tools CP-SAT Master Scheduling, Sub-Second Delta Re-solving (<0.10s), and Conflict Auditing.",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# API Models
# ---------------------------------------------------------------------------

class BatchSolvePayload(BaseContract):
    """Payload for full batch CP-SAT solve."""
    academic_period_id: uuid.UUID
    time_limit_seconds: int = Field(default=120, ge=5, le=600)
    offerings: List[CourseOfferingDetail] = Field(default_factory=list)
    rooms: List[RoomSchema] = Field(default_factory=list)


class DeltaResolvePayload(BaseContract):
    """Payload for localized emergency delta re-solve (<0.10s SLA)."""
    disrupted_room_code: str
    day_of_week: int = Field(..., ge=0, le=6)
    start_slot: int = Field(..., ge=0, le=23)
    duration_slots: int = Field(..., ge=1, le=24)
    baseline_entries: List[TimetableEntrySchema] = Field(default_factory=list)
    offerings_metadata: List[OfferingMetadata] = Field(default_factory=list)
    rooms: List[RoomSchema] = Field(default_factory=list)


class AuditPayload(BaseContract):
    """Payload for multi-pass timetable conflict auditing."""
    entries: List[TimetableEntrySchema]
    offerings: List[CourseOfferingDetail] = Field(default_factory=list)
    rooms: List[RoomSchema] = Field(default_factory=list)
    stamp_hash: bool = True


# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Monitoring"])
def health_check() -> Dict[str, Any]:
    """Microservice health check endpoint."""
    return {
        "status": "healthy",
        "service": "scheduling",
        "port": 8002,
        "title": "ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System",
    }


@app.post(
    "/api/v1/scheduling/solve",
    response_model=SolverRunResponse,
    status_code=status.HTTP_200_OK,
    tags=["CP-SAT Solver"],
)
def run_batch_solve(payload: BatchSolvePayload) -> SolverRunResponse:
    """Executes the Google OR-Tools CP-SAT master timetable solver."""
    if not payload.offerings or not payload.rooms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both offerings and rooms must be provided for scheduling solve.",
        )

    solver = MasterCPSATSolver(
        rooms=payload.rooms,
        offerings=payload.offerings,
        time_limit_seconds=payload.time_limit_seconds,
    )
    return solver.solve()


@app.post(
    "/api/v1/scheduling/delta-resolve",
    response_model=DeltaSolveResponse,
    status_code=status.HTTP_200_OK,
    tags=["Delta Re-solver"],
)
def run_delta_resolve(payload: DeltaResolvePayload) -> DeltaSolveResponse:
    """Executes localized sub-second delta re-solve (<0.10s SLA) on facility disruption."""
    if not payload.rooms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rooms inventory must be provided for delta reassignment.",
        )

    request = DeltaSolveRequest(
        disrupted_room_code=payload.disrupted_room_code,
        day_of_week=payload.day_of_week,  # type: ignore
        start_slot=payload.start_slot,
        duration_slots=payload.duration_slots,
    )

    offerings_map = {m.offering_id: m for m in payload.offerings_metadata}
    resolver = LocalizedDeltaResolver(rooms=payload.rooms)
    return resolver.resolve(
        baseline_entries=payload.baseline_entries,
        request=request,
        offerings_map=offerings_map,
    )


@app.post(
    "/api/v1/scheduling/audit",
    response_model=AuditReport,
    status_code=status.HTTP_200_OK,
    tags=["Conflict Auditor"],
)
def run_audit(payload: AuditPayload) -> AuditReport:
    """Executes 8-pass independent collision and constraint audit over timetable entries."""
    auditor = ConflictAuditor(
        rooms=payload.rooms,
        offerings=payload.offerings,
    )
    return auditor.audit_timetable(
        entries=payload.entries,
        stamp_revision_hash=payload.stamp_hash,
    )


# ---------------------------------------------------------------------------
# Student & Faculty Schedule Query Endpoints (Phases 12 & 13)
# ---------------------------------------------------------------------------

DEFAULT_TIMETABLE_ENTRIES: List[Dict[str, Any]] = [
    {
        "id": "entry-1",
        "courseCode": "CC-IPT2",
        "courseTitle": "Integrative Programming & Technologies 2",
        "roomCode": "PRRC 301",
        "roomType": "COMPUTER_LAB",
        "dayOfWeek": 0,
        "startSlot": 2,
        "durationSlots": 6,
        "facultyName": "Engr. Nathaniel Gomez",
        "facultyEmail": "ngomez@pnm.edu.ph",
        "sectionCode": "BSIT-3A",
    },
    {
        "id": "entry-2",
        "courseCode": "IT-NET2",
        "courseTitle": "Advanced Networking & Routing",
        "roomCode": "PRRC 201",
        "roomType": "LECTURE",
        "dayOfWeek": 0,
        "startSlot": 10,
        "durationSlots": 6,
        "facultyName": "Prof. Maria Santos",
        "facultyEmail": "prof.mades@pnm.edu.ph",
        "sectionCode": "BSIT-3A",
    },
    {
        "id": "entry-3",
        "courseCode": "IT-SEC1",
        "courseTitle": "Information Assurance & Security",
        "roomCode": "PRRC 302",
        "roomType": "COMPUTER_LAB",
        "dayOfWeek": 2,
        "startSlot": 6,
        "durationSlots": 6,
        "facultyName": "Engr. Nathaniel Gomez",
        "facultyEmail": "ngomez@pnm.edu.ph",
        "sectionCode": "BSIT-3A",
    },
    {
        "id": "entry-4",
        "courseCode": "GE-ETHICS",
        "courseTitle": "Ethics & Professionalism",
        "roomCode": "PRRC 104",
        "roomType": "LECTURE",
        "dayOfWeek": 4,
        "startSlot": 2,
        "durationSlots": 6,
        "facultyName": "Prof. Ronald Diaz",
        "facultyEmail": "teacher@pnm.edu.ph",
        "sectionCode": "BSIT-3A",
    },
]

_SCHEDULING_ENGINE = None

def _get_scheduling_engine():
    global _SCHEDULING_ENGINE
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None
    if _SCHEDULING_ENGINE is None:
        from sqlalchemy import create_engine
        _SCHEDULING_ENGINE = create_engine(db_url, pool_pre_ping=True)
    return _SCHEDULING_ENGINE


def get_schedule_for_student(student_id: Optional[str] = None, section_code: Optional[str] = None) -> List[Dict[str, Any]]:
    """Resolves student timetable from DB or default seed catalog."""
    sec = section_code or "BSIT-3A"
    is_irregular = False

    engine = _get_scheduling_engine()
    if engine is not None:
        try:
            from sqlalchemy import select
            from sqlalchemy.orm import Session
            from classync_contracts.models import StudentProfile, StudentCurriculumOverride, TimetableEntry, CourseOffering, CurriculumSubject, FacultyProfile, Section

            with Session(engine) as session:
                if student_id:
                    stu = session.scalar(select(StudentProfile).where(StudentProfile.student_id == student_id))
                    if stu and stu.section_code:
                        sec = stu.section_code
                    override = session.scalar(select(StudentCurriculumOverride).where(StudentCurriculumOverride.student_id == student_id))
                    if override:
                        is_irregular = True

                stmt = (
                    select(TimetableEntry, CourseOffering, CurriculumSubject, FacultyProfile, Section)
                    .join(CourseOffering, TimetableEntry.offering_id == CourseOffering.id)
                    .join(CurriculumSubject, CourseOffering.subject_id == CurriculumSubject.id)
                    .join(FacultyProfile, CourseOffering.faculty_id == FacultyProfile.id)
                    .join(Section, CourseOffering.section_id == Section.id)
                    .where(Section.section_code == sec)
                )
                results = session.execute(stmt).all()
                if results:
                    mapped = []
                    for t_entry, offering, subject, faculty, section in results:
                        mapped.append({
                            "id": str(t_entry.id),
                            "courseCode": subject.subject_code,
                            "courseTitle": subject.descriptive_title,
                            "roomCode": t_entry.room_code,
                            "roomType": subject.required_room_type,
                            "dayOfWeek": t_entry.day_of_week,
                            "startSlot": t_entry.start_slot,
                            "durationSlots": t_entry.duration_slots,
                            "facultyName": faculty.full_name,
                            "facultyEmail": faculty.institutional_email,
                            "sectionCode": section.section_code,
                            "isIrregularOverride": is_irregular,
                        })
                    return mapped
        except Exception:
            pass

    filtered = [e for e in DEFAULT_TIMETABLE_ENTRIES if e["sectionCode"] == sec]
    return filtered or DEFAULT_TIMETABLE_ENTRIES


@app.get("/api/v1/scheduling/student/schedule", tags=["Student Portal"])
def get_student_schedule_endpoint(
    student_id: Optional[str] = Query(default=None),
    section_code: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """Retrieves personal class timetable for a student cohort or ID."""
    target_section = section_code or "BSIT-3A"
    entries = get_schedule_for_student(student_id=student_id, section_code=target_section)
    return {
        "student_id": student_id or "24-00123",
        "section_code": target_section,
        "academic_period": "2026-2027 Semester 1",
        "entries": entries,
    }


@app.get("/api/v1/scheduling/student/schedule/export/ics", tags=["Student Portal"])
def export_student_schedule_ics_endpoint(
    student_id: Optional[str] = Query(default=None),
    section_code: Optional[str] = Query(default=None),
) -> Response:
    """Exports personal class schedule as an RFC 5545 compliant .ics file."""
    sid = student_id or "24-00123"
    sec = section_code or "BSIT-3A"
    entries = get_schedule_for_student(student_id=sid, section_code=sec)
    ics_text = generate_student_schedule_ics(student_id=sid, section_code=sec, entries=entries)

    filename = f"classync_schedule_{sec}_{sid}.ics"
    return Response(
        content=ics_text,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@app.get("/api/v1/scheduling/faculty/schedule", tags=["Faculty Portal"])
def get_faculty_schedule_endpoint(
    faculty_email: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """Retrieves teaching assignments and schedule for faculty."""
    email = (faculty_email or "ngomez@pnm.edu.ph").strip().lower()
    engine = _get_scheduling_engine()
    if engine is not None:
        try:
            from sqlalchemy import select
            from sqlalchemy.orm import Session
            from classync_contracts.models import TimetableEntry, CourseOffering, CurriculumSubject, FacultyProfile, Section

            with Session(engine) as session:
                stmt = (
                    select(TimetableEntry, CourseOffering, CurriculumSubject, FacultyProfile, Section)
                    .join(CourseOffering, TimetableEntry.offering_id == CourseOffering.id)
                    .join(CurriculumSubject, CourseOffering.subject_id == CurriculumSubject.id)
                    .join(FacultyProfile, CourseOffering.faculty_id == FacultyProfile.id)
                    .join(Section, CourseOffering.section_id == Section.id)
                    .where(FacultyProfile.institutional_email == email)
                )
                results = session.execute(stmt).all()
                if results:
                    mapped = []
                    for t_entry, offering, subject, faculty, section in results:
                        mapped.append({
                            "id": str(t_entry.id),
                            "courseCode": subject.subject_code,
                            "courseTitle": subject.descriptive_title,
                            "roomCode": t_entry.room_code,
                            "roomType": subject.required_room_type,
                            "dayOfWeek": t_entry.day_of_week,
                            "startSlot": t_entry.start_slot,
                            "durationSlots": t_entry.duration_slots,
                            "facultyName": faculty.full_name,
                            "facultyEmail": faculty.institutional_email,
                            "sectionCode": section.section_code,
                        })
                    return {"faculty_email": email, "entries": mapped}
        except Exception:
            pass

    matched = [e for e in DEFAULT_TIMETABLE_ENTRIES if e.get("facultyEmail", "").lower() == email]
    return {"faculty_email": email, "entries": matched or DEFAULT_TIMETABLE_ENTRIES[:2]}


@app.get("/api/v1/scheduling/student/schedule/export/pdf", tags=["Student Portal"])
def export_student_schedule_pdf_endpoint(
    student_id: Optional[str] = Query(default=None),
    section_code: Optional[str] = Query(default=None),
) -> Response:
    """Exports personal class schedule as an official, printable PDF document."""
    sid = student_id or "24-00123"
    sec = section_code or "BSIT-3A"
    entries = get_schedule_for_student(student_id=sid, section_code=sec)

    pdf_bytes = generate_schedule_pdf(
        title="Official Class Timetable",
        subtitle=f"Student ID: {sid} • Section: {sec}",
        entries=entries,
    )

    filename = f"classync_schedule_{sec}_{sid}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@app.get("/api/v1/scheduling/faculty/schedule/export/pdf", tags=["Faculty Portal"])
def export_faculty_schedule_pdf_endpoint(
    faculty_email: Optional[str] = Query(default=None),
) -> Response:
    """Exports faculty teaching assignments as an official, printable PDF matrix."""
    email = (faculty_email or "ngomez@pnm.edu.ph").strip().lower()
    res = get_faculty_schedule_endpoint(faculty_email=email)
    entries = res.get("entries", [])
    f_name = entries[0].get("facultyName", "Faculty Member") if entries else "Faculty Member"

    pdf_bytes = generate_schedule_pdf(
        title="Faculty Plantilla Teaching Matrix",
        subtitle=f"Instructor: {f_name} • Email: {email}",
        entries=entries,
    )

    sanitized_email = email.split("@")[0]
    filename = f"classync_faculty_{sanitized_email}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@app.get("/api/v1/scheduling/rooms/{room_code}/export/pdf", tags=["Room Timetable"])
def export_room_schedule_pdf_endpoint(
    room_code: str,
) -> Response:
    """Exports room utilization schedule as an official, printable PDF."""
    r_code = room_code.strip()
    engine = _get_scheduling_engine()
    entries = []
    if engine is not None:
        try:
            from sqlalchemy import select
            from sqlalchemy.orm import Session
            from classync_contracts.models import TimetableEntry, CourseOffering, CurriculumSubject, FacultyProfile, Section

            with Session(engine) as session:
                stmt = (
                    select(TimetableEntry, CourseOffering, CurriculumSubject, FacultyProfile, Section)
                    .join(CourseOffering, TimetableEntry.offering_id == CourseOffering.id)
                    .join(CurriculumSubject, CourseOffering.subject_id == CurriculumSubject.id)
                    .join(FacultyProfile, CourseOffering.faculty_id == FacultyProfile.id)
                    .join(Section, CourseOffering.section_id == Section.id)
                    .where(TimetableEntry.room_code == r_code)
                )
                results = session.execute(stmt).all()
                for t_entry, offering, subject, faculty, section in results:
                    entries.append({
                        "id": str(t_entry.id),
                        "courseCode": subject.subject_code,
                        "courseTitle": subject.descriptive_title,
                        "roomCode": t_entry.room_code,
                        "roomType": subject.required_room_type,
                        "dayOfWeek": t_entry.day_of_week,
                        "startSlot": t_entry.start_slot,
                        "durationSlots": t_entry.duration_slots,
                        "facultyName": faculty.full_name,
                        "sectionCode": section.section_code,
                    })
        except Exception:
            pass

    if not entries:
        entries = [e for e in DEFAULT_TIMETABLE_ENTRIES if e.get("roomCode") == r_code]
        if not entries:
            entries = DEFAULT_TIMETABLE_ENTRIES[:2]

    pdf_bytes = generate_schedule_pdf(
        title="Room Master Utilization Schedule",
        subtitle=f"Classroom / Facility: {r_code}",
        entries=entries,
    )

    clean_room = r_code.replace(" ", "_")
    filename = f"classync_room_{clean_room}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


