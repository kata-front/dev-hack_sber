from __future__ import annotations

import copy
from datetime import datetime
import json
from pathlib import Path
import random
import string
from threading import RLock
from uuid import uuid4

from app.models.domain import (
    AnswerStatus,
    ChatMessage,
    GameInfo,
    GameDifficulty,
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
    def __init__(self, *, storage_path: str | None = None) -> None:
        self._rooms: dict[str, Room] = {}
        self._sid_index: dict[str, tuple[str, str]] = {}
        self._storage_path = Path(storage_path) if storage_path else None
        self._lock = RLock()
        self._load_from_disk()

    def create_room(
        self,
        *,
        host_name: str,
        topic: str,
        difficulty: GameDifficulty,
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
                team=None,
            )
            room = Room(
                room_id=self._new_id(),
                pin=pin,
                topic=topic,
                difficulty=difficulty,
                questions_per_team=questions_per_team,
                max_participants=max_participants,
                timer_seconds=timer_seconds,
                status=GameStatus.WAITING,
                participants=[host],
                messages=[],
                game_info=None,
            )
            self._rooms[pin] = room
            self._persist_to_disk()
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
                team=None,
            )
            room.participants.append(participant)
            self._persist_to_disk()
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
                self._persist_to_disk()
                return Room(
                    room_id=room.room_id,
                    pin=room.pin,
                    topic=room.topic,
                    difficulty=room.difficulty,
                    questions_per_team=room.questions_per_team,
                    max_participants=room.max_participants,
                    timer_seconds=room.timer_seconds,
                    status=room.status,
                    created_at=room.created_at,
                    participants=[],
                    messages=room.messages,
                    game_info=room.game_info,
                ), removed, promoted

            self._persist_to_disk()
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

            self._assign_random_teams(room)
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
            self._persist_to_disk()
            return self._snapshot_room(room)

    def restart_game(self, *, pin: str, requested_by: str) -> Room:
        with self._lock:
            room = self._get_room(pin.upper())
            requester = self._find_participant(room, requested_by)
            if requester is None or requester.role != ParticipantRole.HOST:
                raise AccessDeniedError("Only host can restart the game.")
            if room.status != GameStatus.FINISHED:
                raise RoomStateError("Game is not finished yet.")

            room.status = GameStatus.WAITING
            room.game_info = None
            for participant in room.participants:
                participant.team = None
            self._persist_to_disk()
            return self._snapshot_room(room)

    def kick_participant(
        self,
        *,
        pin: str,
        requested_by: str,
        target_participant_id: str,
    ) -> tuple[Room, Participant]:
        with self._lock:
            room = self._get_room(pin.upper())
            requester = self._find_participant(room, requested_by)
            if requester is None or requester.role != ParticipantRole.HOST:
                raise AccessDeniedError("Only host can kick participants.")
            if room.status != GameStatus.WAITING:
                raise RoomStateError("Kick is allowed only in lobby.")
            if requested_by == target_participant_id:
                raise RoomStateError("Host cannot kick themselves.")

            target = self._find_participant(room, target_participant_id)
            if target is None:
                raise AccessDeniedError("Participant not found.")
            if target.role == ParticipantRole.HOST:
                raise RoomStateError("Host cannot be kicked.")

            updated_room, removed, _ = self.leave_room(
                pin=pin.upper(),
                participant_id=target_participant_id,
            )
            return updated_room, removed

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
            self._persist_to_disk()
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

    def detach_socket(self, *, sid: str) -> tuple[str, str] | None:
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
            participant.socket_sid = None
            self._persist_to_disk()
            return room.pin, participant.participant_id

    def remove_if_disconnected(
        self,
        *,
        pin: str,
        participant_id: str,
    ) -> tuple[Room, Participant, Participant | None] | None:
        with self._lock:
            room = self._rooms.get(pin.upper())
            if room is None:
                return None
            participant = self._find_participant(room, participant_id)
            if participant is None:
                return None
            if participant.socket_sid is not None:
                return None
            return self.leave_room(pin=pin.upper(), participant_id=participant_id)

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

        self._persist_to_disk()

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

    def _assign_random_teams(self, room: Room) -> None:
        if not room.participants:
            return
        shuffled = list(room.participants)
        random.shuffle(shuffled)
        first_team = random.choice([TeamCommand.RED, TeamCommand.BLUE])
        second_team = TeamCommand.BLUE if first_team == TeamCommand.RED else TeamCommand.RED
        for index, participant in enumerate(shuffled):
            participant.team = first_team if index % 2 == 0 else second_team

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

    def _persist_to_disk(self) -> None:
        if self._storage_path is None:
            return

        payload = {
            "rooms": [self._serialize_room(room) for room in self._rooms.values()],
        }
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._storage_path.with_suffix(self._storage_path.suffix + ".tmp")
            tmp_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            tmp_path.replace(self._storage_path)
        except Exception:
            return

    def _load_from_disk(self) -> None:
        if self._storage_path is None or not self._storage_path.exists():
            return
        try:
            raw = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except Exception:
            return
        rooms_raw = raw.get("rooms", [])
        if not isinstance(rooms_raw, list):
            return

        restored: dict[str, Room] = {}
        for item in rooms_raw:
            if not isinstance(item, dict):
                continue
            room = self._deserialize_room(item)
            if room is None:
                continue
            restored[room.pin] = room

        self._rooms = restored
        # sockets are runtime-only and cannot be restored across process restarts
        self._sid_index = {}

    def _serialize_room(self, room: Room) -> dict[str, object]:
        return {
            "roomId": room.room_id,
            "pin": room.pin,
            "topic": room.topic,
            "difficulty": room.difficulty.value,
            "questionsPerTeam": room.questions_per_team,
            "maxParticipants": room.max_participants,
            "timerSeconds": room.timer_seconds,
            "status": room.status.value,
            "createdAt": room.created_at.isoformat(),
            "participants": [self._serialize_participant(item) for item in room.participants],
            "messages": [self._serialize_message(item) for item in room.messages],
            "gameInfo": self._serialize_game_info(room.game_info) if room.game_info else None,
        }

    def _deserialize_room(self, raw: dict[str, object]) -> Room | None:
        try:
            participants_raw = raw.get("participants", [])
            messages_raw = raw.get("messages", [])
            if not isinstance(participants_raw, list) or not isinstance(messages_raw, list):
                return None
            participants = [
                item for item in (self._deserialize_participant(entry) for entry in participants_raw) if item
            ]
            messages = [item for item in (self._deserialize_message(entry) for entry in messages_raw) if item]
            game_info = self._deserialize_game_info(raw.get("gameInfo"))
            return Room(
                room_id=str(raw["roomId"]),
                pin=str(raw["pin"]).upper(),
                topic=str(raw["topic"]),
                difficulty=GameDifficulty(str(raw.get("difficulty", "medium"))),
                questions_per_team=int(raw["questionsPerTeam"]),
                max_participants=int(raw["maxParticipants"]),
                timer_seconds=int(raw["timerSeconds"]),
                status=GameStatus(str(raw["status"])),
                created_at=datetime.fromisoformat(str(raw["createdAt"])),
                participants=participants,
                messages=messages,
                game_info=game_info,
            )
        except Exception:
            return None

    def _serialize_participant(self, participant: Participant) -> dict[str, object]:
        return {
            "id": participant.participant_id,
            "name": participant.name,
            "role": participant.role.value,
            "team": participant.team.value if participant.team else None,
            "joinedAt": participant.joined_at.isoformat(),
        }

    def _deserialize_participant(self, raw: object) -> Participant | None:
        if not isinstance(raw, dict):
            return None
        try:
            team_value = raw.get("team")
            team = TeamCommand(str(team_value)) if team_value else None
            return Participant(
                participant_id=str(raw["id"]),
                name=str(raw["name"]),
                role=ParticipantRole(str(raw["role"])),
                team=team,
                joined_at=datetime.fromisoformat(str(raw["joinedAt"])),
                socket_sid=None,
            )
        except Exception:
            return None

    def _serialize_message(self, message: ChatMessage) -> dict[str, object]:
        return {
            "id": message.message_id,
            "text": message.text,
            "createdAt": message.created_at.isoformat(),
            "authorName": message.author_name,
            "command": message.command.value if message.command else None,
        }

    def _deserialize_message(self, raw: object) -> ChatMessage | None:
        if not isinstance(raw, dict):
            return None
        try:
            command_value = raw.get("command")
            command = TeamCommand(str(command_value)) if command_value else None
            return ChatMessage(
                message_id=str(raw["id"]),
                text=str(raw["text"]),
                created_at=datetime.fromisoformat(str(raw["createdAt"])),
                author_name=str(raw["authorName"]),
                command=command,
            )
        except Exception:
            return None

    def _serialize_game_info(self, game_info: GameInfo) -> dict[str, object]:
        return {
            "status": game_info.status.value,
            "activeTeam": game_info.active_team.value,
            "activeQuestionIndex": game_info.active_question_index,
            "counter": game_info.counter,
            "scores": {team.value: score for team, score in game_info.scores.items()},
            "questions": [self._serialize_question(item) for item in game_info.questions],
        }

    def _deserialize_game_info(self, raw: object) -> GameInfo | None:
        if raw is None:
            return None
        if not isinstance(raw, dict):
            return None
        try:
            scores_raw = raw.get("scores", {})
            if not isinstance(scores_raw, dict):
                return None
            questions_raw = raw.get("questions", [])
            if not isinstance(questions_raw, list):
                return None
            questions = [item for item in (self._deserialize_question(entry) for entry in questions_raw) if item]
            scores: dict[TeamCommand, int] = {}
            for team in TeamCommand:
                scores[team] = int(scores_raw.get(team.value, 0))
            return GameInfo(
                status=GameStatus(str(raw["status"])),
                active_team=TeamCommand(str(raw["activeTeam"])),
                active_question_index=int(raw["activeQuestionIndex"]),
                counter=int(raw["counter"]),
                scores=scores,
                questions=questions,
            )
        except Exception:
            return None

    def _serialize_question(self, question: Question) -> dict[str, object]:
        return {
            "id": question.question_id,
            "text": question.text,
            "options": question.options,
            "correctOption": question.correct_option,
            "team": question.team.value,
            "answered": question.answered,
            "selectedOption": question.selected_option,
            "statusAnswer": question.answer_status.value if question.answer_status else None,
        }

    def _deserialize_question(self, raw: object) -> Question | None:
        if not isinstance(raw, dict):
            return None
        try:
            status_value = raw.get("statusAnswer")
            return Question(
                question_id=str(raw["id"]),
                text=str(raw["text"]),
                options=[str(item) for item in list(raw.get("options", []))],
                correct_option=int(raw["correctOption"]),
                team=TeamCommand(str(raw["team"])),
                answered=bool(raw.get("answered", False)),
                selected_option=int(raw["selectedOption"]) if raw.get("selectedOption") is not None else None,
                answer_status=AnswerStatus(str(status_value)) if status_value else None,
            )
        except Exception:
            return None

    def _snapshot_room(self, room: Room) -> Room:
        return copy.deepcopy(room)
