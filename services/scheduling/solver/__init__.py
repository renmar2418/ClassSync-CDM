"""ClassSync Scheduling Solver Package.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System
"""

from services.scheduling.solver.model_builder import (
    CPSATMasterModelBuilder,
    MasterCPSATSolver,
    OfferingData,
    RoomData,
    SectionData,
    ScheduleSolutionEntry,
    SolverResult,
)
from services.scheduling.solver.objective_weights import (
    SolverObjectiveWeights,
    add_all_objective_weights,
)
from services.scheduling.solver.sunday_rules import (
    DAY_SUNDAY,
    FUNCTION_HALL_ROOM_CODE,
    ROTC_START_SLOT,
    ROTC_DURATION_SLOTS,
    BUFFER_START_SLOT,
    BUFFER_DURATION_SLOTS,
    NSTP_START_SLOT,
    NSTP_DURATION_SLOTS,
    POST_CIVIC_START_SLOT,
    POST_CIVIC_DURATION_SLOTS,
    OUTDOOR_GROUNDS_ROOM_CODES,
    is_rotc_subject,
    is_nstp_subject,
    is_pathfit_subject,
    is_civic_subject,
    is_academic_subject,
    is_outdoor_ground,
    get_sunday_civic_reservations,
    apply_sunday_constraints,
)
from services.scheduling.solver.conflict_auditor import (
    ConflictAuditor,
    CollisionCategory,
    CollisionRecord,
    AuditReport,
    audit_timetable_entries,
)
from services.scheduling.solver.delta_resolver import (
    LocalizedDeltaResolver,
    OfferingMetadata,
)

__all__ = [
    "CPSATMasterModelBuilder",
    "MasterCPSATSolver",
    "OfferingData",
    "RoomData",
    "SectionData",
    "ScheduleSolutionEntry",
    "SolverResult",
    "SolverObjectiveWeights",
    "add_all_objective_weights",
    "DAY_SUNDAY",
    "FUNCTION_HALL_ROOM_CODE",
    "ROTC_START_SLOT",
    "ROTC_DURATION_SLOTS",
    "BUFFER_START_SLOT",
    "BUFFER_DURATION_SLOTS",
    "NSTP_START_SLOT",
    "NSTP_DURATION_SLOTS",
    "POST_CIVIC_START_SLOT",
    "POST_CIVIC_DURATION_SLOTS",
    "OUTDOOR_GROUNDS_ROOM_CODES",
    "is_rotc_subject",
    "is_nstp_subject",
    "is_pathfit_subject",
    "is_civic_subject",
    "is_academic_subject",
    "is_outdoor_ground",
    "get_sunday_civic_reservations",
    "apply_sunday_constraints",
    "ConflictAuditor",
    "CollisionCategory",
    "CollisionRecord",
    "AuditReport",
    "audit_timetable_entries",
    "LocalizedDeltaResolver",
    "OfferingMetadata",
]
