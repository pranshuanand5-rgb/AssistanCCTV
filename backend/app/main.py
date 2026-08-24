from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import BACKEND_DIR, settings
from app.database.base import SessionLocal, init_database
from app.services.camera_service import CameraManager
from app.vision.risk_engine import RiskEngine
from app.websocket.manager import WebSocketManager


websocket_manager = WebSocketManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    websocket_manager.set_loop(asyncio.get_running_loop())
    app.state.websocket_manager = websocket_manager
    app.state.camera_manager = CameraManager(
        session_factory=SessionLocal,
        websocket_manager=websocket_manager,
        risk_engine=RiskEngine(),
    )
    app.state.camera_manager.bootstrap()
    try:
        yield
    finally:
        app.state.camera_manager.stop_all()


app = FastAPI(
    title="IBVAP AI Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.mount("/data", StaticFiles(directory=str(BACKEND_DIR / "data")), name="data")


@app.get("/healthz")
def healthcheck() -> dict:
    return {"ok": True}
