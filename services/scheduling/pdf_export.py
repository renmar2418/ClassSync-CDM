"""Official Institutional PDF Timetable Generator for ClassSync.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Generates clean, printable, executive-ready PDF class schedules for:
- Student Cohorts / Sections (e.g. BSIT-3A)
- Faculty Plantilla Teaching Loads (e.g. Engr. Nathaniel Gomez)
- Room Master Utilization Timetables (e.g. PRRC 301)

Built using ReportLab 5.x.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def format_slot_time_12h(slot: int) -> str:
    """Formats continuous 30-minute slot 0..23 into 12-hour AM/PM string."""
    total_minutes = 7 * 60 + slot * 30
    hours = total_minutes // 60
    minutes = total_minutes % 60
    period = "PM" if hours >= 12 else "AM"
    display_hours = hours - 12 if hours > 12 else (12 if hours == 0 else hours)
    return f"{display_hours:02d}:{minutes:02d} {period}"


def generate_schedule_pdf(
    title: str,
    subtitle: str,
    entries: List[Dict[str, Any]],
    institution_name: str = "PAMANTASAN NG MONTALBAN",
    sub_institution: str = "Colegio de Montalban • Office of the University Registrar",
    academic_term: str = "Academic Year 2026–2027 • 1st Semester",
    is_landscape: bool = True,
) -> bytes:
    """Generates an institutional PDF timetable matching CdM/PNM standards."""
    buffer = io.BytesIO()
    page_size = landscape(letter) if is_landscape else letter
    margin = 36  # 0.5 inch

    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    brand_rouge = colors.HexColor("#8B1E3F")
    brand_midnight = colors.HexColor("#0F172A")
    ink_soft = colors.HexColor("#64748B")

    title_style = ParagraphStyle(
        "InstTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=16,
        textColor=brand_rouge,
        alignment=1,  # Center
    )

    sub_title_style = ParagraphStyle(
        "InstSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=ink_soft,
        alignment=1,
    )

    section_header_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=13,
        textColor=brand_midnight,
        alignment=1,
    )

    term_style = ParagraphStyle(
        "TermStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=brand_rouge,
        alignment=1,
    )

    cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=brand_midnight,
    )

    cell_bold_style = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=brand_midnight,
    )

    th_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10,
        textColor=colors.white,
        alignment=1,
    )

    story = []

    # 1. Official Header
    story.append(Paragraph(institution_name, title_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph(sub_institution, sub_title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(title.upper(), section_header_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph(f"{subtitle} • {academic_term}", term_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=brand_rouge, spaceAfter=8))

    # 2. Sort Entries Chronologically: Day of week ascending, start_slot ascending
    sorted_entries = sorted(
        entries,
        key=lambda x: (x.get("dayOfWeek", x.get("day_of_week", 0)), x.get("startSlot", x.get("start_slot", 0))),
    )

    # 3. Build Table Data
    headers = [
        Paragraph("<b>DAY</b>", th_style),
        Paragraph("<b>TIME</b>", th_style),
        Paragraph("<b>COURSE CODE</b>", th_style),
        Paragraph("<b>COURSE TITLE</b>", th_style),
        Paragraph("<b>ROOM</b>", th_style),
        Paragraph("<b>TYPE</b>", th_style),
        Paragraph("<b>SECTION</b>", th_style),
        Paragraph("<b>INSTRUCTOR</b>", th_style),
    ]

    data = [headers]

    for item in sorted_entries:
        day_idx = item.get("dayOfWeek", item.get("day_of_week", 0))
        day_str = DAYS_OF_WEEK[day_idx] if 0 <= day_idx < len(DAYS_OF_WEEK) else f"Day {day_idx}"

        start_s = item.get("startSlot", item.get("start_slot", 0))
        dur_s = item.get("durationSlots", item.get("duration_slots", 1))
        time_str = f"{format_slot_time_12h(start_s)} – {format_slot_time_12h(start_s + dur_s)}"

        c_code = item.get("courseCode", item.get("course_code", "—"))
        c_title = item.get("courseTitle", item.get("course_title", "—"))
        r_code = item.get("roomCode", item.get("room_code", "—"))
        r_type = item.get("roomType", item.get("room_type", "LECTURE")).replace("_", " ")
        sec_code = item.get("sectionCode", item.get("section_code", "—"))
        f_name = item.get("facultyName", item.get("faculty_name", "—"))

        row = [
            Paragraph(f"<b>{day_str}</b>", cell_bold_style),
            Paragraph(time_str, cell_style),
            Paragraph(f"<b>{c_code}</b>", cell_bold_style),
            Paragraph(c_title, cell_style),
            Paragraph(f"<b>{r_code}</b>", cell_bold_style),
            Paragraph(r_type, cell_style),
            Paragraph(sec_code, cell_style),
            Paragraph(f_name, cell_style),
        ]
        data.append(row)

    if len(data) == 1:
        empty_row = [Paragraph("<i>No scheduled classes found.</i>", cell_style)] + [Paragraph("", cell_style)] * 7
        data.append(empty_row)

    # Table Column Widths (for landscape letter, total printable width ~ 720pt)
    col_widths = [65, 105, 75, 185, 60, 70, 60, 100]

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), brand_rouge),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ])
    )
    story.append(t)

    # 4. Official Sign-off and Verification Footer
    story.append(Spacer(1, 14))
    gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    footer_text = (
        f"Official Timetable Generated via ClassSync AI Platform • Verifiable Institutional Record • Timestamp: {gen_time}"
    )
    footer_style = ParagraphStyle(
        "FooterStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7,
        leading=9,
        textColor=ink_soft,
        alignment=1,
    )
    story.append(Paragraph(footer_text, footer_style))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
