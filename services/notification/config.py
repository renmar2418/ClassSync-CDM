"""Configuration settings for ClassSync Notification Microservice (Brevo + OTP).
Port: 8003
"""

from __future__ import annotations

import os
from typing import Optional
from pydantic import BaseModel, Field


class NotificationSettings(BaseModel):
    service_name: str = "notification"
    port: int = 8003
    host: str = "0.0.0.0"

    # Brevo API Configuration
    brevo_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("BREVO_API_KEY")
    )
    brevo_api_url: str = "https://api.brevo.com/v3/smtp/email"
    sender_email: str = Field(
        default_factory=lambda: os.getenv("BREVO_SENDER_EMAIL", "noreply@pnm.edu.ph")
    )
    sender_name: str = "ClassSync Notification Service"

    # OTP Parameters
    otp_expiry_seconds: int = 300  # 5 minutes
    max_otp_attempts: int = 3
    otp_length: int = 6

    # Operational Mock Mode (activates when BREVO_API_KEY is not set)
    @property
    def is_mock_mode(self) -> bool:
        return not bool(self.brevo_api_key and self.brevo_api_key.strip())


settings = NotificationSettings()
