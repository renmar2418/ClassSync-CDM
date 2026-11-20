"""Unit Test Suite for Phase 12: Student Portal, iCalendar RFC 5545 Export, and Room Availability.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System
"""

import pytest
from fastapi.testclient import TestClient

from services.scheduling.main import app as scheduling_app
from services.presence.main import app as presence_app
from services.scheduling.ical_export import generate_student_schedule_ics


@pytest.fixture
def scheduling_client():
    return TestClient(scheduling_app)


@pytest.fixture
def presence_client():
    return TestClient(presence_app)


class TestStudentScheduleRetrieval:
    """Tests personal class schedule retrieval for standard and irregular students."""

    def test_student_schedule_endpoint_default(self, scheduling_client):
        res = scheduling_client.get("/api/v1/scheduling/student/schedule")
        assert res.status_code == 200
        data = res.json()
        assert data["student_id"] == "24-00123"
        assert data["section_code"] == "BSIT-3A"
        assert "entries" in data
        assert len(data["entries"]) > 0

        # Validate entry fields
        first = data["entries"][0]
        assert "courseCode" in first
        assert "courseTitle" in first
        assert "roomCode" in first
        assert "dayOfWeek" in first
        assert "startSlot" in first
        assert "durationSlots" in first

    def test_student_schedule_custom_student_and_section(self, scheduling_client):
        res = scheduling_client.get(
            "/api/v1/scheduling/student/schedule?student_id=23-00456&section_code=BSIT-3A"
        )
        assert res.status_code == 200
        data = res.json()
        assert data["student_id"] == "23-00456"
        assert data["section_code"] == "BSIT-3A"
        assert len(data["entries"]) > 0


class TestICalendarExportRFC5545:
    """Verifies RFC 5545 iCalendar generation, 75-octet line folding, and RRULE specs."""

    def test_ical_export_endpoint(self, scheduling_client):
        res = scheduling_client.get(
            "/api/v1/scheduling/student/schedule/export/ics?student_id=24-00123&section_code=BSIT-3A"
        )
        assert res.status_code == 200
        assert "text/calendar" in res.headers["content-type"]
        assert "attachment" in res.headers.get("content-disposition", "")
        body = res.text

        # RFC 5545 Envelope
        assert "BEGIN:VCALENDAR\r\n" in body
        assert "VERSION:2.0\r\n" in body
        assert "PRODID:-//ClassSync//Pamantasan ng Montalban//EN\r\n" in body
        assert "CALSCALE:GREGORIAN\r\n" in body
        assert "METHOD:PUBLISH\r\n" in body
        assert "END:VCALENDAR\r\n" in body

        # Weekly RRULE
        assert "RRULE:FREQ=WEEKLY;COUNT=18\r\n" in body
        assert "BEGIN:VEVENT\r\n" in body
        assert "SUMMARY:" in body
        assert "LOCATION:" in body

    def test_ical_line_folding_rfc5545_compliance(self):
        """Verifies that no line exceeds 75 octets without CRLF + space folding."""
        sample_entries = [
            {
                "id": "e-1",
                "courseCode": "CC-IPT2",
                "courseTitle": "Very Long Descriptive Title Exceeding Normal Length Requirements for Philippine Higher Education Curricula in Computer Science and Information Technology",
                "roomCode": "PRRC 301 Computer Laboratory Facility",
                "roomType": "COMPUTER_LAB",
                "dayOfWeek": 0,
                "startSlot": 2,
                "durationSlots": 6,
                "facultyName": "Engr. Nathaniel Gomez, Master of Engineering in Computer Systems",
                "sectionCode": "BSIT-3A",
            }
        ]
        ics = generate_student_schedule_ics("24-00123", "BSIT-3A", sample_entries)
        lines = ics.split("\r\n")

        for line in lines:
            # Each line (excluding the trailing CRLF) must be <= 75 octets
            assert len(line.encode("utf-8")) <= 75, f"Line exceeds 75 octets: {line}"


class TestPDFScheduleExport:
    """Verifies official ReportLab PDF schedule generation."""

    def test_student_schedule_pdf_endpoint(self, scheduling_client):
        res = scheduling_client.get(
            "/api/v1/scheduling/student/schedule/export/pdf?student_id=24-00123&section_code=BSIT-3A"
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert "attachment" in res.headers.get("content-disposition", "")
        assert res.content.startswith(b"%PDF")
        assert len(res.content) > 1000


class TestCampusRoomAvailabilityStatus:
    """Verifies campus-wide real-time room availability telemetry."""

    def test_get_all_rooms_status(self, presence_client):
        res = presence_client.get("/api/v1/presence/rooms/status")
        assert res.status_code == 200
        rooms = res.json()
        assert len(rooms) >= 30

        # Check fields on each room item
        for r in rooms:
            assert "room_code" in r
            assert "building_name" in r
            assert "status" in r
            assert r["status"] in ("AVAILABLE", "OCCUPIED", "QUARANTINED", "MAINTENANCE")
            assert "is_schedulable" in r
            assert "is_quarantined" in r
            assert "total_stations" in r
            assert "occupied_count" in r
            assert "faculty_present" in r

    def test_quarantined_rooms_marked_accurately(self, presence_client):
        res = presence_client.get("/api/v1/presence/rooms/status?is_schedulable=false")
        assert res.status_code == 200
        rooms = res.json()
        assert len(rooms) > 0
        for r in rooms:
            assert r["is_schedulable"] is False
            assert r["is_quarantined"] is True
            assert r["status"] == "QUARANTINED"

    def test_filter_rooms_by_building(self, presence_client):
        res = presence_client.get("/api/v1/presence/rooms/status?building=New Building")
        assert res.status_code == 200
        rooms = res.json()
        assert len(rooms) > 0
        for r in rooms:
            assert r["building_name"] == "New Building"

    def test_get_single_room_status_comlab(self, presence_client):
        res = presence_client.get("/api/v1/presence/rooms/PRRC 301/status")
        assert res.status_code == 200
        data = res.json()
        assert data["room_code"] == "PRRC 301"
        assert data["room_type"] == "COMPUTER_LAB"
        assert data["total_stations"] == 45
        assert data["operational_count"] == 45
        assert data["occupied_count"] >= 0
        assert data["status"] in ("AVAILABLE", "OCCUPIED")
