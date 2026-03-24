"""
智能疗愈仓系统 - FastAPI 后端入口
Healing Pod System - FastAPI Backend Entry Point
"""
from contextlib import asynccontextmanager
from importlib import import_module
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from loguru import logger
import sys
import time

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


def load_router(module_name: str) -> APIRouter | None:
    """按模块单独加载路由，单个组件失败时进入降级模式。"""
    try:
        module = import_module(module_name)
        return getattr(module, "router")
    except Exception as exc:
        logger.warning(f"Skipping router {module_name} due to import failure: {exc}")
        return None


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
for module_name, prefix, tags in [
    ("api.emotion", "/api/emotion", ["Emotion"]),
    ("api.therapy", "/api/therapy", ["Therapy"]),
    ("api.device", "/api/device", ["Device"]),
    ("api.session", "/api/session", ["Session"]),
    ("api.admin", "/api/admin", ["Admin"]),
    ("api.community", "", ["Community"]),
]:
    router = load_router(module_name)
    if router is not None:
        app.include_router(router, prefix=prefix, tags=tags)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "智能疗愈仓系统 API", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
