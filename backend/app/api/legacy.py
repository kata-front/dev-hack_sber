import re

from fastapi import APIRouter, Depends

from app.api.dependencies import get_room_store
from app.models.schemas import CheckPinRequest, CheckPinResponse, ErrorResponse
from app.services.room_store import RoomStore

router = APIRouter(tags=["Legacy"])
PIN_REGEX = re.compile(r"^[A-Z0-9]{6}$")


@router.post(
    "/check_pin",
    response_model=CheckPinResponse,
    responses={422: {"model": ErrorResponse}},
)
@router.post(
    "/check-pin",
    response_model=CheckPinResponse,
    responses={422: {"model": ErrorResponse}},
)
def check_pin_legacy(
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


@router.post(
    "/checkPin",
    response_model=CheckPinResponse,
    responses={422: {"model": ErrorResponse}},
)
def check_pin_legacy_camel(
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
