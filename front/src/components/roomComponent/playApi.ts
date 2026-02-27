import { baseApi } from '../../shared/baseApi'
import { socketService } from '../../shared/socketServise'
import type { AnswerStatus, GameInfo, Question, StatusGame } from '../../shared/types'

type TimerTickPayload = { counter: number }

const createInitialGameInfo = (): GameInfo => ({
  status: 'waiting',
  activeTeam: 'red',
  questions: [],
  activeQuestionIndex: 0,
  counter: 0,
})

const isSameQuestion = (left?: Question, right?: Question) => {
  if (!left || !right) return false
  if (left.question !== right.question || left.team !== right.team) return false
  if (left.answers.length !== right.answers.length) return false

  return left.answers.every((answer, index) => answer === right.answers[index])
}

const normalizeGameInfo = (payload?: Partial<GameInfo>): GameInfo => {
  const questions = Array.isArray(payload?.questions)
    ? payload.questions.map((question) => ({ ...question }))
    : []
  const rawActiveQuestionIndex =
    typeof payload?.activeQuestionIndex === 'number' ? payload.activeQuestionIndex : 0

  return {
    status: payload?.status ?? 'waiting',
    activeTeam: payload?.activeTeam ?? 'red',
    questions,
    activeQuestionIndex: Math.max(0, Math.min(rawActiveQuestionIndex, questions.length)),
    counter: typeof payload?.counter === 'number' ? payload.counter : 0,
  }
}

const appendQuestion = (draft: GameInfo, question: Question) => {
  const lastQuestion = draft.questions[draft.questions.length - 1]
  if (!isSameQuestion(lastQuestion, question)) {
    draft.questions.push({ ...question })
  }

  draft.activeQuestionIndex = draft.questions.length
  draft.activeTeam = question.team
  draft.status = 'active'
  draft.counter = 0
}

export const playApi = baseApi.injectEndpoints({
  endpoints: (build) => ({
    watchGame: build.query<GameInfo, number>({
      queryFn: () => ({ data: createInitialGameInfo() }),

      async onCacheEntryAdded(_roomId, { cacheEntryRemoved, cacheDataLoaded, updateCachedData }) {
        try {
          await cacheDataLoaded
        } catch {
          return
        }

        const socket = socketService.connect()

        const onNewQuestion = (question: Question) => {
          updateCachedData((draft) => {
            appendQuestion(draft, question)
          })
        }

        const onCheckAnswer = (answerStatus: AnswerStatus) => {
          updateCachedData((draft) => {
            const index = Math.max(0, (draft.activeQuestionIndex || 1) - 1)
            const currentQuestion = draft.questions[index]
            if (currentQuestion) {
              currentQuestion.statusAnswer = answerStatus
            }
          })
        }

        const onGameFinished = (status: StatusGame) => {
          updateCachedData((draft) => {
            draft.status = status
            if (status === 'finished') {
              draft.counter = 0
            }
          })
        }

        const onGameStarted = (gameInfo: GameInfo) => {
          updateCachedData((draft) => {
            Object.assign(draft, normalizeGameInfo(gameInfo))
          })
        }

        const onTimerTick = (payload: TimerTickPayload | number) => {
          updateCachedData((draft) => {
            draft.counter = typeof payload === 'number' ? payload : payload.counter
          })
        }

        const onTimerEnd = (payload?: TimerTickPayload | number) => {
          updateCachedData((draft) => {
            if (typeof payload === 'number') {
              draft.counter = payload
              return
            }

            if (payload?.counter !== undefined) {
              draft.counter = payload.counter
              return
            }

            draft.counter = 0
          })
        }

        const onNextQuestion = (question: Question) => {
          onNewQuestion(question)
        }

        socket.on('new_question', onNewQuestion)
        socket.on('check_answer', onCheckAnswer)
        socket.on('game_finished', onGameFinished)
        socket.on('game_started', onGameStarted)
        socket.on('timer_tick', onTimerTick)
        socket.on('timer_end', onTimerEnd)
        socket.on('next_question', onNextQuestion)

        await cacheEntryRemoved

        socket.off('new_question', onNewQuestion)
        socket.off('check_answer', onCheckAnswer)
        socket.off('game_finished', onGameFinished)
        socket.off('game_started', onGameStarted)
        socket.off('timer_tick', onTimerTick)
        socket.off('timer_end', onTimerEnd)
        socket.off('next_question', onNextQuestion)
      },
    }),
    startGame: build.mutation<GameInfo, number>({
      query: (roomId) => ({
        url: `/start_game/${roomId}`,
        method: 'POST',
        body: { roomId },
      }),
    }),
  }),
})

export const { useWatchGameQuery, useStartGameMutation } = playApi
