"""Local and Federated Authentication Routes for ClassSync Gateway.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Endpoints:
- POST /api/v1/auth/verify-turnstile
- POST /api/v1/auth/google-sso
- POST /api/v1/auth/login
- POST /api/v1/auth/login/step1
- POST /api/v1/auth/login/verify-otp
- POST /api/v1/auth/setup-password
- POST /api/v1/auth/refresh
- GET  /api/v1/auth/me
- POST /api/v1/auth/check-password
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from classync_contracts.enums import UserRole
from classync_contracts.schemas import (
    AuthTokenResponse,
    GoogleOAuthTokenRequest,
    LocalLoginRequest,
    LoginStep1Response,
    OTPVerifyRequest,
    PasswordIntegrityResponse,
    PasswordSetupRequest,
    SessionUser,
    TurnstileVerifyRequest,
    TurnstileVerifyResponse,
)

from services.gateway.config import settings
from services.gateway.auth.jwt import JWTManager
from services.gateway.auth.turnstile import CloudflareTurnstileVerifier, TurnstileError
from services.gateway.auth.oauth import (
    GoogleOAuthVerifier,
    OAuthError,
    validate_google_claims,
)
from services.gateway.auth.password import (
    check_password_integrity,
    hash_password,
    validate_password_entropy,
    verify_password,
    PasswordEntropyError,
)
from services.notification.otp import OTPManager
from services.notification.brevo_client import BrevoClient
from services.notification.templates import render_otp_email

auth_router = APIRouter()

jwt_manager = JWTManager(
    secret=settings.jwt_secret,
    algorithm=settings.jwt_algorithm,
    access_exp_minutes=settings.access_token_expire_minutes,
    refresh_exp_days=settings.refresh_token_expire_days,
)

turnstile_verifier = CloudflareTurnstileVerifier(
    secret_key=settings.turnstile_secret_key,
    timeout=settings.turnstile_timeout,
)

oauth_verifier = GoogleOAuthVerifier(
    client_id=settings.google_oauth_client_id,
    timeout=5.0,
)

gateway_otp_manager = OTPManager(
    expiry_seconds=300,
    max_attempts=3,
)
gateway_brevo_client = BrevoClient()


# ---------------------------------------------------------------------------
# In-Memory Credential Store for Gateway Hybrid Authentication (D-07)
# ---------------------------------------------------------------------------

class UserRecord:
    def __init__(
        self,
        user_id: uuid.UUID,
        identifier: str,
        email: str,
        full_name: str,
        role: UserRole,
        password_hash: Optional[str] = None,
        extra_hashes: Optional[List[str]] = None,
        requires_password_change: bool = False,
    ):
        self.user_id = user_id
        self.identifier = identifier
        self.email = email
        self.full_name = full_name
        self.role = role
        self.password_hash = password_hash
        self.extra_hashes = extra_hashes or []
        self.requires_password_change = requires_password_change

    def verify_password(self, plain: str) -> bool:
        if self.password_hash and verify_password(plain, self.password_hash):
            return True
        for h in self.extra_hashes:
            if verify_password(plain, h):
                return True
        return False

    def to_session_user(self) -> SessionUser:
        return SessionUser(
            id=self.user_id,
            identifier=self.identifier,
            full_name=self.full_name,
            role=self.role,
            requires_password_change=self.requires_password_change,
        )


def _init_mock_user_db() -> Dict[str, UserRecord]:
    # Default hashed passwords for mock seed users and official test roles
    student_pw_hash = hash_password("ValidPass2026!#")
    student_alt_hash = hash_password("StudentPass2026!")
    faculty_pw_hash = hash_password("FacultyPass2026!#")
    faculty_alt_hash = hash_password("FacultyPass2026!")
    admin_pw_hash = hash_password("AdminPass2026!#")
    admin_alt_hash = hash_password("CdMAdmin2026!")

    u_student = UserRecord(
        user_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        identifier="24-00123",
        email="24-00123@student.pnm.edu.ph",
        full_name="Juan Dela Cruz",
        role=UserRole.STUDENT,
        password_hash=student_pw_hash,
        extra_hashes=[student_alt_hash],
        requires_password_change=False,
    )

    u_freshie = UserRecord(
        user_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        identifier="24-00999",
        email="24-00999@student.pnm.edu.ph",
        full_name="Freshie Student",
        role=UserRole.STUDENT,
        password_hash=None,
        requires_password_change=True,
    )

    u_faculty = UserRecord(
        user_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        identifier="prof.mades@pnm.edu.ph",
        email="prof.mades@pnm.edu.ph",
        full_name="Prof. Mades",
        role=UserRole.FACULTY,
        password_hash=faculty_pw_hash,
        extra_hashes=[faculty_alt_hash],
        requires_password_change=False,
    )

    u_teacher = UserRecord(
        user_id=uuid.UUID("33333333-3333-3333-3333-333333333302"),
        identifier="teacher@pnm.edu.ph",
        email="teacher@pnm.edu.ph",
        full_name="Prof. Lead Faculty",
        role=UserRole.FACULTY,
        password_hash=faculty_alt_hash,
        extra_hashes=[faculty_pw_hash],
        requires_password_change=False,
    )

    u_ngomez = UserRecord(
        user_id=uuid.UUID("33333333-3333-3333-3333-333333333306"),
        identifier="ngomez@pnm.edu.ph",
        email="ngomez@pnm.edu.ph",
        full_name="Engr. Nathaniel Gomez",
        role=UserRole.FACULTY,
        password_hash=faculty_pw_hash,
        extra_hashes=[faculty_alt_hash],
        requires_password_change=False,
    )

    u_admin = UserRecord(
        user_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        identifier="admin@pnm.edu.ph",
        email="admin@pnm.edu.ph",
        full_name="ClassSync Administrator",
        role=UserRole.ADMIN,
        password_hash=admin_pw_hash,
        extra_hashes=[admin_alt_hash],
        requires_password_change=False,
    )

    # Multi-year cohort mock students (22, 23, 25, 26)
    extra_students = [
        UserRecord(
            user_id=uuid.UUID(f"11111111-1111-1111-1111-1111111111{yr}"),
            identifier=f"{yr}-00123",
            email=f"{yr}-00123@student.pnm.edu.ph",
            full_name=f"Student Cohort 20{yr}",
            role=UserRole.STUDENT,
            password_hash=student_alt_hash,
            extra_hashes=[student_pw_hash],
            requires_password_change=False,
        )
        for yr in ("22", "23", "25", "26")
    ]

    db: Dict[str, UserRecord] = {}
    for u in [u_student, u_freshie, u_faculty, u_teacher, u_ngomez, u_admin] + extra_students:
        db[u.identifier.lower()] = u
        db[u.email.lower()] = u
        db[str(u.user_id)] = u
    return db


USER_DB: Dict[str, UserRecord] = _init_mock_user_db()


def reset_user_db() -> None:
    """Reset the mock database and Turnstile state to initial state (for testing)."""
    global USER_DB
    USER_DB = _init_mock_user_db()
    turnstile_verifier.reset()
    gateway_otp_manager.reset()
    gateway_brevo_client.reset()


def _mask_email(email: str) -> str:
    """Mask email for privacy hints: j***@student.pnm.edu.ph."""
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "***"
    else:
        masked_local = local[0] + "***" + local[-1]
    return f"{masked_local}@{domain}"


# ---------------------------------------------------------------------------
# Endpoint Implementations
# ---------------------------------------------------------------------------

@auth_router.post(
    "/verify-turnstile",
    response_model=TurnstileVerifyResponse,
    summary="Verify Cloudflare Turnstile Token",
)
async def verify_turnstile_endpoint(
    body: TurnstileVerifyRequest,
    request: Request,
) -> TurnstileVerifyResponse:
    """Verify Cloudflare Turnstile token from client widget."""
    client_ip = request.headers.get("x-forwarded-for") or (
        request.client.host if request.client else None
    )
    res = await turnstile_verifier.verify(token=body.token, remote_ip=client_ip)
    return res.to_contract()


@auth_router.post(
    "/google-sso",
    response_model=AuthTokenResponse,
    summary="Google Workspace SSO Login",
)
async def google_sso_endpoint(
    body: GoogleOAuthTokenRequest,
    response: Response,
    request: Request,
) -> AuthTokenResponse:
    """Authenticate or register user via Google Workspace OAuth ID token."""
    try:
        claims = await oauth_verifier.verify_id_token(body.id_token)
    except OAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google authentication failed. Please sign in again.",
        )

    # Resolve or create user record
    lookup_key = claims.email.lower()
    user = USER_DB.get(lookup_key) or USER_DB.get(claims.identifier.lower())

    if user is None:
        # First time login via Google Workspace
        user = UserRecord(
            user_id=uuid.uuid4(),
            identifier=claims.identifier,
            email=claims.email,
            full_name=claims.name or claims.email.split("@")[0],
            role=claims.role,
            password_hash=None,
            requires_password_change=True,
        )
        USER_DB[user.identifier.lower()] = user
        USER_DB[user.email.lower()] = user
        USER_DB[str(user.user_id)] = user

    access_token = jwt_manager.create_access_token(
        user_id=str(user.user_id),
        email=user.email,
        role=user.role.value,
        hd=claims.hd,
        requires_password_change=user.requires_password_change,
        full_name=user.full_name,
    )
    refresh_token = jwt_manager.create_refresh_token(user_id=str(user.user_id))

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
    )

    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user.to_session_user(),
    )


@auth_router.post(
    "/login",
    response_model=AuthTokenResponse,
    summary="Local Credentials Login with Turnstile",
)
async def local_login_endpoint(
    body: LocalLoginRequest,
    response: Response,
    request: Request,
) -> AuthTokenResponse:
    """Authenticate with identifier (Student ID or institutional email) and password."""
    # 1. Turnstile Verification
    client_ip = request.headers.get("x-forwarded-for") or (
        request.client.host if request.client else None
    )
    turn_res = await turnstile_verifier.verify(token=body.turnstile_token, remote_ip=client_ip)
    if not turn_res.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=turn_res.user_message
            or "Human verification check could not be completed. Please tap the verification checkbox and try again.",
        )

    # 2. Identifier Lookup
    lookup_key = body.identifier.strip().lower()
    user = USER_DB.get(lookup_key)
    if user is None or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The email/ID or password you entered does not match our records. Please double-check and try again.",
        )

    # 3. Constant-time Argon2id Verification
    if not user.verify_password(body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The email/ID or password you entered does not match our records. Please double-check and try again.",
        )

    # 4. Issue Tokens
    access_token = jwt_manager.create_access_token(
        user_id=str(user.user_id),
        email=user.email,
        role=user.role.value,
        requires_password_change=user.requires_password_change,
        full_name=user.full_name,
    )
    refresh_token = jwt_manager.create_refresh_token(user_id=str(user.user_id))

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
    )

    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user.to_session_user(),
    )


@auth_router.post(
    "/login/step1",
    response_model=LoginStep1Response,
    summary="2FA Step 1: Validate Credentials and Send Brevo Email OTP",
)
async def login_step1_endpoint(
    body: LocalLoginRequest,
    request: Request,
) -> LoginStep1Response:
    """Validate Turnstile and credentials, then dispatch a 6-digit verification code via Brevo."""
    client_ip = request.headers.get("x-forwarded-for") or (
        request.client.host if request.client else None
    )
    turn_res = await turnstile_verifier.verify(token=body.turnstile_token, remote_ip=client_ip)
    if not turn_res.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=turn_res.user_message
            or "Human verification check could not be completed. Please tap the verification checkbox and try again.",
        )

    lookup_key = body.identifier.strip().lower()
    user = USER_DB.get(lookup_key)
    if user is None or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The email/ID or password you entered does not match our records. Please double-check and try again.",
        )

    if not user.verify_password(body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The email/ID or password you entered does not match our records. Please double-check and try again.",
        )

    otp_session = gateway_otp_manager.create_session(email=user.email, length=6)
    html = render_otp_email(full_name=user.full_name, otp_code=otp_session.otp_code, expiry_minutes=5)
    await gateway_brevo_client.send_transactional_email(
        to_email=user.email,
        subject="ClassSync • Verification Code",
        html_content=html,
        to_name=user.full_name,
    )

    masked = _mask_email(user.email)
    return LoginStep1Response(
        otp_session_id=otp_session.session_id,
        message=f"A 6-digit verification code was sent to {masked}. Enter it below to complete sign in.",
        email_hint=masked,
        requires_otp=True,
    )


@auth_router.post(
    "/login/verify-otp",
    response_model=AuthTokenResponse,
    summary="2FA Step 2: Verify Brevo OTP and Issue Session Tokens",
)
async def login_verify_otp_endpoint(
    body: OTPVerifyRequest,
    response: Response,
) -> AuthTokenResponse:
    """Verify submitted 6-digit OTP code and issue JWT access/refresh tokens."""
    success, message, email = gateway_otp_manager.verify_code(
        session_id=body.otp_session_id,
        code=body.otp_code,
    )
    if not success or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
        )

    user = USER_DB.get(email.lower())
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account matching this verification session could not be found.",
        )

    access_token = jwt_manager.create_access_token(
        user_id=str(user.user_id),
        email=user.email,
        role=user.role.value,
        requires_password_change=user.requires_password_change,
        full_name=user.full_name,
    )
    refresh_token = jwt_manager.create_refresh_token(user_id=str(user.user_id))

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
    )

    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user.to_session_user(),
    )


@auth_router.post(
    "/setup-password",
    response_model=AuthTokenResponse,
    summary="First-time Password Setup (ASVS 4.0 & D-07)",
)
async def setup_password_endpoint(
    body: PasswordSetupRequest,
    response: Response,
    request: Request,
) -> AuthTokenResponse:
    """Setup password for first-time login under OWASP ASVS 4.0 entropy rules."""
    # 1. Check Passwords Match
    if body.new_password != body.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The passwords you entered do not match. Please re-enter them carefully.",
        )

    # 2. Entropy and Institutional Check
    try:
        validate_password_entropy(body.new_password, identifier=body.student_or_employee_id)
    except PasswordEntropyError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        )

    # 3. Locate User
    lookup_key = body.student_or_employee_id.strip().lower()
    user = USER_DB.get(lookup_key)

    if user is None:
        # Create record if not found (e.g. initial student registration for cohorts 20-99)
        is_student = (
            len(lookup_key) == 8
            and lookup_key[:2].isdigit()
            and int(lookup_key[:2]) >= 20
            and lookup_key[2] == "-"
            and all(48 <= ord(c) <= 57 for c in lookup_key[3:])
        )
        user = UserRecord(
            user_id=uuid.uuid4(),
            identifier=lookup_key,
            email=f"{lookup_key}@student.pnm.edu.ph" if is_student else lookup_key,
            full_name=lookup_key,
            role=UserRole.STUDENT if is_student else UserRole.FACULTY,
            requires_password_change=False,
        )
        USER_DB[user.identifier.lower()] = user
        USER_DB[user.email.lower()] = user
        USER_DB[str(user.user_id)] = user

    # 4. Hash and Commit
    user.password_hash = hash_password(body.new_password)
    user.requires_password_change = False

    # 5. Issue Full Unrestricted Tokens
    access_token = jwt_manager.create_access_token(
        user_id=str(user.user_id),
        email=user.email,
        role=user.role.value,
        requires_password_change=False,
        full_name=user.full_name,
    )
    refresh_token = jwt_manager.create_refresh_token(user_id=str(user.user_id))

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )

    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user.to_session_user(),
    )


class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None


@auth_router.post(
    "/refresh",
    response_model=AuthTokenResponse,
    summary="Refresh Access Token",
)
async def refresh_endpoint(
    response: Response,
    request: Request,
    body: Optional[RefreshTokenRequest] = None,
) -> AuthTokenResponse:
    """Exchange a valid refresh token for a fresh 15-minute access token."""
    refresh_token = None
    if body and body.refresh_token:
        refresh_token = body.refresh_token.strip()
    if not refresh_token:
        refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token. Please sign in again.",
        )

    claims = jwt_manager.decode_and_verify(refresh_token, expected_type="refresh")
    user_id = claims.get("sub")
    user = USER_DB.get(str(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
        )

    access_token = jwt_manager.create_access_token(
        user_id=str(user.user_id),
        email=user.email,
        role=user.role.value,
        requires_password_change=user.requires_password_change,
        full_name=user.full_name,
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )

    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user.to_session_user(),
    )


@auth_router.get(
    "/me",
    response_model=SessionUser,
    summary="Get Current Authenticated User",
)
async def me_endpoint(request: Request) -> SessionUser:
    """Retrieve profile of the currently signed-in user."""
    token = jwt_manager.extract_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please sign in to access this portal area.",
        )

    claims = jwt_manager.decode_and_verify(token, expected_type="access")
    user_id = claims.get("sub")
    user = USER_DB.get(str(user_id))
    if not user:
        return SessionUser(
            id=uuid.UUID(str(user_id)) if len(str(user_id)) == 36 else uuid.uuid4(),
            identifier=claims.get("email", ""),
            full_name=claims.get("name", claims.get("email", "")),
            role=UserRole(claims.get("role", "STUDENT")),
            requires_password_change=claims.get("requires_password_change", False),
        )

    return user.to_session_user()


class PasswordCheckRequest(BaseModel):
    password: str
    identifier: Optional[str] = None


@auth_router.post(
    "/check-password",
    response_model=PasswordIntegrityResponse,
    summary="Check Password Entropy (Real-time Feedback)",
)
def check_password_endpoint(body: PasswordCheckRequest) -> PasswordIntegrityResponse:
    """Non-raising endpoint for live frontend password complexity indicators."""
    return check_password_integrity(body.password, identifier=body.identifier)
