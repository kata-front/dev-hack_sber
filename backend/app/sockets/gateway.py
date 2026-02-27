from __future__ import annotations

import asyncio
from typing import Any

import socketio
from pydantic import BaseModel, Field

from app.models.domain import (
    ChatMessage,
    GameInfo,
    GameStatus,
    Participant,
    Question,
    Room,
    TeamCommand,
    TimerEndResult,
)
from app.models.schemas import (
    GameInfoResponse,
    ParticipantResponse,
    QuestionResponse,
    RoomMessageResponse,
    RoomResponse,
    ScoreResponse,
)
from app.services.question_generator import QuestionGenerator
from app.services.room_store import (
    AccessDeniedError,
    RoomCapacityExceededError,
    RoomNotFoundError,
    RoomStateError,
    RoomStore,
)
from app.services.session_store import SessionStore


class SocketJoinPayload(BaseModel):
    pin: str = Field(..., pattern=r"^[A-Za-z0-9]{6}$")
    participantId: str


class SocketMessagePayload(BaseModel):
    pin: str = Field(..., pattern=r"^[A-Za-z0-9]{6}$")
    text: str = Field(..., min_length=1, max_length=400)


class SocketStartPayload(BaseModel):
    pin: str = Field(..., pattern=r"^[A-Za-z0-9]{6}$")


class SocketAnswerPayload(BaseModel):
    pin: str = Field(..., pattern=r"^[A-Za-z0-9]{6}$")
    optionIndex: int = Field(..., ge=0, le=3)


class SocketLeavePayload(BaseModel):
    pin: str = Field(..., pattern=r"^[A-Za-z0-9]{6}$")


class SocketGateway:
    def __init__(
        self,
        *,
        sio: socketio.AsyncServer,
        room_store: RoomStore,
        session_store: SessionStore,
        question_generator: QuestionGenerator,
    ) -> None:
        self._sio = sio
        self._room_store = room_store
        self._session_store = session_store
        self._question_generator = question_generator
        self._timer_tasks: dict[str, asyncio.Task[None]] = {}

    def register_handlers(self) -> None:
        self._sio.on("create_room", handler=self._on_create_room)
        self._sio.on("join_room", handler=self._on_join_room)
        self._sio.on("message", handler=self._on_message)
        self._sio.on("start_game", handler=self._on_start_game)
        self._sio.on("answer", handler=self._on_answer)
        self._sio.on("leave_room", handler=self._on_leave_room)
        self._sio.on("disconnect", handler=self._on_disconnect)

    async def _on_create_room(self, sid: str, raw_payload: Any) -> None:
        try:
            payload = SocketJoinPayload.model_validate(raw_payload)
            room = self._room_store.bind_socket(
                pin=payload.pin.upper(),
                participant_id=payload.participantId,
                sid=sid,
            )
        except (ValueError, RoomNotFoundError, AccessDeniedError) as exc:
            await self._emit_error(sid=sid, message=str(exc))
            return

        room_name = self._socket_room(room.pin)
        await self._sio.enter_room(sid, room_name)
        await self._sio.emit("room_created", self._to_room_payload(room), room=sid)

    async def _on_join_room(self, sid: str, raw_payload: Any) -> None:
        try:
            payload = SocketJoinPayload.model_validate(raw_payload)
            room = self._room_store.bind_socket(
                pin=payload.pin.upper(),
                participant_id=payload.participantId,
                sid=sid,
            )
            participant = self._room_store.get_participant_snapshot(
                pin=payload.pin.upper(),
                participant_id=payload.participantId,
            )
        except (ValueError, RoomNotFoundError, AccessDeniedError) as exc:
            await self._emit_error(sid=sid, message=str(exc))
            return

        room_name = self._socket_room(room.pin)
        await self._sio.enter_room(sid, room_name)
        await self._sio.emit("room_joined", self._to_room_payload(room), room=sid)
        await self._sio.emit(
            "player_joined",
            self._to_participant_payload(participant),
            room=room_name,
            skip_sid=sid,
        )

    async def _on_message(self, sid: str, raw_payload: Any) -> None:
        try:
            payload = SocketMessagePayload.model_validate(raw_payload)
            actor = self._require_bound_actor(sid=sid, pin=payload.pin.upper())
            _, message = self._room_store.add_message(
                pin=payload.pin.upper(),
                participant_id=actor[1],
                text=payload.text,
            )
        except (ValueError, RoomNotFoundError, AccessDeniedError) as exc:
            await self._emit_error(sid=sid, message=str(exc))
            return

        await self._sio.emit(
            "message",
            self._to_message_payload(message),
            room=self._socket_room(payload.pin.upper()),
        )

    async def _on_start_game(self, sid: str, raw_payload: Any) -> None:
        room_name: str | None = None
        preparing_emitted = False
        try:
            payload = SocketStartPayload.model_validate(raw_payload)
            _, participant_id = self._require_bound_actor(sid=sid, pin=payload.pin.upper())
            room_snapshot = self._room_store.get_room_snapshot(pin=payload.pin.upper())
            room_name = self._socket_room(room_snapshot.pin)
            await self._sio.emit(
                "game_preparing",
                {
                    "preparing": True,
                    "topic": room_snapshot.topic,
                    "questionsPerTeam": room_snapshot.questions_per_team,
                },
                room=room_name,
            )
            preparing_emitted = True
            generation = await self._question_generator.generate_questions(
                topic=room_snapshot.topic,
                questions_per_team=room_snapshot.questions_per_team,
            )
            room = self._room_store.start_game(
                pin=payload.pin.upper(),
                requested_by=participant_id,
                generated_questions=generation.questions,
            )
        except (ValueError, RoomNotFoundError, AccessDeniedError, RoomStateError, Exception) as exc:
            if preparing_emitted and room_name is not None:
                await self._sio.emit(
                    "game_preparing",
                    {"preparing": False, "error": str(exc)},
                    room=room_name,
                )
            await self._emit_error(sid=sid, message=str(exc))
            return

        assert room.game_info is not None
        room_name = self._socket_room(room.pin)
        await self._sio.emit(
            "game_preparing",
            {
                "preparing": False,
                "source": generation.source,
                "message": generation.reason,
            },
            room=room_name,
        )
        await self._sio.emit("game_started", self._to_game_info_payload(room.game_info), room=room_name)
        await self._sio.emit(
            "new_question",
            self._to_question_payload(room.game_info.questions[room.game_info.active_question_index]),
            room=room_name,
        )
        await self._restart_timer(pin=room.pin)

    async def _on_answer(self, sid: str, raw_payload: Any) -> None:
        try:
            payload = SocketAnswerPayload.model_validate(raw_payload)
            _, participant_id = self._require_bound_actor(sid=sid, pin=payload.pin.upper())
            submit_result = self._room_store.submit_answer(
                pin=payload.pin.upper(),
                participant_id=participant_id,
                option_index=payload.optionIndex,
            )
        except (ValueError, RoomNotFoundError, AccessDeniedError, RoomStateError) as exc:
            await self._emit_error(sid=sid, message=str(exc))
            return

        room_name = self._socket_room(payload.pin.upper())
        await self._sio.emit("check_answer", submit_result.answer_status.value, room=room_name)

        if submit_result.game_finished:
            await self._cancel_timer(pin=payload.pin.upper())
            await self._sio.emit("game_finished", submit_result.game_info.status.value, room=room_name)
            return

        if submit_result.next_question is not None:
            question_payload = self._to_question_payload(submit_result.next_question)
            await self._sio.emit("new_question", question_payload, room=room_name)
            await self._sio.emit("next_question", question_payload, room=room_name)
            await self._restart_timer(pin=payload.pin.upper())

    async def _on_leave_room(self, sid: str, raw_payload: Any) -> None:
        try:
            payload = SocketLeavePayload.model_validate(raw_payload)
            _, participant_id = self._require_bound_actor(sid=sid, pin=payload.pin.upper())
            room, left_participant, promoted = self._room_store.leave_room(
                pin=payload.pin.upper(),
                participant_id=participant_id,
            )
        except (ValueError, RoomNotFoundError, AccessDeniedError) as exc:
            await self._emit_error(sid=sid, message=str(exc))
            return

        await self._cancel_timer_if_empty(room=room)
        room_name = self._socket_room(payload.pin.upper())
        await self._sio.emit(
            "user_left",
            self._to_participant_payload(left_participant),
            room=room_name,
            skip_sid=sid,
        )
        if promoted is not None:
            self._session_store.update_role(
                room_pin=payload.pin.upper(),
                participant_id=promoted.participant_id,
                role=promoted.role,
            )
            await self._sio.emit("host_changed", self._to_participant_payload(promoted), room=room_name)
        await self._sio.leave_room(sid, room_name)

    async def _on_disconnect(self, sid: str, *args: Any) -> None:
        result = self._room_store.unbind_socket(sid=sid)
        if result is None:
            return

        room, left_participant, promoted = result
        await self._cancel_timer_if_empty(room=room)
        room_name = self._socket_room(room.pin)

        await self._sio.emit(
            "user_left",
            self._to_participant_payload(left_participant),
            room=room_name,
            skip_sid=sid,
        )
        if promoted is not None:
            self._session_store.update_role(
                room_pin=room.pin,
                participant_id=promoted.participant_id,
                role=promoted.role,
            )
            await self._sio.emit("host_changed", self._to_participant_payload(promoted), room=room_name)

    def _require_bound_actor(self, *, sid: str, pin: str) -> tuple[str, str]:
        mapping = self._room_store.get_bound_participant(sid=sid)
        if mapping is None:
            raise AccessDeniedError("Socket is not attached to any room.")
        mapped_pin, participant_id = mapping
        if mapped_pin != pin:
            raise AccessDeniedError("Socket is bound to another room.")
        return mapped_pin, participant_id

    async def _restart_timer(self, *, pin: str) -> None:
        await self._cancel_timer(pin=pin)
        self._timer_tasks[pin] = asyncio.create_task(self._run_timer(pin=pin))

    async def _cancel_timer(self, *, pin: str) -> None:
        task = self._timer_tasks.pop(pin, None)
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def _cancel_timer_if_empty(self, *, room: Room) -> None:
        if not room.participants:
            await self._cancel_timer(pin=room.pin)

    async def _run_timer(self, *, pin: str) -> None:
        try:
            while True:
                room = self._room_store.get_room_snapshot(pin=pin)
                game_info = room.game_info
                if game_info is None or game_info.status != GameStatus.ACTIVE:
                    return

                while game_info.counter > 0:
                    await asyncio.sleep(1)
                    room = self._room_store.set_counter(pin=pin, counter=game_info.counter - 1)
                    game_info = room.game_info
                    if game_info is None:
                        return
                    await self._sio.emit(
                        "timer_tick",
                        {"counter": game_info.counter},
                        room=self._socket_room(pin),
                    )
                    if game_info.status != GameStatus.ACTIVE:
                        return

                await self._sio.emit("timer_end", {"counter": 0}, room=self._socket_room(pin))
                timer_end_result = self._room_store.handle_timer_end(pin=pin)
                await self._handle_timer_end_result(pin=pin, result=timer_end_result)

                if timer_end_result.game_finished:
                    return
        except asyncio.CancelledError:
            return
        except (RoomNotFoundError, RoomStateError):
            return

    async def _handle_timer_end_result(self, *, pin: str, result: TimerEndResult) -> None:
        room_name = self._socket_room(pin)
        if result.game_finished:
            await self._sio.emit("game_finished", result.game_info.status.value, room=room_name)
            return
        if result.next_question is None:
            return
        payload = self._to_question_payload(result.next_question)
        await self._sio.emit("new_question", payload, room=room_name)
        await self._sio.emit("next_question", payload, room=room_name)

    async def _emit_error(self, *, sid: str, message: str) -> None:
        await self._sio.emit("error", {"detail": message}, room=sid)

    def _socket_room(self, pin: str) -> str:
        return f"room:{pin}"

    def _to_room_payload(self, room: Room) -> dict[str, Any]:
        payload = RoomResponse(
            pin=room.pin,
            topic=room.topic,
            questionsPerTeam=room.questions_per_team,
            maxParticipants=room.max_participants,
            timerSeconds=room.timer_seconds,
            status=room.status,
            createdAt=room.created_at,
            participants=[self._to_participant_model(item) for item in room.participants],
            messages=[self._to_message_model(item) for item in room.messages],
            gameInfo=self._to_game_info_model(room.game_info) if room.game_info else None,
        )
        return payload.model_dump(mode="json")

    def _to_game_info_payload(self, game_info: GameInfo) -> dict[str, Any]:
        return self._to_game_info_model(game_info).model_dump(mode="json")

    def _to_game_info_model(self, game_info: GameInfo) -> GameInfoResponse:
        return GameInfoResponse(
            status=game_info.status,
            activeTeam=game_info.active_team,
            activeQuestionIndex=game_info.active_question_index,
            counter=game_info.counter,
            scores=ScoreResponse(
                red=game_info.scores.get(TeamCommand.RED, 0),
                blue=game_info.scores.get(TeamCommand.BLUE, 0),
            ),
            questions=[self._to_question_model(question) for question in game_info.questions],
        )

    def _to_question_payload(self, question: Question) -> dict[str, Any]:
        return self._to_question_model(question).model_dump(mode="json")

    def _to_question_model(self, question: Question) -> QuestionResponse:
        return QuestionResponse(
            id=question.question_id,
            text=question.text,
            options=question.options,
            team=question.team,
            selectedOption=question.selected_option,
            statusAnswer=question.answer_status,
        )

    def _to_message_payload(self, message: ChatMessage) -> dict[str, Any]:
        return self._to_message_model(message).model_dump(mode="json")

    def _to_message_model(self, message: ChatMessage) -> RoomMessageResponse:
        return RoomMessageResponse(
            id=message.message_id,
            text=message.text,
            createdAt=message.created_at,
            authorName=message.author_name,
            command=message.command,
        )

    def _to_participant_payload(self, participant: Participant) -> dict[str, Any]:
        payload = self._to_participant_model(participant).model_dump(mode="json")
        if participant.socket_sid:
            payload["socketId"] = participant.socket_sid
        return payload

    def _to_participant_model(self, participant: Participant) -> ParticipantResponse:
        return ParticipantResponse(
            id=participant.participant_id,
            name=participant.name,
            role=participant.role,
            team=participant.team,
            joinedAt=participant.joined_at,
        )
