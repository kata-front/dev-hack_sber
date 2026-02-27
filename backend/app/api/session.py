from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from app.api.constants import SESSION_COOKIE_NAME
from app.api.dependencies import get_room_store, get_session_store
from app.api.rooms import _clear_session_cookie, _to_participant_response, _to_room_response, _to_session_info
from app.models.schemas import LogoutResponse, SessionStateResponse
from app.services.room_store import AccessDeniedError, RoomNotFoundError, RoomStore
from app.services.session_store import SessionStore

router = APIRouter(prefix="/session", tags=["Session"])


@router.get("", response_model=SessionStateResponse)
def get_session(
    request: Request,
    session_store: SessionStore = Depends(get_session_store),
    room_store: RoomStore = Depends(get_room_store),
) -> SessionStateResponse:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return SessionStateResponse(authenticated=False)

    session = session_store.get(session_id)
    if session is None:
        return SessionStateResponse(authenticated=False)

    try:
        room = room_store.get_room_snapshot(pin=session.room_pin)
        participant = room_store.get_participant_snapshot(
            pin=session.room_pin,
            participant_id=session.participant_id,
        )
    except (RoomNotFoundError, AccessDeniedError):
        session_store.delete(session_id)
        return SessionStateResponse(authenticated=False)

    return SessionStateResponse(
        authenticated=True,
        session=_to_session_info(session),
        participant=_to_participant_response(participant),
        room=_to_room_response(room),
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    response: Response,
    session_store: SessionStore = Depends(get_session_store),
    room_store: RoomStore = Depends(get_room_store),
) -> LogoutResponse:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id:
        session = session_store.get(session_id)
        if session is not None:
            try:
                _, _, promoted = room_store.leave_room(
                    pin=session.room_pin,
                    participant_id=session.participant_id,
                )
                if promoted is not None:
                    session_store.update_role(
                        room_pin=session.room_pin,
                        participant_id=promoted.participant_id,
                        role=promoted.role,
                    )
            except (RoomNotFoundError, AccessDeniedError):
                pass
        session_store.delete(session_id)
    _clear_session_cookie(response)
    return LogoutResponse(ok=True)
