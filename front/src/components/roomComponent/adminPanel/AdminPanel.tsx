import './AdminPanel.scss'
import type { InfoRoom, TeamCommand } from '../../../shared/types'
import type { GameViewState } from '../team/RoomView'
import type { AdminPanelActions, AdminPanelState } from './adminTypes'

type AdminPanelProps = {
  roomIdLabel: string | number
  participants?: InfoRoom['participants']
  participantsCount: number | null
  maxParticipants?: number
  onStartGame?: () => void
  isStartDisabled?: boolean
  onNextQuestion?: () => void
  isNextQuestionDisabled?: boolean
  isNextQuestionLoading?: boolean
  gameView?: GameViewState
  adminState: AdminPanelState
  adminActions: AdminPanelActions
}

const getTeamLabel = (team?: TeamCommand) =>
  team === 'red' ? 'Красные' : team === 'blue' ? 'Синие' : '—'

const getStatusLabel = (status?: GameViewState['status']) => {
  if (status === 'active') return 'Игра идет'
  if (status === 'finished') return 'Игра завершена'
  return 'Ожидание'
}

const getStatusTone = (status?: GameViewState['status']) => {
  if (status === 'active') return 'active'
  if (status === 'finished') return 'done'
  return 'idle'
}

function AdminPanel({
  roomIdLabel,
  participants,
  participantsCount,
  maxParticipants,
  onStartGame,
  isStartDisabled,
  onNextQuestion,
  isNextQuestionDisabled,
  isNextQuestionLoading,
  gameView,
  adminState,
  adminActions,
}: AdminPanelProps) {
  const safeParticipants = participants ?? []
  const redCount = safeParticipants.filter((participant) => participant.command === 'red').length
  const blueCount = safeParticipants.filter((participant) => participant.command === 'blue').length
  const teamTotal = typeof participantsCount === 'number' ? participantsCount : safeParticipants.length
  const redShare = teamTotal ? Math.round((redCount / teamTotal) * 100) : 0
  const blueShare = teamTotal ? Math.round((blueCount / teamTotal) * 100) : 0
  const occupancy =
    maxParticipants && teamTotal
      ? Math.min(100, Math.round((teamTotal / maxParticipants) * 100))
      : 0

  const activeTeamLabel = getTeamLabel(gameView?.activeTeam)
  const statusLabel = getStatusLabel(gameView?.status)
  const statusTone = getStatusTone(gameView?.status)
  const questionsLabel =
    gameView && gameView.totalQuestions > 0
      ? `${gameView.activeQuestionIndex} / ${gameView.totalQuestions}`
      : '—'
  const timerLabel =
    gameView?.isPaused && typeof gameView?.timeLeft === 'number'
      ? 'Пауза'
      : typeof gameView?.timeLeft === 'number'
        ? `${gameView.timeLeft}с`
        : '—'
  const answerLabel =
    gameView?.answerStatus === 'correct'
      ? 'Верно'
      : gameView?.answerStatus === 'incorrect'
        ? 'Неверно'
        : '—'
  const pauseLabel = adminState.isPaused ? 'Продолжить' : 'Пауза'

  return (
    <article className="room-card room-card--full room-card--admin">
      <div className="room-admin">
        <div className="room-admin__header">
          <div>
            <p className="room-eyebrow">Панель хоста</p>
            <h2>Управление игрой</h2>
            <p className="room-text">
              Контролируйте доступ, запускайте раунды и следите за балансом команд.
            </p>
          </div>
          <div className="room-admin__status">
            <span className="room-badge room-badge--live">Хост онлайн</span>
            <span className="room-badge">
              Участники: {participantsCount ?? safeParticipants.length ?? '—'}
            </span>
            <span className="room-badge">PIN: {roomIdLabel}</span>
          </div>
        </div>

        <div className="room-admin__grid">
          <section className="room-admin__panel room-admin__panel--game">
            <h3>Состояние игры</h3>
            <p className="room-text">Быстрый обзор текущего раунда.</p>
            <div className="room-admin__metrics">
              <div className="room-admin__metric">
                <span>Статус</span>
                <strong className={`room-admin__metric-value room-admin__metric-value--${statusTone}`}>
                  {statusLabel}
                </strong>
              </div>
              <div className="room-admin__metric">
                <span>Вопрос</span>
                <strong>{questionsLabel}</strong>
              </div>
              <div className="room-admin__metric">
                <span>Ход</span>
                <strong>{activeTeamLabel}</strong>
              </div>
              <div className="room-admin__metric">
                <span>Таймер</span>
                <strong>{timerLabel}</strong>
              </div>
              <div className="room-admin__metric">
                <span>Ответ</span>
                <strong>{answerLabel}</strong>
              </div>
            </div>
            {gameView?.activeQuestion ? (
              <div className="room-admin__question">
                <p className="room-eyebrow">Вопрос № {gameView.activeQuestionIndex}</p>
                <p className="room-admin__question-text">{gameView.activeQuestion.question}</p>
              </div>
            ) : (
              <p className="room-text">Ожидаем первый вопрос.</p>
            )}
          </section>

          <section className="room-admin__panel">
            <h3>Старт и темп</h3>
            <p className="room-text">Запускайте раунды и держите динамику.</p>
            <div className="room-actions-grid">
              <button
                className="room-btn room-btn--primary"
                type="button"
                onClick={onStartGame}
                disabled={isStartDisabled || !onStartGame}
              >
                Старт раунда
              </button>
              <button
                className="room-btn room-btn--ghost"
                type="button"
                onClick={onNextQuestion}
                disabled={isNextQuestionDisabled || isNextQuestionLoading || !onNextQuestion}
              >
                {isNextQuestionLoading ? 'Загрузка...' : 'Следующий вопрос'}
              </button>
              <button
                className="room-btn room-btn--ghost"
                type="button"
                onClick={adminActions.togglePause}
              >
                {pauseLabel}
              </button>
            </div>
            <div className="room-admin__stat">
              <div className="room-meta">
                <span>Заполнение комнаты</span>
                <strong>{occupancy}%</strong>
              </div>
              <div className="room-progress">
                <div className="room-progress__bar" style={{ width: `${occupancy}%` }} />
              </div>
            </div>
          </section>

          <section className="room-admin__panel">
            <h3>Доступ и чат</h3>
            <p className="room-text">Быстрые переключатели для модерации.</p>
            <div className="room-admin__toggles">
              <button
                className={`room-toggle ${adminState.isLobbyLocked ? 'is-active' : ''}`}
                type="button"
                onClick={adminActions.toggleLobbyLock}
                aria-pressed={adminState.isLobbyLocked}
              >
                <span className="room-toggle__meta">
                  <span className="room-toggle__title">Закрыть вход</span>
                  <span className="room-toggle__desc">Новые участники не смогут зайти.</span>
                </span>
                <span className="room-toggle__pill">
                  {adminState.isLobbyLocked ? 'Вкл' : 'Выкл'}
                </span>
              </button>
              <button
                className={`room-toggle ${adminState.isChatMuted ? 'is-active' : ''}`}
                type="button"
                onClick={adminActions.toggleChatMuted}
                aria-pressed={adminState.isChatMuted}
              >
                <span className="room-toggle__meta">
                  <span className="room-toggle__title">Тихий чат</span>
                  <span className="room-toggle__desc">Сообщения временно отключены.</span>
                </span>
                <span className="room-toggle__pill">
                  {adminState.isChatMuted ? 'Вкл' : 'Выкл'}
                </span>
              </button>
              <button
                className={`room-toggle ${adminState.areHintsEnabled ? 'is-active' : ''}`}
                type="button"
                onClick={adminActions.toggleHintsEnabled}
                aria-pressed={adminState.areHintsEnabled}
              >
                <span className="room-toggle__meta">
                  <span className="room-toggle__title">Подсказки</span>
                  <span className="room-toggle__desc">Показывать командам наводки.</span>
                </span>
                <span className="room-toggle__pill">
                  {adminState.areHintsEnabled ? 'Вкл' : 'Выкл'}
                </span>
              </button>
            </div>
          </section>

          <section className="room-admin__panel">
            <h3>Баланс команд</h3>
            <p className="room-text">Следите за распределением участников.</p>
            <div className="room-admin__teams">
              <div className="room-admin__team room-admin__team--red">
                <div className="room-admin__team-meta">
                  <span>Красные</span>
                  <strong>{redCount}</strong>
                </div>
                <div className="room-progress">
                  <div className="room-progress__bar" style={{ width: `${redShare}%` }} />
                </div>
              </div>
              <div className="room-admin__team room-admin__team--blue">
                <div className="room-admin__team-meta">
                  <span>Синие</span>
                  <strong>{blueCount}</strong>
                </div>
                <div className="room-progress">
                  <div className="room-progress__bar" style={{ width: `${blueShare}%` }} />
                </div>
              </div>
            </div>
            <div className="room-actions-grid">
              <button
                className="room-btn room-btn--ghost"
                type="button"
                onClick={adminActions.shuffleTeams}
              >
                Перемешать состав
              </button>
              <button
                className="room-btn room-btn--ghost"
                type="button"
                onClick={adminActions.resetTeams}
              >
                Сбросить команды
              </button>
            </div>
          </section>
        </div>
      </div>
    </article>
  )
}

export default AdminPanel


