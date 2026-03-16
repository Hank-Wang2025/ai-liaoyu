"""
管理后台 API 路由
Admin Backend API Routes

Requirements: 15.2, 15.3, 15.5, 15.6
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from loguru import logger
import jwt
import hashlib
import os

from db.crud import (
    session_crud, 
    system_log_crud, 
    therapy_plan_crud,
    adjustment_record_crud
)

router = APIRouter()

# JWT Configuration
JWT_SECRET = os.environ.get("JWT_SECRET", "healing-pod-admin-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Admin roles for permission levels
class AdminRole:
    """管理员角色权限分级
    
    Requirements: 15.6 - 支持权限分级
    """
    SUPER_ADMIN = "super_admin"  # 超级管理员 - 所有权限
    ADMIN = "admin"              # 管理员 - 配置和查看权限
    OPERATOR = "operator"        # 操作员 - 仅查看权限


# Default admin credentials (should be changed in production)
# In production, this should be stored in a database with proper password hashing
ADMIN_USERS = {
    "admin": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": AdminRole.SUPER_ADMIN,
        "name": "System Administrator"
    },
    "operator": {
        "password_hash": hashlib.sha256("operator123".encode()).hexdigest(),
        "role": AdminRole.OPERATOR,
        "name": "System Operator"
    }
}

# Security
security = HTTPBearer(auto_error=False)


# ============== Pydantic Models ==============

class AdminLoginRequest(BaseModel):
    """管理员登录请求"""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


class AdminLoginResponse(BaseModel):
    """管理员登录响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class DeviceStatus(BaseModel):
    """设备状态"""
    name: str
    type: str
    connected: bool
    state: Optional[Dict[str, Any]] = None
    last_updated: Optional[str] = None


class DeviceStatusResponse(BaseModel):
    """设备状态响应"""
    devices: List[DeviceStatus]
    total: int
    connected_count: int


class UsageStatsResponse(BaseModel):
    """使用统计响应"""
    total_sessions: int
    total_duration_seconds: int
    avg_session_duration_seconds: float
    avg_improvement: Optional[float]
    sessions_today: int
    sessions_this_week: int
    sessions_this_month: int
    most_common_emotion: Optional[str]
    most_used_plan: Optional[str]
    emotion_distribution: Dict[str, int]
    daily_sessions: List[Dict[str, Any]]


class LogEntry(BaseModel):
    """日志条目"""
    id: int
    timestamp: str
    level: str
    module: str
    message: str
    details: Optional[Dict[str, Any]] = None


class LogQueryResponse(BaseModel):
    """日志查询响应"""
    logs: List[LogEntry]
    total: int
    page: int
    page_size: int


class TherapyPlanConfig(BaseModel):
    """疗愈方案配置"""
    id: str
    name: str
    description: Optional[str] = None
    target_emotions: List[str]
    intensity: str
    style: str
    duration: int
    phases: Optional[List[Dict[str, Any]]] = None


class DeviceConfigUpdate(BaseModel):
    """设备参数配置更新"""
    device_type: str
    settings: Dict[str, Any]


class ContentItem(BaseModel):
    """内容库项目"""
    id: str
    type: str  # audio, visual, plan
    name: str
    path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ============== Authentication ==============

def create_access_token(username: str, role: str) -> str:
    """创建 JWT access token"""
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": username,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """验证 JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, str]:
    """获取当前管理员（验证 token）
    
    Requirements: 15.6 - 管理后台需要管理员密码登录
    
    Returns:
        Dict containing username and role
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return {
        "username": payload.get("sub", ""),
        "role": payload.get("role", AdminRole.OPERATOR)
    }


def require_role(allowed_roles: List[str]):
    """权限检查装饰器
    
    Requirements: 15.6 - 支持权限分级
    
    Args:
        allowed_roles: 允许访问的角色列表
    """
    async def role_checker(admin: Dict[str, str] = Depends(get_current_admin)) -> Dict[str, str]:
        if admin["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {allowed_roles}"
            )
        return admin
    return role_checker


# ============== Auth Endpoints ==============

@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(request: AdminLoginRequest):
    """管理员登录
    
    Requirements: 15.6 - 管理后台需要管理员密码登录，支持权限分级
    """
    # Hash the provided password
    password_hash = hashlib.sha256(request.password.encode()).hexdigest()
    
    # Verify credentials
    user = ADMIN_USERS.get(request.username)
    if user is None or password_hash != user["password_hash"]:
        logger.warning(f"Failed login attempt for user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Create access token with role
    access_token = create_access_token(request.username, user["role"])
    
    logger.info(f"Admin user '{request.username}' (role: {user['role']}) logged in successfully")
    
    return AdminLoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=JWT_EXPIRATION_HOURS * 3600
    )


@router.post("/logout")
async def admin_logout(admin: Dict[str, str] = Depends(get_current_admin)):
    """管理员登出"""
    logger.info(f"Admin user '{admin['username']}' logged out")
    return {"message": "Logged out successfully"}


@router.get("/verify")
async def verify_admin_token(admin: Dict[str, str] = Depends(get_current_admin)):
    """验证管理员 token"""
    return {"valid": True, "username": admin["username"], "role": admin["role"]}


# ============== Device Status Endpoints ==============

@router.get("/devices", response_model=DeviceStatusResponse)
async def get_device_status(admin: Dict[str, str] = Depends(get_current_admin)):
    """获取设备状态
    
    Requirements: 15.2 - 支持查看设备状态
    """
    # In a real implementation, this would query actual device controllers
    # For now, we return mock device status
    devices = [
        DeviceStatus(
            name="main_light",
            type="light",
            connected=True,
            state={"color": "#4ECDC4", "brightness": 60, "is_on": True},
            last_updated=datetime.now().isoformat()
        ),
        DeviceStatus(
            name="ambient_light",
            type="light",
            connected=True,
            state={"color": "#FFD93D", "brightness": 40, "is_on": True},
            last_updated=datetime.now().isoformat()
        ),
        DeviceStatus(
            name="bgm_audio",
            type="audio",
            connected=True,
            state={"state": "playing", "volume": 0.5, "file": "relaxing_music.mp3"},
            last_updated=datetime.now().isoformat()
        ),
        DeviceStatus(
            name="voice_audio",
            type="audio",
            connected=True,
            state={"state": "stopped", "volume": 0.8},
            last_updated=datetime.now().isoformat()
        ),
        DeviceStatus(
            name="massage_chair",
            type="chair",
            connected=True,
            state={"mode": "gentle", "intensity": 5, "is_running": True},
            last_updated=datetime.now().isoformat()
        ),
        DeviceStatus(
            name="scent_diffuser",
            type="scent",
            connected=False,
            state=None,
            last_updated=None
        ),
        DeviceStatus(
            name="heart_rate_monitor",
            type="bio",
            connected=True,
            state={"heart_rate": 72, "connected_device": "Polar H10"},
            last_updated=datetime.now().isoformat()
        ),
        DeviceStatus(
            name="camera",
            type="camera",
            connected=True,
            state={"resolution": "1080p", "fps": 30},
            last_updated=datetime.now().isoformat()
        )
    ]
    
    connected_count = sum(1 for d in devices if d.connected)
    
    return DeviceStatusResponse(
        devices=devices,
        total=len(devices),
        connected_count=connected_count
    )


# ============== Usage Statistics Endpoints ==============

@router.get("/stats", response_model=UsageStatsResponse)
async def get_usage_stats(admin: Dict[str, str] = Depends(get_current_admin)):
    """获取使用统计
    
    Requirements: 15.2 - 支持查看使用统计、疗愈效果分析
    """
    try:
        # Get all sessions
        all_sessions = await session_crud.get_all(limit=1000)
        
        # Calculate statistics
        total_sessions = len(all_sessions)
        total_duration = sum(s.get("duration_seconds", 0) or 0 for s in all_sessions)
        avg_duration = total_duration / total_sessions if total_sessions > 0 else 0
        
        # Calculate improvement (based on emotion intensity change)
        improvements = []
        for s in all_sessions:
            initial = s.get("initial_emotion_intensity")
            final = s.get("final_emotion_intensity")
            if initial is not None and final is not None:
                # For negative emotions, lower intensity is better
                improvements.append(initial - final)
        
        avg_improvement = sum(improvements) / len(improvements) if improvements else None
        
        # Count sessions by time period
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)
        
        sessions_today = 0
        sessions_this_week = 0
        sessions_this_month = 0
        emotion_counts: Dict[str, int] = {}
        plan_counts: Dict[str, int] = {}
        daily_sessions: Dict[str, int] = {}
        
        for s in all_sessions:
            start_time_str = s.get("start_time")
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str)
                    
                    if start_time >= today_start:
                        sessions_today += 1
                    if start_time >= week_start:
                        sessions_this_week += 1
                    if start_time >= month_start:
                        sessions_this_month += 1
                    
                    # Daily breakdown for last 7 days
                    date_key = start_time.strftime("%Y-%m-%d")
                    if start_time >= today_start - timedelta(days=7):
                        daily_sessions[date_key] = daily_sessions.get(date_key, 0) + 1
                except (ValueError, TypeError):
                    pass
            
            # Count emotions
            emotion = s.get("initial_emotion_category")
            if emotion:
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            # Count plans
            plan_id = s.get("plan_id")
            if plan_id:
                plan_counts[plan_id] = plan_counts.get(plan_id, 0) + 1
        
        # Find most common
        most_common_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else None
        most_used_plan = max(plan_counts, key=plan_counts.get) if plan_counts else None
        
        # Format daily sessions for response
        daily_sessions_list = [
            {"date": date, "count": count}
            for date, count in sorted(daily_sessions.items())
        ]
        
        return UsageStatsResponse(
            total_sessions=total_sessions,
            total_duration_seconds=total_duration,
            avg_session_duration_seconds=avg_duration,
            avg_improvement=avg_improvement,
            sessions_today=sessions_today,
            sessions_this_week=sessions_this_week,
            sessions_this_month=sessions_this_month,
            most_common_emotion=most_common_emotion,
            most_used_plan=most_used_plan,
            emotion_distribution=emotion_counts,
            daily_sessions=daily_sessions_list
        )
        
    except Exception as e:
        logger.error(f"Error getting usage stats: {e}")
        # Return empty stats on error
        return UsageStatsResponse(
            total_sessions=0,
            total_duration_seconds=0,
            avg_session_duration_seconds=0,
            avg_improvement=None,
            sessions_today=0,
            sessions_this_week=0,
            sessions_this_month=0,
            most_common_emotion=None,
            most_used_plan=None,
            emotion_distribution={},
            daily_sessions=[]
        )


# ============== Log Query Endpoints ==============

@router.get("/logs", response_model=LogQueryResponse)
async def get_system_logs(
    admin: Dict[str, str] = Depends(get_current_admin),
    level: Optional[str] = Query(None, description="Filter by log level (DEBUG, INFO, WARNING, ERROR)"),
    module: Optional[str] = Query(None, description="Filter by module name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page")
):
    """获取系统日志
    
    Requirements: 15.5 - 支持系统日志查看和故障诊断
    """
    try:
        offset = (page - 1) * page_size
        
        if level:
            # Get logs by level
            all_logs = await system_log_crud.get_by_level(level.upper(), limit=1000)
        else:
            # Get all logs
            all_logs = await system_log_crud.get_all(limit=1000)
        
        # Filter by module if specified
        if module:
            all_logs = [log for log in all_logs if log.get("module") == module]
        
        # Sort by timestamp descending
        all_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Paginate
        total = len(all_logs)
        paginated_logs = all_logs[offset:offset + page_size]
        
        # Format logs
        log_entries = []
        for log in paginated_logs:
            details = log.get("details")
            if details and isinstance(details, str):
                import json
                try:
                    details = json.loads(details)
                except json.JSONDecodeError:
                    details = None
            
            log_entries.append(LogEntry(
                id=log.get("id", 0),
                timestamp=log.get("timestamp", ""),
                level=log.get("level", "INFO"),
                module=log.get("module", "unknown"),
                message=log.get("message", ""),
                details=details
            ))
        
        return LogQueryResponse(
            logs=log_entries,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error getting system logs: {e}")
        return LogQueryResponse(
            logs=[],
            total=0,
            page=page,
            page_size=page_size
        )


@router.get("/logs/levels")
async def get_log_levels(admin: Dict[str, str] = Depends(get_current_admin)):
    """获取可用的日志级别"""
    return {"levels": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]}


@router.get("/logs/modules")
async def get_log_modules(admin: Dict[str, str] = Depends(get_current_admin)):
    """获取已记录日志的模块列表"""
    try:
        all_logs = await system_log_crud.get_all(limit=1000)
        modules = list(set(log.get("module") for log in all_logs if log.get("module")))
        return {"modules": sorted(modules)}
    except Exception as e:
        logger.error(f"Error getting log modules: {e}")
        return {"modules": []}


# ============== Configuration Management Endpoints ==============

@router.get("/config/plans")
async def get_therapy_plans(admin: Dict[str, str] = Depends(get_current_admin)):
    """获取疗愈方案配置列表
    
    Requirements: 15.3 - 支持配置疗愈方案
    """
    try:
        plans = await therapy_plan_crud.get_all(limit=100)
        return {"plans": plans, "total": len(plans)}
    except Exception as e:
        logger.error(f"Error getting therapy plans: {e}")
        return {"plans": [], "total": 0}


@router.post("/config/plans")
async def create_therapy_plan(
    plan: TherapyPlanConfig,
    admin: Dict[str, str] = Depends(require_role([AdminRole.SUPER_ADMIN, AdminRole.ADMIN]))
):
    """创建疗愈方案
    
    Requirements: 15.3 - 支持配置疗愈方案
    Requires: admin or super_admin role
    """
    try:
        import json
        plan_data = {
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "target_emotions": json.dumps(plan.target_emotions),
            "intensity": plan.intensity,
            "style": plan.style,
            "duration": plan.duration,
            "phases": json.dumps(plan.phases) if plan.phases else None,
            "created_at": datetime.now().isoformat()
        }
        
        plan_id = await therapy_plan_crud.create(plan_data)
        logger.info(f"Admin '{admin['username']}' created therapy plan: {plan.name}")
        
        return {"message": "Plan created successfully", "id": plan_id}
        
    except Exception as e:
        logger.error(f"Error creating therapy plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create plan: {str(e)}"
        )


@router.put("/config/plans/{plan_id}")
async def update_therapy_plan(
    plan_id: str,
    plan: TherapyPlanConfig,
    admin: Dict[str, str] = Depends(require_role([AdminRole.SUPER_ADMIN, AdminRole.ADMIN]))
):
    """更新疗愈方案
    
    Requirements: 15.3 - 支持配置疗愈方案
    Requires: admin or super_admin role
    """
    try:
        import json
        plan_data = {
            "name": plan.name,
            "description": plan.description,
            "target_emotions": json.dumps(plan.target_emotions),
            "intensity": plan.intensity,
            "style": plan.style,
            "duration": plan.duration,
            "phases": json.dumps(plan.phases) if plan.phases else None,
            "updated_at": datetime.now().isoformat()
        }
        
        success = await therapy_plan_crud.update(plan_id, plan_data)
        
        if success:
            logger.info(f"Admin '{admin['username']}' updated therapy plan: {plan_id}")
            return {"message": "Plan updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating therapy plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update plan: {str(e)}"
        )


@router.delete("/config/plans/{plan_id}")
async def delete_therapy_plan(
    plan_id: str,
    admin: Dict[str, str] = Depends(require_role([AdminRole.SUPER_ADMIN]))
):
    """删除疗愈方案
    
    Requirements: 15.3 - 支持配置疗愈方案
    Requires: super_admin role only
    """
    try:
        success = await therapy_plan_crud.delete(plan_id)
        
        if success:
            logger.info(f"Admin '{admin['username']}' deleted therapy plan: {plan_id}")
            return {"message": "Plan deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting therapy plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete plan: {str(e)}"
        )


@router.get("/config/devices")
async def get_device_config(admin: Dict[str, str] = Depends(get_current_admin)):
    """获取设备参数配置
    
    Requirements: 15.3 - 支持调整设备参数
    """
    # Return default device configurations
    return {
        "devices": {
            "light": {
                "default_brightness": 60,
                "default_transition_ms": 3000,
                "breath_mode_period_ms": 4000
            },
            "audio": {
                "default_volume": 0.7,
                "fade_in_ms": 2000,
                "fade_out_ms": 2000,
                "sample_rate": 44100
            },
            "chair": {
                "default_mode": "gentle",
                "default_intensity": 5
            },
            "scent": {
                "default_intensity": 5,
                "default_scent": "lavender"
            }
        }
    }


@router.put("/config/devices")
async def update_device_config(
    config: DeviceConfigUpdate,
    admin: Dict[str, str] = Depends(require_role([AdminRole.SUPER_ADMIN, AdminRole.ADMIN]))
):
    """更新设备参数配置
    
    Requirements: 15.3 - 支持调整设备参数
    Requires: admin or super_admin role
    """
    logger.info(f"Admin '{admin['username']}' updated device config for {config.device_type}")
    # In a real implementation, this would persist the configuration
    return {"message": f"Device config for {config.device_type} updated successfully"}


@router.get("/config/content")
async def get_content_library(
    admin: Dict[str, str] = Depends(get_current_admin),
    content_type: Optional[str] = Query(None, description="Filter by content type (audio, visual, plan)")
):
    """获取内容库列表
    
    Requirements: 15.3 - 支持管理内容库
    """
    import os
    from pathlib import Path
    
    content_items = []
    content_base = Path("content")
    
    # Scan audio content
    if content_type is None or content_type == "audio":
        audio_dir = content_base / "audio"
        if audio_dir.exists():
            for f in audio_dir.iterdir():
                if f.is_file() and f.suffix in [".mp3", ".wav", ".ogg", ".flac"]:
                    content_items.append(ContentItem(
                        id=f.stem,
                        type="audio",
                        name=f.name,
                        path=str(f),
                        metadata={"size": f.stat().st_size}
                    ))
    
    # Scan visual content
    if content_type is None or content_type == "visual":
        visual_dir = content_base / "visual"
        if visual_dir.exists():
            for f in visual_dir.iterdir():
                if f.is_file() and f.suffix in [".mp4", ".webm", ".jpg", ".png"]:
                    content_items.append(ContentItem(
                        id=f.stem,
                        type="visual",
                        name=f.name,
                        path=str(f),
                        metadata={"size": f.stat().st_size}
                    ))
    
    # Scan plan content
    if content_type is None or content_type == "plan":
        plans_dir = content_base / "plans"
        if plans_dir.exists():
            for f in plans_dir.iterdir():
                if f.is_file() and f.suffix in [".yaml", ".yml"]:
                    content_items.append(ContentItem(
                        id=f.stem,
                        type="plan",
                        name=f.name,
                        path=str(f),
                        metadata={"size": f.stat().st_size}
                    ))
    
    return {
        "content": [item.model_dump() for item in content_items],
        "total": len(content_items)
    }


# ============== Session Management Endpoints ==============

@router.get("/sessions")
async def get_sessions(
    admin: Dict[str, str] = Depends(get_current_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取会话列表"""
    try:
        offset = (page - 1) * page_size
        sessions = await session_crud.get_all(limit=page_size, offset=offset)
        total = await session_crud.count()
        
        return {
            "sessions": sessions,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        return {"sessions": [], "total": 0, "page": page, "page_size": page_size}


@router.get("/sessions/{session_id}")
async def get_session_detail(
    session_id: str,
    admin: Dict[str, str] = Depends(get_current_admin)
):
    """获取会话详情"""
    try:
        session = await session_crud.get_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Get adjustment records for this session
        adjustments = await adjustment_record_crud.get_by_session(session_id)
        
        return {
            "session": session,
            "adjustments": adjustments
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session: {str(e)}"
        )


# ============== System Status Endpoint ==============

@router.get("/")
async def get_admin_status():
    """获取管理后台状态（无需认证）"""
    return {
        "status": "ready",
        "module": "admin",
        "version": "1.0.0",
        "auth_required": True
    }
