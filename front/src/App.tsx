import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'

import { api } from './api'
import { disconnectSocket, getSocket } from './socket'
import type {
  AnswerStatus,
  AuthRoomResponse,
  GameDifficulty,
  GameInfo,
  Participant,
  ParticipantRole,
  Question,
  Room,
  RoomMessage,
  SessionInfo,
  TeamCommand,
} from './types'
import './App.css'

type GamePreparingPayload = {
  preparing?: boolean
  topic?: string
  questionsPerTeam?: number
  error?: string
  source?: 'ai' | 'fallback'
  message?: string | null
}

type KickedPayload = {
  pin?: string
  participantId?: string
}

function formatClock(dateIso: string): string {
  return new Date(dateIso).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function winnerText(room: Room | null): string {
  if (!room?.gameInfo || room.status !== 'finished') {
    return ''
  }

  const { red, blue } = room.gameInfo.scores
  if (red === blue) {
    return 'Ничья: команды завершили игру с равным счётом.'
  }

  return red > blue
    ? `Победила красная команда со счётом ${red}:${blue}`
    : `Победила синяя команда со счётом ${blue}:${red}`
}

function teamName(team: TeamCommand | null): string {
  if (team === 'red') {
    return 'Красная'
  }
  if (team === 'blue') {
    return 'Синяя'
  }
  return 'Без команды'
}

function difficultyName(difficulty: GameDifficulty): string {
  if (difficulty === 'easy') {
    return 'Легкий'
  }
  if (difficulty === 'hard') {
    return 'Сложный'
  }
  return 'Средний'
}

function isValidName(value: string): boolean {
  return value.trim().replace(/\s+/g, ' ').length >= 2
}

function roleEvent(role: ParticipantRole): 'create_room' | 'join_room' {
  return role === 'host' ? 'create_room' : 'join_room'
}

function normalizeParticipantId(payload: unknown): string | null {
  if (typeof payload !== 'object' || payload === null) {
    return null
  }

  const record = payload as Record<string, unknown>
  if (typeof record.id === 'string' && record.id.length > 0) {
    return record.id
  }
  if (typeof record.participantId === 'string' && record.participantId.length > 0) {
    return record.participantId
  }
  return null
}

export default function App() {
  const [booting, setBooting] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)

  const [session, setSession] = useState<SessionInfo | null>(null)
  const [participant, setParticipant] = useState<Participant | null>(null)
  const [room, setRoom] = useState<Room | null>(null)

  const [createHostName, setCreateHostName] = useState('')
  const [createTopic, setCreateTopic] = useState('')
  const [createDifficulty, setCreateDifficulty] = useState<GameDifficulty>('medium')
  const [createQuestionsPerTeam, setCreateQuestionsPerTeam] = useState<5 | 6 | 7>(5)
  const [createMaxParticipants, setCreateMaxParticipants] = useState(20)
  const [createTimerSeconds, setCreateTimerSeconds] = useState(30)

  const [joinName, setJoinName] = useState('')
  const [joinPin, setJoinPin] = useState('')

  const [chatText, setChatText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [isPreparingGame, setIsPreparingGame] = useState(false)
  const [preparingTopic, setPreparingTopic] = useState('')
  const [launchFx, setLaunchFx] = useState(false)
  const [startCountdown, setStartCountdown] = useState<number | null>(null)

  const clearAuth = useCallback(() => {
    setSession(null)
    setParticipant(null)
    setRoom(null)
    setIsPreparingGame(false)
    setPreparingTopic('')
    setStartCountdown(null)
    setLaunchFx(false)
    disconnectSocket()
  }, [])

  const syncSelfFromRoom = useCallback((snapshot: Room) => {
    setParticipant((prev) => {
      if (!prev) {
        return prev
      }
      const updated = snapshot.participants.find((item) => item.id === prev.id)
      if (!updated) {
        return prev
      }
      return {
        ...prev,
        role: updated.role,
        team: updated.team,
        name: updated.name,
      }
    })
  }, [])

  const syncRoom = useCallback(async (pin: string) => {
    try {
      const nextRoom = await api.getRoom(pin)
      setRoom(nextRoom)
      syncSelfFromRoom(nextRoom)
    } catch {
      // ignore silent sync errors; authoritative failure will surface on next user action
    }
  }, [syncSelfFromRoom])

  const applyAuth = useCallback((payload: AuthRoomResponse) => {
    setSession(payload.session)
    setParticipant(payload.participant)
    setRoom(payload.room)
  }, [])

  const markRoundLaunch = useCallback(() => {
    setLaunchFx(true)
    setStartCountdown(3)
  }, [])

  useEffect(() => {
    if (!launchFx) {
      return
    }

    const timeout = window.setTimeout(() => {
      setLaunchFx(false)
    }, 1400)

    return () => {
      window.clearTimeout(timeout)
    }
  }, [launchFx])

  useEffect(() => {
    if (startCountdown === null) {
      return
    }
    if (startCountdown < 0) {
      setStartCountdown(null)
      return
    }

    const timeout = window.setTimeout(() => {
      setStartCountdown((prev) => (prev === null ? null : prev - 1))
    }, 650)

    return () => {
      window.clearTimeout(timeout)
    }
  }, [startCountdown])

  useEffect(() => {
    void (async () => {
      try {
        const current = await api.getSession()
        if (current.authenticated && current.session && current.participant && current.room) {
          setSession(current.session)
          setParticipant(current.participant)
          setRoom(current.room)
        }
      } catch {
        // app should stay usable even if bootstrap session request fails
      } finally {
        setBooting(false)
      }
    })()
  }, [])

  useEffect(() => {
    if (!session || !participant) {
      return
    }

    const socket = getSocket()
    const pin = session.roomPin
    const participantId = session.participantId

    const onRoomSnapshot = (payload: Room) => {
      setRoom(payload)
      syncSelfFromRoom(payload)
      setError(null)
      if (payload.status === 'active') {
        setIsPreparingGame(false)
        setPreparingTopic('')
      }
    }

    const onPlayerJoined = (payload: Participant) => {
      setRoom((prev) => {
        if (!prev || prev.participants.some((item) => item.id === payload.id)) {
          return prev
        }

        return {
          ...prev,
          participants: [...prev.participants, payload],
        }
      })
    }

    const onUserLeft = (payload: unknown) => {
      const leftId = normalizeParticipantId(payload)
      if (!leftId) {
        return
      }

      setRoom((prev) => {
        if (!prev) {
          return prev
        }

        return {
          ...prev,
          participants: prev.participants.filter((item) => item.id !== leftId),
        }
      })
    }

    const onHostChanged = (payload: Participant) => {
      setParticipant((prev) => {
        if (!prev || prev.id !== payload.id) {
          return prev
        }
        return { ...prev, role: 'host' }
      })

      setRoom((prev) => {
        if (!prev) {
          return prev
        }

        return {
          ...prev,
          participants: prev.participants.map((item) => ({
            ...item,
            role: item.id === payload.id ? 'host' : item.role === 'host' ? 'participant' : item.role,
          })),
        }
      })
    }

    const onMessage = (payload: RoomMessage) => {
      setRoom((prev) => {
        if (!prev || prev.messages.some((msg) => msg.id === payload.id)) {
          return prev
        }

        return {
          ...prev,
          messages: [...prev.messages, payload],
        }
      })
    }

    const onGamePreparing = (payload: GamePreparingPayload) => {
      if (payload.preparing) {
        setIsPreparingGame(true)
        setPreparingTopic(payload.topic ?? '')
        setError(null)
        return
      }

      setIsPreparingGame(false)
      setPreparingTopic('')
      if (payload.error) {
        setError(payload.error)
      }
      if (payload.source === 'fallback') {
        setToast(payload.message ?? 'ИИ недоступен, включены запасные вопросы.')
      }
    }

    const onGameStarted = (payload: GameInfo) => {
      setRoom((prev) => {
        if (!prev) {
          return prev
        }

        return {
          ...prev,
          status: 'active',
          gameInfo: payload,
        }
      })
      setIsPreparingGame(false)
      setPreparingTopic('')
      markRoundLaunch()
      void syncRoom(pin)
    }

    const onQuestion = (payload: Question) => {
      setRoom((prev) => {
        if (!prev?.gameInfo) {
          return prev
        }

        const idx = prev.gameInfo.questions.findIndex((item) => item.id === payload.id)
        if (idx < 0) {
          return prev
        }

        const nextQuestions = [...prev.gameInfo.questions]
        nextQuestions[idx] = payload

        return {
          ...prev,
          gameInfo: {
            ...prev.gameInfo,
            activeQuestionIndex: idx,
            questions: nextQuestions,
          },
        }
      })
    }

    const onCheckAnswer = (status: AnswerStatus) => {
      setToast(status === 'correct' ? 'Правильный ответ' : 'Неправильный ответ')
      void syncRoom(pin)
    }

    const onTimerTick = (payload: { counter: number }) => {
      setRoom((prev) => {
        if (!prev?.gameInfo) {
          return prev
        }

        return {
          ...prev,
          gameInfo: {
            ...prev.gameInfo,
            counter: payload.counter,
          },
        }
      })
    }

    const onGameFinished = () => {
      setRoom((prev) => {
        if (!prev?.gameInfo) {
          return prev
        }

        return {
          ...prev,
          status: 'finished',
          gameInfo: {
            ...prev.gameInfo,
            status: 'finished',
          },
        }
      })
      setIsPreparingGame(false)
      setPreparingTopic('')
      void syncRoom(pin)
    }

    const onGameRestarted = () => {
      setRoom((prev) => {
        if (!prev) {
          return prev
        }
        return {
          ...prev,
          status: 'waiting',
          gameInfo: null,
        }
      })
      setIsPreparingGame(false)
      setPreparingTopic('')
      setToast('Игра перезапущена, вы снова в лобби.')
      void syncRoom(pin)
    }

    const onKicked = (payload: KickedPayload) => {
      if (!participant) {
        return
      }
      if (payload.participantId && payload.participantId !== participant.id) {
        return
      }
      setToast('Вас исключили из лобби.')
      clearAuth()
    }

    const onSocketError = (payload: { detail?: string }) => {
      setIsPreparingGame(false)
      setPreparingTopic('')
      setError(payload.detail ?? 'Ошибка socket-соединения')
    }

    const onConnectError = () => {
      setError('Не удалось подключиться к websocket. Используем резервный режим через REST.')
    }

    socket.on('room_created', onRoomSnapshot)
    socket.on('room_joined', onRoomSnapshot)
    socket.on('room_updated', onRoomSnapshot)
    socket.on('player_joined', onPlayerJoined)
    socket.on('user_left', onUserLeft)
    socket.on('host_changed', onHostChanged)
    socket.on('message', onMessage)
    socket.on('game_preparing', onGamePreparing)
    socket.on('game_started', onGameStarted)
    socket.on('new_question', onQuestion)
    socket.on('next_question', onQuestion)
    socket.on('check_answer', onCheckAnswer)
    socket.on('timer_tick', onTimerTick)
    socket.on('game_finished', onGameFinished)
    socket.on('game_restarted', onGameRestarted)
    socket.on('kicked', onKicked)
    socket.on('error', onSocketError)
    socket.on('connect_error', onConnectError)

    if (!socket.connected) {
      socket.connect()
    }

    socket.emit(roleEvent(participant.role), {
      pin,
      participantId,
    })

    return () => {
      socket.off('room_created', onRoomSnapshot)
      socket.off('room_joined', onRoomSnapshot)
      socket.off('room_updated', onRoomSnapshot)
      socket.off('player_joined', onPlayerJoined)
      socket.off('user_left', onUserLeft)
      socket.off('host_changed', onHostChanged)
      socket.off('message', onMessage)
      socket.off('game_preparing', onGamePreparing)
      socket.off('game_started', onGameStarted)
      socket.off('new_question', onQuestion)
      socket.off('next_question', onQuestion)
      socket.off('check_answer', onCheckAnswer)
      socket.off('timer_tick', onTimerTick)
      socket.off('game_finished', onGameFinished)
      socket.off('game_restarted', onGameRestarted)
      socket.off('kicked', onKicked)
      socket.off('error', onSocketError)
      socket.off('connect_error', onConnectError)
    }
  }, [clearAuth, markRoundLaunch, participant, session, syncRoom, syncSelfFromRoom])

  useEffect(() => {
    if (!toast) {
      return
    }

    const timeout = window.setTimeout(() => {
      setToast(null)
    }, 1800)

    return () => {
      window.clearTimeout(timeout)
    }
  }, [toast])

  const redTeam = useMemo(() => room?.participants.filter((item) => item.team === 'red') ?? [], [room])
  const blueTeam = useMemo(() => room?.participants.filter((item) => item.team === 'blue') ?? [], [room])

  const activeQuestion = useMemo(() => {
    if (!room?.gameInfo) {
      return null
    }

    return room.gameInfo.questions[room.gameInfo.activeQuestionIndex] ?? null
  }, [room])

  const canStartGame = Boolean(
    participant?.role === 'host' && room?.status === 'waiting' && (room?.participants.length ?? 0) >= 2,
  )
  const isLobbyPhase = room?.status === 'waiting'

  const canAnswer = Boolean(
    room?.status === 'active' &&
      room?.gameInfo &&
      activeQuestion &&
      activeQuestion.statusAnswer === null &&
      participant?.team === room.gameInfo.activeTeam,
  )

  const onCreateRoom = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)

    if (!isValidName(createHostName)) {
      setError('Введите имя ведущего: минимум 2 символа.')
      return
    }

    if (createTopic.trim().length < 3) {
      setError('Введите тему квиза: минимум 3 символа.')
      return
    }

    setSubmitting(true)
    try {
      const payload = await api.createRoom({
        hostName: createHostName.trim(),
        topic: createTopic.trim(),
        difficulty: createDifficulty,
        questionsPerTeam: createQuestionsPerTeam,
        maxParticipants: createMaxParticipants,
        timerSeconds: createTimerSeconds,
      })
      applyAuth(payload)
      setToast('Комната создана')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать комнату')
    } finally {
      setSubmitting(false)
    }
  }

  const onJoinRoom = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)

    if (!isValidName(joinName)) {
      setError('Введите имя игрока: минимум 2 символа.')
      return
    }

    const normalizedPin = joinPin.trim().toUpperCase()
    if (!/^[A-Z0-9]{6}$/.test(normalizedPin)) {
      setError('PIN должен состоять из 6 символов: A-Z и 0-9.')
      return
    }

    setSubmitting(true)
    try {
      const pinCheck = await api.checkPin(normalizedPin)
      if (!pinCheck.ok) {
        setError('Комната с таким PIN не найдена.')
        return
      }

      const payload = await api.joinRoom(normalizedPin, {
        playerName: joinName.trim(),
      })
      applyAuth(payload)
      setToast('Вы подключились к комнате')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось войти в комнату')
    } finally {
      setSubmitting(false)
    }
  }

  const onStartGame = async () => {
    if (!room || !participant) {
      return
    }

    setError(null)
    setIsPreparingGame(true)
    setPreparingTopic(room.topic)

    try {
      const socket = getSocket()
      socket.emit('start_game', { pin: room.pin })

      if (!socket.connected) {
        const result = await api.startGame(room.pin)
        setRoom(result.room)
        syncSelfFromRoom(result.room)
        if (result.generationSource === 'fallback') {
          setToast(result.generationMessage ?? 'ИИ недоступен, включены запасные вопросы.')
        }
        setIsPreparingGame(false)
        setPreparingTopic('')
        markRoundLaunch()
      }
    } catch (err) {
      setIsPreparingGame(false)
      setPreparingTopic('')
      setError(err instanceof Error ? err.message : 'Не удалось начать игру')
    }
  }

  const onRestartGame = async () => {
    if (!room) {
      return
    }

    setError(null)
    try {
      const socket = getSocket()
      socket.emit('restart_game', { pin: room.pin })

      if (!socket.connected) {
        const result = await api.restartGame(room.pin)
        setRoom(result.room)
        syncSelfFromRoom(result.room)
        setToast('Игра перезапущена, вы снова в лобби.')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось перезапустить игру')
    }
  }

  const onKickParticipant = async (participantId: string, participantName: string) => {
    if (!room || !participant) {
      return
    }
    if (participant.role !== 'host') {
      return
    }

    setError(null)
    try {
      const socket = getSocket()
      socket.emit('kick_user', {
        pin: room.pin,
        participantId,
      })

      if (!socket.connected) {
        const result = await api.kickParticipant(room.pin, participantId)
        setRoom(result.room)
        syncSelfFromRoom(result.room)
      }
      setToast(`Участник ${participantName} исключён из лобби.`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось исключить участника')
    }
  }

  const onAnswer = async (optionIndex: number) => {
    if (!room) {
      return
    }

    setError(null)
    try {
      const socket = getSocket()
      socket.emit('answer', {
        pin: room.pin,
        optionIndex,
      })

      if (!socket.connected) {
        const result = await api.submitAnswer(room.pin, optionIndex)
        setRoom(result.room)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось отправить ответ')
    }
  }

  const onSendMessage = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!room) {
      return
    }

    const text = chatText.trim()
    if (!text) {
      return
    }

    setError(null)
    try {
      const socket = getSocket()
      socket.emit('message', {
        pin: room.pin,
        text,
      })

      if (!socket.connected) {
        const message = await api.sendMessage(room.pin, text)
        setRoom((prev) => {
          if (!prev || prev.messages.some((item) => item.id === message.id)) {
            return prev
          }
          return { ...prev, messages: [...prev.messages, message] }
        })
      }
      setChatText('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось отправить сообщение')
    }
  }

  const onLeaveRoom = async () => {
    if (!session) {
      return
    }

    setError(null)
    try {
      const socket = getSocket()
      if (socket.connected) {
        socket.emit('leave_room', { pin: session.roomPin })
      }
      await api.leaveRoom(session.roomPin)
    } catch {
      // room may already be removed by disconnect
    } finally {
      clearAuth()
      setToast('Вы вышли из комнаты')
    }
  }

  if (booting) {
    return (
      <main className="shell shell--centered">
        <div className="panel panel--small">Восстанавливаем сессию...</div>
      </main>
    )
  }

  if (!session || !participant || !room) {
    return (
      <main className="shell">
        <section className="hero panel">
          <p className="hero__eyebrow">Командная платформа викторин</p>
          <h1>QuizBattle</h1>
          <p>
            Ведущий создаёт комнату, участники входят по PIN,
            команды соревнуются в реальном времени
          </p>
        </section>

        {error ? <div className="alert alert--error">{error}</div> : null}
        {toast ? <div className="alert alert--ok">{toast}</div> : null}

        <section className="cards-grid">
          <article className="panel card">
            <h2>Создать игру</h2>
            <form className="form" onSubmit={onCreateRoom}>
              <label>
                Имя ведущего
                <input
                  value={createHostName}
                  onChange={(event) => setCreateHostName(event.target.value)}
                  placeholder="Например, Алексей"
                />
              </label>

              <label>
                Тема викторины
                <input
                  value={createTopic}
                  onChange={(event) => setCreateTopic(event.target.value)}
                  placeholder="История России"
                />
              </label>

              <label>
                Сложность
                <select
                  value={createDifficulty}
                  onChange={(event) => setCreateDifficulty(event.target.value as GameDifficulty)}
                >
                  <option value="easy">Легкий</option>
                  <option value="medium">Средний</option>
                  <option value="hard">Сложный</option>
                </select>
              </label>

              <label>
                Вопросов на команду
                <select
                  value={createQuestionsPerTeam}
                  onChange={(event) => setCreateQuestionsPerTeam(Number(event.target.value) as 5 | 6 | 7)}
                >
                  <option value={5}>5</option>
                  <option value={6}>6</option>
                  <option value={7}>7</option>
                </select>
              </label>

              <label>
                Лимит участников
                <input
                  type="number"
                  min={2}
                  max={100}
                  value={createMaxParticipants}
                  onChange={(event) => {
                    const value = Number(event.target.value) || 2
                    setCreateMaxParticipants(Math.max(2, Math.min(100, value)))
                  }}
                />
              </label>

              <label>
                Таймер на вопрос (сек)
                <input
                  type="number"
                  min={10}
                  max={120}
                  value={createTimerSeconds}
                  onChange={(event) => {
                    const value = Number(event.target.value) || 10
                    setCreateTimerSeconds(Math.max(10, Math.min(120, value)))
                  }}
                />
              </label>

              <button type="submit" disabled={submitting}>
                {submitting ? 'Создаём комнату...' : 'Создать комнату'}
              </button>
            </form>
          </article>

          <article className="panel card">
            <h2>Войти в комнату</h2>
            <form className="form" onSubmit={onJoinRoom}>
              <label>
                Имя игрока
                <input
                  value={joinName}
                  onChange={(event) => setJoinName(event.target.value)}
                  placeholder="Ваше имя"
                />
              </label>

              <label>
                PIN-код
                <input
                  value={joinPin}
                  onChange={(event) => setJoinPin(event.target.value.toUpperCase())}
                  maxLength={6}
                  placeholder="A1B2C3"
                />
              </label>

              <button type="submit" disabled={submitting}>
                {submitting ? 'Подключаем...' : 'Подключиться'}
              </button>
            </form>
          </article>
        </section>
      </main>
    )
  }

  return (
    <main className={`shell shell--room ${launchFx ? 'shell--launch' : ''}`}>
      {launchFx ? (
        <div className="launch-banner">
          <span>Раунд стартовал</span>
        </div>
      ) : null}

      {isPreparingGame ? (
        <div className="prepare-overlay">
          <div className="prepare-card">
            <div className="prepare-spinner" />
            <h3>Инициализация игры</h3>
            <p>
              Генерируем вопросы{preparingTopic ? ` по теме «${preparingTopic}»` : ''}. Пожалуйста, подождите.
            </p>
            <div className="prepare-skeleton" />
            <div className="prepare-skeleton prepare-skeleton--short" />
            <div className="prepare-dots">
              <span />
              <span />
              <span />
            </div>
          </div>
        </div>
      ) : null}

      {startCountdown !== null ? (
        <div className="intro-overlay">
          <div className="intro-overlay__inner">
            <p>Раунд начинается</p>
            <strong>{startCountdown > 0 ? startCountdown : 'Старт'}</strong>
          </div>
          <div className="intro-overlay__line" />
        </div>
      ) : null}

      {error ? <div className="alert alert--error">{error}</div> : null}
      {toast ? <div className="alert alert--ok">{toast}</div> : null}

      <section className="panel room-header">
        <div>
          <p className="hero__eyebrow">Комната</p>
          <h1 className="pin">{room.pin}</h1>
          <p className="meta">Тема: {room.topic}</p>
          <p className="meta">Сложность: {difficultyName(room.difficulty)}</p>
          <p className="meta">Статус: {room.status}</p>
        </div>

        <div className="room-actions">
          <div className="badge">Игрок: {participant.name}</div>
          <div className="badge">
            Роль: {participant.role === 'host' ? 'Ведущий' : 'Участник'} / Команда: {teamName(participant.team)}
          </div>
          <button className="ghost" onClick={onLeaveRoom}>Выйти из команды</button>
        </div>
      </section>

      {isLobbyPhase ? (
        <section className="cards-grid cards-grid--lobby">
          <article className="panel room-card lobby-card">
            <div className="room-card__head">
              <h2>Лобби ожидания</h2>
              <p className="meta">Участников: {room.participants.length} / {room.maxParticipants}</p>
            </div>
            <p className="meta">
              После старта игры участники автоматически и случайно распределяются по командам.
            </p>

            <ul className="lobby-list">
              {room.participants.map((item) => (
                <li key={item.id}>
                  <div className="lobby-list__meta">
                    <strong>{item.name}</strong>
                    <span>{item.role === 'host' ? 'Ведущий' : 'Участник'}</span>
                  </div>
                  {participant.role === 'host' && item.role !== 'host' ? (
                    <button
                      type="button"
                      className="ghost lobby-list__kick"
                      onClick={() => onKickParticipant(item.id, item.name)}
                    >
                      Кик
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>

            {participant.role === 'host' ? (
              <button onClick={onStartGame} disabled={!canStartGame || isPreparingGame}>
                {isPreparingGame ? 'Идёт инициализация...' : 'Перейти к игре'}
              </button>
            ) : (
              <p className="meta">Ожидание запуска от ведущего.</p>
            )}
          </article>

          <article className="panel room-card lobby-card">
            <h2>Параметры раунда</h2>
            <p className="meta">Тема: {room.topic}</p>
            <p className="meta">Сложность: {difficultyName(room.difficulty)}</p>
            <p className="meta">Вопросов на команду: {room.questionsPerTeam}</p>
            <p className="meta">Таймер на вопрос: {room.timerSeconds} сек</p>
            <p className="meta">После запуска все игроки автоматически попадут на игровое поле.</p>
          </article>

          <article className="panel panel--chat room-card">
            <h2>Чат комнаты</h2>

            <div className="chat-list">
              {room.messages.length === 0 ? <p className="meta">Пока сообщений нет.</p> : null}

              {room.messages.map((msg) => (
                <div key={msg.id} className="chat-item">
                  <div className="chat-item__meta">
                    <strong>{msg.authorName}</strong>
                    <span className="meta">{teamName(msg.command)} • {formatClock(msg.createdAt)}</span>
                  </div>
                  <p>{msg.text}</p>
                </div>
              ))}
            </div>

            <form className="chat-form" onSubmit={onSendMessage}>
              <input
                value={chatText}
                onChange={(event) => setChatText(event.target.value)}
                placeholder="Введите сообщение"
              />
              <button type="submit">Отправить</button>
            </form>
          </article>
        </section>
      ) : (
        <section className="cards-grid cards-grid--room">
          <article className="panel room-card">
            <div className="room-card__head">
              <h2>Состав команд</h2>
              <p className="meta">Участников: {room.participants.length} / {room.maxParticipants}</p>
            </div>

            <div className="team-columns">
              <div className="team team--red">
                <h3>Красные</h3>
                <ul>
                  {redTeam.length > 0
                    ? redTeam.map((item) => <li key={item.id}>{item.name}</li>)
                    : <li>Пока нет игроков</li>}
                </ul>
              </div>

              <div className="team team--blue">
                <h3>Синие</h3>
                <ul>
                  {blueTeam.length > 0
                    ? blueTeam.map((item) => <li key={item.id}>{item.name}</li>)
                    : <li>Пока нет игроков</li>}
                </ul>
              </div>
            </div>
          </article>

          <article className="panel room-card">
            <h2>Игровое поле</h2>

            {room.gameInfo ? (
              <>
                <div className="scoreboard">
                  <div className="score score--red">Красные: {room.gameInfo.scores.red}</div>
                  <div className="score score--blue">Синие: {room.gameInfo.scores.blue}</div>
                </div>

                <p className="meta game-meta">
                  Ход: {teamName(room.gameInfo.activeTeam)} | Таймер: {room.gameInfo.counter} сек
                </p>

                {activeQuestion ? (
                  <div className="question-box">
                    <p className="question-team">Вопрос для команды: {teamName(activeQuestion.team)}</p>
                    <h3>{activeQuestion.text}</h3>

                    <div className="answers-grid">
                      {activeQuestion.options.map((option, idx) => {
                        const isSelected = activeQuestion.selectedOption === idx
                        const disabled = !canAnswer || activeQuestion.statusAnswer !== null

                        return (
                          <button
                            className={`answer ${isSelected ? 'answer--selected' : ''}`}
                            key={`${idx}-${option}`}
                            onClick={() => onAnswer(idx)}
                            disabled={disabled}
                          >
                            {option}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                ) : (
                  <p className="meta">Ожидание вопроса...</p>
                )}

                {room.status === 'finished' ? <p className="winner">{winnerText(room)}</p> : null}
                {room.status === 'finished' && participant.role === 'host' ? (
                  <button onClick={onRestartGame}>Начать новую игру</button>
                ) : null}
              </>
            ) : (
              <p className="meta">Подготовка игрового поля...</p>
            )}
          </article>

          <article className="panel panel--chat room-card">
            <h2>Чат комнаты</h2>

            <div className="chat-list">
              {room.messages.length === 0 ? <p className="meta">Пока сообщений нет.</p> : null}

              {room.messages.map((msg) => (
                <div key={msg.id} className="chat-item">
                  <div className="chat-item__meta">
                    <strong>{msg.authorName}</strong>
                    <span className="meta">{teamName(msg.command)} • {formatClock(msg.createdAt)}</span>
                  </div>
                  <p>{msg.text}</p>
                </div>
              ))}
            </div>

            <form className="chat-form" onSubmit={onSendMessage}>
              <input
                value={chatText}
                onChange={(event) => setChatText(event.target.value)}
                placeholder="Введите сообщение"
              />
              <button type="submit">Отправить</button>
            </form>
          </article>
        </section>
      )}
    </main>
  )
}
