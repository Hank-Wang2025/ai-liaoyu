"""
系统启动模块测试
System Startup Module Tests

测试 AI 模型预加载、设备扫描和容错启动功能
"""
import asyncio
import pytest
from datetime import datetime

from services.system_startup import (
    LoadingStatus,
    ComponentType,
    LoadingProgress,
    SystemStartupResult,
    AIModelLoader,
    DeviceLoader,
    ProgressMonitor,
    ModelPreloader,
    DeviceScanner,
    DegradedModeManager,
    SystemStartupManager,
    init_startup_manager,
    get_startup_manager,
    cleanup_startup_manager
)


# ============== Test Fixtures ==============

@pytest.fixture
def progress_monitor():
    """创建进度监控器"""
    return ProgressMonitor()


@pytest.fixture
def model_preloader():
    """创建模型预加载器"""
    return ModelPreloader(timeout_seconds=5.0)


@pytest.fixture
def device_scanner():
    """创建设备扫描器"""
    return DeviceScanner()


@pytest.fixture
def degraded_manager():
    """创建降级模式管理器"""
    return DegradedModeManager()


@pytest.fixture
def startup_manager():
    """创建系统启动管理器"""
    return SystemStartupManager(model_timeout=5.0, device_timeout=3.0)


# ============== LoadingProgress Tests ==============

class TestLoadingProgress:
    """LoadingProgress 测试"""
    
    def test_initial_state(self):
        """测试初始状态"""
        progress = LoadingProgress(
            component_name="test_model",
            component_type=ComponentType.AI_MODEL
        )
        
        assert progress.component_name == "test_model"
        assert progress.component_type == ComponentType.AI_MODEL
        assert progress.status == LoadingStatus.PENDING
        assert progress.progress == 0.0
        assert progress.is_complete is False
    
    def test_duration_calculation(self):
        """测试耗时计算"""
        progress = LoadingProgress(
            component_name="test",
            component_type=ComponentType.AI_MODEL,
            start_time=datetime(2024, 1, 1, 0, 0, 0),
            end_time=datetime(2024, 1, 1, 0, 0, 1)
        )
        
        assert progress.duration_ms == 1000.0
    
    def test_is_complete_states(self):
        """测试完成状态判断"""
        # LOADED 状态
        progress = LoadingProgress(
            component_name="test",
            component_type=ComponentType.AI_MODEL,
            status=LoadingStatus.LOADED
        )
        assert progress.is_complete is True
        
        # FAILED 状态
        progress.status = LoadingStatus.FAILED
        assert progress.is_complete is True
        
        # LOADING 状态
        progress.status = LoadingStatus.LOADING
        assert progress.is_complete is False


# ============== AIModelLoader Tests ==============

class TestAIModelLoader:
    """AIModelLoader 测试"""
    
    @pytest.mark.asyncio
    async def test_successful_load(self):
        """测试成功加载"""
        async def mock_load():
            await asyncio.sleep(0.1)
            return True
        
        loader = AIModelLoader(
            name="test_model",
            load_func=mock_load,
            timeout_seconds=5.0
        )
        
        result = await loader.load()
        
        assert result is True
        assert loader.progress.status == LoadingStatus.LOADED
        assert loader.progress.progress == 1.0
        assert loader.progress.duration_ms is not None
    
    @pytest.mark.asyncio
    async def test_failed_load(self):
        """测试加载失败"""
        async def mock_load():
            return False
        
        loader = AIModelLoader(
            name="test_model",
            load_func=mock_load,
            timeout_seconds=5.0
        )
        
        result = await loader.load()
        
        assert result is False
        assert loader.progress.status == LoadingStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_load_timeout(self):
        """测试加载超时"""
        async def slow_load():
            await asyncio.sleep(10)
            return True
        
        loader = AIModelLoader(
            name="test_model",
            load_func=slow_load,
            timeout_seconds=0.1
        )
        
        result = await loader.load()
        
        assert result is False
        assert loader.progress.status == LoadingStatus.FAILED
        assert "超时" in loader.progress.error
    
    @pytest.mark.asyncio
    async def test_load_exception(self):
        """测试加载异常"""
        async def error_load():
            raise RuntimeError("Test error")
        
        loader = AIModelLoader(
            name="test_model",
            load_func=error_load,
            timeout_seconds=5.0
        )
        
        result = await loader.load()
        
        assert result is False
        assert loader.progress.status == LoadingStatus.FAILED
        assert "Test error" in loader.progress.error


# ============== DeviceLoader Tests ==============

class TestDeviceLoader:
    """DeviceLoader 测试"""
    
    @pytest.mark.asyncio
    async def test_successful_connect(self):
        """测试成功连接"""
        async def mock_connect():
            await asyncio.sleep(0.05)
            return True
        
        loader = DeviceLoader(
            name="test_device",
            connect_func=mock_connect,
            timeout_seconds=5.0
        )
        
        result = await loader.load()
        
        assert result is True
        assert loader.progress.status == LoadingStatus.LOADED
    
    @pytest.mark.asyncio
    async def test_connection_timeout(self):
        """测试连接超时"""
        async def slow_connect():
            await asyncio.sleep(10)
            return True
        
        loader = DeviceLoader(
            name="test_device",
            connect_func=slow_connect,
            timeout_seconds=0.1
        )
        
        result = await loader.load()
        
        assert result is False
        assert loader.progress.status == LoadingStatus.FAILED


# ============== ModelPreloader Tests ==============

class TestModelPreloader:
    """ModelPreloader 测试"""
    
    @pytest.mark.asyncio
    async def test_parallel_loading(self, model_preloader):
        """测试并行加载"""
        load_times = []
        
        async def mock_load_1():
            load_times.append(("model1_start", asyncio.get_event_loop().time()))
            await asyncio.sleep(0.2)
            load_times.append(("model1_end", asyncio.get_event_loop().time()))
            return True
        
        async def mock_load_2():
            load_times.append(("model2_start", asyncio.get_event_loop().time()))
            await asyncio.sleep(0.2)
            load_times.append(("model2_end", asyncio.get_event_loop().time()))
            return True
        
        model_preloader.add_model("model1", mock_load_1)
        model_preloader.add_model("model2", mock_load_2)
        
        progress = await model_preloader.load_all()
        
        # 验证两个模型都加载成功
        assert progress["model1"].status == LoadingStatus.LOADED
        assert progress["model2"].status == LoadingStatus.LOADED
        
        # 验证是并行加载（总时间应该接近单个模型时间，而不是两倍）
        summary = model_preloader.get_loading_summary()
        assert summary["elapsed_ms"] < 500  # 应该小于 500ms
    
    @pytest.mark.asyncio
    async def test_loading_summary(self, model_preloader):
        """测试加载摘要"""
        async def success_load():
            return True
        
        async def fail_load():
            return False
        
        model_preloader.add_model("success_model", success_load)
        model_preloader.add_model("fail_model", fail_load)
        
        await model_preloader.load_all()
        
        summary = model_preloader.get_loading_summary()
        
        assert summary["total"] == 2
        assert summary["loaded"] == 1
        assert summary["failed"] == 1
        assert "success_model" in summary["loaded_models"]
        assert "fail_model" in summary["failed_models"]


# ============== DeviceScanner Tests ==============

class TestDeviceScanner:
    """DeviceScanner 测试"""
    
    @pytest.mark.asyncio
    async def test_scan_and_connect(self, device_scanner):
        """测试扫描和连接"""
        async def mock_connect():
            return True
        
        device_scanner.add_device("light", mock_connect)
        device_scanner.add_device("audio", mock_connect)
        
        progress = await device_scanner.scan_and_connect()
        
        assert len(progress) == 2
        assert progress["light"].status == LoadingStatus.LOADED
        assert progress["audio"].status == LoadingStatus.LOADED
    
    @pytest.mark.asyncio
    async def test_partial_connection_failure(self, device_scanner):
        """测试部分连接失败"""
        async def success_connect():
            return True
        
        async def fail_connect():
            return False
        
        device_scanner.add_device("light", success_connect)
        device_scanner.add_device("chair", fail_connect)
        
        progress = await device_scanner.scan_and_connect()
        
        summary = device_scanner.get_connection_summary()
        
        assert summary["connected"] == 1
        assert summary["failed"] == 1


# ============== DegradedModeManager Tests ==============

class TestDegradedModeManager:
    """DegradedModeManager 测试"""
    
    def test_no_failures(self, degraded_manager):
        """测试无失败情况"""
        progress = {
            "light_controller": LoadingProgress(
                component_name="light_controller",
                component_type=ComponentType.DEVICE,
                status=LoadingStatus.LOADED
            )
        }
        
        degraded_manager.process_device_failures(progress)
        
        assert degraded_manager.is_degraded is False
        assert len(degraded_manager.failed_devices) == 0
    
    def test_device_failure_degradation(self, degraded_manager):
        """测试设备失败导致降级"""
        progress = {
            "light_controller": LoadingProgress(
                component_name="light_controller",
                component_type=ComponentType.DEVICE,
                status=LoadingStatus.FAILED
            )
        }
        
        degraded_manager.process_device_failures(progress)
        
        assert degraded_manager.is_degraded is True
        assert "light_controller" in degraded_manager.failed_devices
        assert "ambient_lighting" in degraded_manager.disabled_features
    
    def test_feature_availability(self, degraded_manager):
        """测试功能可用性检查"""
        progress = {
            "audio_controller": LoadingProgress(
                component_name="audio_controller",
                component_type=ComponentType.DEVICE,
                status=LoadingStatus.FAILED
            )
        }
        
        degraded_manager.process_device_failures(progress)
        
        assert degraded_manager.is_feature_available("background_music") is False
        assert degraded_manager.is_feature_available("ambient_lighting") is True


# ============== SystemStartupManager Tests ==============

class TestSystemStartupManager:
    """SystemStartupManager 测试"""
    
    @pytest.mark.asyncio
    async def test_successful_startup(self, startup_manager):
        """测试成功启动"""
        async def mock_model_load():
            await asyncio.sleep(0.05)
            return True
        
        async def mock_device_connect():
            return True
        
        startup_manager.add_model("test_model", mock_model_load)
        startup_manager.add_device("test_device", mock_device_connect)
        
        result = await startup_manager.startup()
        
        assert result.success is True
        assert result.degraded_mode is False
        assert result.loaded_count == 2
        assert result.failed_count == 0
    
    @pytest.mark.asyncio
    async def test_required_model_failure(self, startup_manager):
        """测试必需模型加载失败"""
        async def fail_load():
            return False
        
        startup_manager.add_model("required_model", fail_load, required=True)
        
        result = await startup_manager.startup()
        
        assert result.success is False
        assert "required_model" in result.failed_components
    
    @pytest.mark.asyncio
    async def test_optional_device_failure_degraded_mode(self, startup_manager):
        """测试可选设备失败进入降级模式"""
        async def mock_model_load():
            return True
        
        async def fail_connect():
            return False
        
        startup_manager.add_model("model", mock_model_load)
        startup_manager.add_device("light_controller", fail_connect, required=False)
        
        result = await startup_manager.startup()
        
        assert result.success is True
        assert result.degraded_mode is True
        assert len(result.degraded_features) > 0
    
    @pytest.mark.asyncio
    async def test_startup_time_constraint(self, startup_manager):
        """测试启动时间约束"""
        async def quick_load():
            await asyncio.sleep(0.05)
            return True
        
        startup_manager.add_model("model1", quick_load)
        startup_manager.add_model("model2", quick_load)
        
        result = await startup_manager.startup()
        
        # 验证启动时间在合理范围内
        assert result.total_time_ms < 1000  # 应该小于 1 秒


# ============== Global Instance Tests ==============

class TestGlobalInstance:
    """全局实例测试"""
    
    @pytest.mark.asyncio
    async def test_init_and_get_startup_manager(self):
        """测试初始化和获取启动管理器"""
        await cleanup_startup_manager()
        
        manager = init_startup_manager(model_timeout=10.0)
        assert manager is not None
        
        same_manager = get_startup_manager()
        assert same_manager is manager
        
        await cleanup_startup_manager()
