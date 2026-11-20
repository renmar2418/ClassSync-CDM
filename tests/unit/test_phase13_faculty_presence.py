"""Unit Test Suite for Phase 13: Faculty Portal, PDF Export, and In-Room Presence Management.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System
"""

import pytest
from fastapi.testclient import TestClient

from services.scheduling.main import app as scheduling_app
from services.presence.main import app as presence_app, faculty_presence_manager
from services.gateway.middleware.rbac import RBACRouteGuard, FORBIDDEN_ERROR_MESSAGE
from classync_contracts.enums import UserRole
from fastapi import HTTPException


@pytest.fixture
def scheduling_client():
    return TestClient(scheduling_app)


@pytest.fixture
def presence_client():
    faculty_presence_manager.clear()
    yield TestClient(presence_app)
    faculty_presence_manager.clear()


class TestFacultyScheduleAndExport:
    """Tests faculty teaching matrix retrieval and PDF export."""

    def test_faculty_schedule_retrieval(self, scheduling_client):
        res = scheduling_client.get("/api/v1/scheduling/faculty/schedule?faculty_email=ngomez@pnm.edu.ph")
        assert res.status_code == 200
        data = res.json()
        assert data["faculty_email"] == "ngomez@pnm.edu.ph"
        assert "entries" in data
        assert len(data["entries"]) > 0

        first = data["entries"][0]
        assert first["facultyEmail"].lower() == "ngomez@pnm.edu.ph"
        assert "courseCode" in first
        assert "roomCode" in first

    def test_faculty_schedule_pdf_export(self, scheduling_client):
        res = scheduling_client.get("/api/v1/scheduling/faculty/schedule/export/pdf?faculty_email=ngomez@pnm.edu.ph")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert "attachment" in res.headers.get("content-disposition", "")
        assert res.content.startswith(b"%PDF")
        assert len(res.content) > 1000

    def test_room_schedule_pdf_export(self, scheduling_client):
        res = scheduling_client.get("/api/v1/scheduling/rooms/PRRC%20301/export/pdf")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert res.content.startswith(b"%PDF")


class TestFacultyInRoomPresenceLifecycle:
    """Verifies manual professor check-in/checkout state transitions and room occupancy impact."""

    def test_faculty_checkin_and_status(self, presence_client):
        # 1. Initial state: room available, no faculty
        initial_res = presence_client.get("/api/v1/presence/rooms/PRRC%20201/faculty-status")
        assert initial_res.status_code == 200
        assert initial_res.json()["faculty_present"] is False

        # 2. Professor check-in
        checkin_payload = {
            "faculty_name": "Engr. Nathaniel Gomez",
            "faculty_email": "ngomez@pnm.edu.ph",
            "subject_code": "CC-IPT2",
            "section_code": "BSIT-3A",
            "notes": "Lecture session in progress",
        }
        checkin_res = presence_client.post(
            "/api/v1/presence/rooms/PRRC%20201/faculty-checkin",
            json=checkin_payload,
        )
        assert checkin_res.status_code == 200
        data = checkin_res.json()
        assert data["success"] is True
        assert data["room_code"] == "PRRC 201"
        assert data["faculty_name"] == "Engr. Nathaniel Gomez"
        assert data["status"] == "OCCUPIED"

        # 3. Verify room status reflects faculty presence
        status_res = presence_client.get("/api/v1/presence/rooms/PRRC%20201/status")
        assert status_res.status_code == 200
        room_data = status_res.json()
        assert room_data["faculty_present"] is True
        assert room_data["faculty_name"] == "Engr. Nathaniel Gomez"
        assert room_data["status"] == "OCCUPIED"

        # 4. Professor check-out
        checkout_res = presence_client.post(
            "/api/v1/presence/rooms/PRRC%20201/faculty-checkout",
            json={"faculty_email": "ngomez@pnm.edu.ph"},
        )
        assert checkout_res.status_code == 200
        checkout_data = checkout_res.json()
        assert checkout_data["success"] is True
        assert checkout_data["status"] == "AVAILABLE"

        # 5. Verify room reverts to available
        post_status_res = presence_client.get("/api/v1/presence/rooms/PRRC%20201/status")
        assert post_status_res.status_code == 200
        assert post_status_res.json()["faculty_present"] is False
        assert post_status_res.json()["status"] == "AVAILABLE"


class TestFacultyRBACGuards:
    """Verifies RBAC protection on faculty presence endpoints."""

    def test_faculty_checkin_rbac_matrix(self):
        checkin_path = "/api/v1/presence/rooms/PRRC 301/faculty-checkin"
        checkout_path = "/api/v1/presence/rooms/PRRC 301/faculty-checkout"

        # Required roles are FACULTY or ADMIN
        req_checkin = RBACRouteGuard.get_required_roles(checkin_path)
        assert req_checkin == {UserRole.FACULTY, UserRole.ADMIN}

        req_checkout = RBACRouteGuard.get_required_roles(checkout_path)
        assert req_checkout == {UserRole.FACULTY, UserRole.ADMIN}

        # Student role rejected with 403
        with pytest.raises(HTTPException) as exc_info:
            RBACRouteGuard.check_access(checkin_path, UserRole.STUDENT)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == FORBIDDEN_ERROR_MESSAGE

        # Faculty allowed
        RBACRouteGuard.check_access(checkin_path, UserRole.FACULTY)

        # Admin allowed
        RBACRouteGuard.check_access(checkin_path, UserRole.ADMIN)
