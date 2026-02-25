import { useState } from 'react'
import ModalShell from './ModalShell'
import { useCreateRoomMutation } from '../pinApi'
import { useNavigate } from 'react-router-dom'

function CreateModal() {
  const navigate = useNavigate()
  const [roomName, setRoomName] = useState('')
  const [quizTheme, setQuizTheme] = useState('')
  const [maxParticipants, setMaxParticipants] = useState('')
  const [error, setError] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const [createRoom] = useCreateRoomMutation()

  const handleSubmit = async() => {
    setSubmitted(true)

    const issues: string[] = []
    const nameValue = roomName.trim()
    const themeValue = quizTheme.trim()
    const maxValue = Number(maxParticipants)

    if (!nameValue) issues.push('название комнаты')
    if (!themeValue) issues.push('тематику квиза')
    if (!Number.isFinite(maxValue) || maxValue < 2) {
      issues.push('макс. участников (от 2)')
    }

    if (issues.length > 0) {
      setError(`Проверьте: ${issues.join(', ')}.`)
      return
    }

    setError('')

    const payload = {
      roomName: nameValue,
      quizTheme: themeValue,
      maxParticipants: maxValue,
    }

    const ok = createRoom(payload).unwrap()

    if (!ok) {
      setError('Не удалось создать комнату. Попробуйте снова.')
    }

    navigate('/room')
  }

  const nameInvalid = submitted && !roomName.trim()
  const themeInvalid = submitted && !quizTheme.trim()
  const maxInvalid =
    submitted && (!Number.isFinite(Number(maxParticipants)) || Number(maxParticipants) < 2)

  return (
    <ModalShell
      title="Создание комнаты"
      subtitle="Укажите параметры квиза, чтобы собрать команду и начать игру."
    >
      <label className="modal-field">
        <span>Название комнаты</span>
        <input
          type="text"
          placeholder="Например, Команда Альфа"
          value={roomName}
          onChange={(event) => setRoomName(event.target.value)}
          aria-invalid={nameInvalid}
          data-invalid={nameInvalid}
        />
      </label>
      <label className="modal-field">
        <span>Тематика квиза</span>
        <input
          type="text"
          placeholder="История, IT, кино..."
          value={quizTheme}
          onChange={(event) => setQuizTheme(event.target.value)}
          aria-invalid={themeInvalid}
          data-invalid={themeInvalid}
        />
      </label>
      <label className="modal-field">
        <span>Макс. участников</span>
        <input
          type="number"
          min={2}
          max={200}
          placeholder="Например, 8"
          value={maxParticipants}
          onChange={(event) => setMaxParticipants(event.target.value)}
          aria-invalid={maxInvalid}
          data-invalid={maxInvalid}
        />
        <p className="modal-hint">Рекомендуем 4–12 человек для быстрого старта.</p>
      </label>
      <p className="modal-alert" data-visible={Boolean(error)}>
        {error || 'Заполните поля, чтобы продолжить.'}
      </p>
      <button className="modal-action" type="button" onClick={handleSubmit}>
        Создать комнату
      </button>
    </ModalShell>
  )
}

export default CreateModal
