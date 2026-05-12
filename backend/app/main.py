"""
HealthAI - 智能情绪管理平台
FastAPI Application Entry Point
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine, Base
from app.api.v1 import biometric, emotion, menstrual, diary, chat, music, interview

# Import all models to ensure they are registered with Base.metadata
from app.models.user import User
from app.models.biometric import BiometricData
from app.models.menstrual import MenstrualRecord
from app.models.mood import MoodDiary
from app.models.conversation import Conversation
from app.models.chat_memory import ChatMemory
from app.models.music import Music
from app.models.assessment import AssessmentObservation, AssessmentSession


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create database tables
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: cleanup if needed
    pass


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="智能情绪管理平台 API - 帮助女性追踪月经周期、预测PMS情绪波动、提供AI情绪支持",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Mount music files directory for local music playback
music_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "music")
os.makedirs(music_dir, exist_ok=True)
app.mount("/music", StaticFiles(directory=music_dir), name="music")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


# Include API routers
app.include_router(biometric.router, prefix=settings.API_V1_PREFIX)
app.include_router(emotion.router, prefix=settings.API_V1_PREFIX)
app.include_router(menstrual.router, prefix=settings.API_V1_PREFIX)
app.include_router(diary.router, prefix=settings.API_V1_PREFIX)
app.include_router(chat.router, prefix=settings.API_V1_PREFIX)
app.include_router(music.router, prefix=settings.API_V1_PREFIX)
app.include_router(interview.router, prefix=settings.API_V1_PREFIX)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "欢迎使用 HealthAI - 智能情绪管理平台",
        "docs": "/docs",
        "version": settings.APP_VERSION
    }
