# Real-World University Datasets & Constraint Parameters

To make ClassSync realistic and defense-ready for your 5 professors, your dataset must account for real university constraints: operating hours, lunch and break times, irregular student enrollments, and section reassignment requests (e.g., working students, transfer/anti-bullying protection).

Below are the **5 specific datasets** needed, including exact fields, sample values, and rules.

---

## 1. University Operating Time, Breaks & Daily Periods Dataset
This defines the campus time grid and protects student/teacher well-being.

* **Operating Hours:** Monday to Saturday, `07:00 AM – 07:00 PM` (or `09:00 PM` for night classes).
* **Time Slot Increments:** 1.5 hours (90 mins) or 3.0 hours (180 mins for labs).
* **Mandatory Institutional Breaks:**
  - **Lunch Window:** `11:30 AM – 01:00 PM` (No teacher or student can have a 3-hour class scheduled across this without a lunch gap).
  - **Student Fatigue Rule (Passing Time):** Minimum 15-minute buffer between back-to-back classes.
  - **Maximum Daily Load:** No section or teacher is scheduled for more than 4 consecutive subjects (max 6 hours straight) without a minimum 1-hour break.

```json
{
  "academic_year": "2026-2027",
  "semester": "1st Semester",
  "operating_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
  "day_start": "07:00",
  "day_end": "19:00",
  "lunch_window": {
    "start": "11:30",
    "end": "13:00",
    "required_break_minutes": 60
  },
  "max_consecutive_hours": 4.5,
  "slot_durations": [
    { "type": "lecture_1.5h", "minutes": 90 },
    { "type": "lecture_3.0h", "minutes": 180 },
    { "type": "laboratory_3.0h", "minutes": 180 }
  ]
}
```

---

## 2. Professor / Faculty Dataset (Availability & Load Limits)
Prevents overworking faculty and respects availability contracts.

- *Full-time Faculty:* Must comply with the university operating band of **07:00 AM – 07:00 PM** (Monday–Saturday). While teachers must be available within this 12-hour window, the solver enforces an 8-hour maximum active spread per day and protected 1-hour lunch breaks so teachers aren't scheduled continuously without rest.
- *Part-time / Adjunct Faculty:* Available during specific contracted blocks within the 07:00 AM – 07:00 PM window (or Saturday blocks).

```json
[
  {
    "faculty_id": "FAC-ICS-001",
    "name": "Engr. Juan Dela Cruz",
    "institute_id": "ICS",
    "employment_type": "full_time",
    "max_weekly_units": 21,
    "max_daily_hours": 6,
    "qualified_subjects": ["IT311", "IT312", "CC102", "CPE201"],
    "availability": [
      { "day": "Monday", "start": "08:00", "end": "17:00" },
      { "day": "Wednesday", "start": "08:00", "end": "17:00" },
      { "day": "Friday", "start": "08:00", "end": "17:00" }
    ]
  },
  {
    "faculty_id": "FAC-ICS-002",
    "name": "Prof. Maria Santos (Industry Practitioner)",
    "institute_id": "ICS",
    "employment_type": "part_time",
    "max_weekly_units": 9,
    "max_daily_hours": 3,
    "qualified_subjects": ["IT314", "IT315"],
    "availability": [
      { "day": "Tuesday", "start": "17:30", "end": "20:30" },
      { "day": "Thursday", "start": "17:30", "end": "20:30" },
      { "day": "Saturday", "start": "08:00", "end": "12:00" }
    ]
  }
]
```

---

## 3. Rooms & Physical Facilities Dataset
Ensures classes are assigned to rooms with adequate capacity and required equipment.

```json
[
  {
    "room_id": "ICS-LAB-1",
    "name": "Mac & Networking Lab",
    "building": "Main Academic Building",
    "floor": 2,
    "capacity": 45,
    "room_type": "computer_lab",
    "equipment_tags": ["computers", "aircon", "projector", "cisco_switches"],
    "dedicated_to_institute": "ICS"
  },
  {
    "room_id": "GEN-LEC-301",
    "name": "Lecture Room 301",
    "building": "Main Academic Building",
    "floor": 3,
    "capacity": 55,
    "room_type": "lecture_hall",
    "equipment_tags": ["whiteboard", "projector", "electric_fan"],
    "dedicated_to_institute": null
  }
]
```

---

## 4. Irregular Student Dataset (Custom Cross-Section Enrollments)
Irregular students cannot follow a single block schedule. They carry back-subjects, failed prerequisites, or retakes across multiple year levels.

* **How the System Handles Them:**
  - The student has an enrolled list of specific `subject_codes` from different year levels (e.g., retaking 1st Year `CC101` while taking 3rd Year `IT311`).
  - **The Irregular Conflict Validator:** When an irregular student submits their subject list, the system audits their personal combination across published section timetables.
  - If a clash occurs (e.g., `CC101` is scheduled Monday 10:00–11:30 in Section 1A, clashing with `IT311` in Section 3A), the student's mobile app immediately displays:  
    *"Schedule Conflict: CC101 (Sec 1A) clashes with IT311 (Sec 3A). Recommended alternative: Take CC101 with Section 1B on Tuesday 01:00 PM."*

```json
{
  "student_id": "2024-00123",
  "name": "Alex Reyes",
  "student_type": "irregular",
  "institute_id": "ICS",
  "primary_program": "BSIT",
  "enrolled_subjects": [
    { "subject_code": "CC101", "name": "Intro to Programming", "retake": true },
    { "subject_code": "IT311", "name": "Mobile Application Development", "retake": false },
    { "subject_code": "GE-MATH", "name": "Mathematics in the Modern World", "retake": false }
  ],
  "available_shift": "day_shift"
}
```

---

## 5. Section Reassignment & Special Request Dataset (Working Students, Anti-Bullying, Medical)
In a real university, students frequently request section transfers for legitimate academic or personal reasons.

* **Reassignment Categories:**
  1. **Working Student:** Needs evening or specific morning shifts to match job hours (requires proof/working schedule).
  2. **Safety / Anti-Bullying / Disciplinary Separation:** Enforces a hard administrative rule: *Student A and Student B must NEVER be placed in the same section.*
  3. **Medical / Physical Accommodation:** Student with mobility disability requires classes scheduled only on the Ground Floor or in buildings with working elevators.

```json
[
  {
    "request_id": "REQ-2026-001",
    "student_id": "2024-00452",
    "current_section": "BSIT-3A",
    "target_section": "BSIT-3B",
    "reason_category": "working_student",
    "details": "BPO night shift from 9:00 PM to 6:00 AM. Requests transfer to afternoon/evening block.",
    "status": "approved",
    "proof_attached": "employment_certificate.pdf"
  },
  {
    "request_id": "REQ-2026-002",
    "student_id": "2024-00789",
    "current_section": "BEEd-2A",
    "target_section": "BEEd-2C",
    "reason_category": "disciplinary_safety_separation",
    "details": "Guidance counselor-mandated separation from student ID 2024-00812.",
    "enforced_constraint": "MUTUALLY_EXCLUSIVE_SECTION",
    "status": "enforced_by_admin"
  }
]
```

---

## 6. How to Gather / Prepare These Datasets for Your Defense

You do **not** need 1,000 students to impress the panel. You only need **realistic sample fixtures** covering the edge cases:

1. **Faculty Data:** 5 sample professors (3 full-time, 2 part-time with night/weekend availability).
2. **Room Data:** 4 rooms (2 Computer Labs, 2 General Lecture Halls with different capacities).
3. **Student Cohorts:**
   - **Regular Sections:** `BSIT-3A` and `BSIT-3B` (full block schedules).
   - **Irregular Student:** 1 student with a back-subject showing the clash detection in action.
   - **Working Student / Section Transfer:** 1 approved request demonstrating that the system respects student life accommodations.

A complete documentation file has been written to:
- `docs/academic/DATASET_REQUIREMENTS_AND_REAL_WORLD_CONSTRAINTS.md`
