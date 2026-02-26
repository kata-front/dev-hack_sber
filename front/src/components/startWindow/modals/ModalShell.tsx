import type { ReactNode } from 'react'
import './ModalShell.scss'

type ModalShellProps = {
  title: string
  subtitle?: string
  children?: ReactNode
}

function ModalShell({ title, subtitle, children }: ModalShellProps) {
  return (
    <div className="modal-page">
      <div className="orb orb--one" aria-hidden="true" />
      <div className="orb orb--two" aria-hidden="true" />
      <div className="grid-glow" aria-hidden="true" />

      <section className="modal-card" role="dialog" aria-modal="true">
        <header className="modal-header">
          <p className="modal-eyebrow">SBER TECH LAB</p>
          <h2 className="modal-title">{title}</h2>
          {subtitle ? <p className="modal-subtitle">{subtitle}</p> : null}
        </header>
        <div className="modal-body">{children}</div>
      </section>
    </div>
  )
}

export default ModalShell
