"""
启动编排器模块测试
Startup Orchestrator Module Tests

测试容错启动、降级模式和错误日志记录功能
"""
import asyncio
import pytest
from datetime import datetime

from services.startup_orchestrator import (
    StartupPhase,
    StartupError,
    StartupState,
    FaultTolerantStartup,
    init_fault_tolerant_startup,
    get_fault_tolerant_startup,
    cleanup_fault_tolerant_startup
)
from services.system_startup import LoadingStatus


# ============== Test Fixtures ==============

@pytest.fixture
def fault_tolerant_startup():
    """创建容错启动管理器"""
    return FaultTolerantStartup(
        model_timeout=5.0,
        device_timeout=3.0,
        max_retries=1
    )


# ============== StartupError Tests ==============

class TestStartupError:
    """StartupError 测试"""
    
    def test_error_creation(self):
        """测试错误创建"""
        error = StartupError(
            component="test_model",
            error_type="LoadError",
            message="Failed to load model",
            recoverable=True
        )
        
        assert error.component == "test_model"
        assert error.error_type == "LoadError"
        assert error.recoverable is True
    
    def test_error_to_dict(self):
        """测试错误转换为字典"""
        error = StartupError(
            component="test_device",
            error_type="ConnectionError",
            message="Device not found",
            recoverable=False
        )
        
        data = error.to_dict()
        
        assert data["component"] == "test_device"
        assert data["error_type"] == "ConnectionError"
        assert data["recoverable"] is False
        assert "timestamp" in data


# ============== StartupState Tests ==============

class TestStartupState:
    """StartupState 测试"""
    
    def test_initial_state(self):
        """测试初始状态"""
        state = StartupState()
        
        assert state.phase == StartupPhase.INITIALIZING
        assert state.progress == 0.0
        assert state.has_errors is False
        assert state.has_critical_errors is False
    
    def test_elapsed_time(self):
        """测试已用时间计算"""
        state = StartupState(
            start_time=datetime(2024, 1, 1, 0, 0, 0),
            end_time=datetime(2024, 1, 1, 0, 0, 2)
        )
        
        assert state.elapsed_ms == 2000.0
    
    def test_has_errors(self):
        """测试错误检测"""
        state = StartupState()
        
        assert state.has_errors is False
        
        state.errors.append(StartupError(
            component="test",
            error_type="Error",
            message="Test error",
            recoverable=True
        ))
        
        assert state.has_errors is True
        assert state.has_critical_errors is False
    
    def test_has_critical_errors(self):
        """测试严重错误检测"""
        state = StartupState()
        
        state.errors.append(StartupError(
            component="test",
            error_type="CriticalError",
            message="Critical error",
            recoverable=False
        ))
        
        assert state.has_critical_errors is True


# ============== FaultTolerantStartup Tests ==============

class TestFaultTolerantStartup:
    """FaultTolerantStartup 测试"""
    
    @pytest.mark.asyncio
    async def test_successful_startup(self, fault_tolerant_startup):
        """测试成功启动"""
        async def mock_model_load():
            await asyncio.sleep(0.05)
            return True
        
        async def mock_device_connect():
            return True
        
        fault_tolerant_startup.add_model("test_model", mock_model_load)
        fault_tolerant_startup.add_device("test_device", mock_device_connect)
        
        result = await fault_tolerant_startup.startup()
        
        assert result.success is True
        assert fault_tolerant_startup.state.phase == StartupPhase.READY
    
    @pytest.mark.asyncio
    async def test_model_failure_with_retry(self, fault_tolerant_startup):
        """测试模型加载失败重试"""
        attempt_count = 0
        
        async def flaky_model_load():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                return False
            return True
        
        fault_tolerant_startup.add_model("flaky_model", flaky_model_load, required=True)
        
        result = await fault_tolerant_startup.startup()
        
        # 应该在重试后成功
        assert result.success is True
        assert attempt_count >= 2
    
    @pytest.mark.asyncio
    async def test_required_model_failure(self, fault_tolerant_startup):
        """测试必需模型加载失败"""
        async def fail_load():
            return False
        
        fault_tolerant_startup.add_model("required_model", fail_load, required=True)
        
        result = await fault_tolerant_startup.startup()
        
        assert result.success is False
        assert fault_tolerant_startup.state.phase == StartupPhase.FAILED
        assert fault_tolerant_startup.state.has_critical_errors is True
    
    @pytest.mark.asyncio
    async def test_optional_device_failure_degraded_mode(self, fault_tolerant_startup):
        """测试可选设备失败进入降级模式"""
        async def mock_model_load():
            return True
        
        async def fail_connect():
            return False
        
        fault_tolerant_startup.add_model("model", mock_model_load)
        fault_tolerant_startup.add_device("light_controller", fail_connect, required=False)
        
        result = await fault_tolerant_startup.startup()
        
        assert result.success is True
        assert result.degraded_mode is True
        assert fault_tolerant_startup.is_degraded is True
    
    @pytest.mark.asyncio
    async def test_progress_callback(self, fault_tolerant_startup):
        """测试进度回调"""
        progress_updates = []
        
        def callback(state):
            progress_updates.append({
                "phase": state.phase,
                "progress": state.progress
            })
        
        fault_tolerant_startup.register_progress_callback(callback)
        
        async def mock_load():
            return True
        
        fault_tolerant_startup.add_model("model", mock_load)
        
        await fault_tolerant_startup.startup()
        
        # 应该有多个进度更新
        assert len(progress_updates) > 0
        
        # 最后一个更新应该是 READY 状态
        assert progress_updates[-1]["phase"] == StartupPhase.READY
    
    @pytest.mark.asyncio
    async def test_error_logging(self, fault_tolerant_startup):
        """测试错误日志记录"""
        async def fail_load():
            return False
        
        fault_tolerant_startup.add_model("fail_model", fail_load, required=False)
        
        await fault_tolerant_startup.startup()
        
        # 应该记录了错误
        assert fault_tolerant_startup.state.has_errors is True
        
        errors = fault_tolerant_startup.state.errors
        assert any(e.component == "fail_model" for e in errors)
    
    @pytest.mark.asyncio
    async def test_feature_availability(self, fault_tolerant_startup):
        """测试功能可用性检查"""
        async def mock_model_load():
            return True
        
        async def fail_connect():
            return False
        
        fault_tolerant_startup.add_model("model", mock_model_load)
        fault_tolerant_startup.add_device("audio_controller", fail_connect, required=False)
        
        await fault_tolerant_startup.startup()
        
        # 音频相关功能应该不可用
        assert fault_tolerant_startup.is_feature_available("background_music") is False
        
        # 其他功能应该可用
        assert fault_tolerant_startup.is_feature_available("ambient_lighting") is True
    
    @pytest.mark.asyncio
    async def test_get_status(self, fault_tolerant_startup):
        """测试获取状态"""
        async def mock_load():
            return True
        
        fault_tolerant_startup.add_model("model", mock_load)
        
        await fault_tolerant_startup.startup()
        
        status = fault_tolerant_startup.get_status()
        
        assert "phase" in status
        assert "progress" in status
        assert "message" in status
        assert "is_ready" in status
        assert status["is_ready"] is True
    
    @pytest.mark.asyncio
    async def test_shutdown(self, fault_tolerant_startup):
        """测试关闭系统"""
        async def mock_load():
            return True
        
        fault_tolerant_startup.add_model("model", mock_load)
        
        await fault_tolerant_startup.startup()
        await fault_tolerant_startup.shutdown()
        
        # 关闭后不应该抛出异常


# ============== Global Instance Tests ==============

class TestGlobalInstance:
    """全局实例测试"""
    
    @pytest.mark.asyncio
    async def test_init_and_get_fault_tolerant_startup(self):
        """测试初始化和获取容错启动管理器"""
        await cleanup_fault_tolerant_startup()
        
        manager = init_fault_tolerant_startup(model_timeout=10.0)
        assert manager is not None
        
        same_manager = get_fault_tolerant_startup()
        assert same_manager is manager
        
        await cleanup_fault_tolerant_startup()
