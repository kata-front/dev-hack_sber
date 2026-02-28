# QuizBattle
Кейс от Сбера на devHack. Удобная платформа для проведения командных квиз-викторин с интеграцией AI для генерации вопросов

## ENV переменные

Используются (в `docker-compose.yml` / `.env`):

- `CORS_ALLOW_ORIGINS` — разрешенные origin (`*` по умолчанию)
- `GEMINI_API_KEY` — ключ Gemini для генерации вопросов
- `GEMINI_MODEL` — модель Gemini (по умолчанию `gemini-2.5-flash`)
- `GEMINI_TIMEOUT_SECONDS` — таймаут запроса к Gemini
- `SOCKET_DISCONNECT_GRACE_SECONDS` — задержка перед обработкой disconnect

## Docker запуск

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f
```

Остановка:

```bash
docker compose down
```

После запуска:

- `http://localhost:8888` — фронт
- `http://localhost:8888/api/v1/docs` — Swagger
