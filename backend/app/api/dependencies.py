from fastapi import Request

from app.services.room_store import RoomStore


def get_room_store(request: Request) -> RoomStore:
    return request.app.state.room_store

