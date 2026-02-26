from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.dependencies import get_room_store
from app.models.domain import Player, Room, Team
from app.models.schemas import (
    CreateRoomRequest,
    CreateRoomResponse,
    ErrorResponse,
    JoinRoomRequest,
    JoinRoomResponse,
    PlayerResponse,
    RoomDetailResponse,
    RoomListResponse,
    RoomSummaryResponse,
)
from app.services.room_store import (
    DuplicatePlayerNameError,
    RoomCapacityExceededError,
    RoomJoinClosedError,
    RoomNotFoundError,
    RoomStore,
)

router = APIRouter(prefix="/api/v1/rooms", tags=["Rooms"])


@router.post(
    "",
    response_model=CreateRoomResponse,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": ErrorResponse}},
)
def create_room(
    payload: CreateRoomRequest,
    store: RoomStore = Depends(get_room_store),
) -> CreateRoomResponse:
    room = store.create_room(
        host_name=payload.host_name,
        topic=payload.topic,
        questions_per_team=payload.questions_per_team,
        max_players=payload.max_players,
    )
    return CreateRoomResponse(room=_to_room_detail(room))


@router.post(
    "/{pin}/join",
    response_model=JoinRoomResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def join_room(
    payload: JoinRoomRequest,
    pin: str = Path(..., pattern=r"^[A-Za-z0-9]{6}$"),
    store: RoomStore = Depends(get_room_store),
) -> JoinRoomResponse:
    try:
        room, player = store.join_room(pin=pin, player_name=payload.player_name)
    except RoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (DuplicatePlayerNameError, RoomJoinClosedError, RoomCapacityExceededError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return JoinRoomResponse(player=_to_player_response(player), room=_to_room_detail(room))


@router.get(
    "/{pin}",
    response_model=RoomDetailResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def get_room(
    pin: str = Path(..., pattern=r"^[A-Za-z0-9]{6}$"),
    store: RoomStore = Depends(get_room_store),
) -> RoomDetailResponse:
    try:
        room = store.get_room(pin=pin)
    except RoomNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_room_detail(room)


@router.get("", response_model=RoomListResponse)
def list_rooms(store: RoomStore = Depends(get_room_store)) -> RoomListResponse:
    rooms = [_to_room_summary(room) for room in store.list_rooms()]
    return RoomListResponse(rooms=rooms)


def _to_room_summary(room: Room) -> RoomSummaryResponse:
    return RoomSummaryResponse(
        pin=room.pin,
        host_name=room.host_name,
        topic=room.topic,
        questions_per_team=room.questions_per_team,
        max_players=room.max_players,
        players_count=len(room.players),
        status=room.status,
        created_at=room.created_at,
    )


def _to_room_detail(room: Room) -> RoomDetailResponse:
    teams = {
        Team.RED: [],
        Team.BLUE: [],
    }
    for player in room.players.values():
        teams[player.team].append(_to_player_response(player))

    return RoomDetailResponse(**_to_room_summary(room).model_dump(), teams=teams)


def _to_player_response(player: Player) -> PlayerResponse:
    return PlayerResponse(
        player_id=player.player_id,
        player_name=player.player_name,
        team=player.team,
        joined_at=player.joined_at,
    )

