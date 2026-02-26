import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ModalShell from './ModalShell'
import { useCheckPinMutation } from '../pinApi'

function PinModal() {
  const input = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const [checkPin, { isLoading }] = useCheckPinMutation()
  const [showError, setShowError] = useState(false)

  const handleSubmit = async () => {
    const value = Number(input.current?.value ?? '')

    if (!Number.isFinite(value)) {
      setShowError(true)
      return
    }

    try {
      const response = await checkPin(value).unwrap()
      if (response.ok) {
        setShowError(false)
        navigate(`/room/${response.roomId}`)
      } else {
        setShowError(true)
      }
    } catch {
      setShowError(true)
    }
  }

  return (
    <ModalShell
      title="Введите ПИН-код"
      subtitle="Для доступа к рабочему пространству подтвердите код."
    >
      <label className="modal-field">
        <span>ПИН-код</span>
        <input
          ref={input}
          type="password"
          inputMode="numeric"
          placeholder="••••"
          autoComplete="one-time-code"
        />
      </label>
      <p className="modal-error" data-visible={showError}>
        Неверный ПИН-код. Попробуйте снова.
      </p>
      <button className="modal-action" type="button" onClick={handleSubmit} disabled={isLoading}>
        Войти
      </button>
    </ModalShell>
  )
}

export default PinModal
