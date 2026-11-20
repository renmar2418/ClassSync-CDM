"""Real-Time Server-Sent Events (SSE) Vacancy Stream for ClassSync.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Specifications:
- Fast Server-Sent Events architecture using asyncio.Queue fanout
- Event formatting strictly adhering to W3C SSE standard: 'event: <type>\ndata: <json>\n\n'
- Supported broadcast event types:
  * initial_state: Full room workstation grid snapshot upon client connection
  * occupancy_update: Instantaneous push on check-in / checkout with updated counts and vacant_rate
  * presence_logged: Student ID, workstation number, and timestamp
  * heartbeat: Keep-alive ping every 15s to prevent cellular gateway timeout
- Graceful client disconnect handling without socket or queue leaks
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict
from typing import Any, AsyncGenerator, Dict, Optional, Set
from starlette.requests import Request


def format_sse(event: str, data: Any, event_id: Optional[str] = None) -> str:
    """Formats payload strictly adhering to the W3C Server-Sent Events specification.

    Format:
    [id: <event_id>\n]
    event: <event_type>\n
    data: <json_string>\n\n
    """
    lines = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    if isinstance(data, (dict, list)):
        payload = json.dumps(data, separators=(",", ":"))
    else:
        payload = str(data)
    lines.append(f"data: {payload}")
    return "\n".join(lines) + "\n\n"


class SSEBroadcaster:
    """Manages real-time pub/sub event fanout to SSE connected clients."""

    def __init__(self, heartbeat_interval: float = 15.0):
        self.heartbeat_interval = heartbeat_interval
        self._listeners: Dict[str, Set[asyncio.Queue]] = defaultdict(set)
        self._lock = asyncio.Lock()

    def get_listener_count(self, room_code: str) -> int:
        """Returns the number of active listeners for a room."""
        return len(self._listeners.get(room_code, set()))

    async def subscribe(self, room_code: str) -> asyncio.Queue:
        """Registers a new client listener queue for the specified room."""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._listeners[room_code].add(q)
        return q

    async def unsubscribe(self, room_code: str, q: asyncio.Queue) -> None:
        """Removes client queue from room listeners to prevent socket/memory leaks."""
        async with self._lock:
            if room_code in self._listeners:
                self._listeners[room_code].discard(q)
                if not self._listeners[room_code]:
                    del self._listeners[room_code]

    async def broadcast(self, room_code: str, event_type: str, data: Dict[str, Any]) -> None:
        """Pushes an event to all subscribers registered for room_code."""
        formatted = format_sse(event_type, data)
        async with self._lock:
            queues = list(self._listeners.get(room_code, set()))

        for q in queues:
            try:
                q.put_nowait(formatted)
            except asyncio.QueueFull:
                # Discard oldest message to prevent blocking the event loop
                try:
                    q.get_nowait()
                    q.put_nowait(formatted)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass

    async def event_generator(
        self,
        room_code: str,
        initial_data: Dict[str, Any],
        request: Optional[Request] = None,
        once: bool = False,
    ) -> AsyncGenerator[str, None]:
        """Asynchronous generator yielding formatted SSE events.

        Yields:
        1. initial_state immediately on connection
        2. Dynamic state transitions (occupancy_update, presence_logged)
        3. Periodic heartbeats every 15s to maintain cellular NAT mappings
        """
        q = await self.subscribe(room_code)
        try:
            # Step 1: Yield full initial state grid snapshot
            yield format_sse("initial_state", initial_data)
            if once or (request is not None and request.query_params.get("once", "").lower() in ("true", "1")):
                return

            # Step 2: Stream loop
            while True:
                # Check for client disconnect
                if request is not None and await request.is_disconnected():
                    break

                try:
                    # Wait for broadcast message or heartbeat timeout
                    msg = await asyncio.wait_for(q.get(), timeout=self.heartbeat_interval)
                    yield msg
                except asyncio.TimeoutError:
                    # Heartbeat keep-alive ping
                    yield format_sse(
                        "heartbeat",
                        {"timestamp": int(time.time()), "room_code": room_code},
                    )
        except asyncio.CancelledError:
            # Client disconnected or stream aborted
            pass
        finally:
            # Step 3: Guaranteed resource reclamation
            await self.unsubscribe(room_code, q)
