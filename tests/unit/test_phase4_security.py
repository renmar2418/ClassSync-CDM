"""Comprehensive Phase 4 Test Suite: Security Gateway, Auth, RBAC & Reverse Proxy.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Test Coverage:
1. Cloudflare Turnstile token validation, test keys, and bot rejection.
2. Google Workspace domain-restricted OAuth claim validation and role mapping.
3. OWASP ASVS 4.0 password entropy checking, campus blacklist, and Argon2id hashing.
4. HS256 JWT lifecycle: access (15m) / refresh (7d), claims, expired tokens, tampering.
5. Dual token transport: HttpOnly cookies and Authorization Bearer headers.
6. RBAC route guard matrix (ADMIN, FACULTY, STUDENT) and empathetic 403 copy.
7. Downstream trust header injection (X-User-ID, X-User-Role, X-User-Email, X-Forwarded-For).
8. Client header spoofing sanitization.
9. Dual-tier in-memory token bucket rate limiting (General 60/min, Auth 5/15min).
10. Security headers middleware (CSP, HSTS, X-Frame-Options, X-Content-Type-Options).
11. Reverse proxy streaming and 502 error recovery.
12. AST analysis verifying ZERO 're' module imports across all gateway modules.
"""

import ast
import asyncio
import os
import time
import uuid
import pytest
import httpx
from fastapi.testclient import TestClient

from classync_contracts.enums import UserRole
from services.gateway.config import settings
from services.gateway.auth.turnstile import (
    CloudflareTurnstileVerifier,
    TurnstileResult,
    TurnstileError,
    TurnstileVerificationError,
    TurnstileTimeoutError,
    TURNSTILE_ERROR_MESSAGE,
    TURNSTILE_TIMEOUT_MESSAGE,
    TEST_SECRET_PASS_LONG,
    TEST_SECRET_FAIL_LONG,
    TEST_SECRET_ERROR_LONG,
)
from services.gateway.auth.oauth import (
    GoogleOAuthVerifier,
    GoogleValidatedClaims,
    GoogleDomainRestrictedError,
    GoogleEmailNotVerifiedError,
    GoogleTokenInvalidError,
    STUDENT_DOMAIN_ERROR_COPY,
    FACULTY_DOMAIN_ERROR_COPY,
    validate_google_claims,
)
from services.gateway.auth.password import (
    PasswordEntropyValidator,
    calculate_entropy_bits,
    assess_password_entropy,
    validate_password_entropy,
    check_password_integrity,
    hash_password,
    verify_password,
    PasswordEntropyError,
)
from services.gateway.auth.jwt import JWTManager
from services.gateway.auth.routes import reset_user_db
from services.gateway.middleware.rbac import (
    RBACRouteGuard,
    FORBIDDEN_ERROR_MESSAGE,
    UNAUTHORIZED_ERROR_MESSAGE,
)
from services.gateway.middleware.rate_limiter import InMemoryRateLimiter, TokenBucket
from services.gateway.proxy.reverse_proxy import ReverseProxyHandler, DOWNSTREAM_TIMEOUT_ERROR_MESSAGE
from services.gateway.main import app, rate_limiter


# ---------------------------------------------------------------------------
# Pytest Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def setup_gateway_state():
    """Reset rate limiter and user store state before each test."""
    rate_limiter.reset()
    reset_user_db()
    yield
    rate_limiter.reset()


@pytest.fixture
def jwt_mgr():
    return JWTManager(secret=settings.jwt_secret, access_exp_minutes=15)


@pytest.fixture
def client():
    return TestClient(app)


# ===========================================================================
# 1. Cloudflare Turnstile Tests
# ===========================================================================

def test_turnstile_dummy_token_success():
    async def _run():
        verifier = CloudflareTurnstileVerifier(secret_key=TEST_SECRET_PASS_LONG, mock_mode=True)
        res = await verifier.verify("XXXX.DUMMY.TOKEN.PASS")
        assert res.success is True
        assert res.error_codes == []
        assert res.user_message is None
    asyncio.run(_run())


def test_turnstile_official_test_secret_pass():
    async def _run():
        verifier = CloudflareTurnstileVerifier(secret_key="1x00000000000000000000AA", mock_mode=True)
        res = await verifier.verify("any-valid-token-1")
        assert res.success is True
    asyncio.run(_run())


def test_turnstile_official_test_secret_fail():
    async def _run():
        verifier = CloudflareTurnstileVerifier(secret_key="2x00000000000000000000AB", mock_mode=True)
        res = await verifier.verify("some-token")
        assert res.success is False
        assert "invalid-input-response" in res.error_codes
        assert res.user_message == TURNSTILE_ERROR_MESSAGE
    asyncio.run(_run())


def test_turnstile_official_test_secret_error():
    async def _run():
        verifier = CloudflareTurnstileVerifier(secret_key="3x00000000000000000000FF", mock_mode=True)
        res = await verifier.verify("some-token")
        assert res.success is False
        assert "invalid-input-secret" in res.error_codes
    asyncio.run(_run())


def test_turnstile_missing_or_empty_token_rejection():
    async def _run():
        verifier = CloudflareTurnstileVerifier(secret_key=TEST_SECRET_PASS_LONG, mock_mode=True)
        res_empty = await verifier.verify("")
        assert res_empty.success is False
        assert "missing-input-response" in res_empty.error_codes

        res_none = await verifier.verify(None)  # type: ignore
        assert res_none.success is False
    asyncio.run(_run())


def test_turnstile_token_replay_rejected():
    async def _run():
        verifier = CloudflareTurnstileVerifier(secret_key=TEST_SECRET_PASS_LONG, mock_mode=True)
        single_token = "single-use-token-xyz"
        first = await verifier.verify(single_token)
        assert first.success is True

        # Replay
        second = await verifier.verify(single_token)
        assert second.success is False
        assert "timeout-or-duplicate" in second.error_codes
    asyncio.run(_run())


def test_turnstile_timeout_handling_and_copy():
    async def _run():
        verifier = CloudflareTurnstileVerifier(secret_key=TEST_SECRET_PASS_LONG, mock_mode=True)
        with pytest.raises(TurnstileTimeoutError) as exc_info:
            await verifier.verify("test-turnstile-token-timeout")
        assert exc_info.value.message == TURNSTILE_TIMEOUT_MESSAGE
    asyncio.run(_run())


def test_turnstile_verify_or_raise_exception():
    async def _run():
        verifier = CloudflareTurnstileVerifier(secret_key="2x00000000000000000000AB", mock_mode=True)
        with pytest.raises(TurnstileVerificationError) as exc_info:
            await verifier.verify_or_raise("failing-token")
        assert exc_info.value.message == TURNSTILE_ERROR_MESSAGE
    asyncio.run(_run())


def test_turnstile_endpoint_via_http(client):
    resp = client.post("/api/v1/auth/verify-turnstile", json={"token": "XXXX.DUMMY.PASS"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


# ===========================================================================
# 2. Google Workspace OAuth Claims & Domain Restriction Tests
# ===========================================================================

def test_google_oauth_student_domain_success():
    claims = {
        "sub": "1234567890",
        "email": "24-00123@student.pnm.edu.ph",
        "email_verified": True,
        "hd": "student.pnm.edu.ph",
        "name": "Juan Dela Cruz",
    }
    validated = validate_google_claims(claims)
    assert validated.role == UserRole.STUDENT
    assert validated.identifier == "24-00123"
    assert validated.hd == "student.pnm.edu.ph"


def test_google_oauth_faculty_domain_success():
    claims = {
        "sub": "9876543210",
        "email": "prof.mades@pnm.edu.ph",
        "email_verified": True,
        "hd": "pnm.edu.ph",
        "name": "Prof. Mades",
    }
    validated = validate_google_claims(claims)
    assert validated.role == UserRole.FACULTY
    assert validated.identifier == "prof.mades@pnm.edu.ph"


def test_google_oauth_admin_email_success():
    claims = {
        "sub": "admin-sub-001",
        "email": "admin@pnm.edu.ph",
        "email_verified": True,
        "hd": "pnm.edu.ph",
        "name": "ClassSync Admin",
    }
    validated = validate_google_claims(claims)
    assert validated.role == UserRole.ADMIN


def test_google_oauth_student_id_extracted_from_prefix():
    claims = {
        "sub": "student-sub-777",
        "email": "24-05432@student.pnm.edu.ph",
        "email_verified": True,
        "hd": "student.pnm.edu.ph",
    }
    validated = validate_google_claims(claims)
    assert validated.identifier == "24-05432"


def test_google_oauth_unverified_email_rejected():
    claims = {
        "sub": "sub-unverified",
        "email": "24-00123@student.pnm.edu.ph",
        "email_verified": False,
        "hd": "student.pnm.edu.ph",
    }
    with pytest.raises(GoogleEmailNotVerifiedError):
        validate_google_claims(claims)


def test_google_oauth_personal_gmail_rejected():
    claims = {
        "sub": "sub-personal",
        "email": "student@gmail.com",
        "email_verified": True,
        "hd": "gmail.com",
    }
    with pytest.raises(GoogleDomainRestrictedError) as exc_info:
        validate_google_claims(claims)
    assert exc_info.value.message == STUDENT_DOMAIN_ERROR_COPY


def test_google_oauth_deprecated_cdm_domain_rejected():
    claims = {
        "sub": "sub-cdm",
        "email": "student@cdm.edu.ph",
        "email_verified": True,
        "hd": "cdm.edu.ph",
    }
    with pytest.raises(GoogleDomainRestrictedError) as exc_info:
        validate_google_claims(claims)
    assert "retired" in exc_info.value.message.lower() or "@student.pnm.edu.ph" in exc_info.value.message


def test_google_oauth_missing_hd_claim_rejected():
    claims = {
        "sub": "sub-no-hd",
        "email": "someone@example.com",
        "email_verified": True,
    }
    with pytest.raises(GoogleDomainRestrictedError):
        validate_google_claims(claims)


def test_google_oauth_domain_mismatch_rejected():
    claims = {
        "sub": "sub-mismatch",
        "email": "student@student.pnm.edu.ph",
        "email_verified": True,
        "hd": "pnm.edu.ph",
    }
    with pytest.raises(GoogleDomainRestrictedError):
        validate_google_claims(claims)


def test_google_oauth_role_restriction_mismatch():
    claims = {
        "sub": "sub-faculty",
        "email": "faculty@pnm.edu.ph",
        "email_verified": True,
        "hd": "pnm.edu.ph",
    }
    with pytest.raises(GoogleDomainRestrictedError) as exc_info:
        validate_google_claims(claims, required_role=UserRole.STUDENT)
    assert exc_info.value.message == STUDENT_DOMAIN_ERROR_COPY


def test_google_oauth_endpoint_via_http_student(client):
    resp = client.post(
        "/api/v1/auth/google-sso",
        json={"id_token": "test-token-student-valid"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "STUDENT"
    assert "access_token" in resp.cookies


def test_google_oauth_endpoint_via_http_faculty(client):
    resp = client.post(
        "/api/v1/auth/google-sso",
        json={"id_token": "test-token-faculty-valid"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["role"] == "FACULTY"


# ===========================================================================
# 3. OWASP ASVS 4.0 Password Entropy, Blacklist & Argon2id Tests
# ===========================================================================

def test_password_asvs_minimum_length_enforced():
    valid, _, reasons = assess_password_entropy("Short9!Aa")  # 9 chars
    assert valid is False
    assert any("at least 10 characters" in r for r in reasons)


def test_password_asvs_character_classes_required():
    # Missing symbol
    valid, _, reasons = assess_password_entropy("NoSymbolPass123")
    assert valid is False
    assert any("special symbol" in r for r in reasons)

    # Missing digit
    valid, _, reasons = assess_password_entropy("NoDigitPass!@#")
    assert valid is False
    assert any("number (0–9)" in r for r in reasons)

    # Missing uppercase
    valid, _, reasons = assess_password_entropy("lowercase123!@#")
    assert valid is False
    assert any("capital letter" in r for r in reasons)

    # Missing lowercase
    valid, _, reasons = assess_password_entropy("UPPERCASE123!@#")
    assert valid is False
    assert any("lowercase letter" in r for r in reasons)


def test_password_asvs_campus_dictionary_blacklist_verbatim():
    for word in ("cdm", "montalban", "pnm", "classsync", "password", "123456", "admin"):
        pwd = f"Safe_{word}_2026!#"
        valid, _, reasons = assess_password_entropy(pwd)
        assert valid is False, f"Password containing {word} should be rejected"
        assert any("campus names or common terms" in r for r in reasons)


def test_password_asvs_campus_dictionary_blacklist_leetspeak():
    # 'M0ntalb@n' -> 'montalban', 'P@ssw0rd' -> 'password', 'Adm1n' -> 'admin'
    for evasive in ("M0ntalb@n2026!#", "P@ssw0rd2026!#", "Adm1n2026!#Xy"):
        valid, _, reasons = assess_password_entropy(evasive)
        assert valid is False, f"Evasive password {evasive} should be rejected"
        assert any("campus names or common terms" in r for r in reasons)


def test_password_asvs_sequential_strings_rejected():
    for seq in ("1234", "4321", "abcd", "dcba", "qwerty", "ytrewq"):
        pwd = f"Prefix_{seq}_Suffix!9"
        valid, _, reasons = assess_password_entropy(pwd)
        assert valid is False, f"Password containing {seq} should be rejected"
        assert any("predictable sequences" in r for r in reasons)


def test_password_asvs_repeated_character_sequence_rejected():
    pwd = "Safe_aaaa_Pass9!#"
    valid, _, reasons = assess_password_entropy(pwd)
    assert valid is False
    assert any("predictable sequences" in r for r in reasons)


def test_password_asvs_student_id_inclusion_rejected():
    pwd = "ComplexPass!2400123"
    valid, _, reasons = assess_password_entropy(pwd, identifier="24-00123")
    assert valid is False
    assert any("Student ID" in r for r in reasons)


def test_password_asvs_valid_password_passes():
    valid_pwd = "V3ry$ecure&Str0ngP@ss!"  # wait, has '$ecure', let's check leetspeak: 'sec'
    clean_pwd = "X9#kL2!mP8$vWq"
    valid, entropy, reasons = assess_password_entropy(clean_pwd)
    assert valid is True
    assert reasons == []
    assert entropy >= 50.0

    # Test validator class
    ok, msg, ent = PasswordEntropyValidator.validate_password(clean_pwd)
    assert ok is True


def test_password_argon2id_hashing_and_verification():
    pwd = "MySecretPass2026!#"
    h = hash_password(pwd)
    assert h.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert verify_password(pwd, h) is True


def test_password_argon2id_bidirectional_signature():
    pwd = "AnotherSecretPass2026!#"
    h = hash_password(pwd)
    # verify_password(plain, hash) and verify_password(hash, plain)
    assert verify_password(pwd, h) is True
    assert verify_password(h, pwd) is True


def test_password_argon2id_invalid_password_returns_false():
    h = hash_password("CorrectPass123!#")
    assert verify_password("WrongPass123!#", h) is False
    assert verify_password("CorrectPass123!#", "corrupted_hash") is False


def test_password_entropy_calculator_bits():
    ent = calculate_entropy_bits("aA1!")  # 4 chars from all 4 pools
    assert ent > 0


def test_password_first_time_setup_workflow(client):
    # Setup password for user 24-00999
    body = {
        "student_or_employee_id": "24-00999",
        "new_password": "X9#kL2!mP8$vWq",
        "confirm_password": "X9#kL2!mP8$vWq",
    }
    resp = client.post("/api/v1/auth/setup-password", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["requires_password_change"] is False

    # Now verify login with the new password
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "24-00999",
            "password": "X9#kL2!mP8$vWq",
            "turnstile_token": "XXXX.DUMMY.PASS",
        },
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["requires_password_change"] is False


# ===========================================================================
# 4. HS256 JWT Lifecycle & Auth Endpoints Tests
# ===========================================================================

def test_jwt_creation_and_payload_claims(jwt_mgr):
    tok = jwt_mgr.create_access_token(
        user_id="user-123",
        email="user@pnm.edu.ph",
        role=UserRole.FACULTY,
        hd="pnm.edu.ph",
        full_name="Dr. Test",
    )
    payload = jwt_mgr.decode_and_verify(tok, expected_type="access")
    assert payload["sub"] == "user-123"
    assert payload["email"] == "user@pnm.edu.ph"
    assert payload["role"] == "FACULTY"
    assert payload["token_type"] == "access"
    assert payload["name"] == "Dr. Test"
    assert payload["exp"] > payload["iat"]


def test_jwt_expiration_rejected(jwt_mgr):
    # Create an expired token manually
    now = int(time.time())
    payload = {
        "sub": "user-expired",
        "token_type": "access",
        "iat": now - 3600,
        "exp": now - 10,
    }
    expired_tok = jwt_mgr.create_token(payload)
    with pytest.raises(Exception) as exc_info:
        jwt_mgr.decode_and_verify(expired_tok, expected_type="access")
    assert "expired" in str(exc_info.value).lower()


def test_jwt_signature_tampering_rejected(jwt_mgr):
    tok = jwt_mgr.create_access_token("user-1", "user@pnm.edu.ph", UserRole.STUDENT)
    parts = tok.split(".")
    tampered = f"{parts[0]}.{parts[1]}.badsignature"
    with pytest.raises(Exception):
        jwt_mgr.decode_and_verify(tampered, expected_type="access")


def test_jwt_refresh_token_lifecycle(jwt_mgr, client):
    refresh_tok = jwt_mgr.create_refresh_token("11111111-1111-1111-1111-111111111111")
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_tok})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_jwt_refresh_token_cannot_access_api(jwt_mgr):
    refresh_tok = jwt_mgr.create_refresh_token("user-1")
    with pytest.raises(Exception):
        jwt_mgr.decode_and_verify(refresh_tok, expected_type="access")


def test_auth_extraction_bearer_header(client):
    # Generate token for Student
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "24-00123",
            "password": "ValidPass2026!#",
            "turnstile_token": "XXXX.DUMMY.PASS",
        },
    )
    token = login_resp.json()["access_token"]

    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["identifier"] == "24-00123"


def test_auth_extraction_http_only_cookie(client):
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "prof.mades@pnm.edu.ph",
            "password": "FacultyPass2026!#",
            "turnstile_token": "XXXX.DUMMY.PASS",
        },
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    client.cookies.set("access_token", token)
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["identifier"] == "prof.mades@pnm.edu.ph"
    client.cookies.clear()


def test_local_login_success_with_turnstile(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "admin@pnm.edu.ph",
            "password": "AdminPass2026!#",
            "turnstile_token": "XXXX.DUMMY.PASS",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["role"] == "ADMIN"


def test_local_login_invalid_password_401(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "admin@pnm.edu.ph",
            "password": "WrongPassword123!",
            "turnstile_token": "XXXX.DUMMY.PASS",
        },
    )
    assert resp.status_code == 401
    assert "does not match our records" in resp.json()["detail"]


def test_local_login_invalid_turnstile_400(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "admin@pnm.edu.ph",
            "password": "AdminPass2026!#",
            "turnstile_token": "test-turnstile-token-fail",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == TURNSTILE_ERROR_MESSAGE


def test_auth_me_endpoint_returns_user(client):
    # Unauthenticated /me
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


# ===========================================================================
# 5. RBAC Route Guard Matrix Tests
# ===========================================================================

def test_rbac_admin_route_allowed_for_admin(client, jwt_mgr):
    token = jwt_mgr.create_access_token("admin-1", "admin@pnm.edu.ph", UserRole.ADMIN)
    # Target downstream mock endpoint via proxy
    resp = client.get(
        "/api/v1/academic/admin/rooms",
        headers={"Authorization": f"Bearer {token}"},
    )
    # When downstream is not running, gateway returns 502 (proving RBAC passed!)
    assert resp.status_code in (200, 502)


def test_rbac_admin_route_forbidden_for_faculty(client, jwt_mgr):
    token = jwt_mgr.create_access_token("fac-1", "prof@pnm.edu.ph", UserRole.FACULTY)
    resp = client.get(
        "/api/v1/academic/admin/rooms",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == FORBIDDEN_ERROR_MESSAGE


def test_rbac_admin_route_forbidden_for_student(client, jwt_mgr):
    token = jwt_mgr.create_access_token("stu-1", "24-00123@student.pnm.edu.ph", UserRole.STUDENT)
    resp = client.post(
        "/api/v1/scheduling/solve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == FORBIDDEN_ERROR_MESSAGE


def test_rbac_faculty_route_allowed_for_faculty(client, jwt_mgr):
    token = jwt_mgr.create_access_token("fac-1", "prof@pnm.edu.ph", UserRole.FACULTY)
    resp = client.get(
        "/api/v1/presence/totp/PRRC-301",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 502)


def test_rbac_faculty_route_allowed_for_admin(client, jwt_mgr):
    token = jwt_mgr.create_access_token("admin-1", "admin@pnm.edu.ph", UserRole.ADMIN)
    resp = client.get(
        "/api/v1/presence/totp/PRRC-301",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 502)


def test_rbac_faculty_route_forbidden_for_student(client, jwt_mgr):
    token = jwt_mgr.create_access_token("stu-1", "24-00123@student.pnm.edu.ph", UserRole.STUDENT)
    resp = client.get(
        "/api/v1/presence/totp/PRRC-301",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == FORBIDDEN_ERROR_MESSAGE


def test_rbac_student_route_allowed_for_student(client, jwt_mgr):
    token = jwt_mgr.create_access_token("stu-1", "24-00123@student.pnm.edu.ph", UserRole.STUDENT)
    resp = client.get(
        "/api/v1/presence/rooms/PRRC-301/vacancies",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 502)


def test_rbac_unauthenticated_request_rejected_401(client):
    resp = client.get("/api/v1/academic/admin/rooms")
    assert resp.status_code == 401
    assert resp.json()["detail"] == UNAUTHORIZED_ERROR_MESSAGE


def test_rbac_plain_language_403_message_exact():
    with pytest.raises(Exception) as exc_info:
        RBACRouteGuard.check_access("/api/v1/academic/admin/departments", UserRole.STUDENT)
    assert exc_info.value.detail == (
        "You do not have access to this portal area. Please contact the Academic Administrator if you need permission."
    )


# ===========================================================================
# 6. Header Sanitization & Downstream Trust Injection Tests
# ===========================================================================

def test_downstream_header_injection_authenticated(jwt_mgr):
    async def _run():
        received_headers = {}

        def mock_handler(request: httpx.Request):
            for k, v in request.headers.items():
                received_headers[k.lower()] = v
            return httpx.Response(200, json={"received": True})

        transport = httpx.MockTransport(mock_handler)
        mock_client = httpx.AsyncClient(transport=transport)

        proxy = ReverseProxyHandler(service_routes={"/api/v1/academic": "http://mock-downstream"})
        
        user_ctx = {
            "sub": "user-uuid-9999",
            "role": "ADMIN",
            "email": "admin@pnm.edu.ph",
        }

        from starlette.requests import Request
        async def empty_receive():
            return {"type": "http.request", "body": b"", "more_body": False}
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/academic/courses",
            "headers": [(b"x-forwarded-for", b"203.0.113.195")],
            "query_string": b"",
        }
        req = Request(scope, receive=empty_receive)

        resp = await proxy.proxy_request(req, mock_client, user_context=user_ctx)
        assert resp.status_code == 200
        assert received_headers.get("x-user-id") == "user-uuid-9999"
        assert received_headers.get("x-user-role") == "ADMIN"
        assert received_headers.get("x-user-email") == "admin@pnm.edu.ph"
        assert received_headers.get("x-forwarded-for") == "203.0.113.195"
    asyncio.run(_run())


def test_downstream_header_spoofing_sanitized():
    async def _run():
        received_headers = {}

        def mock_handler(request: httpx.Request):
            for k, v in request.headers.items():
                received_headers[k.lower()] = v
            return httpx.Response(200, json={"status": "ok"})

        transport = httpx.MockTransport(mock_handler)
        mock_client = httpx.AsyncClient(transport=transport)

        proxy = ReverseProxyHandler(service_routes={"/api/v1/presence": "http://mock-downstream"})

        from starlette.requests import Request
        async def empty_receive():
            return {"type": "http.request", "body": b"", "more_body": False}
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/presence/checkin",
            "headers": [
                (b"x-user-role", b"ADMIN"),
                (b"x-user-id", b"hacked-id"),
                (b"x-forwarded-for", b"198.51.100.1"),
            ],
            "query_string": b"",
        }
        req = Request(scope, receive=empty_receive)

        user_ctx = {
            "sub": "student-real-uuid",
            "role": "STUDENT",
            "email": "24-00123@student.pnm.edu.ph",
        }

        resp = await proxy.proxy_request(req, mock_client, user_context=user_ctx)
        assert resp.status_code == 200
        assert received_headers.get("x-user-role") == "STUDENT"
        assert received_headers.get("x-user-id") == "student-real-uuid"
    asyncio.run(_run())


# ===========================================================================
# 7. Dual-Tier Rate Limiter Tests
# ===========================================================================

def test_token_bucket_general_rate_limit_exceeded(client):
    # Consume 60 general tokens quickly
    for _ in range(60):
        resp = client.get("/health")
        assert resp.status_code == 200

    # 61st request triggers rate limit
    blocked = client.get("/health")
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    assert "Too many requests" in blocked.json()["detail"]


def test_token_bucket_login_brute_force_mitigation(client):
    # 5 failed login attempts
    for _ in range(5):
        resp = client.post(
            "/api/v1/auth/login",
            json={
                "identifier": "admin@pnm.edu.ph",
                "password": "WrongPassword!",
                "turnstile_token": "XXXX.DUMMY.PASS",
            },
        )
        assert resp.status_code == 401

    # 6th attempt within 15 min window must be blocked by rate limiter
    blocked = client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "admin@pnm.edu.ph",
            "password": "WrongPassword!",
            "turnstile_token": "XXXX.DUMMY.PASS",
        },
    )
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


# ===========================================================================
# 8. Security Headers Middleware Tests Across All Status Codes
# ===========================================================================

def _assert_full_security_headers(headers):
    """Assert strict presence of all required production security headers."""
    assert "content-security-policy" in headers
    assert "challenges.cloudflare.com" in headers["content-security-policy"]
    assert "default-src 'self'" in headers["content-security-policy"]
    assert "max-age=31536000" in headers["strict-transport-security"]
    assert "includeSubDomains" in headers["strict-transport-security"]
    assert "preload" in headers["strict-transport-security"]
    assert headers["x-frame-options"] == "DENY"
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "camera=(self)" in headers.get("permissions-policy", "")
    assert headers.get("x-xss-protection") == "1; mode=block"


def test_security_headers_middleware_present(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    _assert_full_security_headers(resp.headers)


def test_security_headers_on_200_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    _assert_full_security_headers(resp.headers)


def test_security_headers_on_401_unauthorized(client):
    # Unauthenticated access to protected admin route yields HTTP 401
    resp = client.get("/api/v1/academic/admin/rooms")
    assert resp.status_code == 401
    _assert_full_security_headers(resp.headers)


def test_security_headers_on_403_forbidden(client, jwt_mgr):
    # Student role accessing admin route yields HTTP 403
    token = jwt_mgr.create_access_token("student-uuid-403", "24-00123@student.pnm.edu.ph", UserRole.STUDENT)
    resp = client.get(
        "/api/v1/academic/admin/rooms",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    _assert_full_security_headers(resp.headers)


def test_security_headers_on_429_too_many_requests(client):
    # Exhaust general rate limit tokens
    for _ in range(60):
        client.get("/health")
    resp = client.get("/health")
    assert resp.status_code == 429
    assert "retry-after" in resp.headers
    _assert_full_security_headers(resp.headers)


def test_security_headers_on_502_bad_gateway(client, jwt_mgr):
    # Admin accessing valid route with offline downstream microservice yields HTTP 502
    token = jwt_mgr.create_access_token("admin-uuid-502", "admin@pnm.edu.ph", UserRole.ADMIN)
    resp = client.get(
        "/api/v1/academic/admin/rooms",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 502
    _assert_full_security_headers(resp.headers)


def test_token_bucket_thread_safety_concurrency():
    """Verify thread-safety of TokenBucket with concurrent worker threads."""
    import concurrent.futures
    bucket = TokenBucket(capacity=50.0, fill_rate=0.0)  # No refill during burst

    def _worker():
        allowed, _ = bucket.consume(1.0)
        return allowed

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(_worker) for _ in range(100)]
        results = [f.result() for f in futures]

    assert results.count(True) == 50
    assert results.count(False) == 50



# ===========================================================================
# 9. Reverse Proxy Downstream 502 Recovery & Health Check
# ===========================================================================

def test_reverse_proxy_downstream_service_unavailable_502(client, jwt_mgr):
    token = jwt_mgr.create_access_token("admin-1", "admin@pnm.edu.ph", UserRole.ADMIN)
    resp = client.get(
        "/api/v1/academic/admin/departments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 502
    assert resp.json()["detail"] == DOWNSTREAM_TIMEOUT_ERROR_MESSAGE


def test_gateway_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "gateway"
    assert data["port"] == 8000
    assert "ClassSync" in data["title"]


# ===========================================================================
# 10. Zero-Regex Architecture AST Audit Test (D-02)
# ===========================================================================

def test_zero_regex_architecture_ast_audit():
    """Verify via Python AST that zero 're' module imports exist in services/gateway."""
    forbidden_imports = []
    gateway_dir = os.path.join("services", "gateway")

    for root, _, files in os.walk(gateway_dir):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8") as fh:
                    tree = ast.parse(fh.read(), filename=path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name == "re" or alias.name.startswith("re."):
                                forbidden_imports.append((path, alias.name))
                    elif isinstance(node, ast.ImportFrom):
                        if node.module == "re" or (node.module and node.module.startswith("re.")):
                            forbidden_imports.append((path, node.module))

    assert (
        len(forbidden_imports) == 0
    ), f"Zero-Regex violation: Found forbidden 're' imports: {forbidden_imports}"
