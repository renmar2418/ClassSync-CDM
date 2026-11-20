/**
 * Shared Domain Models & Contracts for ClassSync:
 * AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System
 *
 * Exact 1:1 parity with Python Pydantic V2 contracts.
 */

// ---------------------------------------------------------------------------
// Domain Enums
// ---------------------------------------------------------------------------

export type RoomType =
  | 'LECTURE'
  | 'COMPUTER_LAB'
  | 'SCIENCE_LAB'
  | 'FUNCTION_HALL'
  | 'SPORTS_COURT'
  | 'SPORTS_OVAL'
  | 'MULTI_PURPOSE_HALL'
  | 'SIMULATION_LAB'
  | 'FACULTY_OFFICE'
  | 'FACULTY_LOUNGE';

export type DayOfWeek = 0 | 1 | 2 | 3 | 4 | 5 | 6; // 0=Monday, 6=Sunday

export type CohortMode = 'UNIFIED'; // Strictly UNIFIED per CdM/PNM mandate

export type EmploymentTier = 'FULL_TIME'; // Strictly 100% full-time faculty

export type UserRole = 'ADMIN' | 'FACULTY' | 'STUDENT';

export type WorkstationStatus = 'VACANT' | 'OCCUPIED' | 'MAINTENANCE';

export type LaboratorySessionState = 'STANDBY' | 'INSTRUCTIONAL_SESSION' | 'OPEN_RESEARCH_HUB';

export type SolverStatus = 'OPTIMAL' | 'FEASIBLE' | 'INFEASIBLE';

// ---------------------------------------------------------------------------
// Academic Period
// ---------------------------------------------------------------------------

export interface AcademicPeriodBase {
  academic_year: string; // e.g. '2026-2027'
  semester: 1 | 2 | 3;
  is_active: boolean;
}

export interface AcademicPeriodCreate extends AcademicPeriodBase {}

export interface AcademicPeriod extends AcademicPeriodBase {
  id: string; // UUID
  created_at: string; // ISO 8601
}

// ---------------------------------------------------------------------------
// Room & Physical Facilities
// ---------------------------------------------------------------------------

export interface RoomBase {
  room_code: string; // e.g. 'PRRC 108', 'NB 204'
  building_name: string; // 'PRRC Building', 'New Building'
  floor_level: number;
  room_type: RoomType;
  capacity: number;
  is_schedulable: boolean; // False for NB 204, NB 304, NB 308
  has_aircon: boolean;
  has_projector: boolean;
  exclusive_program: string | null; // 'BSED_SCIENCE' for PRRC 108
}

export interface RoomCreate extends RoomBase {}

export interface Room extends RoomBase {}

export interface RoomFilterQuery {
  is_schedulable?: boolean;
  building_name?: string;
  room_type?: RoomType;
}

// ---------------------------------------------------------------------------
// Curriculum Subject
// ---------------------------------------------------------------------------

export interface CurriculumSubjectBase {
  subject_code: string; // e.g. 'CC-IPT2'
  descriptive_title: string;
  lecture_hours: number;
  lab_hours: number;
  units: number;
  required_room_type: RoomType;
}

export interface CurriculumSubjectCreate extends CurriculumSubjectBase {}

export interface CurriculumSubject extends CurriculumSubjectBase {
  id: string; // UUID
}

// ---------------------------------------------------------------------------
// Faculty Profile
// ---------------------------------------------------------------------------

export interface FacultyProfileBase {
  institutional_email: string; // Must end with @pnm.edu.ph
  full_name: string;
  employment_tier: EmploymentTier; // 'FULL_TIME'
  role: 'ADMIN' | 'FACULTY';
  is_active: boolean;
}

export interface FacultyProfileCreate extends FacultyProfileBase {
  password?: string;
}

export interface FacultyProfile extends FacultyProfileBase {
  id: string; // UUID
  requires_password_change: boolean;
}

// ---------------------------------------------------------------------------
// Section
// ---------------------------------------------------------------------------

export interface SectionBase {
  academic_period_id: string; // UUID
  section_code: string; // e.g. 'BSIT-3A'
  year_level: number; // 1 to 5
  enrolled_student_count: number; // 60-70+
}

export interface SectionCreate extends SectionBase {}

export interface Section extends SectionBase {
  id: string; // UUID
}

// ---------------------------------------------------------------------------
// Course Offering
// ---------------------------------------------------------------------------

export interface CourseOfferingBase {
  academic_period_id: string; // UUID
  subject_id: string; // UUID
  section_id: string; // UUID
  faculty_id: string; // UUID
}

export interface CourseOfferingCreate extends CourseOfferingBase {}

export interface CourseOffering extends CourseOfferingBase {
  id: string; // UUID
}

export interface CourseOfferingDetail extends CourseOffering {
  subject?: CurriculumSubject;
  section?: Section;
  faculty?: FacultyProfile;
}

// ---------------------------------------------------------------------------
// Timetable Entry
// ---------------------------------------------------------------------------

export interface TimetableEntryBase {
  offering_id: string; // UUID
  room_code: string;
  day_of_week: DayOfWeek; // 0=Mon, 6=Sun
  start_slot: number; // 0 to 23 (30-min continuous intervals)
  duration_slots: number; // duration >= 1, start + duration <= 24
  cohort_mode: CohortMode; // Strictly 'UNIFIED'
  is_locked: boolean;
  revision_hash: string;
}

export interface TimetableEntryCreate extends TimetableEntryBase {}

export interface TimetableEntry extends TimetableEntryBase {
  id: string; // UUID
}

export interface TimetableGridSlot {
  day_of_week: number;
  slot_index: number;
  time_label: string;
  is_occupied: boolean;
  entry?: TimetableEntry;
}

// ---------------------------------------------------------------------------
// Workstation
// ---------------------------------------------------------------------------

export interface WorkstationBase {
  room_code: string;
  workstation_number: number;
  is_operational: boolean;
}

export interface WorkstationCreate extends WorkstationBase {}

export interface Workstation extends WorkstationBase {
  id: string; // UUID
}

export interface WorkstationClaim {
  room_code: string;
  workstation_number: number;
  student_id: string; // Strictly 24-XXXXX
  totp_token: string;
}

// ---------------------------------------------------------------------------
// Presence Log & Ingress
// ---------------------------------------------------------------------------

export interface PresenceLogBase {
  room_code: string;
  workstation_number: number;
  student_id: string; // Strictly 24-XXXXX
  session_id: string; // UUID
  totp_verified: boolean;
}

export interface PresenceLogCreate extends PresenceLogBase {}

export interface PresenceLog extends PresenceLogBase {
  id: string; // UUID
  check_in_time: string; // ISO 8601
  check_out_time: string | null;
}

export interface CheckInRequest {
  room_code: string;
  workstation_number: number;
  student_id: string; // Strictly 24-XXXXX
  totp_token: string; // 6-digit TOTP
}

export interface CheckOutRequest {
  room_code: string;
  workstation_number: number;
  student_id: string;
}

// ---------------------------------------------------------------------------
// Security, Auth & Cloudflare Turnstile
// ---------------------------------------------------------------------------

export interface TurnstileVerifyRequest {
  token: string;
}

export interface TurnstileVerifyResponse {
  success: boolean;
  error_codes?: string[];
}

export interface GoogleOAuthTokenRequest {
  id_token: string;
}

export interface GoogleTokenClaims {
  sub: string;
  email: string;
  email_verified: boolean;
  hd?: string; // Must be "student.pnm.edu.ph" or "pnm.edu.ph"
  name?: string;
}

export interface PasswordSetupRequest {
  student_or_employee_id: string;
  current_password?: string;
  new_password: string;
  confirm_password: string;
}

export interface PasswordIntegrityResponse {
  valid: boolean;
  entropy_bits: number;
  message: string;
}

export interface LocalLoginRequest {
  identifier: string; // Email or 24-XXXXX Student ID
  password: string;
  turnstile_token: string;
}

export interface SessionUser {
  id: string; // UUID
  identifier: string;
  full_name: string;
  role: UserRole;
  requires_password_change: boolean;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user: SessionUser;
}

// ---------------------------------------------------------------------------
// Real-Time Presence & Telemetry Events
// ---------------------------------------------------------------------------

export interface LiveRoomVacancyEvent {
  room_code: string;
  occupied_count: number;
  vacant_count: number;
  total_stations: number;
  active_session_id: string | null;
  timestamp: number;
}

export interface WorkstationStateEvent {
  room_code: string;
  workstation_number: number;
  status: WorkstationStatus;
  student_id: string | null;
  timestamp: number;
}

// ---------------------------------------------------------------------------
// Solver & Optimization DTOs
// ---------------------------------------------------------------------------

export interface SolverRunRequest {
  academic_period_id: string; // UUID
  time_limit_seconds?: number;
}

export interface SolverRunResponse {
  status: SolverStatus;
  total_conflicts: number;
  solve_time_seconds: number;
  timetable_entries: TimetableEntry[];
}

export interface DeltaSolveRequest {
  disrupted_room_code: string;
  day_of_week: DayOfWeek;
  start_slot: number;
  duration_slots: number;
}

export interface DeltaSolveResponse {
  delta_solved: boolean;
  solve_time_seconds: number;
  reassigned_entries: TimetableEntry[];
}

export interface ConflictReport {
  has_conflict: boolean;
  room_collisions: number;
  faculty_collisions: number;
  section_collisions: number;
  quarantine_violations: number;
  details: string[];
}
