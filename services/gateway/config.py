"""Configuration settings for ClassSync Gateway Microservice.
Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System
Port: 8000
"""

from __future__ import annotations

import os
from typing import Optional, Tuple
from pydantic import BaseModel, Field


class GatewaySettings(BaseModel):
    service_name: str = "gateway"
    port: int = 8000
    host: str = "0.0.0.0"

    # Microservice Downstream URLs
    academic_service_url: str = Field(
        default_factory=lambda: os.getenv("ACADEMIC_SERVICE_URL", "http://localhost:8001")
    )
    scheduling_service_url: str = Field(
        default_factory=lambda: os.getenv("SCHEDULING_SERVICE_URL", "http://localhost:8002")
    )
    presence_service_url: str = Field(
        default_factory=lambda: os.getenv("PRESENCE_SERVICE_URL", "http://localhost:8004")
    )
    notification_service_url: str = Field(
        default_factory=lambda: os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8003")
    )

    # JWT Configuration
    jwt_secret: str = Field(
        default_factory=lambda: os.getenv(
            "JWT_SECRET_KEY", "classsync-zero-trust-hs256-production-secret-min32bytes!"
        )
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Cloudflare Turnstile Configuration
    turnstile_secret_key: str = Field(
        default_factory=lambda: os.getenv(
            "TURNSTILE_SECRET_KEY",
            os.getenv("CLOUDFLARE_TURNSTILE_SECRET_KEY", "1x0000000000000000000000000000000AA"),
        )
    )
    turnstile_verify_url: str = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    turnstile_timeout: float = 5.0

    # Google Workspace OAuth Configuration
    google_oauth_client_id: Optional[str] = Field(
        default_factory=lambda: os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    )
    google_tokeninfo_url: str = "https://oauth2.googleapis.com/tokeninfo"

    # Institutional Domains & Admin Roles
    allowed_domains: Tuple[str, ...] = ("student.pnm.edu.ph", "pnm.edu.ph")
    student_domain: str = "student.pnm.edu.ph"
    faculty_domain: str = "pnm.edu.ph"
    admin_emails: Tuple[str, ...] = (
        "admin@pnm.edu.ph",
        "ics.chair@pnm.edu.ph",
        "registrar@pnm.edu.ph",
    )


settings = GatewaySettings()
