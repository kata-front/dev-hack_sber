from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from threading import RLock
from uuid import uuid4

from app.models.domain import ParticipantRole, SessionData


class SessionStore:
    def __init__(self, *, storage_path: str | None = None) -> None:
        self._sessions: dict[str, SessionData] = {}
        self._storage_path = Path(storage_path) if storage_path else None
        self._lock = RLock()
        self._load_from_disk()

    def create_session(
        self,
        *,
        room_pin: str,
        participant_id: str,
        name: str,
        role: ParticipantRole,
    ) -> SessionData:
        with self._lock:
            session = SessionData(
                session_id=uuid4().hex,
                room_pin=room_pin,
                participant_id=participant_id,
                name=name,
                role=role,
            )
            self._sessions[session.session_id] = session
            self._persist_to_disk()
            return session

    def get(self, session_id: str) -> SessionData | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            return SessionData(
                session_id=session.session_id,
                room_pin=session.room_pin,
                participant_id=session.participant_id,
                name=session.name,
                role=session.role,
                created_at=session.created_at,
            )

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
            self._persist_to_disk()

    def update_role(self, *, room_pin: str, participant_id: str, role: ParticipantRole) -> None:
        with self._lock:
            changed = False
            for session in self._sessions.values():
                if session.room_pin == room_pin and session.participant_id == participant_id:
                    session.role = role
                    changed = True
            if changed:
                self._persist_to_disk()

    def delete_by_participant(self, *, room_pin: str, participant_id: str) -> list[str]:
        with self._lock:
            removed_ids = [
                session_id
                for session_id, session in self._sessions.items()
                if session.room_pin == room_pin and session.participant_id == participant_id
            ]
            for session_id in removed_ids:
                self._sessions.pop(session_id, None)
            if removed_ids:
                self._persist_to_disk()
            return removed_ids

    def _persist_to_disk(self) -> None:
        if self._storage_path is None:
            return
        payload = {
            "sessions": [
                {
                    "sessionId": session.session_id,
                    "roomPin": session.room_pin,
                    "participantId": session.participant_id,
                    "name": session.name,
                    "role": session.role.value,
                    "createdAt": session.created_at.isoformat(),
                }
                for session in self._sessions.values()
            ]
        }
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._storage_path.with_suffix(self._storage_path.suffix + ".tmp")
            tmp_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            tmp_path.replace(self._storage_path)
        except Exception:
            return

    def _load_from_disk(self) -> None:
        if self._storage_path is None or not self._storage_path.exists():
            return
        try:
            raw = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except Exception:
            return

        sessions_raw = raw.get("sessions", [])
        if not isinstance(sessions_raw, list):
            return

        restored: dict[str, SessionData] = {}
        for item in sessions_raw:
            if not isinstance(item, dict):
                continue
            try:
                session = SessionData(
                    session_id=str(item["sessionId"]),
                    room_pin=str(item["roomPin"]).upper(),
                    participant_id=str(item["participantId"]),
                    name=str(item["name"]),
                    role=ParticipantRole(str(item["role"])),
                    created_at=datetime.fromisoformat(str(item["createdAt"])),
                )
            except Exception:
                continue
            restored[session.session_id] = session
        self._sessions = restored
