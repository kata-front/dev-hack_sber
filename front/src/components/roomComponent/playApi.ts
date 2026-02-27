import { baseApi } from "../../shared/baseApi";
import { socketService } from "../../shared/socketServise";
import type { AnswerStatus, GameInfo, Question, StatusGame } from "../../shared/types";

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

            async onCacheEntryAdded(_, { cacheEntryRemoved, cacheDataLoaded, updateCachedData }) {
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

                socket.on("new_question", onNewQuestion);
                socket.on("check_answer", onCheckAnswer);
                socket.on("game_finished", onGameFinished);

                await cacheEntryRemoved;

                socket.off("new_question", onNewQuestion);
                socket.off("check_answer", onCheckAnswer);
                socket.off("game_finished", onGameFinished);
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
