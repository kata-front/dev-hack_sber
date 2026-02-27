import { type FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useInitCreatingRoomQuery, useInitJoiningRoomQuery } from './socketApi'
import { useStartGameMutation, useWatchGameQuery } from './playApi'
import { socketService } from '../../shared/socketServise'
import { useAppDispatch, useAppSelector } from '../../shared/redux'
import { playApi } from './playApi'
import type { TeamCommand } from '../../shared/types'
import BlueRoom from './team/BlueRoom'
import RedRoom from './team/RedRoom'
import { roleSlice } from '../../shared/roleSlice'

const SOCKET_EVENTS = {
  message: 'message',
  answer: 'answer',
}

const QUESTION_DURATION_SECONDS = 30

function Room() {
  const { roomId } = useParams()
  const role = useAppSelector(roleSlice.selectors.selectRole)
  const roomIdNumber = Number(roomId)
  const canInitRoom = Number.isFinite(roomIdNumber)

  const { data, isLoading, isError } = role === 'host'
    ? useInitCreatingRoomQuery(roomIdNumber)
    : useInitJoiningRoomQuery(roomIdNumber)

  const dispatch = useAppDispatch()
  const { data: gameInfo } = useWatchGameQuery(roomIdNumber, { skip: !canInitRoom })
  const [startGame, { isLoading: isStartingGame }] = useStartGameMutation()

  const [draft, setDraft] = useState('')
  const [timeLeft, setTimeLeft] = useState(QUESTION_DURATION_SECONDS)
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null)
  const messageEndRef = useRef<HTMLLIElement | null>(null)

  const messages = data?.messages ?? []
  const participantsCount =
    typeof data?.participants?.length === 'number' ? data?.participants?.length : null

  const team: TeamCommand =
    data && 'team' in data && (data as { team?: TeamCommand }).team === 'blue' ? 'blue' : 'red'
  const RoomVariant = team === 'blue' ? BlueRoom : RedRoom

  const activeQuestionIndex = gameInfo?.activeQuestionIndex ?? 0
  const activeQuestion =
    activeQuestionIndex > 0 ? gameInfo?.questions?.[activeQuestionIndex - 1] : undefined
  const activeTeam = activeQuestion?.team ?? gameInfo?.activeTeam
  const isGameActive = gameInfo?.status === 'active'
  const hasAnswerStatus = Boolean(activeQuestion?.statusAnswer)
  const isTeamTurn = Boolean(isGameActive && activeTeam && activeTeam === team)
  const isTimeUp = timeLeft <= 0
  const canAnswer = Boolean(
    activeQuestion && isTeamTurn && !hasAnswerStatus && !isTimeUp && canInitRoom
  )

  useEffect(() => {
    if (!data?.gameInfo || !canInitRoom) return

    dispatch(
      playApi.util.updateQueryData('watchGame', roomIdNumber, (draftState) => {
        Object.assign(draftState, data.gameInfo)
      })
    )
  }, [dispatch, data?.gameInfo, roomIdNumber, canInitRoom])

  useEffect(() => {
    const resetTimer = setTimeout(() => {
      setTimeLeft(QUESTION_DURATION_SECONDS)
      setSelectedAnswer(null)
    }, 0)

    return () => clearTimeout(resetTimer)
  }, [activeQuestionIndex])

  useEffect(() => {
    if (!isGameActive || !activeQuestionIndex || hasAnswerStatus) return

    const timer = setInterval(() => {
      setTimeLeft((value) => Math.max(value - 1, 0))
    }, 1000)

    return () => clearInterval(timer)
  }, [isGameActive, activeQuestionIndex, hasAnswerStatus])

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length])

  const handleSend = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const trimmed = draft.trim()
    if (!trimmed || !canInitRoom) return

    const socket = socketService.getSocket() ?? socketService.connect()
    socket.emit(SOCKET_EVENTS.message, {
      roomId: roomIdNumber,
      text: trimmed,
      command: team,
      createdAt: new Date().toISOString(),
    })

    setDraft('')
  }

  const handleStartGame = async () => {
    if (!canInitRoom) return

    try {
      await startGame(roomIdNumber).unwrap()
    } catch (error) {
      console.error('Failed to start game', error)
    }
  }

  const handleAnswer = (answer: string) => {
    if (!canAnswer || !activeQuestion) return

    const socket = socketService.getSocket() ?? socketService.connect()
    socket.emit(SOCKET_EVENTS.answer, {
      roomId: roomIdNumber,
      questionIndex: activeQuestionIndex,
      answer,
      team,
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
    ]
  )

  const isHost = data?.role === 'host'
  const isStartDisabled =
    !isHost || isStartingGame || !canInitRoom || gameInfo?.status === 'active'

  if (!data && !isLoading) {
    return <p className="room-text room-text--error">Некорректная ссылка на комнату.</p>
  }

  return (
    <RoomVariant
      roomId={roomId}
      data={data}
      isLoading={isLoading}
      isError={isError}
      canInitRoom={canInitRoom}
      messages={messages}
      participantsCount={participantsCount}
      draft={draft}
      onDraftChange={setDraft}
      onSend={handleSend}
      messageEndRef={messageEndRef}
      gameView={gameView}
      onStartGame={handleStartGame}
      onAnswer={handleAnswer}
      isStartingGame={isStartingGame}
      isHost={isHost}
      isStartDisabled={isStartDisabled}
    />
  )
}

export default Room


