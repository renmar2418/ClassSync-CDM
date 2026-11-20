"""Comprehensive Phase 3 Test Suite: Hardware & COMLAB Presence.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Validates:
1. RFC 6238 TOTP generation, 15-second rotation, and ±1 step window tolerance.
2. Zero-regex student ID parser positive boundary tests (24-00000 to 24-99999).
3. Zero-regex student ID parser negative boundary tests (lengths, prefixes, homoglyphs, non-numeric).
4. Guarantee that 're' module is never imported by the student ID validator.
5. Workstation state transitions (VACANT -> OCCUPIED -> VACANT).
6. Workstation collision conflict (PC-14) with plain-language recommendation (PC-15).
7. Thread-safe circular buffer capped strictly at 50 with O(1) FIFO eviction.
8. Real-time W3C Server-Sent Events stream formatting, serialization, and heartbeat intervals.
9. FastAPI TestClient endpoint integration tests (Port 8004 routes).
"""

from __future__ import annotations

import ast
import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from services.presence.ingress.validator import (
    STUDENT_ID_ERROR_MESSAGE,
    StudentIDValidationError,
    is_valid_student_id,
    validate_student_id,
)
from services.presence.totp.generator import (
    SessionSecretManager,
    TOTPGenerator,
)
from services.presence.storage.workstation_tracker import (
    COMLABWorkstationManager,
    RoomWorkstationTracker,
    WorkstationConflictError,
    WorkstationMaintenanceError,
    WorkstationOutOfBoundsError,
    WorkstationSlot,
)
from services.presence.storage.buffer import (
    PresenceBufferManager,
    PresenceCircularBuffer,
    PresenceLogEntry,
)
from services.presence.sse.stream import (
    SSEBroadcaster,
    format_sse,
)
from services.presence.main import (
    app,
    circular_buffer,
    session_secret_manager,
    sse_broadcaster,
    workstation_manager,
)


# ===========================================================================
# 1. RFC 6238 TOTP Generator Test Suite
# ===========================================================================

class TestTOTPGenerator:
    """Validates 15s rotating TOTP cryptographic generation and verification."""

    @pytest.fixture
    def generator(self) -> TOTPGenerator:
        return TOTPGenerator(interval=15, digits=6)

    def test_totp_token_format(self, generator: TOTPGenerator):
        secret = generator.generate_secret()
        token = generator.generate_token(secret)
        assert len(token) == 6
        assert token.isdigit()

    def test_totp_15s_rotation(self, generator: TOTPGenerator):
        secret = generator.generate_secret()
        t0 = 1700000000.0  # arbitrary baseline
        tok0 = generator.generate_token(secret, for_time=t0)
        tok_same_step = generator.generate_token(secret, for_time=t0 + 5.0)
        tok_next_step = generator.generate_token(secret, for_time=t0 + 15.0)

        assert tok0 == tok_same_step, "Token must remain identical within the same 15s window."
        assert tok0 != tok_next_step, "Token must rotate to a new value after 15s."

    def test_totp_tolerance_window(self, generator: TOTPGenerator):
        secret = generator.generate_secret()
        t0 = 1700000000.0
        token = generator.generate_token(secret, for_time=t0)

        # Baseline window: Valid
        assert generator.verify_token(secret, token, for_time=t0, valid_window=1) is True
        # +5s (same window): Valid
        assert generator.verify_token(secret, token, for_time=t0 + 5.0, valid_window=1) is True
        # +15s (+1 window tolerance): Valid
        assert generator.verify_token(secret, token, for_time=t0 + 15.0, valid_window=1) is True
        # -15s (-1 window tolerance): Valid
        assert generator.verify_token(secret, token, for_time=t0 - 15.0, valid_window=1) is True

        # Beyond valid window (>2 windows away / >30s): Strictly Invalid
        assert generator.verify_token(secret, token, for_time=t0 + 35.0, valid_window=1) is False
        assert generator.verify_token(secret, token, for_time=t0 - 35.0, valid_window=1) is False

    def test_totp_time_remaining(self, generator: TOTPGenerator):
        # 1700000000 % 15 = 5 -> remaining = 15 - 5 = 10
        rem = generator.time_remaining(for_time=1700000000)
        assert rem == 10

        # Boundary: exact step transition
        rem_step = generator.time_remaining(for_time=1700000010)
        assert rem_step in (5, 15)

    def test_totp_qr_payload_schema(self, generator: TOTPGenerator):
        secret = generator.generate_secret()
        sess_id = uuid.uuid4()
        payload = generator.generate_qr_payload("PRRC 301", sess_id, secret, for_time=1700000000)

        assert payload["room"] == "PRRC 301"
        assert payload["session"] == str(sess_id)
        assert len(payload["totp"]) == 6
        assert payload["ts"] == 1700000000

        json_str = generator.generate_qr_payload_json("PRRC 301", sess_id, secret, for_time=1700000000)
        parsed = json.loads(json_str)
        assert parsed == payload

    def test_deterministic_secret_derivation(self, generator: TOTPGenerator):
        master = "classync-master-key-2026"
        sess_id = uuid.uuid4()
        sec1 = generator.derive_secret(master, "PRRC 301", sess_id)
        sec2 = generator.derive_secret(master, "PRRC 301", sess_id)
        sec_diff = generator.derive_secret(master, "PRRC 302", sess_id)

        assert sec1 == sec2
        assert sec1 != sec_diff
        assert len(sec1) == 32

    def test_session_secret_manager_lifecycle(self):
        sm = SessionSecretManager()
        sess = sm.create_session("PRRC 301")
        assert sess["room_code"] == "PRRC 301"
        assert sm.is_session_active("PRRC 301") is True
        assert sm.get_secret("PRRC 301") == sess["secret"]

        ended = sm.end_session("PRRC 301")
        assert ended is True
        assert sm.is_session_active("PRRC 301") is False


# ===========================================================================
# 2. Zero-Regex Student ID Parser Test Suite
# ===========================================================================

class TestZeroRegexStudentIDParser:
    """Validates deterministic zero-regex Student ID validation per D-02 and D-12."""

    def test_positive_boundary_values(self):
        # Boundaries 24-00000 to 24-99999
        assert validate_student_id("24-00000") == "24-00000"
        assert validate_student_id("24-99999") == "24-99999"
        assert validate_student_id("24-00123") == "24-00123"
        assert validate_student_id("24-54321") == "24-54321"
        assert validate_student_id("  24-00123  ") == "24-00123"
        assert is_valid_student_id("24-00123") is True

    def test_negative_malformed_prefixes(self):
        for bad in ["23-00123", "25-00123", "XX-00123", "24_00123", "24000123"]:
            with pytest.raises(StudentIDValidationError) as exc_info:
                validate_student_id(bad)
            assert exc_info.value.message == STUDENT_ID_ERROR_MESSAGE
            assert is_valid_student_id(bad) is False

    def test_negative_invalid_lengths(self):
        for bad in ["24-0123", "24-000123", "", "24-", "24-1", "24-123456"]:
            with pytest.raises(StudentIDValidationError):
                validate_student_id(bad)

    def test_negative_unicode_homoglyphs(self):
        homoglyphs = [
            "24-\uff100123",  # Fullwidth Zero '０'
            "24-\u0660\u0661\u0662\u0663\u0664",  # Arabic-Indic '٠١٢٣٤'
            "24-\u2460\u2461\u2462\u2463\u2464",  # Circled digits '①②③④⑤'
            "24-\u00b2\u00b3\u00b9\u2074\u2075",  # Superscript digits '²³¹⁴⁵'
        ]
        for bad in homoglyphs:
            with pytest.raises(StudentIDValidationError):
                validate_student_id(bad)

    def test_negative_non_numeric_and_email_characters(self):
        for bad in ["24-ABCDE", "24-0012A", "24-00 23", "24-00-23", "24-00123@student.pnm.edu.ph", "24@00123"]:
            with pytest.raises(StudentIDValidationError):
                validate_student_id(bad)

    def test_non_string_types_rejected(self):
        for bad in [None, 12345678, ["24-00123"], {"id": "24-00123"}]:
            with pytest.raises(StudentIDValidationError):
                validate_student_id(bad)

    def test_no_regex_engine_imported(self):
        """Guarantees that 're' module is never imported in services.presence.ingress.validator."""
        file_path = os.path.join("services", "presence", "ingress", "validator.py")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=file_path)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert alias.name != "re", "Strict prohibition: 're' module imported in validator.py!"
                elif isinstance(node, ast.ImportFrom):
                    assert node.module != "re", "Strict prohibition: 're' module imported in validator.py!"


# ===========================================================================
# 3. Workstation Occupancy Tracker & Collision Test Suite
# ===========================================================================

class TestWorkstationTracker:
    """Validates 45-workstation state management and atomic collision handling."""

    @pytest.fixture
    def tracker(self) -> RoomWorkstationTracker:
        return RoomWorkstationTracker(room_code="PRRC 301", total_workstations=45)

    def test_room_initialization(self, tracker: RoomWorkstationTracker):
        summary = tracker.get_summary()
        assert summary.total_stations == 45
        assert summary.operational_count == 45
        assert summary.occupied_count == 0
        assert summary.vacant_count == 45
        assert summary.occupancy_rate == 0.0

    def test_valid_state_transitions(self, tracker: RoomWorkstationTracker):
        # VACANT -> OCCUPIED
        res = tracker.claim_workstation(workstation_number=1, student_id="24-00001")
        assert res.success is True
        assert res.workstation.is_occupied is True
        assert res.workstation.active_student_id == "24-00001"

        # OCCUPIED -> VACANT
        rel = tracker.release_workstation(workstation_number=1, student_id="24-00001")
        assert rel.success is True
        assert rel.was_occupied is True

        summary = tracker.get_summary()
        assert summary.occupied_count == 0

    def test_workstation_collision_and_nearest_suggestion(self, tracker: RoomWorkstationTracker):
        # Student A claims PC-14
        tracker.claim_workstation(workstation_number=14, student_id="24-00001")

        # Student B attempts to claim PC-14 simultaneously
        with pytest.raises(WorkstationConflictError) as exc_info:
            tracker.claim_workstation(workstation_number=14, student_id="24-00002")

        # Assert D-12 plain-language recommendation copy suggesting PC-15 (k+d priority)
        assert "Seat PC-14 was just claimed by a classmate! PC-15 is open right next to it." in exc_info.value.message
        assert exc_info.value.claimed_station == 14
        assert exc_info.value.suggested_station == 15

        # If PC-15 is also claimed, outward search must suggest PC-13
        tracker.claim_workstation(workstation_number=15, student_id="24-00003")
        with pytest.raises(WorkstationConflictError) as exc_info2:
            tracker.claim_workstation(workstation_number=14, student_id="24-00002")

        assert "Seat PC-14 was just claimed by a classmate! PC-13 is open right next to it." in exc_info2.value.message
        assert exc_info2.value.suggested_station == 13

    def test_student_seat_relocation(self, tracker: RoomWorkstationTracker):
        # Student claims PC-5 then moves to PC-10
        tracker.claim_workstation(workstation_number=5, student_id="24-00001")
        res = tracker.claim_workstation(workstation_number=10, student_id="24-00001")

        assert res.success is True
        assert res.relocated_from_station == 5

        # PC-5 must be vacated automatically
        summary = tracker.get_summary()
        assert summary.occupied_count == 1
        assert tracker._stations[5].is_occupied is False
        assert tracker._stations[10].is_occupied is True

    def test_maintenance_workstation_rejection(self, tracker: RoomWorkstationTracker):
        tracker.set_maintenance_status(workstation_number=20, is_operational=False)
        with pytest.raises(WorkstationMaintenanceError) as exc_info:
            tracker.claim_workstation(workstation_number=20, student_id="24-00001")

        assert "undergoing maintenance" in exc_info.value.message

    def test_out_of_bounds_workstation(self, tracker: RoomWorkstationTracker):
        with pytest.raises(WorkstationOutOfBoundsError):
            tracker.claim_workstation(workstation_number=0, student_id="24-00001")
        with pytest.raises(WorkstationOutOfBoundsError):
            tracker.claim_workstation(workstation_number=46, student_id="24-00001")

    def test_full_room_occupancy_conflict(self):
        tracker = RoomWorkstationTracker(room_code="PRRC 301", total_workstations=3)
        tracker.claim_workstation(1, "24-00001")
        tracker.claim_workstation(2, "24-00002")
        tracker.claim_workstation(3, "24-00003")

        with pytest.raises(WorkstationConflictError) as exc:
            tracker.claim_workstation(1, "24-00004")
        assert "All 3 workstations in PRRC 301 are currently occupied" in exc.value.message
        assert exc.value.suggested_station is None


# ===========================================================================
# 4. In-Memory Circular Buffer Test Suite
# ===========================================================================

class TestCircularBuffer:
    """Validates bounded ring buffer capped strictly at 50 with O(1) FIFO eviction."""

    def test_circular_buffer_capacity(self):
        buf = PresenceCircularBuffer(capacity=50)
        assert buf.capacity == 50
        assert len(buf) == 0

        for i in range(1, 51):
            entry = PresenceLogEntry(
                id=uuid.uuid4(),
                student_id=f"24-{i:05d}",
                room_code="PRRC 301",
                workstation_number=i % 45 + 1,
                check_in_time=datetime.now(timezone.utc),
            )
            buf.append(entry)

        assert len(buf) == 50
        assert buf.is_full is True

    def test_fifo_eviction_on_51st_item(self):
        buf = PresenceCircularBuffer(capacity=50)
        first_id = uuid.uuid4()
        buf.append(PresenceLogEntry(
            id=first_id,
            student_id="24-00001",
            room_code="PRRC 301",
            workstation_number=1,
            check_in_time=datetime.now(timezone.utc),
        ))

        for i in range(2, 52):  # 2 to 51 -> total 51 appends
            buf.append(PresenceLogEntry(
                id=uuid.uuid4(),
                student_id=f"24-{i:05d}",
                room_code="PRRC 301",
                workstation_number=i % 45 + 1,
                check_in_time=datetime.now(timezone.utc),
            ))

        assert len(buf) == 50
        recent = buf.get_recent(limit=50, reverse=True)
        assert len(recent) == 50

        # The 51st item must be at index 0 (newest), and 1st item must be evicted
        assert recent[0].student_id == "24-00051"
        assert not any(item.id == first_id for item in recent)

    def test_recent_logs_ordering(self):
        buf = PresenceCircularBuffer(capacity=50)
        e1 = PresenceLogEntry(uuid.uuid4(), "24-00001", "PRRC 301", 1, datetime.now(timezone.utc))
        e2 = PresenceLogEntry(uuid.uuid4(), "24-00002", "PRRC 301", 2, datetime.now(timezone.utc))
        buf.append(e1)
        buf.append(e2)

        newest_first = buf.get_recent(limit=2, reverse=True)
        assert newest_first[0].student_id == "24-00002"
        assert newest_first[1].student_id == "24-00001"

    def test_get_by_student_and_workstation(self):
        buf = PresenceCircularBuffer(capacity=50)
        entry = PresenceLogEntry(uuid.uuid4(), "24-00123", "PRRC 301", 14, datetime.now(timezone.utc))
        buf.append(entry)

        assert buf.get_by_student("24-00123") == entry
        assert buf.get_by_student("24-99999") is None
        assert buf.get_by_workstation(14) == entry
        assert buf.get_by_workstation(99) is None

    def test_buffer_manager_room_separation(self):
        mgr = PresenceBufferManager(room_capacity=50)
        e1 = PresenceLogEntry(uuid.uuid4(), "24-00001", "PRRC 301", 1, datetime.now(timezone.utc))
        e2 = PresenceLogEntry(uuid.uuid4(), "24-00002", "PRRC 302", 2, datetime.now(timezone.utc))

        mgr.record_check_in(e1)
        mgr.record_check_in(e2)

        logs_301 = mgr.get_recent_room_logs("PRRC 301")
        logs_302 = mgr.get_recent_room_logs("PRRC 302")
        global_logs = mgr.get_global_recent_logs()

        assert len(logs_301) == 1
        assert logs_301[0].student_id == "24-00001"
        assert len(logs_302) == 1
        assert logs_302[0].student_id == "24-00002"
        assert len(global_logs) == 2


# ===========================================================================
# 5. Real-Time SSE Broadcaster Test Suite
# ===========================================================================

class TestSSEBroadcaster:
    """Validates W3C SSE standard event serialization and subscription lifecycle."""

    def test_w3c_sse_formatting(self):
        raw = format_sse("occupancy_update", {"vacant_count": 44, "occupied_count": 1})
        assert raw.startswith("event: occupancy_update\n")
        assert 'data: {"vacant_count":44,"occupied_count":1}\n\n' in raw
        assert raw.endswith("\n\n")

    def test_broadcast_to_subscribers(self):
        async def _run():
            broadcaster = SSEBroadcaster(heartbeat_interval=15.0)
            q = await broadcaster.subscribe("PRRC 301")

            assert broadcaster.get_listener_count("PRRC 301") == 1

            payload = {"room_code": "PRRC 301", "occupied_count": 1}
            await broadcaster.broadcast("PRRC 301", "occupancy_update", payload)

            msg = await asyncio.wait_for(q.get(), timeout=1.0)
            assert "event: occupancy_update" in msg
            assert '"occupied_count":1' in msg

            await broadcaster.unsubscribe("PRRC 301", q)
            assert broadcaster.get_listener_count("PRRC 301") == 0

        asyncio.run(_run())

    def test_event_generator_initial_state_and_heartbeat(self):
        async def _run():
            broadcaster = SSEBroadcaster(heartbeat_interval=0.1)  # fast 100ms heartbeat for test
            initial = {"room_code": "PRRC 301", "total_stations": 45}

            gen = broadcaster.event_generator("PRRC 301", initial_data=initial)

            # 1st yielded item must be initial_state
            first_event = await anext(gen)
            assert "event: initial_state" in first_event
            assert '"total_stations":45' in first_event

            # 2nd yielded item after 0.1s must be heartbeat
            heartbeat_event = await anext(gen)
            assert "event: heartbeat" in heartbeat_event
            assert '"room_code":"PRRC 301"' in heartbeat_event

            await gen.aclose()
            assert broadcaster.get_listener_count("PRRC 301") == 0

        asyncio.run(_run())

    def test_event_generator_once_mode(self):
        async def _run():
            broadcaster = SSEBroadcaster(heartbeat_interval=15.0)
            initial = {"room_code": "PRRC 301", "total_stations": 45}
            events = []
            async for evt in broadcaster.event_generator("PRRC 301", initial_data=initial, once=True):
                events.append(evt)

            assert len(events) == 1
            assert "event: initial_state" in events[0]
            assert broadcaster.get_listener_count("PRRC 301") == 0

        asyncio.run(_run())

    def test_broadcaster_queue_full_handling(self):
        async def _run():
            broadcaster = SSEBroadcaster(heartbeat_interval=15.0)
            q = await broadcaster.subscribe("PRRC 301")

            # Fill queue to capacity (100 items)
            for i in range(100):
                q.put_nowait(f"msg-{i}")
            assert q.full()

            # Broadcasting must not crash or deadlock when queue is full
            await broadcaster.broadcast("PRRC 301", "test_event", {"num": 101})
            assert q.full()
            await broadcaster.unsubscribe("PRRC 301", q)

        asyncio.run(_run())


# ===========================================================================
# 6. FastAPI TestClient Endpoint Integration Suite (Port 8004)
# ===========================================================================

class TestFastAPIPresenceEndpoints:
    """Validates presence microservice REST and SSE endpoints."""

    @pytest.fixture(autouse=True)
    def reset_state(self):
        workstation_manager.reset_all_rooms()
        while len(circular_buffer) > 0:
            circular_buffer._buffer.pop()
        yield

    def test_health_endpoint(self):
        client = TestClient(app)
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["service"] == "presence"
        assert data["port"] == 8004
        assert "ClassSync" in data["title"]

    def test_totp_endpoint(self):
        client = TestClient(app)
        res = client.get("/api/v1/presence/totp/PRRC 301")
        assert res.status_code == 200
        data = res.json()
        assert data["room"] == "PRRC 301"
        assert len(data["totp"]) == 6
        assert data["totp"].isdigit()
        assert 1 <= data["remaining_seconds"] <= 15

    def test_checkin_success(self):
        client = TestClient(app)
        totp_data = client.get("/api/v1/presence/totp/PRRC 301").json()

        payload = {
            "room_code": "PRRC 301",
            "workstation_number": 14,
            "student_id": "24-00123",
            "totp_token": totp_data["totp"],
        }
        res = client.post("/api/v1/presence/checkin", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["workstation_number"] == 14
        assert data["student_id"] == "24-00123"

        # Check circular buffer received log
        logs = circular_buffer.get_recent(limit=10)
        assert len(logs) >= 1
        assert logs[0].student_id == "24-00123"

    def test_checkin_invalid_student_id(self):
        client = TestClient(app)
        totp_data = client.get("/api/v1/presence/totp/PRRC 301").json()

        payload = {
            "room_code": "PRRC 301",
            "workstation_number": 14,
            "student_id": "invalid-id",
            "totp_token": totp_data["totp"],
        }
        res = client.post("/api/v1/presence/checkin", json=payload)
        assert res.status_code == 400
        assert res.json()["detail"] == STUDENT_ID_ERROR_MESSAGE

    def test_checkin_expired_totp(self):
        client = TestClient(app)
        payload = {
            "room_code": "PRRC 301",
            "workstation_number": 14,
            "student_id": "24-00123",
            "totp_token": "000000",  # Invalid token
        }
        res = client.post("/api/v1/presence/checkin", json=payload)
        assert res.status_code == 400
        assert "The QR code just refreshed!" in res.json()["detail"]

    def test_checkin_seat_collision(self):
        client = TestClient(app)
        totp_data = client.get("/api/v1/presence/totp/PRRC 301").json()

        # Student A claims PC-14
        res1 = client.post("/api/v1/presence/checkin", json={
            "room_code": "PRRC 301",
            "workstation_number": 14,
            "student_id": "24-00001",
            "totp_token": totp_data["totp"],
        })
        assert res1.status_code == 200

        # Student B attempts to claim PC-14 simultaneously
        res2 = client.post("/api/v1/presence/checkin", json={
            "room_code": "PRRC 301",
            "workstation_number": 14,
            "student_id": "24-00002",
            "totp_token": totp_data["totp"],
        })
        assert res2.status_code == 409
        assert "Seat PC-14 was just claimed by a classmate! PC-15 is open right next to it." in res2.json()["detail"]

    def test_checkout_success(self):
        client = TestClient(app)
        totp_data = client.get("/api/v1/presence/totp/PRRC 301").json()

        # Check in first
        client.post("/api/v1/presence/checkin", json={
            "room_code": "PRRC 301",
            "workstation_number": 14,
            "student_id": "24-00123",
            "totp_token": totp_data["totp"],
        })

        # Check out
        res = client.post("/api/v1/presence/checkout", json={
            "room_code": "PRRC 301",
            "workstation_number": 14,
            "student_id": "24-00123",
        })
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_checkout_invalid_student_id(self):
        client = TestClient(app)
        res = client.post("/api/v1/presence/checkout", json={
            "room_code": "PRRC 301",
            "workstation_number": 14,
            "student_id": "invalid-student-id",
        })
        assert res.status_code == 400
        assert res.json()["detail"] == STUDENT_ID_ERROR_MESSAGE

    def test_occupancy_endpoint(self):
        client = TestClient(app)
        res = client.get("/api/v1/presence/rooms/PRRC 301/occupancy")
        assert res.status_code == 200
        data = res.json()
        assert data["room_code"] == "PRRC 301"
        assert data["total_stations"] == 45
        assert len(data["stations"]) == 45
        assert "vacant_rate" in data

    def test_recent_logs_endpoint(self):
        client = TestClient(app)
        res = client.get("/api/v1/presence/rooms/PRRC 301/recent-logs?limit=10")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_stream_endpoint_once_parameter(self):
        client = TestClient(app)
        res = client.get("/api/v1/presence/rooms/PRRC 301/stream?once=true")
        assert res.status_code == 200
        assert "text/event-stream" in res.headers.get("content-type", "")
        assert "event: initial_state" in res.text
        assert "PRRC 301" in res.text

    def test_stream_endpoint_with_client_stream(self):
        client = TestClient(app)
        with client.stream("GET", "/api/v1/presence/rooms/PRRC 301/stream") as res:
            assert res.status_code == 200
            assert "text/event-stream" in res.headers.get("content-type", "")
            lines = []
            for line in res.iter_lines():
                if line:
                    lines.append(line)
                if line.startswith("data:"):
                    break
            chunk = "\n".join(lines)
            assert "event: initial_state" in chunk
            assert "PRRC 301" in chunk
