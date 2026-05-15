"""
HealthAI - 智能情绪管理平台
FastAPI Application Entry Point
"""

import asyncio
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine, Base
from app.api.v1 import biometric, emotion, menstrual, diary, chat, music, interview, auth
from app.services.semantic_cache_service import get_semantic_cache
from app.services.conversation_compaction_service import get_conversation_compaction_service

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
    # Startup: Initialize services
    print("[Startup] Initializing HealthAI services...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    print("[Startup] Database tables created")
    
    # Initialize semantic cache service (warm-up)
    if settings.SEMANTIC_CACHE_ENABLED:
        try:
            semantic_cache = get_semantic_cache()
            if semantic_cache and hasattr(semantic_cache, 'get_cache_stats'):
                stats = semantic_cache.get_cache_stats()
            else:
                stats = {"error": "cache unavailable"}
            if stats.get("available"):
                print(f"[Startup] Semantic cache initialized: {stats}")
            else:
                print("[Startup] Semantic cache not available (Redis not connected)")
        except Exception as e:
            print(f"[Startup] Failed to initialize semantic cache: {e}")
    
    # Initialize conversation compaction service
    try:
        compaction_service = get_conversation_compaction_service()
        print("[Startup] Conversation compaction service initialized")
    except Exception as e:
        print(f"[Startup] Failed to initialize compaction service: {e}")
    
    print(f"[Startup] {settings.APP_NAME} v{settings.APP_VERSION} started successfully")
    yield
    
    # Shutdown: cleanup if needed
    print("[Shutdown] Cleaning up resources...")


# Configure FastAPI with HTTP/2 support
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="智能情绪管理平台 API - 帮助女性追踪月经周期、预测PMS情绪波动、提供AI情绪支持",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    # HTTP/2 configuration
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Local development server"
        }
    ]
)

# Mount music files directory for local music playback
music_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "music")
os.makedirs(music_dir, exist_ok=True)
app.mount("/music", StaticFiles(directory=music_dir), name="music")

frontend_dist_path = os.path.join(os.path.dirname(__file__), "../../frontend/dist")
if os.path.isdir(frontend_dist_path):
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="frontend")
    print(f"Frontend static files mounted from {frontend_dist_path}")
else:
    print(f"Frontend dist not found at {frontend_dist_path}, API only mode.")

# GZip compression middleware
if settings.ENABLE_GZIP_COMPRESSION:
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    print("[Config] GZip compression enabled")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Length", "Content-Type", "X-Request-ID"],
    max_age=3600,
)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": asyncio.get_event_loop().time()
    }


# Performance metrics endpoint
@app.get("/metrics", tags=["Metrics"])
async def get_metrics():
    """Get performance metrics and service status"""
    metrics = {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": asyncio.get_event_loop().time(),
        "features": {
            "streaming": settings.STREAMING_ENABLED,
            "semantic_cache": settings.SEMANTIC_CACHE_ENABLED,
            "awareness_memory": settings.AWARENESS_MEMORY_ENABLED,
            "http2": settings.HTTP2_ENABLED,
            "keep_alive": settings.KEEP_ALIVE_ENABLED,
            "gzip_compression": settings.ENABLE_GZIP_COMPRESSION,
        },
    }
    
    if settings.SEMANTIC_CACHE_ENABLED:
        try:
            semantic_cache = get_semantic_cache()
            cache_stats = semantic_cache.get_cache_stats()
            metrics["semantic_cache"] = cache_stats
        except Exception as e:
            metrics["semantic_cache"] = {"error": str(e)}
    
    return metrics


# Include API routers
app.include_router(biometric.router, prefix=settings.API_V1_PREFIX)
app.include_router(emotion.router, prefix=settings.API_V1_PREFIX)
app.include_router(menstrual.router, prefix=settings.API_V1_PREFIX)
app.include_router(diary.router, prefix=settings.API_V1_PREFIX)
app.include_router(chat.router, prefix=settings.API_V1_PREFIX)
app.include_router(music.router, prefix=settings.API_V1_PREFIX)
app.include_router(interview.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "欢迎使用 HealthAI - 智能情绪管理平台",
        "docs": "/docs",
        "version": settings.APP_VERSION,
        "features": {
            "streaming": "/api/v1/chat/stream (SSE)",
            "websocket": "/api/v1/chat/ws/{user_id}",
            "rest": "/api/v1/chat/message",
        }
    }
