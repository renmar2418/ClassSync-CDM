# ClassSync: Comprehensive Faculty & Stakeholder Consultation Guide
## System Requirements & Operational Analysis Questionnaire

**Project Title:** ClassSync: Intelligent Classroom Scheduling, Room Availability, and Conflict Prevention System  
**Target Institution:** Colegio de Montalban (CdM)  
**Stakeholders to Interview:** College Deans, Program Chairs (ICS, ITE, IBE), Registrar, and Capstone Advisers (Sir Nat, Sir Mades, Ma'am Gretchen, Ma'am Lamadora)  
**Document Purpose:** Consolidate all critical operational, academic, administrative, and technical questions required to lock in the system specifications before development.

---

## 1. Academic Policy & Institutional Rules (For Deans & Program Chairs)

### A. Break Times & Daily Scheduling Rhythm
1. **Dynamic vs. Fixed Lunch Break:**  
   * *Question:* "Is a **dynamic 1-hour rolling lunch break** (staggered between 11:00 AM and 2:00 PM per section/teacher) acceptable, or does CdM enforce a strictly synchronized institutional break where no classes can run?"
   * *Impact on ClassSync:* A rolling 1-hour window prevents canteen crowding at PRRC 102/104 and increases room utilization by ~25%.
2. **Transition / Passing Period:**  
   * *Question:* "Do we need an explicit **10-to-15 minute passing period** between classes, especially when students or teachers must travel between the PRRC Building and the New Building?"
   * *Impact on ClassSync:* Dictates whether slot intervals are strictly back-to-back or include travel buffers for inter-building movements.
3. **Daily Operating Band Limits:**  
   * *Question:* "Are there year-level restrictions on evening slots (5:30 PM – 7:00 PM)? For example, are 1st-year students restricted to morning/early afternoon, leaving evening blocks for upper-year working students or irregulars?"

---

### B. Faculty Workload & Teaching Allocations
4. **Teaching Load Ceilings:**  
   * *Question:* "What is the exact maximum and minimum teaching load for full-time regular faculty (e.g., 18, 21, or 24 contact hours/week), and how many hours count as overload?"
5. **Subject Preparations (Preps):**  
   * *Question:* "What is the policy limit on 'preparations' per semester? (e.g., maximum 3 different subjects per professor so lesson preparation remains manageable)?"
   * *Impact on ClassSync:* Modeled as a soft constraint: $\text{Count}(\text{UniqueSubjects}(f)) \le 3$.
6. **Continuous Teaching Endurance:**  
   * *Question:* "What is the maximum continuous lecturing duration allowed for a professor without a mandatory break (e.g., maximum 3.0 or 4.5 continuous hours)?"

---

### C. Enrollment Scaling & Section Management
7. **Section Size Limits & Auto-Splitting:**  
   * *Question:* "At what exact enrollment count does the department decide to split a section? (e.g., strictly at 45 students per CHED guideline, or does CdM stretch to 50 for General Education lectures)?"
8. **Irregular Students & Cross-Enrollment Policy:**  
   * *Question:* "When irregular students take backloaded subjects, do they fill vacant seats within regular blocks, or does the college open dedicated 'petitioner' or evening irregular sections?"
   * *Impact on ClassSync:* Defines the advising logic in the student mobile app and seat-reservation caps per room.

---

## 2. Facilities, Laboratories & Campus Logistics (For Property Office & Deans)

### A. Computer Laboratory & Science Lab Governance
9. **COMLAB Scheduling vs. Open Access:**  
   * *Question:* "Confirming the recent directive: Are the 4 COMLABs (`PRRC 302, 304, 307, 308`) 100% open for independent student research/study, or will certain high-stakes exams/midterm practicals reserve them occasionally?"
   * *Impact on ClassSync:* Determines if COMLABs support 'Special Event / Exam Reservations' on top of being open study hubs.
10. **Science Laboratory Exclusivity (`PRRC 107`):**  
    * *Question:* "Is `PRRC 107` exclusively dedicated to BSEd Science experiments, or do other programs (like Chemistry for Engineers in BSCpE) share this wet lab?"

### B. Multi-Purpose Space Booking
11. **New Building Function Hall & Covered Court:**  
    * *Question:* "What is the institutional workflow to approve classes using the Function Hall (Floor 4) or the Covered Court (e.g., PAHFIT, NSTP, large seminars)? Does it require Dean approval or Property Custodian reservation?"

---

## 3. Technical, Architecture & Capstone Rubric Alignment (For Course Professors)

### A. Sir Nat (API Microservices & Engine Performance)
12. **Incremental Delta Solving vs. Full Batch:**  
    * *Question:* "Sir Nat, when an admin adds or deletes a single section or swaps a room mid-semester, we are designing a **Targeted Delta Re-Solver** (which freezes previously published schedules and only optimizes the modified section in $< 0.1 \text{ seconds}$) instead of recalculating the whole university. Does this fulfill our Process API decoupling requirement?"
13. **Solver Timeout Budget:**  
    * *Question:* "What is the acceptable server timeout threshold for the CP-SAT engine on a full university batch run before returning a diagnostic report (e.g., 30 seconds vs. 60 seconds)?"

---

### B. Sir Mades (Security, Auditing & Administrative Governance)
14. **Approval Hierarchy & Timetable Publishing:**  
    * *Question:* "Sir Mades, what is the required role-based sign-off chain before a draft timetable is published to the live student mobile app? (e.g., Program Chair creates draft $\rightarrow$ Dean reviews $\rightarrow$ VPAA/Registrar commits final publication)?"
15. **Data Privacy & Audit Retention (RA 10173):**  
    * *Question:* "For compliance with the Philippine Data Privacy Act, how long must room reassignment logs, attendance check-ins, and administrative overrides be retained in the database?"

---

### C. Ma'am Gretchen (Database Systems & Mobile Client)
16. **Offline Mode & Synchronization Strategy:**  
    * *Question:* "Ma'am Gretchen, in the mobile client, when students experience intermittent data/Wi-Fi connection on campus, what data must remain accessible offline? (e.g., local SQLite caching of their weekly schedule and room assignments)?"
17. **Lab Attendance & Hardware Station Logging:**  
    * *Question:* "For the shared laboratory check-in module, should students check in via QR code scanning at their assigned PC station, or is an instructor-driven roll-call verification preferred?"

---

### D. Ma'am Lamadora (Manuscript, Evaluation & Defense)
18. **Evaluation Metrics & User Acceptance Testing (UAT):**  
    * *Question:* "Ma'am Lamadora, what specific evaluation instrument or survey standard should we use during testing with CdM faculty and students? (e.g., ISO/IEC 25010 Software Quality Model or System Usability Scale / SUS)?"
19. **Scope Boundaries for Defense:**  
    * *Question:* "Is presenting the verified timetable for the 3 core institutes (ICS, ITE, IBE) with the 36 schedulable campus spaces considered sufficient for our capstone defense scope, or is a full 4-year historical simulation required?"

---

## 4. Quick-Reference Printout (Ready for Consultation)

| # | Topic | Key Question in Plain English | Target Person |
| :-: | :--- | :--- | :--- |
| **1** | **Lunch Break** | Staggered 1-hour rolling break (11 AM–2 PM) or frozen school-wide lunch? | Deans / Program Chairs |
| **2** | **Passing Period** | Do we add 10–15 mins travel time between PRRC and New Building? | Program Chairs |
| **3** | **Faculty Load** | Max weekly teaching hours (21 vs 24 hrs) and max preps (3 preps)? | Program Chairs |
| **4** | **Max Continuous Class** | Max continuous teaching hours before mandatory rest (3 hrs)? | Program Chairs |
| **5** | **Section Splitting** | Exact student count to split a section (45 vs 50 students)? | Registrar / Chairs |
| **6** | **COMLAB Policy** | 100% open-access study lab, or can practical exams reserve slots? | ICTO / Deans |
| **7** | **Delta Solver** | Is incremental re-solving (fast update) approved for Process API? | **Sir Nat** |
| **8** | **Publishing Workflow**| What is the exact sign-off chain before timetables go live? | **Sir Mades** |
| **9** | **Mobile Offline** | What schedule details must be cached offline on student phones? | **Ma'am Gretchen** |
| **10**| **Evaluation Model** | Will we evaluate via ISO 25010 or SUS survey for the manuscript? | **Ma'am Lamadora** |
