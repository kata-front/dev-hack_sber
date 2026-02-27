import { baseApi } from "../../shared/baseApi";
import { socketService } from "../../shared/socketServise";
import type { AnswerStatus, GameInfo, Question, StatusGame } from "../../shared/types";

type TimerTickPayload = { counter: number };

const createInitialGameInfo = (): GameInfo => ({
    status: "waiting",
    activeTeam: "red",
    questions: [],
    activeQuestionIndex: 0,
    counter: 0,
});

export const playApi = baseApi.injectEndpoints({
    endpoints: (build) => ({
        watchGame: build.query<GameInfo, number>({
            queryFn: () => ({ data: createInitialGameInfo() }),

            async onCacheEntryAdded(
                _roomId,
                { cacheEntryRemoved, cacheDataLoaded, updateCachedData }
            ) {
                void _roomId;
                try {
                    await cacheDataLoaded;
                } catch {
                    return;
                }

                const socket = socketService.connect();

                const onNewQuestion = (question: Question) => {
                    updateCachedData((draft) => {
                        draft.questions = [...(draft.questions || []), question];
                        draft.activeQuestionIndex = draft.questions.length;
                        if (draft.status === "waiting") {
                            draft.status = "active";
                        }
                        if (!draft.activeTeam) {
                            draft.activeTeam = question.team;
                        }
                    });
                };

                const onCheckAnswer = (answerStatus: AnswerStatus) => {
                    updateCachedData((draft) => {
                        const index = (draft.activeQuestionIndex || 1) - 1;
                        const current = draft.questions?.[index];
                        if (current) {
                            current.statusAnswer = answerStatus;
                        }
                    });
                };

                const onGameFinished = (status: StatusGame) => {
                    updateCachedData((draft) => {
                        draft.status = status;
                    });
                };

                const onGameStarted = (gameInfo: GameInfo) => {
                    updateCachedData((draft) => {
                        Object.assign(draft, gameInfo);
                    });
                };

                const onTimerTick = (payload: TimerTickPayload | number) => {
                    updateCachedData((draft) => {
                        draft.counter = typeof payload === "number" ? payload : payload.counter;
                    });
                };

                const onTimerEnd = (payload?: TimerTickPayload | number) => {
                    updateCachedData((draft) => {
                        if (typeof payload === "number") {
                            draft.counter = payload;
                            return;
                        }
                        if (payload?.counter !== undefined) {
                            draft.counter = payload.counter;
                            return;
                        }
                        draft.counter = 0;
                    });
                };

                const onNextQuestion = (question: Question) => {
                    onNewQuestion(question);
                };

                socket.on("new_question", onNewQuestion);
                socket.on("check_answer", onCheckAnswer);
                socket.on("game_finished", onGameFinished);
                socket.on("game_started", onGameStarted);
                socket.on("timer_tick", onTimerTick);
                socket.on("timer_end", onTimerEnd);
                socket.on("next_question", onNextQuestion);

                await cacheEntryRemoved;

                socket.off("new_question", onNewQuestion);
                socket.off("check_answer", onCheckAnswer);
                socket.off("game_finished", onGameFinished);
                socket.off("game_started", onGameStarted);
                socket.off("timer_tick", onTimerTick);
                socket.off("timer_end", onTimerEnd);
                socket.off("next_question", onNextQuestion);

                socket.disconnect();
            },
        }),
        startGame: build.mutation<GameInfo, number>({
            query: (roomId) => ({
                url: `/start_game/${roomId}`,
                method: "POST",
                body: { roomId },
            }),
        }),
    }),
});

export const { useWatchGameQuery, useStartGameMutation } = playApi;
