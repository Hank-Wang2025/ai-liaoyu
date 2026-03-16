# API 路由模块
from .emotion import router as emotion_router
from .therapy import router as therapy_router
from .device import router as device_router
from .session import router as session_router
from .admin import router as admin_router
from .community import router as community_router

__all__ = [
    "emotion_router",
    "therapy_router", 
    "device_router",
    "session_router",
    "admin_router",
    "community_router"
]
