"""Presence SSE Package for ClassSync.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System
"""

from services.presence.sse.stream import SSEBroadcaster, format_sse

__all__ = ["SSEBroadcaster", "format_sse"]
