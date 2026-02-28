import os

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.constants import API_V1_PREFIX, DEFAULT_CORS_ORIGINS
from app.api.health import router as health_router
from app.api.legacy import router as legacy_router
from app.api.rooms import router as rooms_router
from app.api.session import router as session_router
from app.services.question_generator import QuestionGenerator
from app.services.room_store import RoomStore
from app.services.session_store import SessionStore
from app.sockets.gateway import SocketGateway

app = FastAPI(
    title="QuizBattle API",
    version="2.0.0",
    description=(
        "based rooms api"
    ),
    docs_url=f"{API_V1_PREFIX}/docs",
    redoc_url=f"{API_V1_PREFIX}/redoc",
    openapi_url=f"{API_V1_PREFIX}/openapi.json",
)

state_dir = os.getenv("STATE_DIR", "/data").strip() or "/data"
room_state_file = os.getenv("ROOM_STATE_FILE", f"{state_dir}/rooms_state.json").strip() or f"{state_dir}/rooms_state.json"
session_state_file = (
    os.getenv("SESSION_STATE_FILE", f"{state_dir}/sessions_state.json").strip()
    or f"{state_dir}/sessions_state.json"
)
disconnect_grace_seconds = int(os.getenv("SOCKET_DISCONNECT_GRACE_SECONDS", "20"))

cors_env = os.getenv("CORS_ALLOW_ORIGINS")
allow_origins = (
    [origin.strip() for origin in cors_env.split(",") if origin.strip()]
    if cors_env
    else DEFAULT_CORS_ORIGINS
)
is_wildcard_cors = "*" in allow_origins

if is_wildcard_cors:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.state.room_store = RoomStore(storage_path=room_state_file)
app.state.session_store = SessionStore(storage_path=session_state_file)
app.state.question_generator = QuestionGenerator()
app.include_router(rooms_router, prefix=API_V1_PREFIX)
app.include_router(health_router, prefix=API_V1_PREFIX)
app.include_router(session_router, prefix=API_V1_PREFIX)
app.include_router(legacy_router, prefix=API_V1_PREFIX)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=["*"] if is_wildcard_cors else allow_origins,
)
socket_gateway = SocketGateway(
    sio=sio,
    room_store=app.state.room_store,
    session_store=app.state.session_store,
    question_generator=app.state.question_generator,
    disconnect_grace_seconds=disconnect_grace_seconds,
)
socket_gateway.register_handlers()
socket_app = socketio.ASGIApp(sio, other_asgi_app=app, socketio_path="socket.io")
