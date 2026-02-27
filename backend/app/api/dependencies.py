from fastapi import Request

from app.services.question_generator import QuestionGenerator
from app.services.room_store import RoomStore
from app.services.session_store import SessionStore


def get_room_store(request: Request) -> RoomStore:
    return request.app.state.room_store


def get_session_store(request: Request) -> SessionStore:
    return request.app.state.session_store


def get_question_generator(request: Request) -> QuestionGenerator:
    return request.app.state.question_generator
