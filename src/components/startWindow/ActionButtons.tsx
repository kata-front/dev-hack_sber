import { useState } from 'react'
import './ActionButtons.scss'
import type { startAction } from '../../shared/types'
import PinModal from './modals/PinModal'
import CreateModal from './modals/CreateModal'

function ActionButtons() {
  const [startAction, setStartAction] = useState<startAction>(null)

  return (
    <div className="action-page">
      {startAction === 'join' && <PinModal />}
      {startAction === 'create' && <CreateModal />}
      <div className="orb orb--one" aria-hidden="true" />
      <div className="orb orb--two" aria-hidden="true" />
      <div className="grid-glow" aria-hidden="true" />

      <section className="action-card">
        <button
          className="action-btn action-btn--join"
          type="button"
          onClick={() => setStartAction('join')}>
          <span>Присоединиться</span>
        </button>
        <button
          className="action-btn action-btn--create"
          type="button"
          onClick={() => setStartAction('create')}>
          <span>Создать</span>
        </button>
      </section>
    </div>
  )
}

export default ActionButtons
