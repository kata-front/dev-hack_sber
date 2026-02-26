from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GameStatus(str, Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class Team(str, Enum):
    RED = "red"
    BLUE = "blue"


@dataclass(slots=True)
class Player:
    player_id: str
    player_name: str
    team: Team
    joined_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class Room:
    pin: str
    host_name: str
    topic: str
    questions_per_team: int
    max_players: int
    status: GameStatus = GameStatus.WAITING
    created_at: datetime = field(default_factory=utc_now)
    players: dict[str, Player] = field(default_factory=dict)

