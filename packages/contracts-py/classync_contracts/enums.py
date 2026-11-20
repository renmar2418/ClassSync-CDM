"""Enums for ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System.

Enforces domain enums aligned with institutional parameters:
- 100% Full-Time Faculty (no part-time, no adjunct)
- UNIFIED Cohort Mode (zero sub-batch splitting)
- Discrete continuous 30-min slots across Mon-Sat 07:00-19:00 and Sunday civic hours
"""

from enum import Enum, IntEnum


class RoomType(str, Enum):
    """Categorization of physical instructional and assembly facilities."""
    LECTURE = "LECTURE"
    COMPUTER_LAB = "COMPUTER_LAB"
    SCIENCE_LAB = "SCIENCE_LAB"
    FUNCTION_HALL = "FUNCTION_HALL"
    SPORTS_COURT = "SPORTS_COURT"
    SPORTS_OVAL = "SPORTS_OVAL"
    MULTI_PURPOSE_HALL = "MULTI_PURPOSE_HALL"
    SIMULATION_LAB = "SIMULATION_LAB"
    FACULTY_OFFICE = "FACULTY_OFFICE"
    FACULTY_LOUNGE = "FACULTY_LOUNGE"


class DayOfWeek(IntEnum):
    """Zero-indexed day of week: 0 = Monday, 6 = Sunday."""
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class CohortMode(str, Enum):
    """Strictly UNIFIED cohort mode per CdM/PNM institutional mandate. Sub-batch splitting is prohibited."""
    UNIFIED = "UNIFIED"


class EmploymentTier(str, Enum):
    """Strictly FULL_TIME faculty per CdM/PNM institutional mandate (100% full-time)."""
    FULL_TIME = "FULL_TIME"


class UserRole(str, Enum):
    """Role-Based Access Control tiers across the platform."""
    ADMIN = "ADMIN"
    FACULTY = "FACULTY"
    STUDENT = "STUDENT"


class WorkstationStatus(str, Enum):
    """Individual workstation operational and occupancy state in computer laboratories."""
    VACANT = "VACANT"
    OCCUPIED = "OCCUPIED"
    MAINTENANCE = "MAINTENANCE"


class LaboratorySessionState(str, Enum):
    """Lifecycle state of instructional laboratory sessions."""
    STANDBY = "STANDBY"
    INSTRUCTIONAL_SESSION = "INSTRUCTIONAL_SESSION"
    OPEN_RESEARCH_HUB = "OPEN_RESEARCH_HUB"


class SolverStatus(str, Enum):
    """CP-SAT constraint solver completion status."""
    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
