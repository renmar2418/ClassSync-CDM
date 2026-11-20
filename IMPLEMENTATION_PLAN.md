# ClassSync V2 — Master Implementation Plan
**Official Project Title:** ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System  
**Institution:** Pamantasan ng Montalban / Colegio de Montalban (CdM / PNM) — Institute of Computing Studies  
**Author:** Lead Systems Architect & Engineering Orchestrator  
**Status:** Approved Architectural Blueprint & Active Execution Roadmap  
**Date:** 2026-11-19  

---

## Executive Summary & Core Mandates

ClassSync is an enterprise academic operations platform engineered to resolve physical room scarcity, cross-building transit bottlenecks, faculty workload distribution, and physical laboratory attendance verification.

### Institutional Parameters (Authoritative Baseline)
1. **Academic Time Horizon & Discretization:**
   - Monday through Saturday, strictly 07:00 to 19:00.
   - Continuous 30-minute standard intervals (Slots 0 to 23).
   - Zero 10-minute inter-building penalties.
2. **Faculty Model:**
   - 100% Full-Time Faculty (0 part-time, 0 adjunct).
   - Available across 07:00–19:00 Mon–Sat by default.
   - Zero artificial daily fatigue caps (no 3-hour limits) and zero course preparation caps.
3. **Cohort Model:**
   - Unified Cohort Mode: Sections regularly exceed 60–70+ students.
   - Zero Sub-Batch Splitting (no A/B partition for lectures or computer labs).
   - COMLAB workstation capacity dynamically scales to match enrolled section sizes.
4. **Spatial Quarantine & Program Exclusivity:**
   - Quarantined: Faculty offices (NB 204, NB 304), faculty lounge (NB 308), property/storage, and canteen are flagged `is_schedulable = FALSE` and hidden from schedules.
   - Program Exclusivity: Room PRRC 108 is strictly locked to `BSED_SCIENCE`.
5. **Sunday Civic Training Space Allocation:**
   - ROTC: Strictly 07:00–12:00 in the Function Hall (Slots 0–9).
   - NSTP (CWTS / LTS): Strictly 13:00–17:00 in the Function Hall (Slots 12–19).
   - Turnover Clearance: 12:00–13:00 (Slots 10–11).
   - PATHFIT / Sports: Exclusively scheduled on Athletic Oval, Montalban Sports Complex, and Open Grounds.
6. **Zero-Trust Security & Identity:**
   - Student ID: Strictly `24-XXXXX` format validated via deterministic zero-regex ASCII/length checking.
   - Google Workspace OAuth: Restricted to hosted domains `student.pnm.edu.ph` and `pnm.edu.ph`.
   - Bot Mitigation: Cloudflare Turnstile token validation via edge proxy.
   - Password Integrity: Argon2id hashing with OWASP ASVS 4.0 entropy rules for mandatory first-login password creation.
7. **Design System & UX Laws:**
   - Soft Rouge & Cool Neutral palette: `--brand-midnight: #34141f`, `--brand-rouge: #872e49`, `--brand-rose: #f8ebf0`.
   - Typography: Self-hosted `InterVariable.woff2` (zero external CDN requests).
   - WCAG 2.2 AA compliance: Text contrast $\ge 4.5:1$, touch targets $\ge 48\times 48\text{px}$.
   - Plain-Language Error Communication: Absolute ban on technical system jargon in user notifications.

---

## Master Architecture & Directory Layout

```
Classync/
├── apps/
│   ├── web/                              # React 19 + TypeScript + Vite + Tailwind CSS v4 PWA
│   │   ├── public/
│   │   │   ├── branding/                 # cdm-seal.png, classsync-logo-assets/
│   │   │   └── fonts/                    # InterVariable.woff2
│   │   └── src/
│   │       ├── api/                      # Gateway clients (SSE, REST, Turnstile)
│   │       ├── components/               # HeroCard, Modals, Tables, Skeletons, RadialTimer
│   │       ├── pages/                    # Admin, Faculty, Student, Projector views
│   │       ├── styles/                   # tokens.css, index.css (@theme)
│   │       └── service-worker.ts         # Offline-first caching strategy
│   └── mobile/                           # React Native (Expo) student companion app
│       └── src/
│           ├── components/               # CameraScanner, ScheduleCard
│           └── storage/                  # SQLite offline timetable cache
├── packages/
│   ├── contracts-py/                    # Python Pydantic V2 schemas & SQLAlchemy 2.0 models
│   │   └── classync_contracts/
│   │       ├── __init__.py
│   │       ├── models.py                 # PostgreSQL 16 declarative ORM models
│   │       ├── schemas.py                # Pydantic V2 validation schemas
│   │       └── enums.py                  # RoomType, CohortMode, Role, DayOfWeek
│   └── shared-types-ts/                 # TypeScript mirrored interfaces & plain-language errors
│       └── src/
│           ├── index.ts
│           ├── models.ts
│           └── errors.ts
├── services/
│   ├── gateway/                         # Port 8000: Turnstile, Google OAuth, Argon2id, RBAC
│   │   ├── auth/                        # Turnstile proxy, OAuth claim validator, Argon2id
│   │   ├── proxy/                       # Reverse proxy dispatching to microservices
│   │   └── main.py
│   ├── academic/                        # Port 8001: Curriculum, Faculty, Sections, Rooms
│   │   ├── api/                         # CRUD endpoints for academic resources
│   │   ├── services/                    # Quarantine filter & program exclusivity logic
│   │   └── main.py
│   ├── scheduling/                      # Port 8002: Google OR-Tools CP-SAT Solver & Auditor
│   │   ├── solver/
│   │   │   ├── model_builder.py         # CP-SAT interval variables & constraints
│   │   │   ├── delta_resolver.py        # Sub-second (<0.10s) localized re-solver
│   │   │   ├── sunday_rules.py          # Civic training space allocation rules
│   │   │   ├── conflict_auditor.py      # Independent multi-pass collision verifier
│   │   │   └── objective_weights.py     # Penalty terms (lunch=100, gaps=50, span=20)
│   │   └── main.py
│   ├── presence/                        # Port 8004: 15s TOTP QR, Workstations, SSE Stream
│   │   ├── totp/                        # RFC 6238 15s rotating token generator
│   │   ├── sse/                         # Server-Sent Events vacancy broadcast
│   │   └── main.py
│   └── notification/                    # Port 8003: Real-time alert relays
├── alembic/                             # Database migrations directory
│   ├── versions/                        # Migration scripts
│   └── env.py
├── tests/
│   ├── unit/                            # Unit tests for contracts, solver, presence
│   ├── integration/                     # Service-to-service integration tests
│   └── e2e/                             # Opaque-box E2E test suite (Tiers 1-4)
├── render.yaml                          # Render microservices deployment blueprint
├── vercel.json                          # Vercel static PWA hosting configuration
└── pnpm-workspace.yaml                  # Monorepo workspace configuration
```

---

## 6-Phase Engineering Pipeline

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PHASE 1: CONTRACTS & DB                         │
│   Pydantic V2 • TypeScript Types • SQLAlchemy 2.0 • Alembic Migrations │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                       PHASE 2: SOLVER CALIBRATION                      │
│     OR-Tools CP-SAT • 30-min Slots • Sunday Rules • Delta Re-solver    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                      PHASE 3: HARDWARE & PRESENCE                      │
│       15s TOTP QR • Projector View • Zero-Regex ID • SSE Vacancy       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                       PHASE 4: SECURITY GATEWAY                        │
│    Cloudflare Turnstile • Google OAuth • Argon2id • OWASP ASVS • RBAC  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                      PHASE 5: CLIENT APPLICATIONS                      │
│     React 19 PWA • Soft Rouge System • Inter Font • Expo QR Scanner    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                       PHASE 6: CLOUD DEPLOYMENT                        │
│      render.yaml • vercel.json • Firestore CQRS • 100% E2E Pass        │
└────────────────────────────────────────────────────────────────────────┘
```

---

### PHASE 1: CONTRACTS & DATABASE SCHEMAS

#### Objectives
Scaffold monorepo structure, establish dual-language contract parity (Pydantic V2 and TypeScript), define PostgreSQL 16 SQLAlchemy 2.0 declarative models, and initialize Alembic migrations.

#### Tasks & Concrete Deliverables
1. **Workspace Initialization:**
   - Author `pnpm-workspace.yaml`, root `package.json`, and pyproject configurations.
   - Scaffold directories: `apps/web`, `apps/mobile`, `packages/contracts-py`, `packages/shared-types-ts`, `services/gateway`, `services/academic`, `services/scheduling`, `services/presence`, `services/notification`, `alembic/`.
2. **Shared Contract Packages:**
   - Author `packages/contracts-py/classync_contracts/schemas.py`: Pydantic V2 schemas for AcademicPeriod, Room, CurriculumSubject, FacultyProfile, Section, CourseOffering, TimetableEntry, Workstation, PresenceLog.
   - Author `packages/contracts-py/classync_contracts/enums.py`: RoomType, DayOfWeek, CohortMode, EmploymentTier, Role.
   - Author `packages/shared-types-ts/src/models.ts`: TypeScript interfaces with exact 1:1 parity with Pydantic V2 models.
   - Author `packages/shared-types-ts/src/errors.ts`: Human-centered plain-language error models.
3. **SQLAlchemy 2.0 Declarative Models:**
   - Author `packages/contracts-py/classync_contracts/models.py`:
     - `AcademicPeriod`: UUID PK, `(academic_year, semester)` compound unique constraint.
     - `Room`: Natural string PK (`room_code`), `is_schedulable` boolean (default TRUE, FALSE for NB 204, NB 304, NB 308), `exclusive_program` nullable string ('BSED_SCIENCE' for PRRC 108).
     - `CurriculumSubject`: UUID PK, unique `subject_code`, positive units/lecture/lab hours.
     - `FacultyProfile`: UUID PK, unique institutional email (`@pnm.edu.ph`), `100% FULL_TIME` employment tier, Argon2id `password_hash`, `requires_password_change` default TRUE.
     - `Section`: UUID PK, unique `section_code`, enrolled student count (60–70+).
     - `CourseOffering`: UUID PK, foreign keys with unique `(academic_period_id, subject_id, section_id)`.
     - `TimetableEntry`: UUID PK, `cohort_mode = 'UNIFIED'`, `start_slot` $\in [0, 23]$, check constraint `duration_slots >= 1 AND start_slot + duration_slots <= 24`, `revision_hash`.
     - `Workstation`: UUID PK, unique `(room_code, workstation_number)`.
     - `PresenceLog`: UUID PK, `student_id` checked via `length(student_id) = 8 AND student_id LIKE '24-%'`.
4. **Alembic Migration Environment:**
   - Author `alembic.ini` and `alembic/env.py`.
   - Generate initial migration script (`0001_initial_schema.py`) creating all tables, indexes, check constraints, and foreign keys with proper cascade behaviors.
   - Author institutional seed data (`alembic/seed_data.py`) with CdM/PNM rooms (including quarantined NB 204/304/308 and PRRC 108), subjects, full-time faculty, and test users (`admin@pnm.edu.ph`, `teacher@pnm.edu.ph`, `24-00123@student.pnm.edu.ph`).
5. **Phase 1 Validation Suite:**
   - Automated test suite `tests/unit/test_phase1_schemas.py` verifying model compilation, check constraints, room quarantine exclusion query, and JSON serialization.

#### Validation Criteria (Phase 1 Gate)
- [x] Monorepo workspace links packages cleanly.
- [x] Pydantic V2 and TypeScript types have 100% field parity.
- [x] All 9 SQLAlchemy 2.0 models compile with explicit check constraints and cascade rules.
- [x] Quarantined rooms (`NB 204`, `NB 304`, `NB 308`) return `is_schedulable = FALSE`.
- [x] Room `PRRC 108` has `exclusive_program = 'BSED_SCIENCE'`.
- [x] Alembic migration executes without error against PostgreSQL.

---

### PHASE 2: SOLVER CALIBRATION (OR-Tools CP-SAT)

#### Objectives
Implement Google OR-Tools CP-SAT constraint optimization engine enforcing institutional parameters, 100% zero-conflict guarantee, Sunday civic space allocation, soft penalty minimization, and sub-second localized delta re-solving.

#### Tasks & Concrete Deliverables
1. **CP-SAT Master Model Builder:**
   - Author `services/scheduling/solver/model_builder.py`:
     - Interval variables $I_o = \text{NewIntervalVar}(\text{start}_o, L(o), \text{end}_o)$.
     - Optional room interval variables $I_{o, r}$ linked to boolean indicators $x_{o, r}$.
     - Hard constraints:
       - Room non-overlap: `AddNoOverlap` per schedulable room.
       - Faculty non-overlap: `AddNoOverlap` per full-time faculty.
       - Section non-overlap: `AddNoOverlap` per unified student cohort.
       - Day boundary contiguity: $\text{start}_o \bmod 24 + L(o) \le 24$.
       - Academic days: $d \in [0, 5]$ (Mon–Sat) for standard curriculum offerings.
       - Exclusive room locks: PRRC 108 locked to BSED_SCIENCE; quarantined rooms excluded from $\mathcal{R}_{\text{sched}}$.
2. **Sunday Civic Space Allocation Engine:**
   - Author `services/scheduling/solver/sunday_rules.py`:
     - Function Hall locked on Sunday ($d=6$):
       - ROTC: 07:00–12:00 (slots 0–9, $L=10$).
       - NSTP: 13:00–17:00 (slots 12–19, $L=8$).
       - Buffer: 12:00–13:00 (slots 10–11) clear.
     - PATHFIT locked to Athletic Oval / Sports Complex / Open Grounds.
3. **Soft Constraint & Objective Function Optimizer:**
   - Author `services/scheduling/solver/objective_weights.py`:
     - $W_{\text{lunch}} = 100$: Penalize failure to preserve continuous 60-min lunch gap in 11:00–14:00.
     - $W_{\text{gap}} = 50$: Penalize unwanted student idle gaps between classes.
     - $W_{\text{compact}} = 20$: Minimize faculty daily teaching span.
     - $W_{\text{room\_stability}} = 10$: Reward scheduling consecutive lectures in same room.
4. **Sub-Second Localized Delta Re-solver:**
   - Author `services/scheduling/solver/delta_resolver.py`:
     - Freezes 99% of assigned variables from baseline timetable $\mathcal{S}^*$.
     - Identifies disrupted offerings $\mathcal{O}_{\text{delta}}$ affected by room outage or emergency closure.
     - Solves localized bipartite matching over vacant candidate rooms without changing time slots.
     - Benchmark latency requirement: $< 0.10\text{s}$ ($<100\text{ms}$).
5. **Independent Multi-Pass Conflict Auditor:**
   - Author `services/scheduling/solver/conflict_auditor.py`:
     - Secondary verification engine that independently scans timetable output.
     - Computes room overlaps, faculty collisions, section collisions, Sunday violations, and quarantine leaks.
     - Emits cryptographic SHA-256 revision hash when total collisions == 0.
6. **Phase 2 Validation Suite:**
   - Automated benchmark tests `tests/unit/test_phase2_solver.py` and `tests/unit/test_delta_resolver.py`.

#### Validation Criteria (Phase 2 Gate)
- [x] Zero hard conflicts: Provably 0 room double-bookings, 0 faculty collisions, 0 section collisions.
- [x] Mon–Sat 07:00–19:00 operational boundary strictly respected.
- [x] Sunday Function Hall strictly partitioned: ROTC 07:00–12:00, NSTP 13:00–17:00.
- [x] All cohorts scheduled in UNIFIED mode (zero sub-batch splitting).
- [x] Quarantined rooms (NB 204/304/308) have exactly 0 assigned offerings.
- [x] Room PRRC 108 assigned only to BSED_SCIENCE offerings.
- [x] Delta re-solver resolves localized room disruption in $< 0.10\text{s}$.

---

### PHASE 3: HARDWARE & COMLAB PRESENCE

#### Objectives
Implement physical computer laboratory hardware telemetry, dynamic 15-second rotating TOTP QR codes, COMLAB projector view with SVG radial countdown ring, zero-regex student ID parsing, and real-time SSE vacancy streaming.

#### Tasks & Concrete Deliverables
1. **RFC 6238 15-Second TOTP Generator:**
   - Author `services/presence/totp/generator.py`:
     - Time step: strictly 15 seconds (`interval=15`).
     - Digest algorithm: HMAC-SHA1.
     - Generates 6-digit dynamic token signed with session secret.
     - Encodes into dynamic QR payload: `{ "room": room_code, "session": session_id, "totp": token, "ts": epoch }`.
2. **COMLAB Presence Projector View:**
   - Author `apps/web/src/pages/ProjectorView.tsx`:
     - High-contrast 1080p/720p dark surface mode (`bg-[#1a0810]`).
     - Real-time SVG radial countdown ring animating smoothly from 15s to 0s.
     - Prominent dynamic QR code displaying active TOTP payload.
     - Live workstation occupancy counter ($N/45$) and active section indicator.
     - Complies with dark surface rule: Light brand logo displayed inside neutral white card (`bg-white rounded-[8px] p-2`, no CSS invert).
3. **Zero-Regex Student ID Ingress & Attendance Service:**
   - Author `services/presence/api/ingress.py`:
     - Validates student ID without regular expressions: length == 8, prefix == '24-', digits 3–7 numeric.
     - Verifies submitted TOTP token against current and previous 15s time window ($\pm 1$ step tolerance).
     - Records `PresenceLog` entry in PostgreSQL and updates workstation status to OCCUPIED.
4. **Real-Time SSE Workstation Vacancy Stream:**
   - Author `services/presence/sse/stream.py`:
     - Server-Sent Events endpoint `/api/v1/presence/rooms/{room_code}/stream`.
     - Broadcasts live vacancy count, workstation grid status (operational/vacant/occupied), and active session details.
5. **Phase 3 Validation Suite:**
   - Automated tests `tests/unit/test_phase3_presence.py` testing TOTP expiration after 15s, valid check-in, invalid ID rejection, and SSE event streaming.

#### Validation Criteria (Phase 3 Gate)
- [x] TOTP rotates strictly every 15 seconds.
- [x] Projector view displays high-contrast QR with SVG radial ring and no CSS inverted logos.
- [x] Student ID parser strictly validates `24-XXXXX` format without using regex engines.
- [x] SSE vacancy stream pushes instant workstation state changes to connected clients.

---

### PHASE 4: SECURITY GATEWAY

#### Objectives
Establish the Zero-Trust Security Gateway handling Cloudflare Turnstile edge bot mitigation, Google Workspace OAuth domain restriction, Argon2id password hashing, OWASP ASVS 4.0 entropy verification, and RBAC middleware.

#### Tasks & Concrete Deliverables
1. **Cloudflare Turnstile Edge Proxy:**
   - Author `services/gateway/auth/turnstile.py`:
     - Server-side validation against `https://challenges.cloudflare.com/turnstile/v0/siteverify`.
     - Supports development dummy keys (`1x00000000000000000000AA` / `1x0000000000000000000000000000000AA`).
     - Blocks automated bot traffic before touching downstream authentication services.
2. **Google Workspace Domain-Restricted OAuth:**
   - Author `services/gateway/auth/oauth.py`:
     - Verifies Google OAuth ID token claims.
     - Deterministically asserts `email_verified == True` and `hd in {"student.pnm.edu.ph", "pnm.edu.ph"}`.
     - Rejects unauthorized external personal Gmail accounts with human-centered plain-language error.
3. **Argon2id Hashing & OWASP ASVS 4.0 Entropy Validator:**
   - Author `services/gateway/auth/password.py`:
     - Argon2id configuration: Memory 64 MiB ($m=65536$), time cost $t=3$, parallelism $p=4$.
     - ASVS 4.0 validator enforcing: minimum 10 characters, upper, lower, digit, symbol, ban on common dictionary passwords and sequential strings.
     - Forces mandatory password setup on first Google OAuth login.
4. **RBAC Reverse Proxy Gateway & Middleware:**
   - Author `services/gateway/main.py`:
     - Reverse proxy routing: `/api/v1/academic/*` $\rightarrow$ :8001, `/api/v1/scheduling/*` $\rightarrow$ :8002, `/api/v1/presence/*` $\rightarrow$ :8004.
     - Generates signed JWT session tokens containing user ID, institutional email, and RBAC role (`ADMIN`, `FACULTY`, `STUDENT`).
     - Enforces role-based route security headers.
5. **Phase 4 Validation Suite:**
   - Automated tests `tests/unit/test_phase4_security.py` verifying Turnstile verification, domain-locking, password entropy checks, Argon2id verification, and RBAC token guards.

#### Validation Criteria (Phase 4 Gate)
- [x] Turnstile challenge verified on auth endpoints.
- [x] Non-institutional Google accounts strictly blocked.
- [x] Argon2id hashes verified with correct security parameters.
- [x] ASVS 4.0 entropy validator blocks weak passwords.
- [x] RBAC correctly isolates Admin, Faculty, and Student routes.

---

### PHASE 5: CLIENT APPLICATIONS

#### Objectives
Build the React 19 Progressive Web Application (PWA) incorporating the Soft Rouge & Cool Neutral design system, self-hosted Inter typography, Laws of UX cognitive optimizations, empathetic plain-language error communication, and the Expo mobile scanner companion.

#### Tasks & Concrete Deliverables
1. **Design System & Tailwind CSS v4 Theme:**
   - Author `apps/web/src/styles/tokens.css`: Custom properties for `--brand-midnight`, `--brand-rouge`, `--brand-rose`, canvases, text, surfaces, borders, states.
   - Author `apps/web/src/index.css`: Tailwind v4 `@theme` directive mapping `--color-*` to CSS custom properties.
   - Install self-hosted `apps/web/public/fonts/InterVariable.woff2` and configure `@font-face` with `font-display: swap`.
   - Place official branding assets in `apps/web/public/branding/`.
2. **PWA Core & Offline-First Service Worker:**
   - Author `apps/web/src/service-worker.ts`: Cache-First strategy for static assets/fonts/branding; Network-First / Stale-While-Revalidate for timetable API data.
   - Configure Web App Manifest (`apps/web/public/manifest.json`) with theme color `#34141f` and responsive icons.
3. **UX Laws & Accessible UI Components:**
   - **Next Class Hero Card (Hick's Law):** `apps/web/src/components/NextClassHero.tsx` answering "Where is my next class right now?" at a single glance.
   - **Accessible Touch Targets (Fitts's Law):** Interactive targets $\ge 48\times 48\text{px}$ on mobile (`h-12 w-12`).
   - **Skeleton Loading Screens (Doherty Threshold & D-11):** `apps/web/src/components/skeletons/` layout-matched CSS skeletons using `animate-pulse` eliminating Cumulative Layout Shift.
   - **Micro-Interactions (D-10):** Active tactile scale `0.97`, transitions $\le 250\text{ms}$, disabled under `prefers-reduced-motion`.
4. **Portal Implementations:**
   - **Student Portal:** `apps/web/src/pages/StudentDashboard.tsx` with Hero card, day-chunked weekly schedule (Miller's Law), COMLAB workstation vacancy monitor, and camera QR scanner modal.
   - **Faculty Portal:** `apps/web/src/pages/FacultyDashboard.tsx` with teaching timetable matrix, room swap request modal, and COMLAB projector launch trigger.
   - **Admin Portal:** `apps/web/src/pages/AdminOverview.tsx` with institutional metrics, room directory with quarantine status toggle, batch solver trigger, and emergency delta re-solver override panel.
5. **Empathetic Plain-Language Error Subsystem:**
   - Author `apps/web/src/utils/errorTranslation.ts` implementing the D-12 Plain-Language matrix (jargon-free messages for 409 conflicts, 15s TOTP expiration, OAuth domain rejection, cellular offline state).
6. **React Native (Expo) Student Companion App:**
   - Author `apps/mobile/src/App.tsx`: Expo application featuring hardware camera scanner (`expo-camera`) and local SQLite schedule caching for offline campus navigation.
7. **Phase 5 Validation Suite:**
   - Automated tests `tests/unit/test_phase5_ui.tsx` verifying component rendering, token application, WCAG contrast compliance, and error message translations.

#### Validation Criteria (Phase 5 Gate)
- [x] Soft Rouge & Cool Neutral color tokens applied across all components.
- [x] Typography uses self-hosted Inter variable font with zero external CDN calls.
- [x] WCAG 2.2 AA compliance: Text contrast $\ge 4.5:1$, touch targets $\ge 48\times 48\text{px}$.
- [x] Portals (Admin, Faculty, Student, Projector) fully functional with responsive layouts.
- [x] Camera QR scanning operational in both Web PWA and Expo mobile companion.
- [x] Zero technical jargon displayed in error states.

---

### PHASE 6: CLOUD DEPLOYMENT & CQRS PROJECTIONS

#### Objectives
Configure multi-cloud deployment blueprints (`render.yaml` for FastAPI microservices and PostgreSQL 16, `vercel.json` for static PWA hosting), implement Cloud Firestore CQRS read projections, and verify the entire system against end-to-end integration criteria.

#### Tasks & Concrete Deliverables
1. **Render Infrastructure Blueprint:**
   - Author `render.yaml`:
     - PostgreSQL 16 database instance with SCRAM-SHA-256 and connection pooling.
     - Web services for `gateway` (:8000), `academic` (:8001), `scheduling` (:8002), `presence` (:8004).
     - Environment variables, health checks (`/health`), and automated build commands.
2. **Vercel Static PWA Blueprint:**
   - Author `vercel.json`:
     - Static PWA build configuration from `apps/web/dist`.
     - SPA routing fallback (`/*` $\rightarrow$ `/index.html`).
     - Security headers: Content-Security-Policy permitting Cloudflare Turnstile (`challenges.cloudflare.com`), self-hosted fonts, and secure WebSocket/SSE connections.
3. **Cloud Firestore CQRS Read Synchronization:**
   - Author `services/academic/projections/firestore_sync.py`:
     - Asynchronous projection worker updating Firestore documents upon timetable publication.
     - Pre-computes read-optimized student section schedules and faculty matrices.
     - Benchmarks mobile document read latency at $< 50\text{ms}$.
4. **Phase 6 Validation Suite:**
   - Automated tests `tests/integration/test_phase6_cloud.py` verifying deployment descriptors, health check probes, and Firestore sync workflows.

#### Validation Criteria (Phase 6 Gate)
- [x] `render.yaml` valid and deploys PostgreSQL + 4 FastAPI microservices.
- [x] `vercel.json` contains Turnstile-compliant CSP headers and SPA fallback.
- [x] Firestore projection worker successfully syncs relational timetable state.
- [x] All microservices pass `/health` probes.

---

## Dual Track: Opaque-Box E2E Testing Suite

In parallel with the implementation track, the E2E Testing Track builds an opaque-box test suite validating system behavior from requirements (`ORIGINAL_REQUEST.md` and `SYSTEM_DESIGN_BLUEPRINT.md`) without coupling to internal implementation details.

### Test Architecture & Methodology
- **Test Runner:** Pytest + Playwright / HTTPX (`tests/e2e/test_runner.py`).
- **4-Tier Test Suite Structure:**
  - **Tier 1 — Feature Coverage ($\ge 5$ tests per feature, $\sim 135$ tests):** Isolated happy-path tests on equivalence-class representatives.
  - **Tier 2 — Boundary & Corner Cases ($\ge 5$ tests per feature, $\sim 135$ tests):** Slot extremes (07:00, 18:30), section size thresholds (59, 60, 70, 75+), TOTP window boundaries ($\pm 14\text{s}$, $16\text{s}$), zero-regex student ID bounds (`24-00000`, `24-99999`, invalid length).
  - **Tier 3 — Cross-Feature Combinations (Pairwise coverage):** Emergency room disruption during active COMLAB TOTP presence session, Sunday civic schedule vs. weekday academic schedule, Turnstile verification with first-time password setup.
  - **Tier 4 — Real-World Application Scenarios ($\ge 5$ domain workloads):**
    1. Full University Enrollment Ingress: 5,000 students accessing Next Class Hero Card simultaneously.
    2. Emergency Electrical Outage: Disruption of entire PRRC 2nd floor triggering delta re-solver reassignment.
    3. Peak Morning COMLAB Ingress: 45 students scanning rotating TOTP QR codes within a 3-minute window.
    4. Sunday Multi-Program Function Hall Turnover: ROTC dismissal at 12:00, turnover buffer, NSTP ingress at 13:00.
    5. Hostile Authentication Flood: Automated bot attack mitigated by Cloudflare Turnstile edge proxy.
- **Tier 5 — Adversarial Coverage Hardening (Phase 2 of Final Milestone):**
  - White-box adversarial probing by dedicated Challengers finding boundary leaks, race conditions, or unhandled exceptions.

---

## Gate Standards & Execution Sequence

| Phase | Milestone | Primary Deliverable | Acceptance Gate Condition |
|---|---|---|---|
| **Phase 1** | M1 | Contracts & Database Schemas | Pydantic/TS parity, SQLAlchemy models compile, Alembic migration clean, quarantine verified |
| **Phase 2** | M2 | Solver Calibration | 0 hard conflicts, Mon–Sat 07:00–19:00, Sunday Function Hall partitioned, delta re-solve $< 0.10\text{s}$ |
| **Phase 3** | M3 | Hardware & Presence | 15s TOTP rotation, Projector dark UI with radial ring, zero-regex ID parser, SSE vacancy stream |
| **Phase 4** | M4 | Security Gateway | Turnstile verified, Google OAuth `@pnm.edu.ph` locked, Argon2id ASVS 4.0 enforced, RBAC |
| **Phase 5** | M5 | Client Applications | Soft Rouge design system, self-hosted Inter font, React 19 PWA, Expo scanner, plain-language errors |
| **Phase 6** | M6 | Cloud Deployment | `render.yaml`, `vercel.json`, Firestore CQRS sync worker, 100% E2E test pass |
| **Final** | E2E | Adversarial Hardening (Tier 5) | Challengers confirm zero remaining test gaps or vulnerabilities |

---
*End of Master Implementation Plan. Ready for sequential Phase 1 execution.*
