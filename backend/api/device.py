"""设备控制 API 路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from loguru import logger

from services.device_manager import get_device_manager

router = APIRouter()


class LightControlRequest(BaseModel):
    """灯光控制请求"""
    color: str = Field(..., description="HEX 颜色值，如 #FF6B6B")
    brightness: int = Field(default=80, ge=0, le=100, description="亮度 0-100")
    transition_ms: int = Field(default=3000, ge=0, description="过渡时间（毫秒）")
    mode: Optional[str] = Field(default=None, description="模式: breath/static")


class AudioControlRequest(BaseModel):
    """音频控制请求"""
    action: str = Field(..., description="操作: play/stop/pause/resume/volume")
    file: Optional[str] = Field(default=None, description="音频文件路径")
    volume: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="音量 0-1")
    loop: bool = Field(default=True, description="是否循环播放")
    fade_ms: int = Field(default=1000, ge=0, description="淡入淡出时间（毫秒）")


class ChairControlRequest(BaseModel):
    """座椅控制请求"""
    action: str = Field(..., description="操作: start/stop/set_mode")
    mode: Optional[str] = Field(default=None, description="按摩模式")
    intensity: Optional[int] = Field(default=None, ge=0, le=100, description="强度 0-100")


class ScentControlRequest(BaseModel):
    """香薰控制请求"""
    action: str = Field(..., description="操作: start/stop/set_intensity")
    scent_type: Optional[str] = Field(default=None, description="香薰类型")
    intensity: Optional[int] = Field(default=None, ge=0, le=100, description="强度 0-100")


@router.get("/")
async def get_device_status():
    """获取所有设备连接状态"""
    try:
        manager = get_device_manager()
        status = manager.get_connection_status()
        return {
            "status": "ready",
            "module": "device",
            **status
        }
    except Exception as e:
        logger.error(f"获取设备状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取设备状态失败: {e}")


@router.post("/scan")
async def scan_devices(timeout: float = 5.0):
    """扫描可用硬件设备"""
    try:
        manager = get_device_manager()
        results = await manager.scan_all_devices(timeout)
        total = sum(len(devices) for devices in results.values())
        return {
            "devices": {
                device_type: [d.to_dict() for d in devices]
                for device_type, devices in results.items()
            },
            "total": total,
            "message": f"扫描完成，发现 {total} 个设备"
        }
    except Exception as e:
        logger.error(f"设备扫描失败: {e}")
        raise HTTPException(status_code=500, detail=f"设备扫描失败: {e}")


@router.post("/light")
async def control_light(request: LightControlRequest):
    """控制灯光设备"""
    try:
        manager = get_device_manager()
        # 获取灯光控制器（如果已注册）
        controllers = manager._device_controllers

        # 尝试查找灯光控制器
        light_controller = None
        for device_id, controller in controllers.items():
            if hasattr(controller, 'set_all_lights') or hasattr(controller, 'set_color'):
                light_controller = controller
                break

        if light_controller is None:
            # 没有实际设备时返回模拟结果
            logger.warning("没有已连接的灯光设备，返回模拟结果")
            return {
                "success": True,
                "simulated": True,
                "color": request.color,
                "brightness": request.brightness,
                "message": "灯光指令已发送（模拟模式）"
            }

        # 呼吸灯模式
        if request.mode == "breath" and hasattr(light_controller, 'start_breath_mode_all'):
            await light_controller.start_breath_mode_all(
                request.color,
                min_brightness=30,
                max_brightness=request.brightness
            )
        elif hasattr(light_controller, 'set_all_lights'):
            await light_controller.set_all_lights(
                request.color,
                request.brightness,
                request.transition_ms
            )
        else:
            await light_controller.set_color(
                request.color,
                request.brightness,
                request.transition_ms
            )

        return {
            "success": True,
            "simulated": False,
            "color": request.color,
            "brightness": request.brightness,
            "message": "灯光设置成功"
        }
    except Exception as e:
        logger.error(f"灯光控制失败: {e}")
        raise HTTPException(status_code=500, detail=f"灯光控制失败: {e}")


@router.post("/audio")
async def control_audio(request: AudioControlRequest):
    """控制音频设备"""
    try:
        manager = get_device_manager()
        controllers = manager._device_controllers

        audio_player = None
        for device_id, controller in controllers.items():
            if hasattr(controller, 'play_background_music') or hasattr(controller, 'stop_all'):
                audio_player = controller
                break

        if audio_player is None:
            logger.warning("没有已连接的音频设备，返回模拟结果")
            return {
                "success": True,
                "simulated": True,
                "action": request.action,
                "message": f"音频指令 [{request.action}] 已发送（模拟模式）"
            }

        if request.action == "play" and request.file:
            await audio_player.play_background_music(
                request.file,
                volume=request.volume or 0.7,
                loop=request.loop,
                fade_in_ms=request.fade_ms
            )
        elif request.action == "stop":
            await audio_player.stop_all(fade_out_ms=request.fade_ms)
        elif request.action == "pause" and hasattr(audio_player, 'pause'):
            await audio_player.pause()
        elif request.action == "resume" and hasattr(audio_player, 'resume'):
            await audio_player.resume()
        elif request.action == "volume" and request.volume is not None:
            if hasattr(audio_player, 'set_volume'):
                await audio_player.set_volume(request.volume)

        return {
            "success": True,
            "simulated": False,
            "action": request.action,
            "message": f"音频指令 [{request.action}] 执行成功"
        }
    except Exception as e:
        logger.error(f"音频控制失败: {e}")
        raise HTTPException(status_code=500, detail=f"音频控制失败: {e}")


@router.post("/chair")
async def control_chair(request: ChairControlRequest):
    """控制座椅设备"""
    try:
        manager = get_device_manager()
        controllers = manager._device_controllers

        chair_controller = None
        for device_id, controller in controllers.items():
            if hasattr(controller, 'apply_therapy_config') or hasattr(controller, 'start_massage'):
                chair_controller = controller
                break

        if chair_controller is None:
            logger.warning("没有已连接的座椅设备，返回模拟结果")
            return {
                "success": True,
                "simulated": True,
                "action": request.action,
                "message": f"座椅指令 [{request.action}] 已发送（模拟模式）"
            }

        if request.action == "stop" and hasattr(chair_controller, 'stop'):
            await chair_controller.stop()
        elif request.action == "start" and hasattr(chair_controller, 'start_massage'):
            await chair_controller.start_massage(
                mode=request.mode,
                intensity=request.intensity or 50
            )

        return {
            "success": True,
            "simulated": False,
            "action": request.action,
            "message": f"座椅指令 [{request.action}] 执行成功"
        }
    except Exception as e:
        logger.error(f"座椅控制失败: {e}")
        raise HTTPException(status_code=500, detail=f"座椅控制失败: {e}")


@router.post("/scent")
async def control_scent(request: ScentControlRequest):
    """控制香薰设备"""
    try:
        manager = get_device_manager()
        controllers = manager._device_controllers

        scent_controller = None
        for device_id, controller in controllers.items():
            if hasattr(controller, 'apply_therapy_config') and hasattr(controller, 'set_scent'):
                scent_controller = controller
                break

        if scent_controller is None:
            logger.warning("没有已连接的香薰设备，返回模拟结果")
            return {
                "success": True,
                "simulated": True,
                "action": request.action,
                "message": f"香薰指令 [{request.action}] 已发送（模拟模式）"
            }

        if request.action == "stop" and hasattr(scent_controller, 'stop'):
            await scent_controller.stop()
        elif request.action == "start" and hasattr(scent_controller, 'start'):
            await scent_controller.start(
                scent_type=request.scent_type,
                intensity=request.intensity or 50
            )

        return {
            "success": True,
            "simulated": False,
            "action": request.action,
            "message": f"香薰指令 [{request.action}] 执行成功"
        }
    except Exception as e:
        logger.error(f"香薰控制失败: {e}")
        raise HTTPException(status_code=500, detail=f"香薰控制失败: {e}")


@router.post("/visual")
async def control_visual():
    """控制视觉显示"""
    return {"message": "视觉控制端点 - 由前端直接处理"}
