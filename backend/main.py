"""
智能疗愈仓系统 - FastAPI 后端入口
Healing Pod System - FastAPI Backend Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import sys
import time

from api import emotion_router, therapy_router, device_router, session_router, admin_router, community_router
from db.database import init_db, close_db


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/healing_pod_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level="DEBUG"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Healing Pod System...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down Healing Pod System...")
    await close_db()


app = FastAPI(
    title="智能疗愈仓系统",
    description="Healing Pod System API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


# Register routers
app.include_router(emotion_router, prefix="/api/emotion", tags=["Emotion"])
app.include_router(therapy_router, prefix="/api/therapy", tags=["Therapy"])
app.include_router(device_router, prefix="/api/device", tags=["Device"])
app.include_router(session_router, prefix="/api/session", tags=["Session"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(community_router, tags=["Community"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "智能疗愈仓系统 API", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
