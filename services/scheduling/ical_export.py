"""RFC 5545 iCalendar (.ics) Timetable Exporter for ClassSync.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Conforms to:
- RFC 5545 Specification (Internet Calendaring and Scheduling Core Object Specification)
- Discrete continuous 30-min intervals (Slots 0-23, Mon-Sat 07:00-19:00)
- Asia/Manila Standard Time (UTC+08:00)
- Strict CRLF line terminators and 75-octet line folding
"""

from __future__ import annotations
import datetime
import uuid
from typing import Any, Dict, List, Optional


def fold_line(line: str) -> str:
    """Folds lines exceeding 75 octets per RFC 5545 section 3.1."""
    if len(line.encode("utf-8")) <= 75:
        return line
    folded = []
    current = ""
    for ch in line:
        test = current + ch
        if len(test.encode("utf-8")) > 74 and current:
            folded.append(current)
            current = " " + ch
        else:
            current = test
    if current:
        folded.append(current)
    return "\r\n".join(folded)


def format_slot_to_time(slot: number_or_int) -> tuple[int, int]:
    """Converts 30-minute continuous slot (0-23) starting at 07:00 AM into (hour, minute)."""
    total_minutes = 7 * 60 + slot * 30
    return total_minutes // 60, total_minutes % 60


def generate_student_schedule_ics(
    student_id: str,
    section_code: str,
    entries: List[Dict[str, Any]],
    semester_start_date: Optional[datetime.date] = None,
    total_weeks: int = 18,
) -> str:
    """Generates an RFC 5545 compliant .ics string for a student's personal timetable."""
    # Default to current academic semester start (Monday)
    if semester_start_date is None:
        semester_start_date = datetime.date(2026, 8, 17)  # Monday, Aug 17, 2026

    # Align to Monday if not already
    day_offset = semester_start_date.weekday()
    monday_base = semester_start_date - datetime.timedelta(days=day_offset)

    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    raw_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ClassSync//Pamantasan ng Montalban//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:ClassSync Schedule - {section_code} ({student_id})",
        "X-WR-TIMEZONE:Asia/Manila",
    ]

    for entry in entries:
        course_code = entry.get("courseCode") or entry.get("subject_code") or "CLASS"
        course_title = entry.get("courseTitle") or entry.get("descriptive_title") or "Scheduled Class"
        room_code = entry.get("roomCode") or entry.get("room_code") or "TBA"
        faculty_name = entry.get("facultyName") or entry.get("faculty_name") or "Faculty Instructor"
        day_of_week = int(entry.get("dayOfWeek", entry.get("day_of_week", 0)))
        start_slot = int(entry.get("startSlot", entry.get("start_slot", 0)))
        duration_slots = int(entry.get("durationSlots", entry.get("duration_slots", 2)))

        # Calculate event date: Monday + day_of_week (0=Mon ... 5=Sat)
        event_date = monday_base + datetime.timedelta(days=day_of_week)

        start_h, start_m = format_slot_to_time(start_slot)
        end_h, end_m = format_slot_to_time(start_slot + duration_slots)

        start_str = f"{event_date.strftime('%Y%m%d')}T{start_h:02d}{start_m:02d}00"
        end_str = f"{event_date.strftime('%Y%m%d')}T{end_h:02d}{end_m:02d}00"

        event_uid = entry.get("id") or str(uuid.uuid4())
        clean_uid = f"{event_uid}_{student_id}@classync.renmar.dev"

        raw_lines.extend([
            "BEGIN:VEVENT",
            f"UID:{clean_uid}",
            f"DTSTAMP:{now_utc}",
            f"DTSTART;TZID=Asia/Manila:{start_str}",
            f"DTEND;TZID=Asia/Manila:{end_str}",
            f"RRULE:FREQ=WEEKLY;COUNT={total_weeks}",
            f"SUMMARY:{course_code} - {course_title}",
            f"LOCATION:{room_code} - Pamantasan ng Montalban",
            f"DESCRIPTION:Course: {course_title}\\nInstructor: {faculty_name}\\nSection: {section_code}\\nRoom: {room_code}",
            "STATUS:CONFIRMED",
            "END:VEVENT",
        ])

    raw_lines.append("END:VCALENDAR")

    # Apply line folding and CRLF formatting
    folded_lines = [fold_line(line) for line in raw_lines]
    return "\r\n".join(folded_lines) + "\r\n"
