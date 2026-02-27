from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GameStatus(str, Enum):
    WAITING = "waiting"
    ACTIVE = "active"
    FINISHED = "finished"


class TeamCommand(str, Enum):
    RED = "red"
    BLUE = "blue"


class ParticipantRole(str, Enum):
    HOST = "host"
    PARTICIPANT = "participant"


class AnswerStatus(str, Enum):
    CORRECT = "correct"
    INCORRECT = "incorrect"


@dataclass(slots=True)
class Question:
    question_id: str
    text: str
    options: list[str]
    correct_option: int
    team: TeamCommand
    answered: bool = False
    selected_option: int | None = None
    answer_status: AnswerStatus | None = None


@dataclass(slots=True)
class GameInfo:
    status: GameStatus
    active_team: TeamCommand
    active_question_index: int
    counter: int
    scores: dict[TeamCommand, int]
    questions: list[Question]


@dataclass(slots=True)
class ChatMessage:
    message_id: str
    text: str
    created_at: datetime
    author_name: str
    command: TeamCommand | None


@dataclass(slots=True)
class Participant:
    participant_id: str
    name: str
    role: ParticipantRole
    team: TeamCommand | None
    joined_at: datetime = field(default_factory=utc_now)
    socket_sid: str | None = None


@dataclass(slots=True)
class Room:
    room_id: str
    pin: str
    topic: str
    questions_per_team: int
    max_participants: int
    timer_seconds: int
    status: GameStatus = GameStatus.WAITING
    created_at: datetime = field(default_factory=utc_now)
    participants: list[Participant] = field(default_factory=list)
    messages: list[ChatMessage] = field(default_factory=list)
    game_info: GameInfo | None = None


@dataclass(slots=True)
class SessionData:
    session_id: str
    room_pin: str
    participant_id: str
    name: str
    role: ParticipantRole
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class SubmitAnswerResult:
    answer_status: AnswerStatus
    answered_question: Question
    next_question: Question | None
    game_info: GameInfo
    game_finished: bool


@dataclass(slots=True)
class TimerEndResult:
    next_question: Question | None
    game_info: GameInfo
    game_finished: bool


@dataclass(slots=True)
class GeneratedQuestion:
    text: str
    options: list[str]
    correct_option: int


JSONDict = dict[str, Any]

