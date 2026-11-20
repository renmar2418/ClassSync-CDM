"""Unit & Integration tests for ClassSync Phase 8:
- Brevo Email & 2FA OTP Service
- Real Workflow Testing for Admin, Faculty, and Multi-Year Students (22..26)
- OWASP ASVS 4.0 OTP TTL Expiry & Brute-Force Rate Limiting
"""

import time
import pytest
from fastapi.testclient import TestClient

from services.gateway.main import app as gateway_app, rate_limiter
from services.gateway.auth.routes import reset_user_db, gateway_brevo_client, gateway_otp_manager
from services.notification.main import app as notification_app
from services.notification.otp import OTPManager
from services.notification.brevo_client import BrevoClient
from services.notification.templates import render_otp_email, render_schedule_change_email


@pytest.fixture(autouse=True)
def setup_teardown():
    rate_limiter.reset()
    reset_user_db()
    yield
    rate_limiter.reset()
    reset_user_db()


@pytest.fixture
def gateway_client():
    return TestClient(gateway_app)


@pytest.fixture
def notif_client():
    return TestClient(notification_app)


class TestOTPManagerCore:
    """Verifies in-memory cryptographic OTP lifecycle, TTL expiration, and attempt limiting."""

    def test_otp_code_is_6_numeric_digits(self):
        mgr = OTPManager()
        code = mgr.generate_code(6)
        assert len(code) == 6
        assert code.isdigit()

    def test_otp_session_verification_success(self):
        mgr = OTPManager(expiry_seconds=300, max_attempts=3)
        session = mgr.create_session("student@pnm.edu.ph")
        success, msg, email = mgr.verify_code(session.session_id, session.otp_code)
        assert success is True
        assert "verified successfully" in msg.lower()
        assert email == "student@pnm.edu.ph"

    def test_otp_single_use_consumption(self):
        mgr = OTPManager(expiry_seconds=300, max_attempts=3)
        session = mgr.create_session("student@pnm.edu.ph")
        # First use succeeds
        s1, _, _ = mgr.verify_code(session.session_id, session.otp_code)
        assert s1 is True
        # Second use fails because session was consumed
        s2, msg, _ = mgr.verify_code(session.session_id, session.otp_code)
        assert s2 is False
        assert "not found" in msg.lower() or "completed" in msg.lower()

    def test_otp_expiry_after_ttl(self):
        # 1-second TTL
        mgr = OTPManager(expiry_seconds=1, max_attempts=3)
        session = mgr.create_session("student@pnm.edu.ph")
        time.sleep(1.2)
        success, msg, _ = mgr.verify_code(session.session_id, session.otp_code)
        assert success is False
        assert "expired" in msg.lower()

    def test_otp_brute_force_lockout_after_3_attempts(self):
        mgr = OTPManager(expiry_seconds=300, max_attempts=3)
        session = mgr.create_session("student@pnm.edu.ph")

        # Attempt 1: wrong code
        s1, msg1, _ = mgr.verify_code(session.session_id, "000000")
        assert s1 is False
        assert "2 attempt(s) remaining" in msg1

        # Attempt 2: wrong code
        s2, msg2, _ = mgr.verify_code(session.session_id, "111111")
        assert s2 is False
        assert "1 attempt(s) remaining" in msg2

        # Attempt 3: wrong code -> locked
        s3, msg3, _ = mgr.verify_code(session.session_id, "222222")
        assert s3 is False
        assert "invalid" in msg3.lower()

        # Attempt 4: even if now providing the correct code, it's purged
        s4, _, _ = mgr.verify_code(session.session_id, session.otp_code)
        assert s4 is False


class TestBrevoNotificationService:
    """Verifies standalone notification service endpoints on Port 8003."""

    def test_notification_health(self, notif_client):
        resp = notif_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["service"] == "notification"

    def test_send_and_verify_otp_service_endpoints(self, notif_client):
        # 1. Send OTP
        send_resp = notif_client.post(
            "/api/v1/notification/send-otp",
            json={"email": "prof.test@pnm.edu.ph", "full_name": "Prof. Test"},
        )
        assert send_resp.status_code == 200
        data = send_resp.json()
        assert data["success"] is True
        assert data["mock"] is True
        session_id = data["otp_session_id"]
        otp_code = data["debug_code"]
        assert len(otp_code) == 6

        # 2. Verify with wrong code
        fail_resp = notif_client.post(
            "/api/v1/notification/verify-otp",
            json={"otp_session_id": session_id, "otp_code": "999999"},
        )
        assert fail_resp.status_code == 401
        assert "remaining" in fail_resp.json()["detail"].lower()

        # 3. Verify with correct code
        ok_resp = notif_client.post(
            "/api/v1/notification/verify-otp",
            json={"otp_session_id": session_id, "otp_code": otp_code},
        )
        assert ok_resp.status_code == 200
        assert ok_resp.json()["success"] is True
        assert ok_resp.json()["email"] == "prof.test@pnm.edu.ph"

    def test_send_email_transactional_endpoint(self, notif_client):
        html = render_schedule_change_email("Prof. Mades", "Room changed from PRRC 301 to PRRC 302")
        resp = notif_client.post(
            "/api/v1/notification/send-email",
            json={
                "to_email": "prof.mades@pnm.edu.ph",
                "subject": "Room Change Notice",
                "html_content": html,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "dispatched"


class TestGatewayTwoStepLoginWorkflow:
    """Verifies end-to-end 2-Step Brevo OTP Login Flow across Admin, Faculty, and Multi-Year Students."""

    TURNSTILE_PASS = "test-turnstile-token-pass"

    def test_admin_2step_login_flow(self, gateway_client):
        """Admin logs in via credentials -> Brevo OTP sent -> OTP submitted -> JWT issued with role=ADMIN."""
        # Step 1: Submit Credentials + Turnstile
        s1_resp = gateway_client.post(
            "/api/v1/auth/login/step1",
            json={
                "identifier": "admin@pnm.edu.ph",
                "password": "CdMAdmin2026!",
                "turnstile_token": self.TURNSTILE_PASS,
            },
        )
        assert s1_resp.status_code == 200
        s1_data = s1_resp.json()
        assert s1_data["requires_otp"] is True
        session_id = s1_data["otp_session_id"]
        assert "@pnm.edu.ph" in s1_data["email_hint"]

        # Retrieve OTP code from Brevo dispatcher
        otp_code = gateway_brevo_client.get_last_sent_otp_for("admin@pnm.edu.ph")
        assert otp_code is not None and len(otp_code) == 6

        # Step 2: Verify OTP
        s2_resp = gateway_client.post(
            "/api/v1/auth/login/verify-otp",
            json={
                "otp_session_id": session_id,
                "otp_code": otp_code,
            },
        )
        assert s2_resp.status_code == 200
        s2_data = s2_resp.json()
        assert "access_token" in s2_data
        assert s2_data["user"]["role"] == "ADMIN"
        assert s2_data["user"]["identifier"] == "admin@pnm.edu.ph"

        # Verify access token works on /api/v1/auth/me
        me_resp = gateway_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {s2_data['access_token']}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["role"] == "ADMIN"

    def test_faculty_2step_login_flow(self, gateway_client):
        """Faculty logs in via credentials -> Brevo OTP -> JWT issued with role=FACULTY."""
        s1_resp = gateway_client.post(
            "/api/v1/auth/login/step1",
            json={
                "identifier": "teacher@pnm.edu.ph",
                "password": "FacultyPass2026!",
                "turnstile_token": self.TURNSTILE_PASS,
            },
        )
        assert s1_resp.status_code == 200
        session_id = s1_resp.json()["otp_session_id"]

        otp_code = gateway_brevo_client.get_last_sent_otp_for("teacher@pnm.edu.ph")
        assert otp_code is not None

        s2_resp = gateway_client.post(
            "/api/v1/auth/login/verify-otp",
            json={"otp_session_id": session_id, "otp_code": otp_code},
        )
        assert s2_resp.status_code == 200
        assert s2_resp.json()["user"]["role"] == "FACULTY"

    @pytest.mark.parametrize("student_id", [
        "22-00123",
        "23-00123",
        "24-00123",
        "25-00123",
        "26-00123",
    ])
    def test_multi_year_student_2step_login(self, gateway_client, student_id):
        """Students from cohorts 2022 to 2026 can log in through 2-Step Brevo OTP."""
        rate_limiter.reset()
        s1_resp = gateway_client.post(
            "/api/v1/auth/login/step1",
            json={
                "identifier": student_id,
                "password": "StudentPass2026!",
                "turnstile_token": self.TURNSTILE_PASS,
            },
        )
        assert s1_resp.status_code == 200
        session_id = s1_resp.json()["otp_session_id"]

        expected_email = f"{student_id}@student.pnm.edu.ph"
        otp_code = gateway_brevo_client.get_last_sent_otp_for(expected_email)
        assert otp_code is not None

        s2_resp = gateway_client.post(
            "/api/v1/auth/login/verify-otp",
            json={"otp_session_id": session_id, "otp_code": otp_code},
        )
        assert s2_resp.status_code == 200
        assert s2_resp.json()["user"]["role"] == "STUDENT"
        assert s2_resp.json()["user"]["identifier"] == student_id

    def test_step1_turnstile_failure_blocks_login(self, gateway_client):
        resp = gateway_client.post(
            "/api/v1/auth/login/step1",
            json={
                "identifier": "admin@pnm.edu.ph",
                "password": "CdMAdmin2026!",
                "turnstile_token": "test-turnstile-token-fail",
            },
        )
        assert resp.status_code == 400
        assert "Human verification" in resp.json()["detail"] or "verification check" in resp.json()["detail"].lower()

    def test_step1_wrong_password_blocks_otp_dispatch(self, gateway_client):
        resp = gateway_client.post(
            "/api/v1/auth/login/step1",
            json={
                "identifier": "admin@pnm.edu.ph",
                "password": "TotallyWrongPassword123!",
                "turnstile_token": self.TURNSTILE_PASS,
            },
        )
        assert resp.status_code == 401
        assert "does not match our records" in resp.json()["detail"]

    def test_step2_incorrect_otp_returns_401_with_countdown(self, gateway_client):
        # Step 1
        s1_resp = gateway_client.post(
            "/api/v1/auth/login/step1",
            json={
                "identifier": "admin@pnm.edu.ph",
                "password": "CdMAdmin2026!",
                "turnstile_token": self.TURNSTILE_PASS,
            },
        )
        session_id = s1_resp.json()["otp_session_id"]

        # Step 2: Submit wrong code
        s2_resp = gateway_client.post(
            "/api/v1/auth/login/verify-otp",
            json={"otp_session_id": session_id, "otp_code": "000000"},
        )
        assert s2_resp.status_code == 401
        assert "2 attempt(s) remaining" in s2_resp.json()["detail"]
