import { type FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import type { GameInfo, InfoRoom, TeamCommand } from '../../../shared/types'
import { useInitCreatingRoomQuery, useInitJoiningRoomQuery } from '../socketApi'
import { playApi, useStartGameMutation, useWatchGameQuery } from '../playApi'
import { socketService } from '../../../shared/socketServise'
import { useAppDispatch, useAppSelector } from '../../../shared/redux'
import { roleSlice } from '../../../shared/roleSlice'
import { useQuestionTimer } from './useQuestionTimer'
import { useAdminControls } from './useAdminControls'

const SOCKET_EVENTS = {
  message: 'message',
  answer: 'answer',
  startGame: 'start_game',
  nextQuestion: 'next_question',
} as const

const QUESTION_DURATION_SECONDS = 30

const resolveSelfParticipantId = (
  data?: (InfoRoom & { role?: 'host' | 'participant'; team?: TeamCommand }) | null
) => {
  if (!data?.participants?.length) return null
  const role = data.role
  const team = data.team

  const possible = [...data.participants].reverse()
  if (role === 'host') {
    return possible.find((participant) => participant.role === 'host')?.id ?? null
  }

  if (role && team) {
    return (
      possible.find(
        (participant) => participant.role === role && participant.command === team
      )?.id ?? null
    )
  }

  return possible[0]?.id ?? null
}

const normalizeTeam = (value?: TeamCommand) => (value === 'blue' ? 'blue' : 'red')

const applyGameInfoSnapshot = (draftState: GameInfo, payload?: Partial<GameInfo>) => {
  const questions = Array.isArray(payload?.questions)
    ? payload.questions.map((question) => ({ ...question }))
    : []
  const nextActiveQuestionIndex =
    typeof payload?.activeQuestionIndex === 'number' ? payload.activeQuestionIndex : 0

  draftState.status = payload?.status ?? 'waiting'
  draftState.activeTeam = payload?.activeTeam ?? 'red'
  draftState.questions = questions
  draftState.activeQuestionIndex = Math.max(
    0,
    Math.min(nextActiveQuestionIndex, questions.length)
  )
  draftState.counter = typeof payload?.counter === 'number' ? payload.counter : 0
}

type UseRoomControllerParams = {
  roomId: string | undefined
}

export const useRoomController = ({ roomId }: UseRoomControllerParams) => {
  const role = useAppSelector(roleSlice.selectors.selectRole)
  const roomIdNumber = Number(roomId)
  const canInitRoom = Number.isFinite(roomIdNumber)

  const initQuery = role === 'host' ? useInitCreatingRoomQuery : useInitJoiningRoomQuery
  const { data, isLoading, isError } = initQuery(roomIdNumber, { skip: !canInitRoom })

  const dispatch = useAppDispatch()
  const { data: gameInfo } = useWatchGameQuery(roomIdNumber, { skip: !canInitRoom })
  const [startGame, { isLoading: isStartingGame }] = useStartGameMutation()
  const [isAdvancingQuestion, setIsAdvancingQuestion] = useState(false)

  const [draft, setDraft] = useState('')
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null)
  const messageEndRef = useRef<HTMLLIElement | null>(null)
  const selfParticipantIdRef = useRef<number | null>(null)

  useEffect(() => {
    if (!selfParticipantIdRef.current) {
      selfParticipantIdRef.current = resolveSelfParticipantId(data)
    }
  }, [data])

  useEffect(() => {
    if (!data?.gameInfo || !canInitRoom) return

    dispatch(
      playApi.util.updateQueryData('watchGame', roomIdNumber, (draftState) => {
        applyGameInfoSnapshot(draftState, data.gameInfo)
      })
    )
  }, [dispatch, data?.gameInfo, roomIdNumber, canInitRoom])

  const baseTeam =
    data && 'team' in data ? normalizeTeam((data as { team?: TeamCommand }).team) : 'red'

  const admin = useAdminControls({
    roomId: canInitRoom ? roomIdNumber : null,
    canInitRoom,
    isHost: data?.role === 'host',
    team: baseTeam,
    messages: data?.messages ?? [],
    participants: data?.participants,
    roomQueryEndpoint: role === 'host' ? 'initCreatingRoom' : 'initJoiningRoom',
    selfParticipantId: selfParticipantIdRef.current,
  })

  const messages = admin.visibleMessages
  const participantsCount =
    typeof data?.participants?.length === 'number' ? data?.participants?.length : null

  const activeQuestionIndex = Math.max(
    0,
    Math.min(gameInfo?.activeQuestionIndex ?? 0, gameInfo?.questions?.length ?? 0)
  )
  const activeQuestion =
    activeQuestionIndex > 0 ? gameInfo?.questions?.[activeQuestionIndex - 1] : undefined
  const activeTeam = activeQuestion?.team ?? gameInfo?.activeTeam
  const isHost = data?.role === 'host'
  const isGameActive = gameInfo?.status === 'active'
  const hasAnswerStatus = Boolean(activeQuestion?.statusAnswer)

  const { timeLeft } = useQuestionTimer({
    isGameActive,
    activeQuestionIndex,
    hasAnswerStatus,
    serverCounter: gameInfo?.counter,
    questionDurationSeconds: QUESTION_DURATION_SECONDS,
    isPaused: admin.state.isPaused,
  })

  const isTimeUp = timeLeft <= 0
  const isTeamTurn = Boolean(isGameActive && activeTeam && activeTeam === baseTeam)
  const canAnswer = Boolean(
    activeQuestion &&
      isTeamTurn &&
      !hasAnswerStatus &&
      !isTimeUp &&
      canInitRoom &&
      !admin.state.isPaused
  )
  const canRequestNextQuestion = Boolean(
    isHost &&
      canInitRoom &&
      isGameActive &&
      !admin.state.isPaused &&
      (!activeQuestion || hasAnswerStatus || isTimeUp)
  )

  useEffect(() => {
    setSelectedAnswer(null)
  }, [activeQuestionIndex, gameInfo?.status])

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length])

  const handleSend = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const trimmed = draft.trim()
    if (!trimmed || !canInitRoom || admin.state.isChatMuted) return

    const socket = socketService.getSocket() ?? socketService.connect()
    socket.emit(SOCKET_EVENTS.message, {
      roomId: roomIdNumber,
      text: trimmed,
      command: baseTeam,
      createdAt: new Date().toISOString(),
    })

    setDraft('')
  }

  const handleStartGame = async () => {
    if (!canInitRoom || !isHost) return

    const socket = socketService.getSocket() ?? socketService.connect()
    socket.emit(SOCKET_EVENTS.startGame, { roomId: roomIdNumber })

    try {
      const gameSnapshot = await startGame(roomIdNumber).unwrap()
      dispatch(
        playApi.util.updateQueryData('watchGame', roomIdNumber, (draftState) => {
          applyGameInfoSnapshot(draftState, gameSnapshot)
        })
      )
      setSelectedAnswer(null)
    } catch (error) {
      console.error('Failed to start game', error)
    }
  }

  const handleNextQuestion = async () => {
    if (!canRequestNextQuestion || !canInitRoom) return

    setIsAdvancingQuestion(true)
    const socket = socketService.getSocket() ?? socketService.connect()
    socket.emit(SOCKET_EVENTS.nextQuestion, { roomId: roomIdNumber })
    setSelectedAnswer(null)
    setTimeout(() => setIsAdvancingQuestion(false), 500)
  }

  const handleAnswer = (answer: string) => {
    if (!canAnswer || !activeQuestion) return

    const socket = socketService.getSocket() ?? socketService.connect()
    socket.emit(SOCKET_EVENTS.answer, {
      roomId: roomIdNumber,
      questionIndex: activeQuestionIndex,
      answer,
      team: baseTeam,
    })

    setSelectedAnswer(answer)
  }

  const gameView = useMemo(
    () => ({
      status: gameInfo?.status ?? 'waiting',
      activeQuestion,
      activeQuestionIndex,
      totalQuestions: gameInfo?.questions?.length ?? 0,
      activeTeam,
      timeLeft,
      isTeamTurn,
      isTimeUp,
      selectedAnswer,
      canAnswer,
      answerStatus: activeQuestion?.statusAnswer,
      isPaused: admin.state.isPaused,
    }),
    [
      gameInfo?.status,
      activeQuestion,
      activeQuestionIndex,
      gameInfo?.questions?.length,
      activeTeam,
      timeLeft,
      isTeamTurn,
      isTimeUp,
      selectedAnswer,
      canAnswer,
      admin.state.isPaused,
    ]
  )

  const isStartDisabled =
    !isHost || isStartingGame || !canInitRoom || gameInfo?.status === 'active'

  return {
    roomId,
    data,
    isLoading,
    isError,
    canInitRoom,
    team: baseTeam,
    messages,
    participantsCount,
    draft,
    onDraftChange: setDraft,
    onSend: handleSend,
    messageEndRef,
    gameView,
    onStartGame: handleStartGame,
    onNextQuestion: handleNextQuestion,
    onAnswer: handleAnswer,
    isStartingGame,
    isAdvancingQuestion,
    canRequestNextQuestion,
    isHost,
    isStartDisabled,
    adminState: admin.state,
    adminActions: admin.actions,
  }
}
