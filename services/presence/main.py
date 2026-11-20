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
