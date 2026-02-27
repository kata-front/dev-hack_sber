import { baseApi } from "../../shared/baseApi";
import { socketService } from "../../shared/socketServise";
import type { AnswerStatus, GameInfo, Question, StatusGame } from "../../shared/types";

export const playApi = baseApi.injectEndpoints({
    endpoints: (build) => ({
        startGame: build.query<GameInfo, number>({
            query: (roomId) => ({
                url: `/start_game/${roomId}`,
                method: "POST",
                body: { roomId },
            }),

            async onCacheEntryAdded(_,
                { cacheEntryRemoved, cacheDataLoaded, updateCachedData }
            ) {
                try {
                    await cacheDataLoaded;
                } catch {
                    return;
                }

                const socket = socketService.getSocket();

                if (!socket) {
                    return;
                }

                const onNewQuestion = (question: Question) => {
                    updateCachedData((draft) => {
                        draft.questions = [...(draft.questions || []), question];
                        draft.activeQuestionIndex = draft.questions.length;
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
            }
        }),

    }),
});
