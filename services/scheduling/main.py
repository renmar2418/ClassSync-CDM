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
import uuid
from typing import List, Dict, Optional, Any
from fastapi import FastAPI, HTTPException, status
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
