from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GameStatus(str, Enum):
    WAITING = "waiting"
    ACTIVE = "active"
    FINISHED = "finished"


class TeamCommand(str, Enum):
    RED = "red"
    BLUE = "blue"


class AnswerStatus(str, Enum):
    CORRECT = "correct"
    INCORRECT = "incorrect"


class ParticipantRole(str, Enum):
    HOST = "host"
    PARTICIPANT = "participant"


@dataclass(slots=True)
class Question:
    question: str
    team: TeamCommand
    answers: list[str]
    status_answer: AnswerStatus | None = None


@dataclass(slots=True)
class GameInfo:
    status: GameStatus = GameStatus.WAITING
    active_team: TeamCommand = TeamCommand.RED
    questions: list[Question] = field(default_factory=list)
    active_question_index: int = 0
    counter: int = 30


@dataclass(slots=True)
class RoomMessage:
    command: TeamCommand
    created_at: datetime
    text: str


@dataclass(slots=True)
class Participant:
    participant_id: int
    role: ParticipantRole
    command: TeamCommand | None = None
    socket_sid: str | None = None


@dataclass(slots=True)
class Room:
    room_id: int
    room_name: str
    quiz_theme: str
    max_participants: int
    messages: list[RoomMessage] = field(default_factory=list)
    participants: list[Participant] = field(default_factory=list)
    game_info: GameInfo | None = None
