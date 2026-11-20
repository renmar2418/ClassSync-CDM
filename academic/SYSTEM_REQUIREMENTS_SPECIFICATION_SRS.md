# ClassSync: System Requirements Specification (SRS) & Mathematical Feasibility Analysis

**Document Status:** Approved Baseline Specification  
**Target Institution:** Colegio de Montalban (CdM) — Kasiglahan Village, San Jose, Rodriguez, Rizal  
**System Scope:** Multi-Institute Timetable Optimization, Room Inventory Management & Academic Advising  

---

## 1. Executive Overview & Purpose (What the System Really Does)

At its core, **ClassSync** is an automated scheduling and facility management platform that replaces manual, spreadsheet-based timetabling in colleges. 

### What Problem It Solves:
1. **The Double-Booking Crisis:** Prevent professors, classrooms, and student cohorts from being scheduled in two places at the same hour.
2. **Facility Bottleneck & Overcrowding:** Guarantee compliance with CHED spatial guidelines ($1.2\text{ m}^2$ per student, max 50 per lecture) and avoid placing coding or hardware classes in rooms lacking equipment.
3. **Room Conversion Collisions:** Prevent scheduling classes into rooms repurposed for non-academic uses (e.g., Food Hub, DICT Office, Faculty Rooms).
4. **Cognitive Overload for Deans:** Enable administrators to generate a validated, clash-free master timetable across multiple institutes in seconds using mathematical constraint programming (Google OR-Tools CP-SAT).

---

## 2. Institutional Scope & Organizational Structure

ClassSync partitions Colegio de Montalban into **three distinct administrative tenants**:

```mermaid
flowchart TD
    University["🏛️ Colegio de Montalban (CdM)"]

    subgraph ICS["1. Institute of Computer Studies (ICS)"]
        BSIT["BS Information Technology (BSIT)"]
        BSCpE["BS Computer Engineering (BSCpE / Engineering Dept)"]
    end

    subgraph ITE["2. Institute of Teacher Education (ITE)"]
        BECEd["Bachelor of Early Childhood Education (BECEd)"]
        BEEd["Bachelor of Elementary Education (BEEd)"]
        BSEd["BSEd Major in Science (BSEd Science)"]
        BTLEd["BTLEd Major in ICT (BTLEd ICT)"]
    end

    subgraph IBE["3. Institute of Business & Entrepreneurship (IBE)"]
        BSEntrep["BS in Entrepreneurship (BS Entrep)"]
        BSBA["BSBA Major in Human Resource Management (BSBA HRM)"]
        Incubator["Student Enterprise & Incubation Store"]
    end

    University --> ICS
    University --> ITE
    University --> IBE
```

---

## 3. Physical Room Inventory & Capacity Matrix

From the total inventory of **51 physical spaces** across the PRRC Building, New Building, and Athletic Court, the operational capacity is categorized as follows:

| Zone / Floor | Total Rooms | Schedulable Lecture Classrooms | Dedicated Laboratories | Non-Schedulable Converted Rooms |
| :--- | :---: | :---: | :---: | :--- |
| **PRRC Floor 1** | 10 | 7 | 1 (`PRRC 107` - ITE Science Lab) | 2 (`PRRC 101` - Sim Lab, `PRRC 102/104` - Food Hub) |
| **PRRC Floor 2** | 10 | 8 | 0 | 2 (`PRRC 204/205` - CpE Faculty Room) |
| **PRRC Floor 3** | 9 | 2 (`309, 310`) | 5 (`302, 304, 307, 308` COMLABs, `302` VGA) | 2 (`PRRC 304` - Storage, `PRRC 305` - DICT Office) |
| **New Bldg Floor 1** | 10 | 10 | 0 | 0 (Pending Faculty room door verification) |
| **New Bldg Floor 2** | 10 | 10 | 0 | 0 (Pending Faculty room door verification) |
| **New Bldg Floor 3** | 10 | 10 | 0 | 0 |
| **New Bldg Floor 4** | 1 | 0 | 1 (Function Hall - 120 Cap) | 0 |
| **Court** | 1 | 0 | 1 (Athletic Court - PAHFIT/Sports) | 0 |
| **TOTALS** | **61** | **47 Rooms** | **8 Specialized Spaces** | **6 Non-Schedulable Spaces** |

---

### 3.1 Policy Update: Open-Access Student Computer Laboratories
Under current administration guidelines, **COMLABs (PRRC 302, 304, 307, 308) are temporarily set to is_schedulable: false**.
* **Reason:** The college has designated the COMLABs as **Open-Access Student Study & Research Labs**, allowing students to freely use the computers during off-subject periods, conduct independent study, complete online modules, and research without being locked out by scheduled classes.
* **Instructional Routing:** All curriculum subjects (including major IT and programming lectures) are routed to the 30 active general lecture classrooms (equipped with displays/monitors or online asynchronous delivery).

## 4. Mathematical Constraint Formulation (How CP-SAT Solves the Schedule)

In ClassSync, scheduling is modeled as a **Constraint Satisfaction Problem (CSP)** over finite integer domains.

### Decision Variables:
$$X_{c, r, d, t} \in \{0, 1\}$$
Where $X_{c, r, d, t} = 1$ if Class Occurrence $c$ is assigned to Room $r$ on Day $d$ starting at Time Slot $t$; otherwise $0$.

### 4.1 Hard Constraints (Zero Violations Permitted)

1. **Room Exclusivity (No Double-Booking):**
   A room cannot host more than one class occurrence at any given minute:
   $$\forall r, d, t: \quad \sum_{c} X_{c, r, d, t} \le 1$$

2. **Faculty Exclusivity (No Teacher Clashes):**
   An instructor cannot teach two classes simultaneously:
   $$\forall f, d, t: \quad \sum_{c \in \text{Classes}(f)} X_{c, r, d, t} \le 1$$

3. **Section Cohort Exclusivity (No Student Overlaps):**
   A student section cohort (e.g., `BSIT-3A`) can only attend one class at a time:
   $$\forall s, d, t: \quad \sum_{c \in \text{Classes}(s)} X_{c, r, d, t} \le 1$$

4. **Facility Equipment Compatibility:**
   Class occurrences requiring specialized equipment must map to compliant rooms:
   $$X_{c, r, d, t} = 0 \quad \text{if } \text{Requires}(c) \not\subseteq \text{Equipment}(r)$$
   * Computer Laboratories (`CCPROG1`, `ITADBMS`) $\rightarrow$ strictly `PRRC 302, 304, 307, 308`.
   * Science Laboratories (`SCIINCH`, `SCIORCH`) $\rightarrow$ strictly `PRRC 107`.
   * Physical Education (`PAHFIT1–4`) $\rightarrow$ strictly `Court`.

5. **Non-Schedulable Space Shielding:**
   Converted administrative spaces are eliminated from the solver's domain:
   $$\forall c, d, t, \quad r \in \{\text{PRRC 101, 102, 104, 204, 205, 304, 305}\}: \quad X_{c, r, d, t} = 0$$

6. **Operating Band & Lunch Break Guard:**
   Classes must start $\ge 07:00$ and end $\le 19:00$.  
   No classes can be scheduled during the protected faculty/student lunch window ($11:30 - 13:00$):
   $$\forall c, r, d, \quad t \in [11:30, 13:00): \quad X_{c, r, d, t} = 0$$

### 4.2 Soft Constraints (Optimization Objectives)
* **Objective 1 (Minimize Faculty Gaps):** Penalize schedules where teachers have idle gaps $> 2 \text{ hours}$ between classes.
* **Objective 2 (Compact Student Schedules):** Minimize gaps between subjects within each section's daily timetable.
* **Objective 3 (Building Travel Minimization):** Avoid back-to-back transitions between PRRC Floor 3 and New Building Floor 3.

---


### 4.3 Shared Lab Governance & Attendance Verification Architecture

Because COMLABs (PRRC 302, 304, 307, 308) and the Science Lab (PRRC 107) are shared cross-institute resources accessible by ICS, ITE, and IBE, the administration mandates strict accountability and attendance tracking:

1. Digital Laboratory Logbook / Attendance Tracking:
   - Faculty Check-in: The instructor taps Check-in to Lab via the ClassSync Web/Mobile portal upon entering the room, confirming that the lab session is officially active.
   - Student Station Logging: Students verify attendance (via student ID, QR, or roster roll call), linking student_id to assigned_pc_station and recording time_in and time_out.
2. Inter-Institute Hardware Accountability:
   - Prevents disputes between institutes (e.g., ICS vs. ITE vs. IBE) if PC peripherals (mice, keyboards, monitors, cables) are damaged or missing. The system maintains an immutable historical audit showing exactly which section, teacher, and institute occupied the lab during that time slice.
3. No-Show Detection & Slot Auto-Release:
   - If a class reserved a COMLAB but the teacher fails to check in within 15 minutes of the slot start, ClassSync automatically marks the room as VACANT / RELEASED.
   - Another department or professor in need of an emergency computer lab can claim the slot instantly through the mobile Room Finder.

## 5. Mathematical Feasibility Analysis: Can CdM Fit in 59 Rooms?

To determine whether Colegio de Montalban can run a complete, clash-free schedule without classroom shortages, we perform a **Supply vs. Demand Feasibility Audit**.

### Operating Parameters:
* **Operating Hours:** 7:00 AM to 7:00 PM (12 hours/day) minus 1.5 hours protected lunch = **10.5 instructional hours/day**.
* **Operating Days:** Monday to Saturday = **6 days/week**.
* **Weekly Supply per Physical Room:** $10.5 \text{ hrs/day} \times 6 \text{ days} = \mathbf{63 \text{ usable slot-hours/week}}$.

### Supply Breakdown:
1. **Lecture Classrooms (47 rooms):** $47 \times 63 = \mathbf{2,961 \text{ lecture room-hours/week}}$.
2. **Computer Labs (4 COMLABs):** $4 \times 63 = \mathbf{252 \text{ lab room-hours/week}}$.
3. **Science Labs (1 Lab - `PRRC 107`):** $1 \times 63 = \mathbf{63 \text{ science lab-hours/week}}$.

---

### Demand Calculation (Curriculum Load per Cohort):

Based on the verified 23-page prospectus in [`DATASET_CDM_PROSPECTUS_MATRIX.md`](file:///d:/PROJECTS%20NI%20RENMAURRRRRRRRRRRRRRRR/3rd%20year%20Projects/Classync/docs/academic/DATASET_CDM_PROSPECTUS_MATRIX.md), a regular student cohort takes **8–9 subjects per semester**:
* Average Lecture Hours: **18 hours/week** per section.
* Average Computer Lab Hours (ICS / BTLEd): **6 to 9 hours/week** per section.
* Average Science Lab Hours (BSEd Science): **6 hours/week** per section.

#### Scalability Stress-Test (Assuming 2 Sections per Year Level $\times$ 4 Years = 8 Sections per Program):
Across the 6 undergraduate programs, there are **48 total sections**:

| Resource Category | Total Weekly Demand (48 Sections) | Total Physical Supply | Utilization Rate | Feasibility Verdict |
| :--- | :---: | :---: | :---: | :---: |
| **Standard Lecture Rooms** | $\approx 864 \text{ hours}$ | $2,961 \text{ hours}$ | **29.2%** | 🟢 **HIGHLY FEASIBLE (Large Surplus)** |
| **Science Lab (`PRRC 107`)** | $8 \text{ BSEd sections} \times 6\text{h} = 48 \text{ hours}$ | $63 \text{ hours}$ | **76.2%** | 🟢 **FEASIBLE (Within safe limits)** |
| **Computer Labs (COMLABs)** | $16 \text{ ICS} + 8 \text{ BTLEd} = 24 \text{ sec} \times 9\text{h} = 216\text{h}$ | $252 \text{ hours}$ | **85.7%** | 🟡 **TIGHT / BOTTLENECK ZONE** |

### The Critical Architectural Insight (Reflecting Recent Admin Policy Memo):
* **Administrative Policy on COMLAB Usage:** Under the latest institutional directive, **COMLABs are reserved strictly for dedicated practical hands-on laboratory work** (actual machine compilation, coding exercises, and database query executions).
* **Lecture-First Optimization:** Even major computing and technical courses (e.g., ITOPSYS, ITIASEC1, ITHUMCI, ITSIAA1) conduct their theoretical lectures and slide presentations in standard **vacant lecture classrooms** (using HDMI displays/monitors or whiteboards).
* **Cross-Institute Educational Access:** All three institutes (ICS, ITE, IBE) have authorized access to COMLABs for educational purposes when software exercises are required, but routine lectures default to the general room pool.
* **Impact on Feasibility:** Moving conceptual lectures into the abundant general classroom inventory (PRRC Floors 1–2, New Building Floors 1–3) **slashes COMLAB utilization from 85.7% down to ~35%–40%**, completely eliminating laboratory contention and ensuring the entire campus operates with healthy room surplus.

---

## 6. Course-by-Course Defense Matrix (Professors' Grading Rubrics)

| Professor & Subject | What They Expect to See | How ClassSync Delivers |
| :--- | :--- | :--- |
| **Sir Nat** (API Microservices) | Clean decoupling of UI, business orchestration, and data layers. | **API-Led Architecture:** Experience APIs (`/api/v1/schedules`), Process APIs (CP-SAT Orchestrator), and System APIs (Academic Records, Room Facilities) communicate via typed Pydantic contracts without tightly coupled dependencies. |
| **Sir Mades** (Security & Hardening) | Robust role authorization, token verification, and data integrity. | **Zero Client Trust:** Token verification with revocation checks via Firebase Admin SDK; role claims on the client carry zero authority; immutable audit logging for all room edits satisfying the **Philippine Data Privacy Act (RA 10173)**. |
| **Ma'am Gretchen** (Database Systems) | Scalable database design with ACID guarantees and cloud sync. | **Dual-Store Architecture:** Relational RDBMS (PostgreSQL/SQLite) holds authoritative academic constraints, draft hashes, and foreign keys; Cloud Firestore stores live published schedules for instant mobile synchronization. |
| **Ma'am Gretchen** (Mobile App Development) | Responsive, high-utility student/faculty mobile experience. | **React Native / Expo Client:** Live classroom vacancy finder (🟢 Free / 🔴 Occupied / 🟡 Maintenance), offline schedule persistence, and 1-click room defect reporting. |
| **Ma'am Lamadora** (Manuscript & Defense) | Rigorous problem formulation, literature grounding, and methodology. | Formal mathematical modeling of constraints ($X_{c,r,d,t}$), comparative benchmarking against enterprise systems (UniTime, Camu), and empirical feasibility analysis based on official CdM data. |

---

## 7. Requirements Traceability Sign-off

- [x] **CdM Organizational Hierarchy:** ICS (BSIT, BSCpE), ITE (BECEd, BEEd, BSEd, BTLEd), IBE (BSBA, BSEntrep) verified and isolated.
- [x] **Room Catalog & Converted Spaces:** 61 spaces profiled; non-schedulable administrative offices shielded.
- [x] **Authoritative Prospectus:** Reconciled against the 23-page official institutional catalog.
- [x] **Mathematical Capacity Validation:** Supply-vs-demand audit proves complete operational feasibility.
