from __future__ import annotations

import copy
from datetime import datetime
from threading import RLock

from app.models.domain import (
    AnswerStatus,
    GameInfo,
    GameStatus,
    Participant,
    ParticipantRole,
    Question,
    Room,
    RoomMessage,
    TeamCommand,
)


class RoomNotFoundError(Exception):
    pass


class RoomCapacityExceededError(Exception):
    pass


class RoomStore:
    def __init__(self) -> None:
        self._rooms: dict[int, Room] = {}
        self._lock = RLock()
        self._next_participant_id = 1
        self._sid_index: dict[str, tuple[int, int]] = {}

    def check_pin(self, pin: int) -> tuple[bool, int | None]:
        with self._lock:
            if pin in self._rooms:
                return True, pin
            return False, None

    def create_room(
        self,
        *,
        room_id: int,
        room_name: str,
        quiz_theme: str,
        max_participants: int,
    ) -> bool:
        with self._lock:
            if room_id in self._rooms:
                return False

            self._rooms[room_id] = Room(
                room_id=room_id,
                room_name=room_name,
                quiz_theme=quiz_theme,
                max_participants=max_participants,
                game_info=self._build_waiting_game_info(quiz_theme),
            )
            return True

    def init_room_as_host(self, *, room_id: int) -> Room:
        with self._lock:
            room = self._get_room(room_id)
            host = self._find_participant_by_role(room, ParticipantRole.HOST)
            if host is None:
                room.participants.append(
                    Participant(
                        participant_id=self._issue_participant_id(),
                        role=ParticipantRole.HOST,
                        command=TeamCommand.RED,
                    )
                )
            return self._snapshot_room(room)

    def init_room_as_participant(self, *, room_id: int) -> tuple[Room, TeamCommand]:
        with self._lock:
            room = self._get_room(room_id)
            if len(room.participants) >= room.max_participants:
                raise RoomCapacityExceededError("Room has reached maxParticipants limit.")

            team = self._next_team(room)
            room.participants.append(
                Participant(
                    participant_id=self._issue_participant_id(),
                    role=ParticipantRole.PARTICIPANT,
                    command=team,
                )
            )
            return self._snapshot_room(room), team

    def bind_host_socket(self, *, room_id: int, sid: str) -> Room:
        with self._lock:
            room = self._get_room(room_id)
            host = self._find_participant_by_role(room, ParticipantRole.HOST)
            if host is None:
                host = Participant(
                    participant_id=self._issue_participant_id(),
                    role=ParticipantRole.HOST,
                    command=TeamCommand.RED,
                )
                room.participants.append(host)

            self._bind_sid(room_id=room_id, participant=host, sid=sid)
            return self._snapshot_room(room)

    def bind_participant_socket(self, *, room_id: int, sid: str) -> tuple[Room, Participant]:
        with self._lock:
            room = self._get_room(room_id)

            existing = self._find_participant_by_sid(room, sid)
            if existing is not None:
                snapshot = self._snapshot_room(room)
                snapshot_participant = self._find_participant_by_id(snapshot, existing.participant_id)
                if snapshot_participant is None:
                    raise RuntimeError("Participant snapshot not found for existing sid binding.")
                return snapshot, snapshot_participant

            participant = self._find_unbound_participant(room)
            if participant is None:
                if len(room.participants) >= room.max_participants:
                    raise RoomCapacityExceededError("Room has reached maxParticipants limit.")
                participant = Participant(
                    participant_id=self._issue_participant_id(),
                    role=ParticipantRole.PARTICIPANT,
                    command=self._next_team(room),
                )
                room.participants.append(participant)

            self._bind_sid(room_id=room_id, participant=participant, sid=sid)
            snapshot = self._snapshot_room(room)
            snapshot_participant = self._find_participant_by_id(snapshot, participant.participant_id)
            if snapshot_participant is None:
                raise RuntimeError("Participant snapshot not found after sid binding.")
            return snapshot, snapshot_participant

    def unbind_socket(self, *, sid: str) -> tuple[int, Participant, Participant | None] | None:
        with self._lock:
            sid_mapping = self._sid_index.pop(sid, None)
            if sid_mapping is None:
                sid_mapping = self._find_sid_mapping_without_index(sid)
                if sid_mapping is None:
                    return None

            room_id, participant_id = sid_mapping
            room = self._rooms.get(room_id)
            if room is None:
                return None

            participant = self._find_participant_by_id(room, participant_id)
            if participant is None:
                return None

            disconnected_participant = copy.deepcopy(participant)
            was_host = participant.role == ParticipantRole.HOST

            room.participants = [p for p in room.participants if p.participant_id != participant_id]

            promoted_host: Participant | None = None
            if was_host and room.participants:
                promoted_host = room.participants[0]
                promoted_host.role = ParticipantRole.HOST
                if promoted_host.command is None:
                    promoted_host.command = TeamCommand.RED
                if promoted_host.socket_sid:
                    self._sid_index[promoted_host.socket_sid] = (room_id, promoted_host.participant_id)

            return room_id, disconnected_participant, copy.deepcopy(promoted_host) if promoted_host else None

    def _find_sid_mapping_without_index(self, sid: str) -> tuple[int, int] | None:
        for room_id, room in self._rooms.items():
            for participant in room.participants:
                if participant.socket_sid == sid:
                    return room_id, participant.participant_id
        return None

    def get_room_snapshot(self, *, room_id: int) -> Room:
        with self._lock:
            room = self._get_room(room_id)
            return self._snapshot_room(room)

    def add_message(
        self,
        *,
        room_id: int,
        text: str,
        command: TeamCommand,
        created_at: datetime,
    ) -> RoomMessage:
        with self._lock:
            room = self._get_room(room_id)
            message = RoomMessage(command=command, created_at=created_at, text=text)
            room.messages.append(message)
            return copy.deepcopy(message)

    def start_game(self, *, room_id: int, payload_room_id: int) -> GameInfo:
        with self._lock:
            room = self._get_room(room_id)
            if payload_room_id != room_id:
                raise ValueError("roomId in request body must match path roomId.")

            if room.game_info is None:
                room.game_info = self._build_waiting_game_info(room.quiz_theme)

            room.game_info.status = GameStatus.ACTIVE
            room.game_info.active_team = TeamCommand.RED
            room.game_info.active_question_index = 0
            room.game_info.counter = 30
            return copy.deepcopy(room.game_info)

    def get_current_question(self, *, room_id: int) -> Question | None:
        with self._lock:
            room = self._get_room(room_id)
            game_info = room.game_info
            if game_info is None:
                return None
            index = game_info.active_question_index
            if index < 0 or index >= len(game_info.questions):
                return None
            return copy.deepcopy(game_info.questions[index])

    def submit_answer(
        self,
        *,
        room_id: int,
        question_index: int,
        answer: str,
        team: TeamCommand,
    ) -> tuple[AnswerStatus, Question | None, GameStatus]:
        with self._lock:
            room = self._get_room(room_id)
            game_info = room.game_info
            if game_info is None or game_info.status != GameStatus.ACTIVE:
                return AnswerStatus.INCORRECT, None, GameStatus.WAITING

            if question_index != game_info.active_question_index:
                return AnswerStatus.INCORRECT, None, game_info.status

            if question_index < 0 or question_index >= len(game_info.questions):
                return AnswerStatus.INCORRECT, None, game_info.status

            question = game_info.questions[question_index]
            if team != game_info.active_team:
                answer_status = AnswerStatus.INCORRECT
            else:
                correct_answer = question.answers[0] if question.answers else ""
                answer_status = (
                    AnswerStatus.CORRECT
                    if answer.strip().casefold() == correct_answer.strip().casefold()
                    else AnswerStatus.INCORRECT
                )

            question.status_answer = answer_status
            next_question = self._advance_question(game_info)
            return answer_status, copy.deepcopy(next_question) if next_question else None, game_info.status

    def set_counter(self, *, room_id: int, counter: int) -> int:
        with self._lock:
            room = self._get_room(room_id)
            if room.game_info is None:
                room.game_info = self._build_waiting_game_info(room.quiz_theme)
            room.game_info.counter = max(0, counter)
            return room.game_info.counter

    def handle_timer_end(self, *, room_id: int) -> tuple[Question | None, GameStatus]:
        with self._lock:
            room = self._get_room(room_id)
            game_info = room.game_info
            if game_info is None:
                return None, GameStatus.WAITING
            if game_info.status != GameStatus.ACTIVE:
                return None, game_info.status

            idx = game_info.active_question_index
            if 0 <= idx < len(game_info.questions):
                current_question = game_info.questions[idx]
                if current_question.status_answer is None:
                    current_question.status_answer = AnswerStatus.INCORRECT

            next_question = self._advance_question(game_info)
            return copy.deepcopy(next_question) if next_question else None, game_info.status

    def _advance_question(self, game_info: GameInfo) -> Question | None:
        next_index = game_info.active_question_index + 1
        if next_index >= len(game_info.questions):
            game_info.status = GameStatus.FINISHED
            return None

        game_info.active_question_index = next_index
        game_info.active_team = game_info.questions[next_index].team
        game_info.counter = 30
        return game_info.questions[next_index]

    def _bind_sid(self, *, room_id: int, participant: Participant, sid: str) -> None:
        previous_sid = participant.socket_sid
        if previous_sid and previous_sid != sid:
            self._sid_index.pop(previous_sid, None)

        participant.socket_sid = sid
        self._sid_index[sid] = (room_id, participant.participant_id)

    def _get_room(self, room_id: int) -> Room:
        room = self._rooms.get(room_id)
        if room is None:
            raise RoomNotFoundError(f"Room with id {room_id} not found.")
        return room

    def _issue_participant_id(self) -> int:
        participant_id = self._next_participant_id
        self._next_participant_id += 1
        return participant_id

    def _find_participant_by_role(
        self,
        room: Room,
        role: ParticipantRole,
    ) -> Participant | None:
        for participant in room.participants:
            if participant.role == role:
                return participant
        return None

    def _find_participant_by_sid(self, room: Room, sid: str) -> Participant | None:
        for participant in room.participants:
            if participant.socket_sid == sid:
                return participant
        return None

    def _find_unbound_participant(self, room: Room) -> Participant | None:
        for participant in room.participants:
            if participant.role == ParticipantRole.PARTICIPANT and participant.socket_sid is None:
                return participant
        return None

    def _find_participant_by_id(self, room: Room, participant_id: int) -> Participant | None:
        for participant in room.participants:
            if participant.participant_id == participant_id:
                return participant
        return None

    def _next_team(self, room: Room) -> TeamCommand:
        red_count = sum(1 for item in room.participants if item.command == TeamCommand.RED)
        blue_count = sum(1 for item in room.participants if item.command == TeamCommand.BLUE)
        if red_count <= blue_count:
            return TeamCommand.RED
        return TeamCommand.BLUE

    def _build_waiting_game_info(self, quiz_theme: str) -> GameInfo:
        return GameInfo(
            status=GameStatus.WAITING,
            active_team=TeamCommand.RED,
            questions=self._default_questions(quiz_theme),
            active_question_index=0,
            counter=30,
        )

    def _default_questions(self, quiz_theme: str) -> list[Question]:
        return [
            Question(
                question=f"{quiz_theme}: вопрос для красной команды №1",
                team=TeamCommand.RED,
                answers=["A", "B", "C", "D"],
            ),
            Question(
                question=f"{quiz_theme}: вопрос для синей команды №1",
                team=TeamCommand.BLUE,
                answers=["A", "B", "C", "D"],
            ),
        ]

    def _snapshot_room(self, room: Room) -> Room:
        return copy.deepcopy(room)
