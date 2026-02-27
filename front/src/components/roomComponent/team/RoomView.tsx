import type { FormEvent, RefObject } from 'react'
import type {
  AnswerStatus,
  InfoRoom,
  Question,
  RoomMessage,
  StatusGame,
  TeamCommand,
} from '../../../shared/types'
import AdminPanel from '../adminPanel/AdminPanel'
import type { AdminPanelActions, AdminPanelState } from '../adminPanel/adminTypes'
import '../Room.scss'

const formatTime = (value?: string) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

const getTeamLabel = (team?: TeamCommand) =>
  team === 'red' ? 'Красные' : team === 'blue' ? 'Синие' : '—'

const getStatusLabel = (status: StatusGame) => {
  if (status === 'active') return 'Игра идет'
  if (status === 'finished') return 'Игра завершена'
  return 'Ожидание'
}

const getStatusTone = (status: StatusGame) => {
  if (status === 'active') return 'active'
  if (status === 'finished') return 'done'
  return 'idle'
}

export type GameViewState = {
  status: StatusGame
  activeQuestion?: Question
  activeQuestionIndex: number
  totalQuestions: number
  activeTeam?: TeamCommand
  timeLeft: number
  isTeamTurn: boolean
  isTimeUp: boolean
  selectedAnswer: string | null
  canAnswer: boolean
  answerStatus?: AnswerStatus
  isPaused: boolean
}

export type RoomViewProps = {
  team: TeamCommand
  roomId?: string
  data?: InfoRoom & { role?: 'host' | 'participant' }
  isLoading: boolean
  isError: boolean
  canInitRoom: boolean
  messages: RoomMessage[]
  participantsCount: number | null
  draft: string
  onDraftChange: (value: string) => void
  onSend: (event: FormEvent<HTMLFormElement>) => void
  messageEndRef: RefObject<HTMLLIElement | null>
  gameView: GameViewState
  onStartGame: () => void
  onNextQuestion: () => void
  onAnswer: (answer: string) => void
  isStartingGame: boolean
  isAdvancingQuestion: boolean
  canRequestNextQuestion: boolean
  isHost: boolean
  isStartDisabled: boolean
  adminState: AdminPanelState
  adminActions: AdminPanelActions
}

function RoomView({
  team,
  roomId,
  data,
  isLoading,
  isError,
  canInitRoom,
  messages,
  participantsCount,
  draft,
  onDraftChange,
  onSend,
  messageEndRef,
  gameView,
  onStartGame,
  onNextQuestion,
  onAnswer,
  isStartingGame,
  isAdvancingQuestion,
  canRequestNextQuestion,
  isHost,
  isStartDisabled,
  adminState,
  adminActions,
}: RoomViewProps) {
  const roomIdLabel = data?.roomId ?? roomId ?? '—'
  const teamLabel = getTeamLabel(team)
  const pageClass = team === 'red' ? 'room-page--red' : 'room-page--blue'
  const activeTeamLabel = getTeamLabel(gameView.activeTeam)
  const activeTeamClass = gameView.activeTeam ?? team
  const hasActiveQuestion = Boolean(gameView.activeQuestion)
  const isGameFinished = gameView.status === 'finished'
  const startLabel = isHost ? (isStartingGame ? 'Запуск...' : 'Старт раунда') : 'Ожидание старта'
  const nextLabel = isAdvancingQuestion ? 'Загрузка...' : 'Следующий вопрос'
  const statusLabel = getStatusLabel(gameView.status)
  const statusTone = getStatusTone(gameView.status)
  const questionsLabel =
    gameView.totalQuestions > 0
      ? `${gameView.activeQuestionIndex} / ${gameView.totalQuestions}`
      : '—'
  const timerLabel = gameView.isPaused ? 'Пауза' : `${gameView.timeLeft}с`

  return (
    <div className={`room-page ${pageClass}`}>
      <div className="orb orb--one" />
      <div className="orb orb--two" />
      <div className="grid-glow" />

      <header className="room-top">
        <div className="room-title">
          <p className="room-eyebrow">Комната № {roomIdLabel}</p>
          <h1 className="room-name">{data?.roomName ?? 'Название не указано'}</h1>
          <p className="room-subtitle">{data?.quizTheme ?? 'Тема не указана'}</p>
          <div className="room-tags">
            <span className={`room-tag room-tag--${statusTone}`}>Статус: {statusLabel}</span>
            <span className="room-tag">Вопрос: {questionsLabel}</span>
            <span className={`room-team room-team--${team} is-active room-team--static`}>
              Ваша команда: {teamLabel}
            </span>
          </div>
        </div>
        <div className="room-actions">
          <button className="room-btn room-btn--ghost" type="button">
            Поделиться ссылкой
          </button>
          <button
            className="room-btn room-btn--primary"
            type="button"
            onClick={onStartGame}
            disabled={isStartDisabled}
          >
            {startLabel}
          </button>
        </div>
      </header>

      {!canInitRoom && (
        <p className="room-text room-text--error">
          Некорректный идентификатор комнаты. Пример: /room/12345.
        </p>
      )}
      {isError && (
        <p className="room-text room-text--error">Не удалось загрузить данные комнаты.</p>
      )}

      <section className="room-grid">
        <article className="room-card room-card--accent">
          <h2>Параметры</h2>
          <p className="room-text">
            {isLoading
              ? 'Загружаем данные комнаты...'
              : 'Сводка по комнате и текущему составу.'}
          </p>
          <ul className="room-list">
            <li>
              <span>ID комнаты</span>
              <strong>{roomIdLabel}</strong>
            </li>
            <li>
              <span>Тематика</span>
              <strong>{data?.quizTheme ?? '—'}</strong>
            </li>
            <li>
              <span>Лимит участников</span>
              <strong>{data?.maxParticipants ?? '—'}</strong>
            </li>
            <li>
              <span>Участники</span>
              <strong>
                {participantsCount ?? '—'}
                {data?.maxParticipants ? ` / ${data.maxParticipants}` : ''}
              </strong>
            </li>
            <li>
              <span>Сообщений</span>
              <strong>{messages.length}</strong>
            </li>
          </ul>
        </article>

        <article className="room-card room-card--wide room-card--accent">
          <div className="room-game">
            <div className="room-game__header">
              <div>
                <h2>Раунд</h2>
                <p className="room-text">
                  {isGameFinished
                    ? 'Игра завершена.'
                    : hasActiveQuestion
                      ? 'Вопросы идут по очереди, ходят команды по очереди.'
                      : 'Ожидаем старт раунда.'}
                </p>
              </div>
              <div className="room-game__meta">
                <span
                  className={`room-team room-team--${activeTeamClass} is-active room-team--static`}
                >
                  Ход: {activeTeamLabel}
                </span>
                <span
                  className={`room-tag ${gameView.isTimeUp ? 'room-tag--danger' : ''}`}
                  aria-live="polite"
                >
                  Таймер: {timerLabel}
                </span>
              </div>
            </div>

            {!hasActiveQuestion && !isGameFinished && (
              <p className="room-text">Ждем первый вопрос.</p>
            )}

            {hasActiveQuestion && (
              <>
                <div className="room-game__question">
                  <p className="room-eyebrow">Вопрос № {gameView.activeQuestionIndex}</p>
                  <h3>{gameView.activeQuestion?.question}</h3>
                </div>

                {gameView.isTeamTurn ? (
                  <div className="room-game__answers">
                    <p className="room-text">
                      Ваш ход. Обсудите ответ и выберите вариант.
                    </p>
                    <div className="room-actions-grid">
                      {gameView.activeQuestion?.answers.map((answer) => (
                        <button
                          key={answer}
                          className={`room-chip ${gameView.selectedAnswer === answer ? 'is-selected' : ''}`}
                          type="button"
                          onClick={() => onAnswer(answer)}
                          disabled={!gameView.canAnswer}
                          aria-pressed={gameView.selectedAnswer === answer}
                        >
                          {answer}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="room-game__waiting">
                    <p className="room-text">
                      Сейчас отвечает соперник. У вас обратный отсчет.
                    </p>
                  </div>
                )}

                {gameView.selectedAnswer && (
                  <p className="room-text">Вы выбрали: {gameView.selectedAnswer}</p>
                )}
                {gameView.answerStatus && (
                  <p className="room-text">
                    Результат: {gameView.answerStatus === 'correct' ? 'Верно' : 'Неверно'}
                  </p>
                )}
                {gameView.isTimeUp && !gameView.answerStatus && (
                  <p className="room-text room-text--error">Время вышло.</p>
                )}
              </>
            )}

            {isHost && gameView.status === 'active' && (
              <div className="room-game__controls">
                <button
                  className="room-btn room-btn--ghost"
                  type="button"
                  onClick={onNextQuestion}
                  disabled={!canRequestNextQuestion || isAdvancingQuestion}
                >
                  {nextLabel}
                </button>
                <p className="room-text">Следующий вопрос открывается кнопкой хоста.</p>
              </div>
            )}
          </div>
        </article>

        <article className="room-card room-card--wide room-card--chat">
          <div className="room-chat">
            <div className="room-chat__header">
              <div>
                <h2>Чат комнаты</h2>
                <p className="room-text">Сообщения видны всем участникам.</p>
              </div>
              <div className="room-chat__teams">
                <span className={`room-team room-team--${team} is-active room-team--static`}>
                  Ваша команда: {teamLabel}
                </span>
              </div>
            </div>

            <ul className="room-chat__messages">
              {messages.length === 0 && (
                <li className="room-chat__empty">Сообщений пока нет.</li>
              )}
              {messages.map((message, index) => {
                const isRed = message.command === 'red'
                const time = formatTime(message.createdAt)
                return (
                  <li
                    key={`${message.createdAt}-${index}`}
                    className={`room-chat__bubble ${
                      isRed ? 'room-chat__bubble--red' : 'room-chat__bubble--blue'
                    }`}
                  >
                    <div className="room-chat__meta">
                      <span className="room-chat__team">{isRed ? 'Красные' : 'Синие'}</span>
                      {time && <span>{time}</span>}
                    </div>
                    <p className="room-chat__text">{message.text}</p>
                  </li>
                )
              })}
              <li ref={messageEndRef} className="room-chat__spacer" aria-hidden="true" />
            </ul>

            <form className="room-chat__composer" onSubmit={onSend}>
              <input
                type="text"
                placeholder={adminState.isChatMuted ? 'Чат на паузе' : 'Ваше сообщение'}
                value={draft}
                onChange={(event) => onDraftChange(event.target.value)}
                maxLength={300}
                disabled={adminState.isChatMuted}
              />
              <button
                className="room-btn room-btn--primary"
                type="submit"
                disabled={!draft.trim() || !canInitRoom || adminState.isChatMuted}
              >
                Отправить
              </button>
            </form>
          </div>
        </article>

        {data?.role === 'host' && (
          <AdminPanel
            roomIdLabel={roomIdLabel}
            participants={data?.participants}
            participantsCount={participantsCount}
            maxParticipants={data?.maxParticipants}
            onStartGame={onStartGame}
            isStartDisabled={isStartDisabled}
            onNextQuestion={onNextQuestion}
            isNextQuestionDisabled={!canRequestNextQuestion}
            isNextQuestionLoading={isAdvancingQuestion}
            gameView={gameView}
            adminState={adminState}
            adminActions={adminActions}
          />
        )}
      </section>
    </div>
  )
}

export default RoomView
