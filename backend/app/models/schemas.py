from __future__ import annotations

from datetime import datetime
import re
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.models.domain import AnswerStatus, GameStatus, ParticipantRole, TeamCommand

PIN_PATTERN = r"^[A-Za-z0-9]{6}$"
PIN_COMPILED = re.compile(r"^[A-Z0-9]{6}$")


def _normalize_human_name(value: str) -> str:
    normalized = " ".join(value.split())
    if len(normalized) < 2:
        raise ValueError("name must contain at least 2 characters")
    return normalized


def _normalize_text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("must not be empty")
    return normalized


class ScoreResponse(BaseModel):
    red: int = Field(0, ge=0)
    blue: int = Field(0, ge=0)


class ParticipantResponse(BaseModel):
    id: str
    name: str
    role: ParticipantRole
    team: TeamCommand | None = None
    joinedAt: datetime


class RoomMessageResponse(BaseModel):
    id: str
    text: str
    createdAt: datetime
    authorName: str
    command: TeamCommand | None = None


class QuestionResponse(BaseModel):
    id: str
    text: str
    options: list[str]
    team: TeamCommand
    selectedOption: int | None = None
    statusAnswer: AnswerStatus | None = None


class GameInfoResponse(BaseModel):
    status: GameStatus
    activeTeam: TeamCommand
    activeQuestionIndex: int = Field(ge=0)
    counter: int = Field(ge=0)
    scores: ScoreResponse
    questions: list[QuestionResponse]


class RoomResponse(BaseModel):
    pin: str = Field(pattern=r"^[A-Z0-9]{6}$")
    topic: str
    questionsPerTeam: Literal[5, 6, 7]
    maxParticipants: int = Field(ge=2, le=100)
    timerSeconds: int = Field(ge=10, le=120)
    status: GameStatus
    createdAt: datetime
    participants: list[ParticipantResponse]
    messages: list[RoomMessageResponse]
    gameInfo: GameInfoResponse | None = None


class SessionInfoResponse(BaseModel):
    roomPin: str = Field(pattern=r"^[A-Z0-9]{6}$")
    participantId: str
    name: str
    role: ParticipantRole


class AuthRoomResponse(BaseModel):
    session: SessionInfoResponse
    participant: ParticipantResponse
    room: RoomResponse


class SessionStateResponse(BaseModel):
    authenticated: bool
    session: SessionInfoResponse | None = None
    participant: ParticipantResponse | None = None
    room: RoomResponse | None = None


class CreateRoomRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    hostName: str = Field(..., min_length=2, max_length=40)
    topic: str = Field(..., min_length=3, max_length=120)
    questionsPerTeam: Literal[5, 6, 7]
    maxParticipants: int = Field(20, ge=2, le=100)
    timerSeconds: int = Field(30, ge=10, le=120)

    @field_validator("hostName")
    @classmethod
    def validate_host_name(cls, value: str) -> str:
        return _normalize_human_name(value)

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        return _normalize_text(value)


class JoinRoomRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    playerName: str = Field(..., min_length=2, max_length=40)

    @field_validator("playerName")
    @classmethod
    def validate_player_name(cls, value: str) -> str:
        return _normalize_human_name(value)


class CheckPinRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    pin: str | int = Field(validation_alias=AliasChoices("pin", "roomId"))

    @field_validator("pin", mode="before")
    @classmethod
    def validate_pin(cls, value: str | int) -> str:
        normalized = str(value).strip().upper()
        if not normalized:
            raise ValueError("pin must not be empty")
        return normalized


class CheckPinResponse(BaseModel):
    ok: bool
    roomPin: str | None = None
    roomId: str | None = None


class StartGameResponse(BaseModel):
    room: RoomResponse
    gameInfo: GameInfoResponse
    generationSource: Literal["ai", "fallback"] = "fallback"
    generationMessage: str | None = None


class SubmitAnswerRequest(BaseModel):
    optionIndex: int = Field(..., ge=0, le=3)


class SubmitAnswerResponse(BaseModel):
    answerStatus: AnswerStatus
    room: RoomResponse
    gameInfo: GameInfoResponse
    nextQuestion: QuestionResponse | None = None


class SendMessageRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(..., min_length=1, max_length=400)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _normalize_text(value)


class LeaveRoomResponse(BaseModel):
    ok: bool


class LogoutResponse(BaseModel):
    ok: bool


class ErrorResponse(BaseModel):
    detail: str
