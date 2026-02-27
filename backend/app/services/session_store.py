from __future__ import annotations

from threading import RLock
from uuid import uuid4

from app.models.domain import ParticipantRole, SessionData


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionData] = {}
        self._lock = RLock()

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

    def update_role(self, *, room_pin: str, participant_id: str, role: ParticipantRole) -> None:
        with self._lock:
            for session in self._sessions.values():
                if session.room_pin == room_pin and session.participant_id == participant_id:
                    session.role = role
