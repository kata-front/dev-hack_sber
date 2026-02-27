from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.dependencies import get_room_store
from app.models.domain import GameInfo as DomainGameInfo
from app.models.domain import Participant as DomainParticipant
from app.models.domain import Question as DomainQuestion
from app.models.domain import Room as DomainRoom
from app.models.schemas import (
    CheckPinRequest,
    DataFormCreateRoom,
    GameInfo,
    InfoRoom,
    LoginResponse,
    Participant,
    RoomInitHostResponse,
    RoomInitParticipantResponse,
    RoomMessage,
    StartGameRequest,
)
from app.services.room_store import RoomCapacityExceededError, RoomNotFoundError, RoomStore

INT64_MAX = 9_223_372_036_854_775_807

router = APIRouter(tags=["Rooms"])


@router.post("/check_pin", response_model=LoginResponse)
def check_pin(
    payload: CheckPinRequest,
    store: RoomStore = Depends(get_room_store),
) -> LoginResponse:
    ok, room_id = store.check_pin(payload.pin)
    return LoginResponse(ok=ok, roomId=room_id)


@router.post("/create_room", response_model=LoginResponse)
def create_room(
    payload: DataFormCreateRoom,
    store: RoomStore = Depends(get_room_store),
) -> LoginResponse:
    ok = store.create_room(
        room_id=payload.roomId,
        room_name=payload.roomName,
        quiz_theme=payload.quizTheme,
        max_participants=payload.maxParticipants,
    )
    return LoginResponse(ok=ok, roomId=payload.roomId if ok else None)


@router.get("/create_room/{roomId}", response_model=RoomInitHostResponse)
def init_room_host(
    roomId: int = Path(..., ge=1, le=INT64_MAX),
    store: RoomStore = Depends(get_room_store),
) -> RoomInitHostResponse:
    try:
        room = store.init_room_as_host(room_id=roomId)
    except RoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return _to_room_init_host_response(room, role="host")


@router.get("/join_room/{roomId}", response_model=RoomInitParticipantResponse)
def init_room_participant(
    roomId: int = Path(..., ge=1, le=INT64_MAX),
    store: RoomStore = Depends(get_room_store),
) -> RoomInitParticipantResponse:
    try:
        room, team = store.init_room_as_participant(room_id=roomId)
    except RoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RoomCapacityExceededError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return _to_room_init_participant_response(room, role="participant", team=team)


@router.post("/start_game/{roomId}", response_model=GameInfo)
def start_game(
    payload: StartGameRequest,
    roomId: int = Path(..., ge=1, le=INT64_MAX),
    store: RoomStore = Depends(get_room_store),
) -> GameInfo:
    try:
        game_info = store.start_game(room_id=roomId, payload_room_id=payload.roomId)
    except RoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_game_info_response(game_info)


def _to_room_init_host_response(room: DomainRoom, *, role: str) -> RoomInitHostResponse:
    base = _to_info_room(room)
    return RoomInitHostResponse(**base.model_dump(), role=role)


def _to_room_init_participant_response(
    room: DomainRoom,
    *,
    role: str,
    team: str,
) -> RoomInitParticipantResponse:
    base = _to_info_room(room)
    return RoomInitParticipantResponse(**base.model_dump(), role=role, team=team)


def _to_info_room(room: DomainRoom) -> InfoRoom:
    return InfoRoom(
        roomId=room.room_id,
        roomName=room.room_name,
        quizTheme=room.quiz_theme,
        maxParticipants=room.max_participants,
        messages=[_to_room_message(item) for item in room.messages],
        participants=[_to_participant(item) for item in room.participants],
        gameInfo=_to_game_info_response(room.game_info) if room.game_info else None,
    )


def _to_room_message(message) -> RoomMessage:
    return RoomMessage(
        command=message.command,
        createdAt=message.created_at,
        text=message.text,
    )


def _to_participant(participant: DomainParticipant) -> Participant:
    return Participant(
        id=participant.participant_id,
        command=participant.command,
        role=participant.role,
    )


def _to_game_info_response(game_info: DomainGameInfo) -> GameInfo:
    return GameInfo(
        status=game_info.status,
        activeTeam=game_info.active_team,
        questions=[_to_question(item) for item in game_info.questions],
        activeQuestionIndex=game_info.active_question_index,
        counter=game_info.counter,
    )


def _to_question(question: DomainQuestion):
    return {
        "question": question.question,
        "team": question.team,
        "answers": question.answers,
        "statusAnswer": question.status_answer,
    }
