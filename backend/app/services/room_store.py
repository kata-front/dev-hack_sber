from __future__ import annotations

import copy
import random
import string
from threading import RLock
from uuid import uuid4

from app.models.domain import (
    AnswerStatus,
    ChatMessage,
    GameInfo,
    GameStatus,
    GeneratedQuestion,
    Participant,
    ParticipantRole,
    Question,
    Room,
    SubmitAnswerResult,
    TeamCommand,
    TimerEndResult,
    utc_now,
)


class RoomNotFoundError(Exception):
    pass


class RoomAlreadyJoinedError(Exception):
    pass


class RoomCapacityExceededError(Exception):
    pass


class RoomStateError(Exception):
    pass


class AccessDeniedError(Exception):
    pass


class RoomStore:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}
        self._sid_index: dict[str, tuple[str, str]] = {}
        self._lock = RLock()

    def create_room(
        self,
        *,
        host_name: str,
        topic: str,
        questions_per_team: int,
        max_participants: int,
        timer_seconds: int,
    ) -> tuple[Room, Participant]:
        with self._lock:
            pin = self._generate_unique_pin()
            host = Participant(
                participant_id=self._new_id(),
                name=host_name,
                role=ParticipantRole.HOST,
                team=random.choice([TeamCommand.RED, TeamCommand.BLUE]),
            )
            room = Room(
                room_id=self._new_id(),
                pin=pin,
                topic=topic,
                questions_per_team=questions_per_team,
                max_participants=max_participants,
                timer_seconds=timer_seconds,
                status=GameStatus.WAITING,
                participants=[host],
                messages=[],
                game_info=None,
            )
            self._rooms[pin] = room
            snapshot = self._snapshot_room(room)
            return snapshot, snapshot.participants[0]

    def check_pin(self, *, pin: str) -> bool:
        with self._lock:
            return pin.upper() in self._rooms

    def join_room(self, *, pin: str, player_name: str) -> tuple[Room, Participant]:
        normalized_pin = pin.upper()
        with self._lock:
            room = self._get_room(normalized_pin)
            if room.status != GameStatus.WAITING:
                raise RoomStateError("Game already started in this room.")
            if len(room.participants) >= room.max_participants:
                raise RoomCapacityExceededError("Room has reached participant limit.")
            if self._has_name_collision(room, player_name):
                raise RoomStateError("This name is already used in the room.")

            participant = Participant(
                participant_id=self._new_id(),
                name=player_name,
                role=ParticipantRole.PARTICIPANT,
                team=self._next_team(room),
            )
            room.participants.append(participant)
            snapshot = self._snapshot_room(room)
            created = self._find_participant(snapshot, participant.participant_id)
            if created is None:
                raise RuntimeError("Failed to locate participant after join.")
            return snapshot, created

    def get_room_snapshot(self, *, pin: str) -> Room:
        with self._lock:
            room = self._get_room(pin.upper())
            return self._snapshot_room(room)

    def get_participant_snapshot(self, *, pin: str, participant_id: str) -> Participant:
        with self._lock:
            room = self._get_room(pin.upper())
            participant = self._find_participant(room, participant_id)
            if participant is None:
                raise AccessDeniedError("Participant not found in this room.")
            return copy.deepcopy(participant)

    def leave_room(self, *, pin: str, participant_id: str) -> tuple[Room, Participant, Participant | None]:
        with self._lock:
            room = self._get_room(pin.upper())
            participant = self._find_participant(room, participant_id)
            if participant is None:
                raise AccessDeniedError("Participant not found in this room.")

            for sid, mapping in list(self._sid_index.items()):
                mapped_pin, mapped_participant_id = mapping
                if mapped_pin == room.pin and mapped_participant_id == participant_id:
                    self._sid_index.pop(sid, None)

            removed = copy.deepcopy(participant)
            room.participants = [item for item in room.participants if item.participant_id != participant_id]

            promoted: Participant | None = None
            if participant.role == ParticipantRole.HOST and room.participants:
                new_host = room.participants[0]
                new_host.role = ParticipantRole.HOST
                promoted = copy.deepcopy(new_host)

            if not room.participants:
                self._rooms.pop(room.pin, None)
                return Room(
                    room_id=room.room_id,
                    pin=room.pin,
                    topic=room.topic,
                    questions_per_team=room.questions_per_team,
                    max_participants=room.max_participants,
                    timer_seconds=room.timer_seconds,
                    status=room.status,
                    created_at=room.created_at,
                    participants=[],
                    messages=room.messages,
                    game_info=room.game_info,
                ), removed, promoted

            snapshot = self._snapshot_room(room)
            return snapshot, removed, promoted

    def start_game(
        self,
        *,
        pin: str,
        requested_by: str,
        generated_questions: list[GeneratedQuestion],
    ) -> Room:
        with self._lock:
            room = self._get_room(pin.upper())
            if room.status != GameStatus.WAITING:
                raise RoomStateError("Game already started.")
            requester = self._find_participant(room, requested_by)
            if requester is None or requester.role != ParticipantRole.HOST:
                raise AccessDeniedError("Only host can start the game.")
            if len(room.participants) < 2:
                raise RoomStateError("Need at least 2 participants to start.")

            questions = self._build_questions(room=room, generated_questions=generated_questions)
            room.status = GameStatus.ACTIVE
            room.game_info = GameInfo(
                status=GameStatus.ACTIVE,
                active_team=questions[0].team,
                active_question_index=0,
                counter=room.timer_seconds,
                scores={TeamCommand.RED: 0, TeamCommand.BLUE: 0},
                questions=questions,
            )
            return self._snapshot_room(room)

    def submit_answer(
        self,
        *,
        pin: str,
        participant_id: str,
        option_index: int,
    ) -> SubmitAnswerResult:
        with self._lock:
            room = self._get_room(pin.upper())
            if room.game_info is None or room.status != GameStatus.ACTIVE:
                raise RoomStateError("Game is not active.")

            participant = self._find_participant(room, participant_id)
            if participant is None:
                raise AccessDeniedError("Participant not found.")
            if participant.team != room.game_info.active_team:
                raise AccessDeniedError("It is not your team turn.")

            question = room.game_info.questions[room.game_info.active_question_index]
            if question.answered:
                raise RoomStateError("Current question already answered.")

            question.answered = True
            question.selected_option = option_index
            if option_index == question.correct_option:
                question.answer_status = AnswerStatus.CORRECT
                room.game_info.scores[participant.team] += 1
            else:
                question.answer_status = AnswerStatus.INCORRECT

            return self._advance_after_answer(room, answered_question=question)

    def add_message(self, *, pin: str, participant_id: str, text: str) -> tuple[Room, ChatMessage]:
        with self._lock:
            room = self._get_room(pin.upper())
            participant = self._find_participant(room, participant_id)
            if participant is None:
                raise AccessDeniedError("Participant not found.")

            message = ChatMessage(
                message_id=self._new_id(),
                text=text,
                created_at=utc_now(),
                author_name=participant.name,
                command=participant.team,
            )
            room.messages.append(message)
            return self._snapshot_room(room), copy.deepcopy(message)

    def bind_socket(self, *, pin: str, participant_id: str, sid: str) -> Room:
        with self._lock:
            room = self._get_room(pin.upper())
            participant = self._find_participant(room, participant_id)
            if participant is None:
                raise AccessDeniedError("Participant not found.")
            if participant.socket_sid and participant.socket_sid != sid:
                self._sid_index.pop(participant.socket_sid, None)
            participant.socket_sid = sid
            self._sid_index[sid] = (room.pin, participant.participant_id)
            return self._snapshot_room(room)

    def unbind_socket(self, *, sid: str) -> tuple[Room, Participant, Participant | None] | None:
        with self._lock:
            mapping = self._sid_index.pop(sid, None)
            if mapping is None:
                mapping = self._find_mapping_by_sid(sid)
                if mapping is None:
                    return None
            pin, participant_id = mapping
            room = self._rooms.get(pin)
            if room is None:
                return None
            participant = self._find_participant(room, participant_id)
            if participant is None:
                return None
            if participant.socket_sid != sid:
                return None
            return self.leave_room(pin=pin, participant_id=participant.participant_id)

    def get_bound_participant(self, *, sid: str) -> tuple[str, str] | None:
        with self._lock:
            mapping = self._sid_index.get(sid)
            if mapping is not None:
                return mapping
            return self._find_mapping_by_sid(sid)

    def set_counter(self, *, pin: str, counter: int) -> Room:
        with self._lock:
            room = self._get_room(pin.upper())
            if room.game_info is None:
                raise RoomStateError("Game not initialized.")
            room.game_info.counter = max(0, counter)
            return self._snapshot_room(room)

    def handle_timer_end(self, *, pin: str) -> TimerEndResult:
        with self._lock:
            room = self._get_room(pin.upper())
            if room.game_info is None:
                raise RoomStateError("Game not initialized.")
            if room.status != GameStatus.ACTIVE:
                raise RoomStateError("Game is not active.")

            question = room.game_info.questions[room.game_info.active_question_index]
            if not question.answered:
                question.answered = True
                question.answer_status = AnswerStatus.INCORRECT

            submission = self._advance_after_answer(room, answered_question=question)
            return TimerEndResult(
                next_question=submission.next_question,
                game_info=submission.game_info,
                game_finished=submission.game_finished,
            )

    def _advance_after_answer(self, room: Room, *, answered_question: Question) -> SubmitAnswerResult:
        assert room.game_info is not None
        next_index = room.game_info.active_question_index + 1
        next_question: Question | None = None
        game_finished = False

        if next_index >= len(room.game_info.questions):
            room.status = GameStatus.FINISHED
            room.game_info.status = GameStatus.FINISHED
            game_finished = True
        else:
            room.game_info.active_question_index = next_index
            room.game_info.active_team = room.game_info.questions[next_index].team
            room.game_info.counter = room.timer_seconds
            next_question = copy.deepcopy(room.game_info.questions[next_index])

        return SubmitAnswerResult(
            answer_status=answered_question.answer_status or AnswerStatus.INCORRECT,
            answered_question=copy.deepcopy(answered_question),
            next_question=next_question,
            game_info=copy.deepcopy(room.game_info),
            game_finished=game_finished,
        )

    def _build_questions(self, *, room: Room, generated_questions: list[GeneratedQuestion]) -> list[Question]:
        total_questions = room.questions_per_team * 2
        if len(generated_questions) < total_questions:
            raise RoomStateError("Not enough generated questions for the game.")

        questions: list[Question] = []
        for index in range(total_questions):
            team = TeamCommand.RED if index % 2 == 0 else TeamCommand.BLUE
            item = generated_questions[index]
            questions.append(
                Question(
                    question_id=self._new_id(),
                    text=item.text,
                    options=item.options,
                    correct_option=item.correct_option,
                    team=team,
                )
            )
        return questions

    def _get_room(self, pin: str) -> Room:
        room = self._rooms.get(pin)
        if room is None:
            raise RoomNotFoundError(f"Room with PIN '{pin}' not found.")
        return room

    def _next_team(self, room: Room) -> TeamCommand:
        red_count = 0
        blue_count = 0
        for participant in room.participants:
            if participant.team is None:
                continue
            if participant.team == TeamCommand.RED:
                red_count += 1
            elif participant.team == TeamCommand.BLUE:
                blue_count += 1
        if red_count < blue_count:
            return TeamCommand.RED
        if blue_count < red_count:
            return TeamCommand.BLUE
        return random.choice([TeamCommand.RED, TeamCommand.BLUE])

    def _find_participant(self, room: Room, participant_id: str) -> Participant | None:
        for participant in room.participants:
            if participant.participant_id == participant_id:
                return participant
        return None

    def _find_mapping_by_sid(self, sid: str) -> tuple[str, str] | None:
        for room in self._rooms.values():
            for participant in room.participants:
                if participant.socket_sid == sid:
                    return room.pin, participant.participant_id
        return None

    def _has_name_collision(self, room: Room, name: str) -> bool:
        needle = name.casefold()
        for participant in room.participants:
            if participant.name.casefold() == needle:
                return True
        return False

    def _generate_unique_pin(self) -> str:
        alphabet = string.ascii_uppercase + string.digits
        max_attempts = 200
        for _ in range(max_attempts):
            pin = "".join(random.choices(alphabet, k=6))
            if pin not in self._rooms:
                return pin
        raise RuntimeError("Failed to generate unique PIN.")

    def _new_id(self) -> str:
        return uuid4().hex[:12]

    def _snapshot_room(self, room: Room) -> Room:
        return copy.deepcopy(room)
