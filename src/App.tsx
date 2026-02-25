import './App.css'

function App() {

  return (
    <div className="page">
      <div className="orb orb--one" aria-hidden="true" />
      <div className="orb orb--two" aria-hidden="true" />
      <div className="grid-glow" aria-hidden="true" />

      <main className="auth">
        <header className="auth__intro">
          <div className="brand">
            <span className="brand__pulse" aria-hidden="true" />
            <div>
              <p className="brand__eyebrow">SBER TECH LAB</p>
              <h1 className="brand__title">Регистрация в системе</h1>
            </div>
          </div>
          <p className="brand__subtitle">
            Создайте аккаунт для доступа к песочнице, документации и управлению
            цифровыми продуктами.
          </p>
          <div className="signals">
            <div className="signal">
              <span className="signal__label">Статус</span>
              <span className="signal__value">Стабильная сеть</span>
            </div>
            <div className="signal">
              <span className="signal__label">API</span>
              <span className="signal__value">v3.2 / 128 ms</span>
            </div>
            <div className="signal">
              <span className="signal__label">Контроль</span>
              <span className="signal__value">Полный доступ</span>
            </div>
          </div>
        </header>

        <section className="auth__card">
          <div className="auth__tabs">
            <button className="tab" type="button">
              Вход
            </button>
            <button className="tab tab--active" type="button">
              Регистрация
            </button>
          </div>

          <form className="auth__form">
            <label className="field">
              <span>Имя и фамилия</span>
              <input type="text" placeholder="Анна Новикова" />
            </label>
            <label className="field">
              <span>Корпоративный email</span>
              <input type="email" placeholder="name@sber.tech" />
            </label>
            <label className="field">
              <span>Пароль</span>
              <input type="password" placeholder="Минимум 8 символов" />
            </label>
            <label className="field">
              <span>Роль в проекте</span>
              <input type="text" placeholder="Product / Engineering" />
            </label>
          </form>

          <div className="auth__actions">
            <button className="btn btn--primary" type="button">
              Создать аккаунт
            </button>
            <button className="btn btn--ghost" type="button">
              Продолжить с SSO
            </button>
          </div>

          <p className="auth__footnote">
            Нажимая «Создать аккаунт», вы подтверждаете согласие с политиками
            безопасности.
          </p>
        </section>
      </main>
    </div>
  )
}

export default App
