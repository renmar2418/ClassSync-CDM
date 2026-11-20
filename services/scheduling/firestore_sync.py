"""Cloud Firestore CQRS Projection Pipeline for ClassSync V2.

Official Project Title: ClassSync: AI-Powered University Classroom Scheduling,
Availability Monitoring, and Conflict Detection System

Projects relational PostgreSQL scheduling & presence writes into high-throughput,
low-latency Cloud Firestore documents for mobile offline-first client consumption.
"""

from __future__ import annotations
import os
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

class FirestoreProjectionPipeline:
    """CQRS Projection manager synchronizing state from relational writes to Cloud Firestore."""

    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.getenv("FIREBASE_PROJECT_ID", "classync-pnm-2026")
        self._in_memory_store: Dict[str, Dict[str, Any]] = {
            "timetables": {},
            "workstation_presence": {},
            "facility_directory": {},
        }
        self.is_connected = False
        self._init_client()

    def _init_client(self):
        """Attempts to initialize google-cloud-firestore if credentials exist, otherwise operates in high-speed local projection mode."""
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if credentials_path and os.path.exists(credentials_path):
            try:
                from google.cloud import firestore  # type: ignore
                self.client = firestore.Client(project=self.project_id)
                self.is_connected = True
            except Exception:
                self.client = None
                self.is_connected = False
        else:
            self.client = None
            self.is_connected = False

    def project_timetable_entries(
        self,
        academic_period_id: str | uuid.UUID,
        entries: List[Dict[str, Any]],
        revision_hash: str,
    ) -> Dict[str, Any]:
        """Projects a batch of verified timetable entries into the 'timetables' collection."""
        doc_id = str(academic_period_id)
        payload = {
            "academic_period_id": doc_id,
            "revision_hash": revision_hash,
            "entry_count": len(entries),
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "entries": entries,
        }

        if self.is_connected and self.client:
            self.client.collection("timetables").document(doc_id).set(payload)
        else:
            self._in_memory_store["timetables"][doc_id] = payload

        return payload

    def project_workstation_occupancy(
        self,
        room_code: str,
        occupied_count: int,
        total_stations: int,
        occupancy_rate: float,
        stations_state: Dict[int, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Projects real-time COMLAB workstation presence into 'workstation_presence'."""
        payload = {
            "room_code": room_code,
            "occupied_count": occupied_count,
            "total_stations": total_stations,
            "vacant_count": max(0, total_stations - occupied_count),
            "occupancy_rate": round(occupancy_rate, 4),
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "stations": stations_state,
        }

        if self.is_connected and self.client:
            self.client.collection("workstation_presence").document(room_code).set(payload)
        else:
            self._in_memory_store["workstation_presence"][room_code] = payload

        return payload

    def project_facility_directory(self, rooms: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Projects schedulable facilities (hiding quarantined spaces) into 'facility_directory'."""
        schedulable_rooms = [r for r in rooms if r.get("is_schedulable", True)]
        payload = {
            "total_schedulable_rooms": len(schedulable_rooms),
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "rooms": schedulable_rooms,
        }

        doc_id = "schedulable_rooms"
        if self.is_connected and self.client:
            self.client.collection("facility_directory").document(doc_id).set(payload)
        else:
            self._in_memory_store["facility_directory"][doc_id] = payload

        return payload

    def get_projection(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves projected read document."""
        if self.is_connected and self.client:
            doc = self.client.collection(collection).document(doc_id).get()
            return doc.to_dict() if doc.exists else None
        return self._in_memory_store.get(collection, {}).get(doc_id)


# Global Projection Pipeline Singleton
firestore_pipeline = FirestoreProjectionPipeline()
