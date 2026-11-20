"""FastAPI Application for ClassSync Presence Microservice.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Port: 8004
Endpoints:
- GET  /health
- GET  /api/v1/presence/totp/{room_code}
- POST /api/v1/presence/checkin
- POST /api/v1/presence/checkout
- GET  /api/v1/presence/rooms/{room_code}/occupancy
- GET  /api/v1/presence/rooms/{room_code}/recent-logs
- GET  /api/v1/presence/rooms/{room_code}/stream
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from classync_contracts.schemas import (
    CheckInRequest,
    CheckOutRequest,
)
from services.presence.ingress.validator import (
    STUDENT_ID_ERROR_MESSAGE,
    StudentIDValidationError,
    validate_student_id,
)
from services.presence.storage.workstation_tracker import (
    COMLABWorkstationManager,
    WorkstationConflictError,
    WorkstationMaintenanceError,
    WorkstationOutOfBoundsError,
)
from services.presence.storage.buffer import (
    PresenceCircularBuffer,
    PresenceLogEntry,
)
from services.presence.storage.faculty_presence import (
    FacultyPresenceManager,
    FacultyPresenceRecord,
)
from services.presence.totp.generator import (
    SessionSecretManager,
    TOTPGenerator,
)
from services.presence.sse.stream import (
    SSEBroadcaster,
)

# ---------------------------------------------------------------------------
# Application Initialization
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System - Presence Service",
    description="Microservice responsible for 15s RFC 6238 TOTP Presence, COMLAB 45-Workstation Tracking, and Real-Time SSE Vacancy Streaming.",
    version="1.0.0",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Translates validation errors into human-centered plain language per D-12."""
    for err in exc.errors():
        msg = str(err.get("msg", ""))
        loc = err.get("loc", ())
        if "student_id" in loc or "Student IDs must look like" in msg:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": STUDENT_ID_ERROR_MESSAGE},
            )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


# ---------------------------------------------------------------------------
# Service Dependencies / Singletons
# ---------------------------------------------------------------------------

workstation_manager = COMLABWorkstationManager(auto_init_standard=True)
circular_buffer = PresenceCircularBuffer(capacity=50)
session_secret_manager = SessionSecretManager()
totp_generator = TOTPGenerator(interval=15, digits=6)
sse_broadcaster = SSEBroadcaster(heartbeat_interval=15.0)
faculty_presence_manager = FacultyPresenceManager()

_PRESENCE_ENGINE = None

def _get_presence_engine():
    global _PRESENCE_ENGINE
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None
    if _PRESENCE_ENGINE is None:
        try:
            from sqlalchemy import create_engine
            _PRESENCE_ENGINE = create_engine(db_url, pool_pre_ping=True)
        except Exception:
            _PRESENCE_ENGINE = None
    return _PRESENCE_ENGINE


# ---------------------------------------------------------------------------
# Institutional Room Directory Cache (Authoritative 53 Campus Spaces)
# ---------------------------------------------------------------------------

INSTITUTIONAL_ROOMS_CATALOG: List[Dict[str, Any]] = [
    # PRRC Floor 1
    {"room_code": "PRRC 101", "building_name": "PRRC Building", "floor_level": 1, "room_type": "SIMULATION_LAB", "capacity": 40, "is_schedulable": False},
    {"room_code": "PRRC 102", "building_name": "PRRC Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 50, "is_schedulable": False},
    {"room_code": "PRRC 103", "building_name": "PRRC Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 70, "is_schedulable": True},
    {"room_code": "PRRC 104", "building_name": "PRRC Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 50, "is_schedulable": False},
    {"room_code": "PRRC 105", "building_name": "PRRC Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 70, "is_schedulable": True},
    {"room_code": "PRRC 106", "building_name": "PRRC Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 70, "is_schedulable": True},
    {"room_code": "PRRC 107", "building_name": "PRRC Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 70, "is_schedulable": True},
    {"room_code": "PRRC 108", "building_name": "PRRC Building", "floor_level": 1, "room_type": "SCIENCE_LAB", "capacity": 70, "is_schedulable": True},
    # PRRC Floor 2
    {"room_code": "PRRC 201", "building_name": "PRRC Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "PRRC 202", "building_name": "PRRC Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "PRRC 203", "building_name": "PRRC Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "PRRC 204", "building_name": "PRRC Building", "floor_level": 2, "room_type": "COMPUTER_LAB", "capacity": 40, "is_schedulable": False},
    {"room_code": "PRRC 205", "building_name": "PRRC Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 40, "is_schedulable": False},
    {"room_code": "PRRC 206", "building_name": "PRRC Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "PRRC 207", "building_name": "PRRC Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "PRRC 208", "building_name": "PRRC Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "PRRC 209", "building_name": "PRRC Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    # PRRC Floor 3
    {"room_code": "PRRC 301", "building_name": "PRRC Building", "floor_level": 3, "room_type": "COMPUTER_LAB", "capacity": 50, "is_schedulable": True},
    {"room_code": "PRRC 302", "building_name": "PRRC Building", "floor_level": 3, "room_type": "COMPUTER_LAB", "capacity": 50, "is_schedulable": True},
    {"room_code": "PRRC 303", "building_name": "PRRC Building", "floor_level": 3, "room_type": "COMPUTER_LAB", "capacity": 50, "is_schedulable": True},
    {"room_code": "PRRC 304", "building_name": "PRRC Building", "floor_level": 3, "room_type": "COMPUTER_LAB", "capacity": 50, "is_schedulable": True},
    {"room_code": "PRRC 305", "building_name": "PRRC Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 20, "is_schedulable": False},
    {"room_code": "PRRC 306", "building_name": "PRRC Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 20, "is_schedulable": False},
    {"room_code": "PRRC 307", "building_name": "PRRC Building", "floor_level": 3, "room_type": "COMPUTER_LAB", "capacity": 50, "is_schedulable": True},
    {"room_code": "PRRC 308", "building_name": "PRRC Building", "floor_level": 3, "room_type": "COMPUTER_LAB", "capacity": 50, "is_schedulable": True},
    {"room_code": "PRRC 309", "building_name": "PRRC Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "PRRC 310", "building_name": "PRRC Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    # New Building Floor 1
    {"room_code": "NB 101", "building_name": "New Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "NB 102", "building_name": "New Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "NB 103", "building_name": "New Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "NB 104", "building_name": "New Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "NB 105", "building_name": "New Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "NB 106", "building_name": "New Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "NB 107", "building_name": "New Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    # New Building Floor 2
    {"room_code": "NB 201", "building_name": "New Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "NB 202", "building_name": "New Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "NB 203", "building_name": "New Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "NB 204", "building_name": "New Building", "floor_level": 2, "room_type": "FACULTY_OFFICE", "capacity": 25, "is_schedulable": False},
    {"room_code": "NB 205", "building_name": "New Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "NB 206", "building_name": "New Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "NB 207", "building_name": "New Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "NB 208", "building_name": "New Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    # New Building Floor 3
    {"room_code": "NB 301", "building_name": "New Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "NB 302", "building_name": "New Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "NB 303", "building_name": "New Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "NB 304", "building_name": "New Building", "floor_level": 3, "room_type": "FACULTY_OFFICE", "capacity": 30, "is_schedulable": False},
    {"room_code": "NB 305", "building_name": "New Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "NB 306", "building_name": "New Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "NB 307", "building_name": "New Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True},
    {"room_code": "NB 308", "building_name": "New Building", "floor_level": 3, "room_type": "FACULTY_LOUNGE", "capacity": 20, "is_schedulable": False},
    # Large Venues & Grounds
    {"room_code": "FUNCTION_HALL", "building_name": "New Building", "floor_level": 4, "room_type": "MULTI_PURPOSE_HALL", "capacity": 300, "is_schedulable": True},
    {"room_code": "Court", "building_name": "Campus Grounds", "floor_level": 1, "room_type": "SPORTS_COURT", "capacity": 200, "is_schedulable": True},
    {"room_code": "Oval", "building_name": "Municipal Ground", "floor_level": 1, "room_type": "SPORTS_OVAL", "capacity": 500, "is_schedulable": True},
    {"room_code": "PROPERTY_OFFICE", "building_name": "Main Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 10, "is_schedulable": False},
    {"room_code": "CAMPUS_CANTEEN", "building_name": "Student Center", "floor_level": 1, "room_type": "LECTURE", "capacity": 150, "is_schedulable": False},
]


# ---------------------------------------------------------------------------
# Response DTO Models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    service: str
    port: int
    title: str


class TOTPResponse(BaseModel):
    room: str
    session: str
    totp: str
    ts: int
    remaining_seconds: int


class CheckInResponse(BaseModel):
    success: bool
    message: str
    room_code: str
    workstation_number: int
    student_id: str
    check_in_time: str
    relocated_from_station: Optional[int] = None


class CheckOutResponse(BaseModel):
    success: bool
    message: str
    room_code: str
    workstation_number: int
    student_id: str


class FacultyCheckInRequest(BaseModel):
    faculty_name: str
    faculty_id: Optional[str] = None
    faculty_email: Optional[str] = None
    session_id: Optional[str] = None
    subject_code: Optional[str] = None
    section_code: Optional[str] = None
    notes: Optional[str] = None


class FacultyCheckOutRequest(BaseModel):
    faculty_id: Optional[str] = None
    faculty_email: Optional[str] = None


class RoomStatusItem(BaseModel):
    room_code: str
    building_name: str
    floor_level: int
    room_type: str
    capacity: int
    is_schedulable: bool
    is_quarantined: bool
    status: str
    total_stations: int
    occupied_count: int
    vacant_count: int
    operational_count: int
    occupancy_rate: float
    faculty_present: bool
    faculty_name: Optional[str] = None
    faculty_email: Optional[str] = None
    checked_in_at: Optional[str] = None
    last_updated: str


def _get_rooms_inventory() -> List[Dict[str, Any]]:
    """Retrieves full room list from DB if connected, otherwise fallback to institutional cache."""
    engine = _get_presence_engine()
    if engine is not None:
        try:
            from sqlalchemy import select
            from sqlalchemy.orm import Session
            from classync_contracts.models import Room

            with Session(engine) as session:
                rooms = session.scalars(select(Room)).all()
                if rooms:
                    return [
                        {
                            "room_code": r.room_code,
                            "building_name": r.building_name,
                            "floor_level": r.floor_level,
                            "room_type": r.room_type,
                            "capacity": r.capacity,
                            "is_schedulable": r.is_schedulable,
                        }
                        for r in rooms
                    ]
        except Exception:
            pass
    return INSTITUTIONAL_ROOMS_CATALOG


def _build_room_status_item(raw_room: Dict[str, Any]) -> Dict[str, Any]:
    code = raw_room["room_code"]
    schedulable = raw_room.get("is_schedulable", True)
    is_quarantined = not schedulable

    total_stations = 0
    operational_count = 0
    occupied_count = 0
    vacant_count = 0
    occupancy_rate = 0.0

    if code in workstation_manager._rooms or raw_room.get("room_type") == "COMPUTER_LAB":
        tracker = workstation_manager.get_room_tracker(code)
        summary = tracker.get_summary()
        total_stations = summary.total_stations
        operational_count = summary.operational_count
        occupied_count = summary.occupied_count
        vacant_count = summary.vacant_count
        occupancy_rate = round(summary.occupancy_rate, 4)

    fac = faculty_presence_manager.get_presence(code)
    faculty_present = fac is not None
    faculty_name = fac.faculty_name if fac else None
    faculty_email = fac.faculty_email if fac else None
    checked_in_at = fac.checked_in_at.isoformat() if fac and fac.checked_in_at else None

    if is_quarantined:
        computed_status = "QUARANTINED"
    elif faculty_present or occupied_count > 0:
        computed_status = "OCCUPIED"
    else:
        computed_status = "AVAILABLE"

    return {
        "room_code": code,
        "building_name": raw_room.get("building_name", "PRRC Building"),
        "floor_level": raw_room.get("floor_level", 1),
        "room_type": raw_room.get("room_type", "LECTURE"),
        "capacity": raw_room.get("capacity", 50),
        "is_schedulable": schedulable,
        "is_quarantined": is_quarantined,
        "status": computed_status,
        "total_stations": total_stations,
        "operational_count": operational_count,
        "occupied_count": occupied_count,
        "vacant_count": vacant_count,
        "occupancy_rate": occupancy_rate,
        "faculty_present": faculty_present,
        "faculty_name": faculty_name,
        "faculty_email": faculty_email,
        "checked_in_at": checked_in_at,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# REST API Route Handlers
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
def health_check() -> Dict[str, Any]:
    """Microservice health check endpoint."""
    return {
        "status": "healthy",
        "service": "presence",
        "port": 8004,
        "title": "ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System",
    }


@app.get(
    "/api/v1/presence/totp/{room_code}",
    response_model=TOTPResponse,
    status_code=status.HTTP_200_OK,
    tags=["TOTP QR Stream"],
)
def get_room_totp(room_code: str) -> Dict[str, Any]:
    """Generates the active 15s rotating TOTP QR payload and remaining seconds."""
    session = session_secret_manager.get_session(room_code)
    if not session:
        session = session_secret_manager.create_session(room_code)

    secret = session["secret"]
    session_id = session["session_id"]
    now = time.time()
    token = totp_generator.generate_token(secret, for_time=now)
    rem = totp_generator.time_remaining(for_time=now)

    return {
        "room": room_code,
        "session": str(session_id),
        "totp": token,
        "ts": int(now),
        "remaining_seconds": rem,
    }


@app.post(
    "/api/v1/presence/checkin",
    response_model=CheckInResponse,
    status_code=status.HTTP_200_OK,
    tags=["Presence"],
)
async def check_in_workstation(payload: CheckInRequest) -> Dict[str, Any]:
    """Validates Zero-Regex Student ID & 15s TOTP, then atomically claims workstation."""
    # 1. Deterministic Zero-Regex Student ID Validation (D-02, D-12)
    try:
        validated_student_id = validate_student_id(payload.student_id)
    except StudentIDValidationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=STUDENT_ID_ERROR_MESSAGE,
        )

    # 2. RFC 6238 TOTP Verification (D-04, D-12)
    session = session_secret_manager.get_session(payload.room_code)
    if not session:
        session = session_secret_manager.create_session(payload.room_code)

    secret = session["secret"]
    is_totp_valid = totp_generator.verify_token(secret, payload.totp_token, valid_window=1)
    if not is_totp_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The QR code just refreshed! Point your camera at the screen to scan the new code.",
        )

    # 3. Atomic Workstation Claim & Collision Detection (D-12)
    tracker = workstation_manager.get_room_tracker(payload.room_code)
    session_id = session["session_id"]

    try:
        claim_result = tracker.claim_workstation(
            workstation_number=payload.workstation_number,
            student_id=validated_student_id,
            session_id=session_id,
        )
    except WorkstationOutOfBoundsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except WorkstationMaintenanceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except WorkstationConflictError as e:
        # 409 Conflict with empathetic nearest-neighbor recommendation
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)

    # 4. In-Memory Circular Buffer Record (Capped at 50, O(1) FIFO)
    check_in_dt = claim_result.workstation.check_in_time or datetime.now(timezone.utc)
    log_entry = PresenceLogEntry(
        id=uuid.uuid4(),
        student_id=validated_student_id,
        room_code=payload.room_code,
        workstation_number=payload.workstation_number,
        check_in_time=check_in_dt,
        totp_verified=True,
        session_id=session_id,
    )
    circular_buffer.append(log_entry)

    # 5. Broadcast Real-Time SSE Events
    summary = tracker.get_summary()
    vacant_rate = round(summary.vacant_count / summary.total_stations, 4) if summary.total_stations > 0 else 0.0

    occupancy_payload = {
        "room_code": payload.room_code,
        "total_stations": summary.total_stations,
        "operational_count": summary.operational_count,
        "occupied_count": summary.occupied_count,
        "vacant_count": summary.vacant_count,
        "vacant_rate": vacant_rate,
        "occupancy_rate": round(summary.occupancy_rate, 4),
        "timestamp": int(time.time()),
    }
    await sse_broadcaster.broadcast(payload.room_code, "occupancy_update", occupancy_payload)

    presence_payload = {
        "room_code": payload.room_code,
        "student_id": validated_student_id,
        "workstation_number": payload.workstation_number,
        "action": "CHECK_IN",
        "timestamp": int(time.time()),
    }
    await sse_broadcaster.broadcast(payload.room_code, "presence_logged", presence_payload)

    return {
        "success": True,
        "message": claim_result.message,
        "room_code": payload.room_code,
        "workstation_number": payload.workstation_number,
        "student_id": validated_student_id,
        "check_in_time": check_in_dt.isoformat(),
        "relocated_from_station": claim_result.relocated_from_station,
    }


@app.post(
    "/api/v1/presence/checkout",
    response_model=CheckOutResponse,
    status_code=status.HTTP_200_OK,
    tags=["Presence"],
)
async def check_out_workstation(payload: CheckOutRequest) -> Dict[str, Any]:
    """Releases an occupied workstation and broadcasts vacancy update via SSE."""
    try:
        validated_student_id = validate_student_id(payload.student_id)
    except StudentIDValidationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=STUDENT_ID_ERROR_MESSAGE,
        )

    tracker = workstation_manager.get_room_tracker(payload.room_code)
    try:
        release_result = tracker.release_workstation(
            workstation_number=payload.workstation_number,
            student_id=validated_student_id,
        )
    except (WorkstationOutOfBoundsError, WorkstationConflictError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Broadcast SSE update
    summary = tracker.get_summary()
    vacant_rate = round(summary.vacant_count / summary.total_stations, 4) if summary.total_stations > 0 else 0.0

    occupancy_payload = {
        "room_code": payload.room_code,
        "total_stations": summary.total_stations,
        "operational_count": summary.operational_count,
        "occupied_count": summary.occupied_count,
        "vacant_count": summary.vacant_count,
        "vacant_rate": vacant_rate,
        "occupancy_rate": round(summary.occupancy_rate, 4),
        "timestamp": int(time.time()),
    }
    await sse_broadcaster.broadcast(payload.room_code, "occupancy_update", occupancy_payload)

    presence_payload = {
        "room_code": payload.room_code,
        "student_id": validated_student_id,
        "workstation_number": payload.workstation_number,
        "action": "CHECK_OUT",
        "timestamp": int(time.time()),
    }
    await sse_broadcaster.broadcast(payload.room_code, "presence_logged", presence_payload)

    return {
        "success": True,
        "message": f"Workstation PC-{payload.workstation_number} successfully released.",
        "room_code": payload.room_code,
        "workstation_number": payload.workstation_number,
        "student_id": validated_student_id,
    }


@app.get(
    "/api/v1/presence/rooms/{room_code}/occupancy",
    status_code=status.HTTP_200_OK,
    tags=["Occupancy Telemetry"],
)
def get_room_occupancy(room_code: str) -> Dict[str, Any]:
    """Returns the complete workstation grid snapshot and vacancy metrics."""
    tracker = workstation_manager.get_room_tracker(room_code)
    summary = tracker.get_summary()
    data = summary.to_dict()
    data["vacant_rate"] = round(summary.vacant_count / summary.total_stations, 4) if summary.total_stations > 0 else 0.0
    return data


@app.get(
    "/api/v1/presence/rooms/{room_code}/recent-logs",
    status_code=status.HTTP_200_OK,
    tags=["Occupancy Telemetry"],
)
def get_recent_presence_logs(
    room_code: str,
    limit: int = Query(default=50, ge=1, le=50),
) -> List[Dict[str, Any]]:
    """Returns recent check-in events from the circular buffer (capped at 50, newest first)."""
    logs = circular_buffer.get_recent(limit=limit, reverse=True)
    room_logs = [log.to_dict() for log in logs if log.room_code == room_code]
    return room_logs


@app.get(
    "/api/v1/presence/rooms/{room_code}/stream",
    tags=["Real-Time SSE"],
)
async def stream_room_vacancy(
    room_code: str,
    request: Request,
    once: bool = Query(default=False),
) -> StreamingResponse:
    """Server-Sent Events endpoint pushing real-time vacancy transitions to connected clients."""
    tracker = workstation_manager.get_room_tracker(room_code)
    summary = tracker.get_summary()
    initial_data = summary.to_dict()
    initial_data["vacant_rate"] = (
        round(summary.vacant_count / summary.total_stations, 4) if summary.total_stations > 0 else 0.0
    )

    return StreamingResponse(
        sse_broadcaster.event_generator(room_code, initial_data=initial_data, request=request, once=once),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Campus Room Availability & Faculty Presence (Phase 12 & 13)
# ---------------------------------------------------------------------------

@app.get(
    "/api/v1/presence/rooms/status",
    response_model=List[RoomStatusItem],
    status_code=status.HTTP_200_OK,
    tags=["Occupancy Telemetry"],
)
def get_all_rooms_status(
    building: Optional[str] = Query(default=None),
    is_schedulable: Optional[bool] = Query(default=None),
    room_type: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None),
) -> List[Dict[str, Any]]:
    """Returns the live occupancy, faculty check-in, and operational status of all campus spaces."""
    raw_rooms = _get_rooms_inventory()
    items: List[Dict[str, Any]] = []

    for raw in raw_rooms:
        if building and raw.get("building_name", "").lower() != building.lower():
            continue
        if is_schedulable is not None and raw.get("is_schedulable") != is_schedulable:
            continue
        if room_type and raw.get("room_type", "").lower() != room_type.lower():
            continue

        item = _build_room_status_item(raw)
        if status_filter and item["status"].lower() != status_filter.lower():
            continue

        items.append(item)

    return items


@app.get(
    "/api/v1/presence/rooms/{room_code}/status",
    response_model=RoomStatusItem,
    status_code=status.HTTP_200_OK,
    tags=["Occupancy Telemetry"],
)
def get_room_status(room_code: str) -> Dict[str, Any]:
    """Retrieves live occupancy and faculty presence for a single room."""
    raw_rooms = _get_rooms_inventory()
    matched = next((r for r in raw_rooms if r["room_code"].lower() == room_code.lower()), None)
    if not matched:
        # Create minimal fallback item if not in catalog
        matched = {
            "room_code": room_code,
            "building_name": "PRRC Building",
            "floor_level": 1,
            "room_type": "LECTURE",
            "capacity": 50,
            "is_schedulable": True,
        }
    return _build_room_status_item(matched)


@app.get(
    "/api/v1/presence/rooms/{room_code}/faculty-status",
    status_code=status.HTTP_200_OK,
    tags=["Faculty Presence"],
)
def get_room_faculty_status(room_code: str) -> Dict[str, Any]:
    """Checks whether a professor is currently present/checked into the room."""
    rec = faculty_presence_manager.get_presence(room_code)
    return {
        "room_code": room_code,
        "faculty_present": rec is not None,
        "presence": rec.to_dict() if rec else None,
    }


@app.post(
    "/api/v1/presence/rooms/{room_code}/faculty-checkin",
    status_code=status.HTTP_200_OK,
    tags=["Faculty Presence"],
)
async def faculty_checkin_endpoint(
    room_code: str,
    payload: FacultyCheckInRequest,
) -> Dict[str, Any]:
    """Marks professor as physically present in the room and broadcasts SSE event."""
    record = faculty_presence_manager.check_in(
        room_code=room_code,
        faculty_name=payload.faculty_name,
        faculty_id=payload.faculty_id,
        faculty_email=payload.faculty_email,
        session_id=payload.session_id,
        subject_code=payload.subject_code,
        section_code=payload.section_code,
        notes=payload.notes,
    )

    # Broadcast real-time SSE event
    sse_payload = {
        "room_code": room_code,
        "faculty_name": record.faculty_name,
        "faculty_email": record.faculty_email,
        "checked_in_at": record.checked_in_at.isoformat() if record.checked_in_at else None,
        "status": "OCCUPIED",
        "action": "FACULTY_CHECK_IN",
        "timestamp": int(time.time()),
    }
    await sse_broadcaster.broadcast(room_code, "faculty_presence", sse_payload)

    return {
        "success": True,
        "message": f"Professor {record.faculty_name} checked into {room_code}.",
        "room_code": room_code,
        "faculty_name": record.faculty_name,
        "checked_in_at": record.checked_in_at.isoformat() if record.checked_in_at else None,
        "status": "OCCUPIED",
    }


@app.post(
    "/api/v1/presence/rooms/{room_code}/faculty-checkout",
    status_code=status.HTTP_200_OK,
    tags=["Faculty Presence"],
)
async def faculty_checkout_endpoint(
    room_code: str,
    payload: Optional[FacultyCheckOutRequest] = None,
) -> Dict[str, Any]:
    """Releases professor presence from the room and broadcasts vacancy SSE event."""
    fid = payload.faculty_id if payload else None
    femail = payload.faculty_email if payload else None
    record = faculty_presence_manager.check_out(
        room_code=room_code,
        faculty_id=fid,
        faculty_email=femail,
    )

    sse_payload = {
        "room_code": room_code,
        "status": "AVAILABLE",
        "action": "FACULTY_CHECK_OUT",
        "timestamp": int(time.time()),
    }
    await sse_broadcaster.broadcast(room_code, "faculty_presence", sse_payload)

    return {
        "success": True,
        "message": f"Faculty checked out from {room_code}.",
        "room_code": room_code,
        "status": "AVAILABLE",
        "previous_presence": record.to_dict() if record else None,
    }

