"""FastAPI Application for ClassSync Transactional Notification Microservice.
Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System
Port: 8003
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.notification.routes import notification_router

app = FastAPI(
    title="ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System - Notification Service",
    description="Brevo Email & 2FA OTP Verification Microservice on Port 8003.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(notification_router, prefix="/api/v1/notification", tags=["Notification"])


@app.get("/health", tags=["Monitoring"])
def health_check():
    return {
        "status": "healthy",
        "service": "notification",
        "port": 8003,
        "title": "ClassSync: AI-Powered University Classroom Scheduling, Availability Monitoring, and Conflict Detection System",
    }
