"""API Endpoints for ClassSync Notification Microservice.
Endpoints:
- POST /api/v1/notification/send-otp
- POST /api/v1/notification/verify-otp
- POST /api/v1/notification/send-email
- GET  /api/v1/notification/health
"""

from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from services.notification.config import settings
from services.notification.brevo_client import BrevoClient
from services.notification.otp import OTPManager
from services.notification.templates import render_otp_email, render_schedule_change_email

logger = logging.getLogger("classync.notification.routes")

notification_router = APIRouter()

otp_manager = OTPManager(
    expiry_seconds=settings.otp_expiry_seconds,
    max_attempts=settings.max_otp_attempts,
)
brevo_client = BrevoClient()


class SendOTPRequestBody(BaseModel):
    email: str
    full_name: Optional[str] = None
    purpose: str = "login"


class SendOTPResponseBody(BaseModel):
    otp_session_id: str
    success: bool
    message: str
    expires_in_seconds: int = 300
    mock: bool = False
    debug_code: Optional[str] = None  # Populated only in mock mode for test automation


class VerifyOTPRequestBody(BaseModel):
    otp_session_id: str
    otp_code: str


class VerifyOTPResponseBody(BaseModel):
    success: bool
    message: str
    email: Optional[str] = None


class SendEmailRequestBody(BaseModel):
    to_email: str
    subject: str
    html_content: str
    to_name: Optional[str] = None


@notification_router.post(
    "/send-otp",
    response_model=SendOTPResponseBody,
    summary="Dispatch 6-Digit OTP via Brevo Email",
)
async def send_otp_endpoint(body: SendOTPRequestBody) -> SendOTPResponseBody:
    """Generate and dispatch a 2FA OTP code to the requested institutional email."""
    email_clean = body.email.strip().lower()

    # 1. Create OTP Session
    session = otp_manager.create_session(email=email_clean, length=settings.otp_length)

    # 2. Render Template
    html = render_otp_email(
        full_name=body.full_name or email_clean,
        otp_code=session.otp_code,
        expiry_minutes=settings.otp_expiry_seconds // 60,
    )

    # 3. Dispatch via Brevo (or mock)
    try:
        await brevo_client.send_transactional_email(
            to_email=email_clean,
            subject="ClassSync • Verification Code",
            html_content=html,
            to_name=body.full_name,
        )
    except Exception as e:
        logger.error(f"Failed to dispatch OTP to {email_clean}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to send verification email. Please try again in a few moments.",
        )

    # In mock mode, expose debug code for test suite assertions
    debug_code = session.otp_code if brevo_client.is_mock_mode else None

    return SendOTPResponseBody(
        otp_session_id=session.session_id,
        success=True,
        message=f"Verification code sent to {email_clean}. Please check your inbox.",
        expires_in_seconds=settings.otp_expiry_seconds,
        mock=brevo_client.is_mock_mode,
        debug_code=debug_code,
    )


@notification_router.post(
    "/verify-otp",
    response_model=VerifyOTPResponseBody,
    summary="Verify OTP Code",
)
async def verify_otp_endpoint(body: VerifyOTPRequestBody) -> VerifyOTPResponseBody:
    """Validate submitted 6-digit OTP code against session."""
    success, message, email = otp_manager.verify_code(
        session_id=body.otp_session_id,
        code=body.otp_code,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
        )

    return VerifyOTPResponseBody(
        success=True,
        message=message,
        email=email,
    )


@notification_router.post(
    "/send-email",
    summary="Dispatch Generic Transactional Email",
)
async def send_email_endpoint(body: SendEmailRequestBody):
    """Send transactional notification email (e.g. schedule revisions, emergency alerts)."""
    try:
        res = await brevo_client.send_transactional_email(
            to_email=body.to_email,
            subject=body.subject,
            html_content=body.html_content,
            to_name=body.to_name,
        )
        return {"status": "dispatched", "details": res}
    except Exception as e:
        logger.error(f"Transactional email delivery error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to dispatch notification email.",
        )
