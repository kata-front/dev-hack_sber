from __future__ import annotations

import asyncio
from typing import Any

import socketio

from app.models.domain import (
    GameInfo as DomainGameInfo,
    GameStatus as DomainGameStatus,
    Participant as DomainParticipant,
    Question as DomainQuestion,
    Room as DomainRoom,
    TeamCommand,
)
from app.models.schemas import (
    AnswerPayload,
    GameInfo,
    Participant,
    RoomInitHostResponse,
    RoomInitParticipantResponse,
    RoomMessage,
    RoomMessageOutbound,
    StartGameRequest,
)
from app.services.room_store import RoomCapacityExceededError, RoomNotFoundError, RoomStore


class SocketGateway:
    def __init__(self, *, sio: socketio.AsyncServer, store: RoomStore) -> None:
        self._sio = sio
        self._store = store
        self._timer_tasks: dict[int, asyncio.Task[None]] = {}

    def register_handlers(self) -> None:
        self._sio.on("create_room", handler=self._on_create_room)
        self._sio.on("join_room", handler=self._on_join_room)
        self._sio.on("message", handler=self._on_message)
        self._sio.on("answer", handler=self._on_answer)
        self._sio.on("start_game", handler=self._on_start_game)
        self._sio.on("disconnect", handler=self._on_disconnect)

    async def _on_create_room(self, sid: str, room_id_payload: Any) -> None:
        room_id = self._to_room_id(room_id_payload)
        try:
            room = self._store.bind_host_socket(room_id=room_id, sid=sid)
        except (RoomNotFoundError, ValueError) as exc:
            await self._emit_error(sid=sid, message=str(exc))
            return

        await self._sio.enter_room(sid, self._socket_room(room_id))
        payload = self._to_room_init_host_payload(room, role="host")
        await self._sio.emit("room_created", payload, room=sid)

    async def _on_join_room(self, sid: str, room_id_payload: Any) -> None:
        room_id = self._to_room_id(room_id_payload)
        try:
            room, participant = self._store.bind_participant_socket(room_id=room_id, sid=sid)
        except (RoomNotFoundError, RoomCapacityExceededError, ValueError) as exc:
            await self._emit_error(sid=sid, message=str(exc))
            return

        await self._sio.enter_room(sid, self._socket_room(room_id))
        payload = self._to_room_init_participant_payload(
            room,
            role="participant",
            team=participant.command or TeamCommand.RED,
        )
        await self._sio.emit("room_joined", payload, room=sid)
        await self._sio.emit(
            "player_joined",
            self._to_participant_payload(participant),
            room=self._socket_room(room_id),
            skip_sid=sid,
        )

    async def _on_message(self, sid: str, raw_payload: dict[str, Any]) -> None:
        try:
            payload = RoomMessageOutbound.model_validate(raw_payload)
            message = self._store.add_message(
                room_id=payload.roomId,
                text=payload.text,
                command=payload.command,
                created_at=payload.createdAt,
            )
        except (RoomNotFoundError, ValueError) as exc:
            await self._emit_error(sid=sid, message=str(exc))
            return

        await self._sio.emit(
            "message",
            self._to_room_message_payload(message),
            room=self._socket_room(payload.roomId),
        )

    async def _on_start_game(self, sid: str, raw_payload: dict[str, Any]) -> None:
        try:
            payload = StartGameRequest.model_validate(raw_payload)
            game_info = self._store.start_game(room_id=payload.roomId, payload_room_id=payload.roomId)
            room = self._store.get_room_snapshot(room_id=payload.roomId)
            question = self._store.get_current_question(room_id=payload.roomId)
        except (RoomNotFoundError, ValueError) as exc:
            await self._emit_error(sid=sid, message=str(exc))
            return

        await self._sio.emit(
            "game_started",
            self._to_game_info_payload(game_info),
            room=self._socket_room(payload.roomId),
        )
        if question is not None:
            question_payload = self._to_question_payload(question)
            await self._sio.emit("new_question", question_payload, room=self._socket_room(payload.roomId))
        await self._restart_timer(room.room_id)

    async def _on_answer(self, sid: str, raw_payload: dict[str, Any]) -> None:
        try:
            payload = AnswerPayload.model_validate(raw_payload)
            answer_status, next_question, game_status = self._store.submit_answer(
                room_id=payload.roomId,
                question_index=payload.questionIndex,
                answer=payload.answer,
                team=payload.team,
            )
        except (RoomNotFoundError, ValueError) as exc:
            await self._emit_error(sid=sid, message=str(exc))
            return

        await self._sio.emit(
            "check_answer",
            answer_status.value,
            room=self._socket_room(payload.roomId),
        )

        if game_status == DomainGameStatus.FINISHED:
            await self._cancel_timer(payload.roomId)
            await self._sio.emit(
                "game_finished",
                DomainGameStatus.FINISHED.value,
                room=self._socket_room(payload.roomId),
            )
            return

        if next_question is not None:
            question_payload = self._to_question_payload(next_question)
            await self._sio.emit("new_question", question_payload, room=self._socket_room(payload.roomId))
            await self._sio.emit("next_question", question_payload, room=self._socket_room(payload.roomId))
            await self._restart_timer(payload.roomId)

    async def _on_disconnect(self, sid: str, *args: Any) -> None:
        result = self._store.unbind_socket(sid=sid)
        if result is None:
            return

        room_id, participant, promoted_host = result

        await self._sio.emit(
            "user_left",
            self._to_participant_payload(participant),
            room=self._socket_room(room_id),
            skip_sid=sid,
        )

        if promoted_host is not None:
            await self._sio.emit(
                "host_changed",
                self._to_participant_payload(promoted_host),
                room=self._socket_room(room_id),
            )
        await self._cancel_timer_if_empty(room_id)

    async def _restart_timer(self, room_id: int) -> None:
        await self._cancel_timer(room_id)
        self._timer_tasks[room_id] = asyncio.create_task(self._run_timer(room_id))

    async def _cancel_timer(self, room_id: int) -> None:
        task = self._timer_tasks.pop(room_id, None)
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def _cancel_timer_if_empty(self, room_id: int) -> None:
        try:
            snapshot = self._store.get_room_snapshot(room_id=room_id)
        except RoomNotFoundError:
            await self._cancel_timer(room_id)
            return
        if not snapshot.participants:
            await self._cancel_timer(room_id)

    async def _run_timer(self, room_id: int) -> None:
        try:
            while True:
                room = self._store.get_room_snapshot(room_id=room_id)
                game_info = room.game_info
                if game_info is None or game_info.status != DomainGameStatus.ACTIVE:
                    return

                counter = game_info.counter
                while counter > 0:
                    await asyncio.sleep(1)
                    counter = self._store.set_counter(room_id=room_id, counter=counter - 1)
                    await self._sio.emit(
                        "timer_tick",
                        {"counter": counter},
                        room=self._socket_room(room_id),
                    )

                    room_after_tick = self._store.get_room_snapshot(room_id=room_id)
                    status = room_after_tick.game_info.status if room_after_tick.game_info else None
                    if status != DomainGameStatus.ACTIVE:
                        return

                await self._sio.emit("timer_end", {"counter": 0}, room=self._socket_room(room_id))
                next_question, status = self._store.handle_timer_end(room_id=room_id)
                if status == DomainGameStatus.FINISHED:
                    await self._sio.emit(
                        "game_finished",
                        DomainGameStatus.FINISHED.value,
                        room=self._socket_room(room_id),
                    )
                    return

                if next_question is not None:
                    payload = self._to_question_payload(next_question)
                    await self._sio.emit("new_question", payload, room=self._socket_room(room_id))
                    await self._sio.emit("next_question", payload, room=self._socket_room(room_id))
        except asyncio.CancelledError:
            return

    async def _emit_error(self, *, sid: str, message: str) -> None:
        await self._sio.emit("error", {"detail": message}, room=sid)

    def _socket_room(self, room_id: int) -> str:
        return str(room_id)

    def _to_room_id(self, payload: Any) -> int:
        if isinstance(payload, dict):
            value = payload.get("roomId")
        else:
            value = payload
        room_id = int(value)
        if room_id <= 0:
            raise ValueError("roomId must be positive.")
        return room_id

    def _to_room_init_host_payload(self, room: DomainRoom, *, role: str) -> dict[str, Any]:
        return RoomInitHostResponse(
            **self._to_info_room_payload(room),
            role=role,
        ).model_dump(mode="json")

    def _to_room_init_participant_payload(
        self,
        room: DomainRoom,
        *,
        role: str,
        team: TeamCommand,
    ) -> dict[str, Any]:
        return RoomInitParticipantResponse(
            **self._to_info_room_payload(room),
            role=role,
            team=team,
        ).model_dump(mode="json")

    def _to_info_room_payload(self, room: DomainRoom) -> dict[str, Any]:
        return {
            "roomId": room.room_id,
            "roomName": room.room_name,
            "quizTheme": room.quiz_theme,
            "maxParticipants": room.max_participants,
            "messages": [self._to_room_message_payload(message) for message in room.messages],
            "participants": [
                self._to_participant_payload(participant) for participant in room.participants
            ],
            "gameInfo": self._to_game_info_payload(room.game_info) if room.game_info else None,
        }

    def _to_game_info_payload(self, game_info: DomainGameInfo) -> dict[str, Any]:
        return GameInfo(
            status=game_info.status,
            activeTeam=game_info.active_team,
            questions=[self._to_question_payload(question) for question in game_info.questions],
            activeQuestionIndex=game_info.active_question_index,
            counter=game_info.counter,
        ).model_dump(mode="json")

    def _to_question_payload(self, question: DomainQuestion) -> dict[str, Any]:
        return {
            "question": question.question,
            "team": question.team.value,
            "answers": question.answers,
            "statusAnswer": question.status_answer.value if question.status_answer else None,
        }

    def _to_room_message_payload(self, message) -> dict[str, Any]:
        return RoomMessage(
            command=message.command,
            createdAt=message.created_at,
            text=message.text,
        ).model_dump(mode="json")

    def _to_participant_payload(self, participant: DomainParticipant) -> dict[str, Any]:
        return Participant(
            id=participant.participant_id,
            command=participant.command,
            role=participant.role,
        ).model_dump(mode="json")
