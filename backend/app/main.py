from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend/.env is loaded at startup
ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / "backend" / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.predictions import router as prediction_router
from app.api.complaints import router as complaints_router
from app.api.network import router as network_router
from app.api.chatbot import router as chatbot_router

app = FastAPI(title="Intelligent Telecom Operations Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router, prefix="/api")
app.include_router(prediction_router, prefix="/api")
app.include_router(complaints_router, prefix="/api")
app.include_router(network_router, prefix="/api")
app.include_router(chatbot_router, prefix="/api")

@app.get("/")
def root():
    return {
        "name": "Intelligent Telecom Operations Platform",
        "status": "running"
    }