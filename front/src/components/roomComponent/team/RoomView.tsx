import type { FormEvent, RefObject } from 'react'
import type { InfoRoom, RoomMessage, TeamCommand } from '../../../shared/types'
import AdminPanel from '../adminPanel/AdminPanel'
import '../Room.scss'

const formatTime = (value?: string) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
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
}: RoomViewProps) {
  const roomIdLabel = data?.roomId ?? roomId ?? '—'
  const teamLabel = team === 'red' ? 'Красные' : 'Синие'
  const pageClass = team === 'red' ? 'room-page--red' : 'room-page--blue'

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
        </div>
        <div className="room-actions">
          <button className="room-btn room-btn--ghost" type="button">
            Поделиться ссылкой
          </button>
          <button className="room-btn room-btn--primary" type="button">
            Старт
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
            {isLoading ? 'Загружаем данные комнаты...' : 'Данные комнаты и статистика.'}
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

        <article className="room-card room-card--wide room-card--chat">
          <div className="room-chat">
            <div className="room-chat__header">
              <div>
                <h2>Чат комнаты</h2>
                <p className="room-text">Сообщения видны всем участникам.</p>
              </div>
              <div className="room-chat__teams">
                <span
                  className={`room-team room-team--${team} is-active room-team--static`}
                >
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
                placeholder="Ваше сообщение"
                value={draft}
                onChange={(event) => onDraftChange(event.target.value)}
                maxLength={300}
              />
              <button
                className="room-btn room-btn--primary"
                type="submit"
                disabled={!draft.trim() || !canInitRoom}
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
          />
        )}
      </section>
    </div>
  )
}

export default RoomView
