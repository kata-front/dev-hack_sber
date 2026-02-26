from fastapi import FastAPI

from app.api.rooms import router as rooms_router
from app.services.room_store import RoomStore

app = FastAPI(
    title="QuizBattle API",
    version="0.1.0",
    description=(
        "based api"
    ),
    docs_url='/api/v1/docs'
)

app.state.room_store = RoomStore()
app.include_router(rooms_router)


@app.get("/api/v1/health", tags=["Health"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}

