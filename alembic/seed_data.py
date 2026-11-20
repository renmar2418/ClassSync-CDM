"""Institutional Seed Data for ClassSync:
AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System.

Seeds Pamantasan ng Montalban (CdM/PNM) institutional data:
- Active Academic Term (2026-2027 Semester 1)
- Standard Schedulable Rooms (PRRC 108 locked to BSED_SCIENCE, PRRC 301-304 COMLABs, FUNCTION_HALL)
- Quarantined Spaces (NB 204, NB 304, NB 308, PROPERTY_OFFICE, CAMPUS_CANTEEN with is_schedulable=False)
- Workstations (45 per COMLAB)
- Core Curriculum Subjects across the 6 capstone tracks
- 100% Full-Time Faculty Profiles with OWASP ASVS 4.0 Argon2id hashes
- High-capacity Sections (60-70+ students, unified cohorts)
- Course Offerings
"""

import uuid
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from classync_contracts.models import (
    AcademicPeriod,
    Room,
    CurriculumSubject,
    FacultyProfile,
    Section,
    CourseOffering,
    Workstation,
    CurriculumVersion,
    StudentCurriculumOverride,
    StudentProfile,
)

# Standard genuine Argon2id hashes (m=65536, t=3, p=4)
# Passwords:
# Admin: AdminPass2026!# / CdMAdmin2026!
# Faculty: FacultyPass2026!# / FacultyPass2026!
# Student: ValidPass2026!#
ADMIN_ARGON2_HASH = "$argon2id$v=19$m=65536,t=3,p=4$jLk8/ksvHOST+qTy/gPRVg$8ItPYYpD/dQ9qIFAaofAN3laQugRnTPgMg3iEsNtBVI"
FACULTY_ARGON2_HASH = "$argon2id$v=19$m=65536,t=3,p=4$UmyNR6CsVbc8UyX1VPnn5Q$SxPRjTfftE2oa3nVk2ifbT4D5szWphg7zteFn9U5Bo0"
STUDENT_ARGON2_HASH = "$argon2id$v=19$m=65536,t=3,p=4$SwxwyafI6vTCccc8O28h8A$T7HjEMJ3WsdTi4rnWNLMxsBrpHrgjU0SEu1ABndcTN8"


def seed_database(session: Session) -> Dict[str, int]:
    """Idempotently seeds authoritative institutional records into PostgreSQL/SQLite."""
    counts = {
        "academic_periods": 0,
        "rooms": 0,
        "workstations": 0,
        "subjects": 0,
        "faculty": 0,
        "sections": 0,
        "offerings": 0,
        "curriculum_versions": 0,
        "students": 0,
    }

    # 1. Academic Period
    existing_period = session.scalar(
        select(AcademicPeriod).where(
            AcademicPeriod.academic_year == "2026-2027",
            AcademicPeriod.semester == 1
        )
    )
    if not existing_period:
        period = AcademicPeriod(
            id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            academic_year="2026-2027",
            semester=1,
            is_active=True,
        )
        session.add(period)
        session.flush()
        counts["academic_periods"] += 1
    else:
        period = existing_period

    # 2. Rooms — Authoritative 53 Spaces from Verified On-Site Inventory
    rooms_data: List[Dict[str, Any]] = [
        # --- PRRC Building Floor 1 (8 spaces) ---
        {"room_code": "PRRC 101", "building_name": "PRRC Building", "floor_level": 1, "room_type": "SIMULATION_LAB", "capacity": 40, "is_schedulable": False, "has_aircon": True, "has_projector": False, "exclusive_program": None},
        {"room_code": "PRRC 102", "building_name": "PRRC Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 50, "is_schedulable": False, "has_aircon": False, "has_projector": False, "exclusive_program": None},
        {"room_code": "PRRC 103", "building_name": "PRRC Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 70, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "PRRC 104", "building_name": "PRRC Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 50, "is_schedulable": False, "has_aircon": False, "has_projector": False, "exclusive_program": None},
        {"room_code": "PRRC 105", "building_name": "PRRC Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 70, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "PRRC 106", "building_name": "PRRC Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 70, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "PRRC 107", "building_name": "PRRC Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 70, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "PRRC 108", "building_name": "PRRC Building", "floor_level": 1, "room_type": "SCIENCE_LAB", "capacity": 70, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": "BSED_SCIENCE"},

        # --- PRRC Building Floor 2 (9 spaces) ---
        {"room_code": "PRRC 201", "building_name": "PRRC Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "PRRC 202", "building_name": "PRRC Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "PRRC 203", "building_name": "PRRC Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "PRRC 204", "building_name": "PRRC Building", "floor_level": 2, "room_type": "COMPUTER_LAB", "capacity": 40, "is_schedulable": False, "has_aircon": True, "has_projector": False, "exclusive_program": None},
        {"room_code": "PRRC 205", "building_name": "PRRC Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 40, "is_schedulable": False, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "PRRC 206", "building_name": "PRRC Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "PRRC 207", "building_name": "PRRC Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "PRRC 208", "building_name": "PRRC Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "PRRC 209", "building_name": "PRRC Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},

        # --- PRRC Building Floor 3 (10 spaces) ---
        {"room_code": "PRRC 301", "building_name": "PRRC Building", "floor_level": 3, "room_type": "COMPUTER_LAB", "capacity": 50, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "PRRC 302", "building_name": "PRRC Building", "floor_level": 3, "room_type": "COMPUTER_LAB", "capacity": 50, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "PRRC 303", "building_name": "PRRC Building", "floor_level": 3, "room_type": "COMPUTER_LAB", "capacity": 50, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "PRRC 304", "building_name": "PRRC Building", "floor_level": 3, "room_type": "COMPUTER_LAB", "capacity": 50, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "PRRC 305", "building_name": "PRRC Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 20, "is_schedulable": False, "has_aircon": False, "has_projector": False, "exclusive_program": None},
        {"room_code": "PRRC 306", "building_name": "PRRC Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 20, "is_schedulable": False, "has_aircon": False, "has_projector": False, "exclusive_program": None},
        {"room_code": "PRRC 307", "building_name": "PRRC Building", "floor_level": 3, "room_type": "COMPUTER_LAB", "capacity": 50, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "PRRC 308", "building_name": "PRRC Building", "floor_level": 3, "room_type": "COMPUTER_LAB", "capacity": 50, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "PRRC 309", "building_name": "PRRC Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "PRRC 310", "building_name": "PRRC Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},

        # --- New Building Floor 1 (7 spaces) ---
        {"room_code": "NB 101", "building_name": "New Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "NB 102", "building_name": "New Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "NB 103", "building_name": "New Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "NB 104", "building_name": "New Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "NB 105", "building_name": "New Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "NB 106", "building_name": "New Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "NB 107", "building_name": "New Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},

        # --- New Building Floor 2 (8 spaces) ---
        {"room_code": "NB 201", "building_name": "New Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "NB 202", "building_name": "New Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "NB 203", "building_name": "New Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "NB 204", "building_name": "New Building", "floor_level": 2, "room_type": "FACULTY_OFFICE", "capacity": 25, "is_schedulable": False, "has_aircon": True, "has_projector": False, "exclusive_program": None},
        {"room_code": "NB 205", "building_name": "New Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "NB 206", "building_name": "New Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "NB 207", "building_name": "New Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "NB 208", "building_name": "New Building", "floor_level": 2, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},

        # --- New Building Floor 3 (8 spaces) ---
        {"room_code": "NB 301", "building_name": "New Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "NB 302", "building_name": "New Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "NB 303", "building_name": "New Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "NB 304", "building_name": "New Building", "floor_level": 3, "room_type": "FACULTY_OFFICE", "capacity": 30, "is_schedulable": False, "has_aircon": True, "has_projector": False, "exclusive_program": None},
        {"room_code": "NB 305", "building_name": "New Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "NB 306", "building_name": "New Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "NB 307", "building_name": "New Building", "floor_level": 3, "room_type": "LECTURE", "capacity": 65, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},
        {"room_code": "NB 308", "building_name": "New Building", "floor_level": 3, "room_type": "FACULTY_LOUNGE", "capacity": 20, "is_schedulable": False, "has_aircon": True, "has_projector": False, "exclusive_program": None},

        # --- New Building Floor 4 (1 space) ---
        {"room_code": "FUNCTION_HALL", "building_name": "New Building", "floor_level": 4, "room_type": "MULTI_PURPOSE_HALL", "capacity": 300, "is_schedulable": True, "has_aircon": True, "has_projector": True, "exclusive_program": None},

        # --- Campus Grounds & Athletic Grounds (2 spaces) ---
        {"room_code": "Court", "building_name": "Campus Grounds", "floor_level": 1, "room_type": "SPORTS_COURT", "capacity": 200, "is_schedulable": True, "has_aircon": False, "has_projector": False, "exclusive_program": None},
        {"room_code": "Oval", "building_name": "Municipal Ground", "floor_level": 1, "room_type": "SPORTS_OVAL", "capacity": 500, "is_schedulable": True, "has_aircon": False, "has_projector": False, "exclusive_program": None},

        # --- Legacy & Ancillary Offices ---
        {"room_code": "PROPERTY_OFFICE", "building_name": "Main Building", "floor_level": 1, "room_type": "LECTURE", "capacity": 10, "is_schedulable": False, "has_aircon": False, "has_projector": False, "exclusive_program": None},
        {"room_code": "CAMPUS_CANTEEN", "building_name": "Student Center", "floor_level": 1, "room_type": "LECTURE", "capacity": 150, "is_schedulable": False, "has_aircon": False, "has_projector": False, "exclusive_program": None},
    ]

    for rdata in rooms_data:
        existing_room = session.get(Room, rdata["room_code"])
        if not existing_room:
            room = Room(**rdata)
            session.add(room)
            counts["rooms"] += 1

    session.flush()

    # 3. Workstations for COMLABs (45 stations each)
    comlab_codes = ["PRRC 301", "PRRC 302", "PRRC 303", "PRRC 304", "PRRC 307", "PRRC 308"]
    for code in comlab_codes:
        for station_num in range(1, 46):
            existing_ws = session.scalar(
                select(Workstation).where(
                    Workstation.room_code == code,
                    Workstation.workstation_number == station_num
                )
            )
            if not existing_ws:
                ws = Workstation(
                    id=uuid.uuid4(),
                    room_code=code,
                    workstation_number=station_num,
                    is_operational=True,
                )
                session.add(ws)
                counts["workstations"] += 1

    session.flush()

    # 4. Curriculum Subjects
    subjects_data: List[Dict[str, Any]] = [
        {
            "id": uuid.UUID("22222222-2222-2222-2222-222222222201"),
            "subject_code": "CC-IPT2",
            "descriptive_title": "Integrative Programming and Technologies 2",
            "lecture_hours": 2,
            "lab_hours": 3,
            "units": 3,
            "required_room_type": "COMPUTER_LAB",
        },
        {
            "id": uuid.UUID("22222222-2222-2222-2222-222222222202"),
            "subject_code": "CC-ADMS",
            "descriptive_title": "Advanced Database Management System",
            "lecture_hours": 2,
            "lab_hours": 3,
            "units": 3,
            "required_room_type": "COMPUTER_LAB",
        },
        {
            "id": uuid.UUID("22222222-2222-2222-2222-222222222203"),
            "subject_code": "CC-APPSDEV",
            "descriptive_title": "Application Development",
            "lecture_hours": 2,
            "lab_hours": 3,
            "units": 3,
            "required_room_type": "COMPUTER_LAB",
        },
        {
            "id": uuid.UUID("22222222-2222-2222-2222-222222222204"),
            "subject_code": "CC-IAS",
            "descriptive_title": "Information Assurance and Security",
            "lecture_hours": 2,
            "lab_hours": 3,
            "units": 3,
            "required_room_type": "COMPUTER_LAB",
        },
        {
            "id": uuid.UUID("22222222-2222-2222-2222-222222222205"),
            "subject_code": "CC-IM",
            "descriptive_title": "Information Management",
            "lecture_hours": 3,
            "lab_hours": 0,
            "units": 3,
            "required_room_type": "LECTURE",
        },
        {
            "id": uuid.UUID("22222222-2222-2222-2222-222222222206"),
            "subject_code": "HCI-101",
            "descriptive_title": "Human-Computer Interaction",
            "lecture_hours": 3,
            "lab_hours": 0,
            "units": 3,
            "required_room_type": "LECTURE",
        },
        {
            "id": uuid.UUID("22222222-2222-2222-2222-222222222207"),
            "subject_code": "BSED-SCI101",
            "descriptive_title": "Inorganic and Organic Chemistry",
            "lecture_hours": 3,
            "lab_hours": 0,
            "units": 3,
            "required_room_type": "LECTURE",
        },
        {
            "id": uuid.UUID("22222222-2222-2222-2222-222222222208"),
            "subject_code": "ROTC-1",
            "descriptive_title": "Reserve Officers' Training Corps 1",
            "lecture_hours": 3,
            "lab_hours": 0,
            "units": 3,
            "required_room_type": "FUNCTION_HALL",
        },
        {
            "id": uuid.UUID("22222222-2222-2222-2222-222222222209"),
            "subject_code": "NSTP-1",
            "descriptive_title": "National Service Training Program 1",
            "lecture_hours": 3,
            "lab_hours": 0,
            "units": 3,
            "required_room_type": "FUNCTION_HALL",
        },
        {
            "id": uuid.UUID("22222222-2222-2222-2222-222222222210"),
            "subject_code": "PATHFIT-3",
            "descriptive_title": "Physical Activity Towards Health and Fitness 3",
            "lecture_hours": 2,
            "lab_hours": 0,
            "units": 2,
            "required_room_type": "FUNCTION_HALL",
        },
    ]

    subject_map: Dict[str, CurriculumSubject] = {}
    for sdata in subjects_data:
        existing_subj = session.scalar(
            select(CurriculumSubject).where(CurriculumSubject.subject_code == sdata["subject_code"])
        )
        if not existing_subj:
            subj = CurriculumSubject(**sdata)
            session.add(subj)
            subject_map[sdata["subject_code"]] = subj
            counts["subjects"] += 1
        else:
            subject_map[sdata["subject_code"]] = existing_subj

    session.flush()

    # 5. Faculty Profiles (100% FULL_TIME)
    faculty_data: List[Dict[str, Any]] = [
        {
            "id": uuid.UUID("33333333-3333-3333-3333-333333333301"),
            "institutional_email": "admin@pnm.edu.ph",
            "full_name": "ClassSync Administrator",
            "employment_tier": "FULL_TIME",
            "password_hash": ADMIN_ARGON2_HASH,
            "requires_password_change": False,
            "is_active": True,
            "role": "ADMIN",
        },
        {
            "id": uuid.UUID("33333333-3333-3333-3333-333333333302"),
            "institutional_email": "teacher@pnm.edu.ph",
            "full_name": "Prof. Lead Faculty",
            "employment_tier": "FULL_TIME",
            "password_hash": FACULTY_ARGON2_HASH,
            "requires_password_change": False,
            "is_active": True,
            "role": "FACULTY",
        },
        {
            "id": uuid.UUID("33333333-3333-3333-3333-333333333303"),
            "institutional_email": "nat@pnm.edu.ph",
            "full_name": "Prof. Nathaniel IPT2",
            "employment_tier": "FULL_TIME",
            "password_hash": FACULTY_ARGON2_HASH,
            "requires_password_change": False,
            "is_active": True,
            "role": "FACULTY",
        },
        {
            "id": uuid.UUID("33333333-3333-3333-3333-333333333304"),
            "institutional_email": "mades@pnm.edu.ph",
            "full_name": "Prof. Mades IAS",
            "employment_tier": "FULL_TIME",
            "password_hash": FACULTY_ARGON2_HASH,
            "requires_password_change": False,
            "is_active": True,
            "role": "FACULTY",
        },
        {
            "id": uuid.UUID("33333333-3333-3333-3333-333333333305"),
            "institutional_email": "gretchen@pnm.edu.ph",
            "full_name": "Prof. Gretchen ADMS",
            "employment_tier": "FULL_TIME",
            "password_hash": FACULTY_ARGON2_HASH,
            "requires_password_change": False,
            "is_active": True,
            "role": "FACULTY",
        },
        {
            "id": uuid.UUID("33333333-3333-3333-3333-333333333306"),
            "institutional_email": "ngomez@pnm.edu.ph",
            "full_name": "Engr. Nathaniel Gomez",
            "employment_tier": "FULL_TIME",
            "password_hash": FACULTY_ARGON2_HASH,
            "requires_password_change": False,
            "is_active": True,
            "role": "FACULTY",
        },
        {
            "id": uuid.UUID("33333333-3333-3333-3333-333333333307"),
            "institutional_email": "prof.mades@pnm.edu.ph",
            "full_name": "Prof. Mades",
            "employment_tier": "FULL_TIME",
            "password_hash": FACULTY_ARGON2_HASH,
            "requires_password_change": False,
            "is_active": True,
            "role": "FACULTY",
        },
    ]

    faculty_map: Dict[str, FacultyProfile] = {}
    for fdata in faculty_data:
        existing_faculty = session.scalar(
            select(FacultyProfile).where(FacultyProfile.institutional_email == fdata["institutional_email"])
        )
        if not existing_faculty:
            fac = FacultyProfile(**fdata)
            session.add(fac)
            faculty_map[fdata["institutional_email"]] = fac
            counts["faculty"] += 1
        else:
            faculty_map[fdata["institutional_email"]] = existing_faculty

    session.flush()

    # 6. Sections (High capacity cohorts)
    sections_data: List[Dict[str, Any]] = [
        {
            "id": uuid.UUID("44444444-4444-4444-4444-444444444401"),
            "academic_period_id": period.id,
            "section_code": "BSIT-3A",
            "year_level": 3,
            "enrolled_student_count": 65,
        },
        {
            "id": uuid.UUID("44444444-4444-4444-4444-444444444402"),
            "academic_period_id": period.id,
            "section_code": "BSIT-3B",
            "year_level": 3,
            "enrolled_student_count": 68,
        },
        {
            "id": uuid.UUID("44444444-4444-4444-4444-444444444403"),
            "academic_period_id": period.id,
            "section_code": "BSED_SCI-2A",
            "year_level": 2,
            "enrolled_student_count": 60,
        },
    ]

    section_map: Dict[str, Section] = {}
    for sec_data in sections_data:
        existing_sec = session.scalar(
            select(Section).where(Section.section_code == sec_data["section_code"])
        )
        if not existing_sec:
            sec = Section(**sec_data)
            session.add(sec)
            section_map[sec_data["section_code"]] = sec
            counts["sections"] += 1
        else:
            section_map[sec_data["section_code"]] = existing_sec

    session.flush()

    # 7. Course Offerings
    offerings_data = [
        {
            "academic_period_id": period.id,
            "subject_id": subject_map["CC-IPT2"].id,
            "section_id": section_map["BSIT-3A"].id,
            "faculty_id": faculty_map["nat@pnm.edu.ph"].id,
        },
        {
            "academic_period_id": period.id,
            "subject_id": subject_map["CC-IAS"].id,
            "section_id": section_map["BSIT-3A"].id,
            "faculty_id": faculty_map["mades@pnm.edu.ph"].id,
        },
        {
            "academic_period_id": period.id,
            "subject_id": subject_map["CC-ADMS"].id,
            "section_id": section_map["BSIT-3B"].id,
            "faculty_id": faculty_map["gretchen@pnm.edu.ph"].id,
        },
        {
            "academic_period_id": period.id,
            "subject_id": subject_map["BSED-SCI101"].id,
            "section_id": section_map["BSED_SCI-2A"].id,
            "faculty_id": faculty_map["teacher@pnm.edu.ph"].id,
        },
    ]

    for odata in offerings_data:
        existing_offering = session.scalar(
            select(CourseOffering).where(
                CourseOffering.academic_period_id == odata["academic_period_id"],
                CourseOffering.subject_id == odata["subject_id"],
                CourseOffering.section_id == odata["section_id"],
            )
        )
        if not existing_offering:
            offering = CourseOffering(
                id=uuid.uuid4(),
                **odata
            )
            session.add(offering)
            counts["offerings"] += 1

    # 8. Curriculum Versions (Years 22, 23, 24, 25, 26 across ICS, ITE, IBE)
    curricula_specs = [
        # ICS
        ("22", "BSIT", "ICS", False),
        ("23", "BSIT", "ICS", False),
        ("24", "BSIT", "ICS", False),
        ("25", "BSIT", "ICS", True),
        ("26", "BSIT", "ICS", False),
        ("22", "BSCPE", "ICS", False),
        ("23", "BSCPE", "ICS", False),
        ("24", "BSCPE", "ICS", False),
        ("25", "BSCPE", "ICS", True),
        ("26", "BSCPE", "ICS", False),
        # ITE
        ("23", "BECED", "ITE", False),
        ("24", "BECED", "ITE", False),
        ("25", "BECED", "ITE", True),
        ("22", "BEED", "ITE", False),
        ("23", "BEED", "ITE", False),
        ("24", "BEED", "ITE", False),
        ("25", "BEED", "ITE", True),
        ("22", "BSED_SCIENCE", "ITE", False),
        ("23", "BSED_SCIENCE", "ITE", False),
        ("24", "BSED_SCIENCE", "ITE", False),
        ("25", "BSED_SCIENCE", "ITE", True),
        ("23", "BTLED_ICT", "ITE", False),
        ("24", "BTLED_ICT", "ITE", False),
        ("25", "BTLED_ICT", "ITE", True),
        # IBE
        ("22", "BS_ENTREP", "IBE", False),
        ("23", "BS_ENTREP", "IBE", False),
        ("24", "BS_ENTREP", "IBE", False),
        ("25", "BS_ENTREP", "IBE", True),
        ("22", "BSBA_HRM", "IBE", False),
        ("23", "BSBA_HRM", "IBE", False),
        ("24", "BSBA_HRM", "IBE", False),
        ("25", "BSBA_HRM", "IBE", True),
    ]

    cv_map: Dict[str, CurriculumVersion] = {}
    for c_year, p_code, inst, is_curr in curricula_specs:
        existing_cv = session.scalar(
            select(CurriculumVersion).where(
                CurriculumVersion.curriculum_year == c_year,
                CurriculumVersion.program_code == p_code,
            )
        )
        if not existing_cv:
            cv = CurriculumVersion(
                id=uuid.uuid4(),
                curriculum_year=c_year,
                program_code=p_code,
                institute=inst,
                is_current=is_curr,
            )
            session.add(cv)
            cv_map[f"{p_code}_{c_year}"] = cv
            counts["curriculum_versions"] += 1
        else:
            cv_map[f"{p_code}_{c_year}"] = existing_cv

    session.flush()

    # Link Section to Curriculum Version (e.g., BSIT-3A follows Curriculum 23)
    if "BSIT_23" in cv_map and "BSIT-3A" in section_map:
        section_map["BSIT-3A"].curriculum_version_id = cv_map["BSIT_23"].id

    # 9. Student Profiles (Phase 11 Real Authentication Roster)
    students_data: List[Dict[str, Any]] = [
        {
            "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
            "student_id": "24-00123",
            "institutional_email": "24-00123@student.pnm.edu.ph",
            "full_name": "Juan Dela Cruz",
            "section_code": "BSIT-3A",
            "curriculum_version_id": cv_map.get("BSIT_23").id if "BSIT_23" in cv_map else None,
            "year_level": 3,
            "password_hash": STUDENT_ARGON2_HASH,
            "requires_password_change": False,
            "is_active": True,
        },
        {
            "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
            "student_id": "24-00999",
            "institutional_email": "24-00999@student.pnm.edu.ph",
            "full_name": "Freshie Student",
            "section_code": "BSIT-3A",
            "curriculum_version_id": cv_map.get("BSIT_24").id if "BSIT_24" in cv_map else None,
            "year_level": 1,
            "password_hash": None,
            "requires_password_change": True,
            "is_active": True,
        },
        {
            "id": uuid.UUID("11111111-1111-1111-1111-111111111122"),
            "student_id": "22-00123",
            "institutional_email": "22-00123@student.pnm.edu.ph",
            "full_name": "Student Cohort 2022",
            "section_code": "BSIT-3A",
            "curriculum_version_id": cv_map.get("BSIT_22").id if "BSIT_22" in cv_map else None,
            "year_level": 4,
            "password_hash": STUDENT_ARGON2_HASH,
            "requires_password_change": False,
            "is_active": True,
        },
        {
            "id": uuid.UUID("11111111-1111-1111-1111-111111111123"),
            "student_id": "23-00123",
            "institutional_email": "23-00123@student.pnm.edu.ph",
            "full_name": "Student Cohort 2023",
            "section_code": "BSIT-3A",
            "curriculum_version_id": cv_map.get("BSIT_23").id if "BSIT_23" in cv_map else None,
            "year_level": 3,
            "password_hash": STUDENT_ARGON2_HASH,
            "requires_password_change": False,
            "is_active": True,
        },
        {
            "id": uuid.UUID("11111111-1111-1111-1111-111111111125"),
            "student_id": "25-00123",
            "institutional_email": "25-00123@student.pnm.edu.ph",
            "full_name": "Student Cohort 2025",
            "section_code": "BSIT-3A",
            "curriculum_version_id": cv_map.get("BSIT_25").id if "BSIT_25" in cv_map else None,
            "year_level": 2,
            "password_hash": STUDENT_ARGON2_HASH,
            "requires_password_change": False,
            "is_active": True,
        },
        {
            "id": uuid.UUID("11111111-1111-1111-1111-111111111126"),
            "student_id": "26-00123",
            "institutional_email": "26-00123@student.pnm.edu.ph",
            "full_name": "Student Cohort 2026",
            "section_code": "BSIT-3A",
            "curriculum_version_id": cv_map.get("BSIT_26").id if "BSIT_26" in cv_map else None,
            "year_level": 1,
            "password_hash": STUDENT_ARGON2_HASH,
            "requires_password_change": False,
            "is_active": True,
        },
    ]

    for stu_data in students_data:
        existing_student = session.scalar(
            select(StudentProfile).where(StudentProfile.student_id == stu_data["student_id"])
        )
        if not existing_student:
            student = StudentProfile(**stu_data)
            session.add(student)
            counts["students"] += 1

    session.commit()
    return counts


if __name__ == "__main__":
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_url = os.getenv("DATABASE_URL", "sqlite:///classync_dev.db")
    engine = create_engine(db_url)
    from classync_contracts.models import Base
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db_session:
        res = seed_database(db_session)
        print("Database seeded successfully:", res)
