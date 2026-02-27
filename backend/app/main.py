import os

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.constants import API_V1_PREFIX, DEFAULT_CORS_ORIGINS
from app.api.health import router as health_router
from app.api.rooms import router as rooms_router
from app.services.room_store import RoomStore
from app.sockets.gateway import SocketGateway

app = FastAPI(
    title="Dev Hack Sber API",
    version="1.1.0",
    description=(
        "based rooms api"
    ),
    docs_url=f"{API_V1_PREFIX}/docs",
    redoc_url=f"{API_V1_PREFIX}/redoc",
    openapi_url=f"{API_V1_PREFIX}/openapi.json",
)

cors_env = os.getenv("CORS_ALLOW_ORIGINS")
allow_origins = (
    [origin.strip() for origin in cors_env.split(",") if origin.strip()]
    if cors_env
    else DEFAULT_CORS_ORIGINS
)
is_wildcard_cors = "*" in allow_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if is_wildcard_cors else allow_origins,
    allow_credentials=False if is_wildcard_cors else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.room_store = RoomStore()
app.include_router(rooms_router, prefix=API_V1_PREFIX)
app.include_router(health_router, prefix=API_V1_PREFIX)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=["*"] if is_wildcard_cors else allow_origins,
)
socket_gateway = SocketGateway(sio=sio, store=app.state.room_store)
socket_gateway.register_handlers()
socket_app = socketio.ASGIApp(sio, other_asgi_app=app, socketio_path="socket.io")
