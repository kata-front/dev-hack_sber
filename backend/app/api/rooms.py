from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response, status

from app.api.constants import SESSION_COOKIE_MAX_AGE, SESSION_COOKIE_NAME
from app.api.dependencies import get_question_generator, get_room_store, get_session_store
from app.models.domain import (
    ChatMessage,
    Participant,
    Question,
    Room,
    SessionData,
    TeamCommand,
)
from app.models.schemas import (
    AuthRoomResponse,
    CheckPinRequest,
    CheckPinResponse,
    CreateRoomRequest,
    ErrorResponse,
    GameInfoResponse,
    JoinRoomRequest,
    LeaveRoomResponse,
    ParticipantResponse,
    QuestionResponse,
    RoomMessageResponse,
    RoomResponse,
    ScoreResponse,
    SendMessageRequest,
    SessionInfoResponse,
    StartGameResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.services.question_generator import QuestionGenerator
from app.services.room_store import (
    AccessDeniedError,
    RoomCapacityExceededError,
    RoomNotFoundError,
    RoomStateError,
    RoomStore,
)
from app.services.session_store import SessionStore

router = APIRouter(prefix="/rooms", tags=["Rooms"])
PIN_REGEX = re.compile(r"^[A-Z0-9]{6}$")


@router.post(
    "/check-pin",
    response_model=CheckPinResponse,
    responses={422: {"model": ErrorResponse}},
)
@router.post(
    "/check_pin",
    response_model=CheckPinResponse,
    responses={422: {"model": ErrorResponse}},
)
def check_pin(
    payload: CheckPinRequest,
    room_store: RoomStore = Depends(get_room_store),
) -> CheckPinResponse:
    normalized = payload.pin.upper()
    if not PIN_REGEX.fullmatch(normalized):
        return CheckPinResponse(ok=False, roomPin=normalized, roomId=None)

    exists = room_store.check_pin(pin=normalized)
    return CheckPinResponse(
        ok=exists,
        roomPin=normalized if exists else None,
        roomId=normalized if exists else None,
    )


@router.get(
    "/check-pin",
    response_model=CheckPinResponse,
)
@router.get(
    "/check_pin",
    response_model=CheckPinResponse,
)
def check_pin_query(
    pin: str = Query(..., min_length=1),
    room_store: RoomStore = Depends(get_room_store),
) -> CheckPinResponse:
    normalized = pin.strip().upper()
    if not PIN_REGEX.fullmatch(normalized):
        return CheckPinResponse(ok=False, roomPin=normalized, roomId=None)

    exists = room_store.check_pin(pin=normalized)
    return CheckPinResponse(
        ok=exists,
        roomPin=normalized if exists else None,
        roomId=normalized if exists else None,
    )


@router.post(
    "",
    response_model=AuthRoomResponse,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_room(
    payload: CreateRoomRequest,
    request: Request,
    response: Response,
    room_store: RoomStore = Depends(get_room_store),
    session_store: SessionStore = Depends(get_session_store),
) -> AuthRoomResponse:
    _ensure_no_active_session(request=request, room_store=room_store, session_store=session_store)

    room, host = room_store.create_room(
        host_name=payload.hostName,
        topic=payload.topic,
        questions_per_team=payload.questionsPerTeam,
        max_participants=payload.maxParticipants,
        timer_seconds=payload.timerSeconds,
    )
    session = session_store.create_session(
        room_pin=room.pin,
        participant_id=host.participant_id,
        name=host.name,
        role=host.role,
    )
    _set_session_cookie(response=response, session_id=session.session_id)
    return AuthRoomResponse(
        session=_to_session_info(session),
        participant=_to_participant_response(host),
        room=_to_room_response(room),
    )


@router.post(
    "/{pin}/join",
    response_model=AuthRoomResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def join_room(
    payload: JoinRoomRequest,
    request: Request,
    response: Response,
    pin: str = Path(..., pattern=r"^[A-Za-z0-9]{6}$"),
    room_store: RoomStore = Depends(get_room_store),
    session_store: SessionStore = Depends(get_session_store),
) -> AuthRoomResponse:
    _ensure_no_active_session(request=request, room_store=room_store, session_store=session_store)

    try:
        room, participant = room_store.join_room(pin=pin, player_name=payload.playerName)
    except RoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (RoomStateError, RoomCapacityExceededError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    session = session_store.create_session(
        room_pin=room.pin,
        participant_id=participant.participant_id,
        name=participant.name,
        role=participant.role,
    )
    _set_session_cookie(response=response, session_id=session.session_id)
    return AuthRoomResponse(
        session=_to_session_info(session),
        participant=_to_participant_response(participant),
        room=_to_room_response(room),
    )


@router.get(
    "/{pin}",
    response_model=RoomResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def get_room(
    request: Request,
    pin: str = Path(..., pattern=r"^[A-Za-z0-9]{6}$"),
    room_store: RoomStore = Depends(get_room_store),
    session_store: SessionStore = Depends(get_session_store),
) -> RoomResponse:
    session = _require_session(request=request, session_store=session_store, room_store=room_store)
    if session.room_pin != pin.upper():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session belongs to another room.")

    try:
        room = room_store.get_room_snapshot(pin=pin)
    except RoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_room_response(room)


@router.post(
    "/{pin}/start",
    response_model=StartGameResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def start_game(
    request: Request,
    pin: str = Path(..., pattern=r"^[A-Za-z0-9]{6}$"),
    room_store: RoomStore = Depends(get_room_store),
    session_store: SessionStore = Depends(get_session_store),
    question_generator: QuestionGenerator = Depends(get_question_generator),
) -> StartGameResponse:
    session = _require_session(request=request, session_store=session_store, room_store=room_store)
    if session.room_pin != pin.upper():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session belongs to another room.")

    try:
        room_snapshot = room_store.get_room_snapshot(pin=pin)
        generation = await question_generator.generate_questions(
            topic=room_snapshot.topic,
            questions_per_team=room_snapshot.questions_per_team,
        )
        room = room_store.start_game(
            pin=pin,
            requested_by=session.participant_id,
            generated_questions=generation.questions,
        )
    except RoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except RoomStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    assert room.game_info is not None
    return StartGameResponse(
        room=_to_room_response(room),
        gameInfo=_to_game_info_response(room.game_info),
        generationSource=generation.source,
        generationMessage=generation.reason,
    )


@router.post(
    "/{pin}/answer",
    response_model=SubmitAnswerResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def submit_answer(
    payload: SubmitAnswerRequest,
    request: Request,
    pin: str = Path(..., pattern=r"^[A-Za-z0-9]{6}$"),
    room_store: RoomStore = Depends(get_room_store),
    session_store: SessionStore = Depends(get_session_store),
) -> SubmitAnswerResponse:
    session = _require_session(request=request, session_store=session_store, room_store=room_store)
    if session.room_pin != pin.upper():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session belongs to another room.")

    try:
        result = room_store.submit_answer(
            pin=pin,
            participant_id=session.participant_id,
            option_index=payload.optionIndex,
        )
        room = room_store.get_room_snapshot(pin=pin)
    except RoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except RoomStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return SubmitAnswerResponse(
        answerStatus=result.answer_status,
        room=_to_room_response(room),
        gameInfo=_to_game_info_response(result.game_info),
        nextQuestion=_to_question_response(result.next_question) if result.next_question else None,
    )


@router.post(
    "/{pin}/messages",
    response_model=RoomMessageResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def send_message(
    payload: SendMessageRequest,
    request: Request,
    pin: str = Path(..., pattern=r"^[A-Za-z0-9]{6}$"),
    room_store: RoomStore = Depends(get_room_store),
    session_store: SessionStore = Depends(get_session_store),
) -> RoomMessageResponse:
    session = _require_session(request=request, session_store=session_store, room_store=room_store)
    if session.room_pin != pin.upper():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session belongs to another room.")

    try:
        _, message = room_store.add_message(
            pin=pin,
            participant_id=session.participant_id,
            text=payload.text,
        )
    except RoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return _to_message_response(message)


@router.post(
    "/{pin}/leave",
    response_model=LeaveRoomResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def leave_room(
    request: Request,
    response: Response,
    pin: str = Path(..., pattern=r"^[A-Za-z0-9]{6}$"),
    room_store: RoomStore = Depends(get_room_store),
    session_store: SessionStore = Depends(get_session_store),
) -> LeaveRoomResponse:
    session = _require_session(request=request, session_store=session_store, room_store=room_store)
    if session.room_pin != pin.upper():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session belongs to another room.")

    try:
        _, _, promoted = room_store.leave_room(pin=pin, participant_id=session.participant_id)
    except RoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if promoted is not None:
        session_store.update_role(
            room_pin=pin.upper(),
            participant_id=promoted.participant_id,
            role=promoted.role,
        )

    session_store.delete(session.session_id)
    _clear_session_cookie(response)
    return LeaveRoomResponse(ok=True)


def _require_session(
    *,
    request: Request,
    session_store: SessionStore,
    room_store: RoomStore,
) -> SessionData:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session is missing.")

    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session is invalid.")

    try:
        room_store.get_participant_snapshot(pin=session.room_pin, participant_id=session.participant_id)
    except (RoomNotFoundError, AccessDeniedError):
        session_store.delete(session.session_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Session expired.")

    return session


def _ensure_no_active_session(
    *,
    request: Request,
    room_store: RoomStore,
    session_store: SessionStore,
) -> None:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return

    session = session_store.get(session_id)
    if session is None:
        return

    try:
        room_store.get_participant_snapshot(pin=session.room_pin, participant_id=session.participant_id)
    except (RoomNotFoundError, AccessDeniedError):
        session_store.delete(session_id)
        return

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Current browser session is already inside a room. Leave it first.",
    )


def _set_session_cookie(*, response: Response, session_id: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME)


def _to_session_info(session: SessionData) -> SessionInfoResponse:
    return SessionInfoResponse(
        roomPin=session.room_pin,
        participantId=session.participant_id,
        name=session.name,
        role=session.role,
    )


def _to_room_response(room: Room) -> RoomResponse:
    return RoomResponse(
        pin=room.pin,
        topic=room.topic,
        questionsPerTeam=room.questions_per_team,
        maxParticipants=room.max_participants,
        timerSeconds=room.timer_seconds,
        status=room.status,
        createdAt=room.created_at,
        participants=[_to_participant_response(participant) for participant in room.participants],
        messages=[_to_message_response(message) for message in room.messages],
        gameInfo=_to_game_info_response(room.game_info) if room.game_info else None,
    )


def _to_participant_response(participant: Participant) -> ParticipantResponse:
    return ParticipantResponse(
        id=participant.participant_id,
        name=participant.name,
        role=participant.role,
        team=participant.team,
        joinedAt=participant.joined_at,
    )


def _to_message_response(message: ChatMessage) -> RoomMessageResponse:
    return RoomMessageResponse(
        id=message.message_id,
        text=message.text,
        createdAt=message.created_at,
        authorName=message.author_name,
        command=message.command,
    )


def _to_game_info_response(game_info) -> GameInfoResponse:
    return GameInfoResponse(
        status=game_info.status,
        activeTeam=game_info.active_team,
        activeQuestionIndex=game_info.active_question_index,
        counter=game_info.counter,
        scores=ScoreResponse(
            red=game_info.scores.get(TeamCommand.RED, 0),
            blue=game_info.scores.get(TeamCommand.BLUE, 0),
        ),
        questions=[_to_question_response(question) for question in game_info.questions],
    )


def _to_question_response(question: Question) -> QuestionResponse:
    return QuestionResponse(
        id=question.question_id,
        text=question.text,
        options=question.options,
        team=question.team,
        selectedOption=question.selected_option,
        statusAnswer=question.answer_status,
    )
