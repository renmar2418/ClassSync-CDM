"""Brevo (Sendinblue) Transactional Email Dispatcher.
Supports real Brevo REST API v3 and seamless local development mock mode.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import httpx

from services.notification.config import settings

logger = logging.getLogger("classync.notification.brevo")


class BrevoClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        sender_email: Optional[str] = None,
        sender_name: Optional[str] = None,
    ):
        self.api_key = api_key or settings.brevo_api_key
        self.api_url = api_url or settings.brevo_api_url
        self.sender_email = sender_email or settings.sender_email
        self.sender_name = sender_name or settings.sender_name

        # Test audit log (captures dispatched messages in test/mock mode)
        self.dispatched_messages: List[Dict[str, Any]] = []

    @property
    def is_mock_mode(self) -> bool:
        return not bool(self.api_key and self.api_key.strip())

    async def send_transactional_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        to_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatch a single transactional email via Brevo or mock logger."""
        recipient = {"email": to_email}
        if to_name:
            recipient["name"] = to_name

        payload = {
            "sender": {"name": self.sender_name, "email": self.sender_email},
            "to": [recipient],
            "subject": subject,
            "htmlContent": html_content,
        }

        # Record for telemetry and test inspection
        self.dispatched_messages.append({
            "to_email": to_email,
            "subject": subject,
            "html": html_content,
            "is_mock": self.is_mock_mode,
        })

        if self.is_mock_mode:
            logger.info(
                f"[BREVO MOCK MODE] Email successfully queued for {to_email}. "
                f"Subject: '{subject}'"
            )
            return {
                "messageId": f"mock-msg-{len(self.dispatched_messages)}",
                "status": "success",
                "mock": True,
            }

        headers = {
            "accept": "application/json",
            "api-key": self.api_key,
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(self.api_url, headers=headers, json=payload)
            if response.status_code >= 400:
                logger.error(
                    f"Brevo API error: {response.status_code} - {response.text}"
                )
                raise RuntimeError(
                    f"Brevo delivery failure ({response.status_code}): {response.text}"
                )
            return response.json()

    def get_last_sent_otp_for(self, email: str) -> Optional[str]:
        """Helper for test runners to retrieve the most recent OTP sent to an email."""
        for msg in reversed(self.dispatched_messages):
            if msg["to_email"].lower() == email.lower():
                # Extract code from the HTML or recorded payload
                html = msg["html"]
                # 6 digits centered
                import re
                match = re.search(r'>\s*([0-9]{6})\s*<', html)
                if match:
                    return match.group(1)
        return None

    def reset(self) -> None:
        """Clear audit history (for tests)."""
        self.dispatched_messages.clear()
