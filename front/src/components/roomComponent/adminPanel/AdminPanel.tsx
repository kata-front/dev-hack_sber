import { useState } from 'react'
import './AdminPanel.scss'
import type { InfoRoom } from '../../../shared/types'

type AdminPanelProps = {
  roomIdLabel: string | number
  participants?: InfoRoom['participants']
  participantsCount: number | null
  maxParticipants?: number
}

function AdminPanel({
  roomIdLabel,
  participants,
  participantsCount,
  maxParticipants,
}: AdminPanelProps) {
  const [isLobbyLocked, setIsLobbyLocked] = useState(false)
  const [isChatMuted, setIsChatMuted] = useState(false)
  const [areHintsEnabled, setAreHintsEnabled] = useState(true)

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

  return (
    <article className="room-card room-card--full room-card--admin">
      <div className="room-admin">
        <div className="room-admin__header">
          <div>
            <p className="room-eyebrow">Панель хоста</p>
            <h2>Управление игрой</h2>
            <p className="room-text">
              Настройте доступ, запустите раунд и следите за балансом команд.
            </p>
          </div>
          <div className="room-admin__status">
            <span className="room-badge room-badge--live">Хост онлайн</span>
            <span className="room-badge">
              Участники: {participantsCount ?? safeParticipants.length ?? '—'}
            </span>
            <span className="room-badge">ПИН: {roomIdLabel}</span>
          </div>
        </div>

        <div className="room-admin__grid">
          <section className="room-admin__panel">
            <h3>Старт и темп</h3>
            <p className="room-text">Запускайте раунды и держите динамику.</p>
            <div className="room-actions-grid">
              <button className="room-btn room-btn--primary" type="button">
                Старт раунда
              </button>
              <button className="room-btn room-btn--ghost" type="button">
                Пауза
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
                className={`room-toggle ${isLobbyLocked ? 'is-active' : ''}`}
                type="button"
                onClick={() => setIsLobbyLocked((value) => !value)}
                aria-pressed={isLobbyLocked}
              >
                <span className="room-toggle__meta">
                  <span className="room-toggle__title">Закрыть вход</span>
                  <span className="room-toggle__desc">
                    Новые участники не смогут зайти.
                  </span>
                </span>
                <span className="room-toggle__pill">{isLobbyLocked ? 'Вкл' : 'Выкл'}</span>
              </button>
              <button
                className={`room-toggle ${isChatMuted ? 'is-active' : ''}`}
                type="button"
                onClick={() => setIsChatMuted((value) => !value)}
                aria-pressed={isChatMuted}
              >
                <span className="room-toggle__meta">
                  <span className="room-toggle__title">Тихий чат</span>
                  <span className="room-toggle__desc">Сообщения временно отключены.</span>
                </span>
                <span className="room-toggle__pill">{isChatMuted ? 'Вкл' : 'Выкл'}</span>
              </button>
              <button
                className={`room-toggle ${areHintsEnabled ? 'is-active' : ''}`}
                type="button"
                onClick={() => setAreHintsEnabled((value) => !value)}
                aria-pressed={areHintsEnabled}
              >
                <span className="room-toggle__meta">
                  <span className="room-toggle__title">Подсказки</span>
                  <span className="room-toggle__desc">Показывать командам наводки.</span>
                </span>
                <span className="room-toggle__pill">{areHintsEnabled ? 'Вкл' : 'Выкл'}</span>
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
              <button className="room-btn room-btn--ghost" type="button">
                Перемешать состав
              </button>
              <button className="room-btn room-btn--ghost" type="button">
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
