from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.domain import AnswerStatus, GameStatus, ParticipantRole, TeamCommand


INT32_MAX = 2_147_483_647
INT64_MAX = 9_223_372_036_854_775_807


def _clean_text(value: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError("must not be empty")
    return cleaned


class CheckPinRequest(BaseModel):
    pin: int = Field(..., ge=1, le=INT64_MAX)


class LoginResponse(BaseModel):
    ok: bool
    roomId: int | None = Field(default=None, ge=1, le=INT64_MAX)


class DataFormCreateRoom(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    roomId: int = Field(..., ge=1, le=INT64_MAX)
    roomName: str = Field(..., min_length=1, max_length=120)
    quizTheme: str = Field(..., min_length=1, max_length=120)
    maxParticipants: int = Field(..., ge=2, le=INT32_MAX)

    @field_validator("roomName")
    @classmethod
    def validate_room_name(cls, value: str) -> str:
        return _clean_text(value)

    @field_validator("quizTheme")
    @classmethod
    def validate_quiz_theme(cls, value: str) -> str:
        return _clean_text(value)


class Question(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    team: TeamCommand
    answers: list[str] = Field(..., min_length=2, max_length=6)
    statusAnswer: AnswerStatus | None = None

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, value: list[str]) -> list[str]:
        cleaned = [_clean_text(item) for item in value]
        if len(set(answer.casefold() for answer in cleaned)) != len(cleaned):
            raise ValueError("answers must be unique")
        return cleaned


class GameInfo(BaseModel):
    status: GameStatus
    activeTeam: TeamCommand
    questions: list[Question]
    activeQuestionIndex: int = Field(..., ge=0, le=INT32_MAX)
    counter: int = Field(..., ge=0, le=INT32_MAX)


class RoomMessage(BaseModel):
    command: TeamCommand
    createdAt: datetime
    text: str = Field(..., min_length=1, max_length=500)


class RoomMessageOutbound(BaseModel):
    roomId: int = Field(..., ge=1, le=INT64_MAX)
    text: str = Field(..., min_length=1, max_length=500)
    command: TeamCommand
    createdAt: datetime


class Participant(BaseModel):
    id: int = Field(..., ge=1, le=INT32_MAX, description="Socket id")
    command: TeamCommand | None = None
    role: ParticipantRole


class InfoRoom(BaseModel):
    roomId: int = Field(..., ge=1, le=INT64_MAX)
    roomName: str
    quizTheme: str
    maxParticipants: int = Field(..., ge=2, le=INT32_MAX)
    messages: list[RoomMessage] | None = None
    participants: list[Participant] | None = None
    gameInfo: GameInfo | None = None


class RoomInitHostResponse(InfoRoom):
    role: ParticipantRole


class RoomInitParticipantResponse(InfoRoom):
    role: ParticipantRole
    team: TeamCommand


class AnswerPayload(BaseModel):
    roomId: int = Field(..., ge=1, le=INT64_MAX)
    questionIndex: int = Field(..., ge=0, le=INT32_MAX)
    answer: str = Field(..., min_length=1, max_length=300)
    team: TeamCommand


class StartGameRequest(BaseModel):
    roomId: int = Field(..., ge=1, le=INT64_MAX)
