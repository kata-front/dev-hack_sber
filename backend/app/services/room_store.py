from __future__ import annotations

import copy
import random
import string
from threading import RLock
from uuid import uuid4

from app.models.domain import GameStatus, Player, Room, Team


class RoomNotFoundError(Exception):
    pass


class DuplicatePlayerNameError(Exception):
    pass


class RoomJoinClosedError(Exception):
    pass


class RoomCapacityExceededError(Exception):
    pass


class PinGenerationError(Exception):
    pass


class RoomStore:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}
        self._lock = RLock()

    def create_room(
        self,
        *,
        host_name: str,
        topic: str,
        questions_per_team: int,
        max_players: int,
    ) -> Room:
        with self._lock:
            pin = self._generate_unique_pin()
            room = Room(
                pin=pin,
                host_name=host_name,
                topic=topic,
                questions_per_team=questions_per_team,
                max_players=max_players,
            )
            self._rooms[pin] = room
            return self._snapshot_room(room)

    def join_room(self, *, pin: str, player_name: str) -> tuple[Room, Player]:
        normalized_pin = pin.upper()
        with self._lock:
            room = self._rooms.get(normalized_pin)
            if room is None:
                raise RoomNotFoundError(f"Room with PIN '{normalized_pin}' not found.")

            if room.status != GameStatus.WAITING:
                raise RoomJoinClosedError("Room is no longer accepting players.")

            if len(room.players) >= room.max_players:
                raise RoomCapacityExceededError("Room has reached its player limit.")

            requested_name = player_name.casefold()
            for existing in room.players.values():
                if existing.player_name.casefold() == requested_name:
                    raise DuplicatePlayerNameError(
                        f"Player name '{player_name}' is already used in this room."
                    )

            team = self._next_team(room)
            player = Player(
                player_id=uuid4().hex[:12],
                player_name=player_name,
                team=team,
            )
            room.players[player.player_id] = player
            room_snapshot = self._snapshot_room(room)
            return room_snapshot, room_snapshot.players[player.player_id]

    def get_room(self, *, pin: str) -> Room:
        normalized_pin = pin.upper()
        with self._lock:
            room = self._rooms.get(normalized_pin)
            if room is None:
                raise RoomNotFoundError(f"Room with PIN '{normalized_pin}' not found.")
            return self._snapshot_room(room)

    def list_rooms(self) -> list[Room]:
        with self._lock:
            rooms = sorted(self._rooms.values(), key=lambda room: room.created_at, reverse=True)
            return [self._snapshot_room(room) for room in rooms]

    def _next_team(self, room: Room) -> Team:
        red_count = sum(1 for player in room.players.values() if player.team == Team.RED)
        blue_count = sum(1 for player in room.players.values() if player.team == Team.BLUE)
        if red_count < blue_count:
            return Team.RED
        if blue_count < red_count:
            return Team.BLUE
        return random.choice([Team.RED, Team.BLUE])

    def _generate_unique_pin(self) -> str:
        alphabet = string.ascii_uppercase + string.digits
        max_attempts = 100

        for _ in range(max_attempts):
            pin = "".join(random.choices(alphabet, k=6))
            if pin not in self._rooms:
                return pin

        raise PinGenerationError("Failed to generate a unique room PIN.")

    def _snapshot_room(self, room: Room) -> Room:
        return copy.deepcopy(room)
