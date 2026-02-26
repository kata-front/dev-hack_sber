import './Room.scss'

function Room() {
  return (
    <div className="room-page">
      <div className="orb orb--one" aria-hidden="true" />
      <div className="orb orb--two" aria-hidden="true" />
      <div className="grid-glow" aria-hidden="true" />

      <header className="room-top">
        <div className="room-title">
          <p className="room-eyebrow">QUIZ ROOM</p>
          <h1 className="room-name">Комната «Альфа»</h1>
          <p className="room-subtitle">Подготовка к старту. Участники подключаются.</p>
        </div>
        <div className="room-actions">
          <button className="room-btn room-btn--primary" type="button">
            Запустить раунд
          </button>
          <button className="room-btn room-btn--ghost" type="button">
            Настройки
          </button>
        </div>
      </header>

      <section className="room-grid">
        <article className="room-card">
          <h2>Сценарий квиза</h2>
          <p className="room-text">
            Тематика: Технологии и креатив. Сетка вопросов собирается автоматически.
          </p>
          <div className="room-progress">
            <div className="room-progress__bar" style={{ width: '62%' }} />
          </div>
          <div className="room-meta">
            <span>Раунд 1</span>
            <span>12 вопросов</span>
          </div>
        </article>

        <article className="room-card room-card--accent">
          <h2>Участники</h2>
          <ul className="room-list">
            <li>
              <span>Алиса</span>
              <span>готово</span>
            </li>
            <li>
              <span>Кирилл</span>
              <span>подключается</span>
            </li>
            <li>
              <span>Мария</span>
              <span>готово</span>
            </li>
            <li>
              <span>Илья</span>
              <span>в ожидании</span>
            </li>
          </ul>
          <button className="room-btn room-btn--ghost" type="button">
            Пригласить
          </button>
        </article>

        <article className="room-card">
          <h2>Быстрые действия</h2>
          <div className="room-actions-grid">
            <button className="room-chip" type="button">Скопировать код</button>
            <button className="room-chip" type="button">Сбросить таймер</button>
            <button className="room-chip" type="button">Сменить тему</button>
            <button className="room-chip" type="button">Проверка связи</button>
          </div>
        </article>
      </section>
    </div>
  )
}

export default Room
