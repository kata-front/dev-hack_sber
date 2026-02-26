import { type FormEvent, useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import './Room.scss'
import { useInitCreatingRoomQuery } from './socketApi'
import { socketService } from '../../shared/socketServise'
import type { TeamCommand } from '../../shared/types'

const SOCKET_EVENTS = {
  message: 'message',
}

const formatTime = (value?: string) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

function Room() {
  const { roomId } = useParams()
  const roomIdNumber = Number(roomId)
  const canInitRoom = Number.isFinite(roomIdNumber)

  const { data, isLoading, isError } = useInitCreatingRoomQuery(roomIdNumber, {
    skip: !canInitRoom,
  })

  const [draft, setDraft] = useState('')
  const [team, setTeam] = useState<TeamCommand>('red')
  const messageEndRef = useRef<HTMLLIElement | null>(null)

  const messages = data?.messages ?? []
  const participantsCount =
    typeof data?.participants?.length === 'number' ? data?.participants?.length : null

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

  return (
    <div className="room-page">
      <div className="orb orb--one" />
      <div className="orb orb--two" />
      <div className="grid-glow" />

      <header className="room-top">
        <div className="room-title">
          <p className="room-eyebrow">Комната № {data?.roomId ?? roomId ?? '—'}</p>
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
              <strong>{data?.roomId ?? roomId ?? '—'}</strong>
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
                <button
                  type="button"
                  className={`room-team room-team--red ${team === 'red' ? 'is-active' : ''}`}
                  onClick={() => setTeam('red')}
                  aria-pressed={team === 'red'}
                >
                  Красные
                </button>
                <button
                  type="button"
                  className={`room-team room-team--blue ${team === 'blue' ? 'is-active' : ''}`}
                  onClick={() => setTeam('blue')}
                  aria-pressed={team === 'blue'}
                >
                  Синие
                </button>
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

            <form className="room-chat__composer" onSubmit={handleSend}>
              <input
                type="text"
                placeholder="Ваше сообщение"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
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
      </section>
    </div>
  )
}

export default Room
