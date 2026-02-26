from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.domain import GameStatus, Team


def _normalize_name(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("must not be empty")
    if len(normalized) < 2:
        raise ValueError("must contain at least 2 characters")
    if not all(ch.isprintable() for ch in normalized):
        raise ValueError("contains non-printable characters")
    return normalized


class CreateRoomRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    host_name: str = Field(
        ...,
        min_length=2,
        max_length=40,
        description="Display name of the host.",
        examples=["Алексей"],
    )
    topic: str = Field(
        ...,
        min_length=3,
        max_length=120,
        description="Topic for the quiz questions.",
        examples=["Технологии будущего"],
    )
    questions_per_team: Literal[5, 6, 7] = Field(
        ...,
        description="Number of questions per team.",
        examples=[7],
    )
    max_players: int = Field(
        20,
        ge=2,
        le=100,
        description="Maximum players allowed in room.",
        examples=[12],
    )

    @field_validator("host_name")
    @classmethod
    def validate_host_name(cls, value: str) -> str:
        return _normalize_name(value)

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned


class JoinRoomRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    player_name: str = Field(
        ...,
        min_length=2,
        max_length=40,
        description="Player display name.",
        examples=["Марина"],
    )

    @field_validator("player_name")
    @classmethod
    def validate_player_name(cls, value: str) -> str:
        return _normalize_name(value)


class PlayerResponse(BaseModel):
    player_id: str = Field(..., examples=["9a1f1b2e08ab"])
    player_name: str = Field(..., examples=["Марина"])
    team: Team
    joined_at: datetime


class RoomSummaryResponse(BaseModel):
    pin: str = Field(..., pattern=r"^[A-Z0-9]{6}$", examples=["A1B2C3"])
    host_name: str
    topic: str
    questions_per_team: Literal[5, 6, 7]
    max_players: int
    players_count: int
    status: GameStatus
    created_at: datetime


class RoomDetailResponse(RoomSummaryResponse):
    teams: dict[Team, list[PlayerResponse]]


class CreateRoomResponse(BaseModel):
    room: RoomDetailResponse


class JoinRoomResponse(BaseModel):
    player: PlayerResponse
    room: RoomDetailResponse


class RoomListResponse(BaseModel):
    rooms: list[RoomSummaryResponse]


class ErrorResponse(BaseModel):
    detail: str

