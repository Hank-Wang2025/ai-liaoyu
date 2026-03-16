"""
设备连接容错属性测试
Device Connection Fault Tolerance Property Tests

Property 33: 设备连接容错
*For any* 硬件设备连接失败的情况，系统 SHALL 记录错误日志并继续启动，不影响其他功能。

Validates: Requirements 16.3
"""
import asyncio
import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import List, Tuple, Dict, Any

from services.system_startup import (
    LoadingStatus,
    ComponentType,
    LoadingProgress,
    SystemStartupResult,
    DeviceLoader,
    DeviceScanner,
    DegradedModeManager,
    SystemStartupManager
)
from services.startup_orchestrator import (
    StartupPhase,
    StartupError,
    StartupState,
    FaultTolerantStartup
)


# ============== 测试策略 ==============

# 设备名称策略
device_name_strategy = st.text(
    min_size=1, 
    max_size=20, 
    alphabet="abcdefghijklmnopqrstuvwxyz_"
)

# 设备连接结果策略（True 表示成功，False 表示失败）
device_success_strategy = st.booleans()

# 设备配置策略：(名称, 是否成功, 是否必需)
device_config_strategy = st.tuples(
    device_name_strategy,
    device_success_strategy,
    st.booleans()  # 是否必需
)

# 设备列表策略（1 到 5 个设备）
device_list_strategy = st.lists(
    device_config_strategy,
    min_size=1,
    max_size=5,
    unique_by=lambda x: x[0]  # 确保设备名称唯一
)


# ============== 辅助函数 ==============

def create_mock_device_connector(success: bool, delay: float = 0.001):
    """创建模拟设备连接函数
    
    Args:
        success: 是否连接成功
        delay: 连接延迟（秒）
        
    Returns:
        异步连接函数
    """
    async def mock_connect():
        await asyncio.sleep(delay)
        return success
    return mock_connect


def create_mock_model_loader(success: bool = True, delay: float = 0.001):
    """创建模拟模型加载函数
    
    Args:
        success: 是否加载成功
        delay: 加载延迟（秒）
        
    Returns:
        异步加载函数
    """
    async def mock_load():
        await asyncio.sleep(delay)
        return success
    return mock_load


# ============== Property 33: 设备连接容错 ==============

class TestDeviceConnectionFaultToleranceProperties:
    """
    设备连接容错属性测试
    
    **Feature: healing-pod-system, Property 33: 设备连接容错**
    **Validates: Requirements 16.3**
    """
    
    @given(
        device_configs=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=15, alphabet="abcdefghijklmnopqrstuvwxyz"),
                st.booleans()  # 是否连接成功
            ),
            min_size=1,
            max_size=5,
            unique_by=lambda x: x[0]
        )
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_system_continues_startup_on_optional_device_failure(
        self,
        device_configs: List[Tuple[str, bool]]
    ):
        """
        属性测试：可选设备连接失败时系统继续启动
        
        **Feature: healing-pod-system, Property 33: 设备连接容错**
        **Validates: Requirements 16.3**
        
        对于任意数量的可选设备，无论连接成功或失败，
        系统都应该能够继续启动并进入就绪状态。
        """
        startup_manager = SystemStartupManager(
            model_timeout=5.0,
            device_timeout=3.0
        )
        
        # 添加一个必需的模型（确保模型加载成功）
        startup_manager.add_model(
            "required_model",
            create_mock_model_loader(success=True),
            required=True
        )
        
        # 添加所有设备（全部设为可选）
        for name, success in device_configs:
            startup_manager.add_device(
                name,
                create_mock_device_connector(success),
                required=False  # 可选设备
            )
        
        # 执行启动
        result = await startup_manager.startup()
        
        # 验证系统启动成功（即使有设备连接失败）
        assert result.success is True, \
            f"系统应该在可选设备失败时继续启动，但启动失败: {result.failed_components}"
        
        # 验证失败的设备数量正确
        failed_devices = [name for name, success in device_configs if not success]
        
        # 如果有设备失败，应该进入降级模式
        if failed_devices:
            assert result.degraded_mode is True, \
                "有设备连接失败时应该进入降级模式"
    
    @given(
        failing_device_count=st.integers(min_value=1, max_value=4),
        successful_device_count=st.integers(min_value=0, max_value=3)
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_error_logging_on_device_failure(
        self,
        failing_device_count: int,
        successful_device_count: int
    ):
        """
        属性测试：设备连接失败时记录错误日志
        
        **Feature: healing-pod-system, Property 33: 设备连接容错**
        **Validates: Requirements 16.3**
        
        对于任意数量的失败设备，系统应该记录每个失败设备的错误信息。
        """
        fault_tolerant_startup = FaultTolerantStartup(
            model_timeout=5.0,
            device_timeout=3.0,
            max_retries=0  # 禁用重试以便测试
        )
        
        # 添加必需的模型
        fault_tolerant_startup.add_model(
            "required_model",
            create_mock_model_loader(success=True),
            required=True
        )
        
        # 添加失败的设备
        failing_device_names = []
        for i in range(failing_device_count):
            name = f"failing_device_{i}"
            failing_device_names.append(name)
            fault_tolerant_startup.add_device(
                name,
                create_mock_device_connector(success=False),
                required=False
            )
        
        # 添加成功的设备
        for i in range(successful_device_count):
            fault_tolerant_startup.add_device(
                f"successful_device_{i}",
                create_mock_device_connector(success=True),
                required=False
            )
        
        # 执行启动
        result = await fault_tolerant_startup.startup()
        
        # 验证系统启动成功
        assert result.success is True, \
            "系统应该在可选设备失败时继续启动"
        
        # 验证错误被记录
        state = fault_tolerant_startup.state
        assert state.has_errors is True, \
            "设备连接失败时应该记录错误"
        
        # 验证每个失败设备都有对应的错误记录
        error_components = [e.component for e in state.errors]
        for device_name in failing_device_names:
            assert device_name in error_components, \
                f"设备 {device_name} 的错误应该被记录"
    
    @given(
        device_count=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_other_devices_not_affected_by_failure(
        self,
        device_count: int
    ):
        """
        属性测试：设备失败不影响其他设备
        
        **Feature: healing-pod-system, Property 33: 设备连接容错**
        **Validates: Requirements 16.3**
        
        对于任意数量的设备，一个设备的连接失败不应该影响其他设备的连接。
        """
        device_scanner = DeviceScanner()
        
        # 添加一个失败的设备
        device_scanner.add_device(
            "failing_device",
            create_mock_device_connector(success=False),
            required=False
        )
        
        # 添加多个成功的设备
        successful_device_names = []
        for i in range(device_count):
            name = f"successful_device_{i}"
            successful_device_names.append(name)
            device_scanner.add_device(
                name,
                create_mock_device_connector(success=True),
                required=False
            )
        
        # 执行扫描和连接
        progress = await device_scanner.scan_and_connect()
        
        # 验证失败的设备被标记为失败
        assert progress["failing_device"].status == LoadingStatus.FAILED, \
            "失败的设备应该被标记为 FAILED"
        
        # 验证所有成功的设备都连接成功
        for name in successful_device_names:
            assert progress[name].status == LoadingStatus.LOADED, \
                f"设备 {name} 应该连接成功，但状态为 {progress[name].status}"
    
    @given(
        device_configs=st.lists(
            st.tuples(
                st.sampled_from([
                    "light_controller",
                    "audio_controller", 
                    "chair_controller",
                    "camera",
                    "microphone"
                ]),
                st.booleans()  # 是否连接成功
            ),
            min_size=1,
            max_size=5,
            unique_by=lambda x: x[0]
        )
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_degraded_mode_features_correctly_disabled(
        self,
        device_configs: List[Tuple[str, bool]]
    ):
        """
        属性测试：降级模式正确禁用相关功能
        
        **Feature: healing-pod-system, Property 33: 设备连接容错**
        **Validates: Requirements 16.3**
        
        对于任意设备连接失败的情况，系统应该正确识别并禁用相关功能。
        """
        degraded_manager = DegradedModeManager()
        
        # 创建设备进度字典
        device_progress: Dict[str, LoadingProgress] = {}
        for name, success in device_configs:
            device_progress[name] = LoadingProgress(
                component_name=name,
                component_type=ComponentType.DEVICE,
                status=LoadingStatus.LOADED if success else LoadingStatus.FAILED
            )
        
        # 处理设备失败
        degraded_manager.process_device_failures(device_progress)
        
        # 获取失败的设备
        failed_devices = [name for name, success in device_configs if not success]
        
        # 验证失败设备被正确记录
        for device_name in failed_devices:
            assert device_name in degraded_manager.failed_devices, \
                f"设备 {device_name} 应该在失败设备列表中"
        
        # 验证降级模式状态
        if failed_devices:
            assert degraded_manager.is_degraded is True, \
                "有设备失败时应该进入降级模式"
        else:
            assert degraded_manager.is_degraded is False, \
                "所有设备成功时不应该进入降级模式"
    
    @given(
        exception_message=st.text(min_size=1, max_size=50)
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_device_exception_handled_gracefully(
        self,
        exception_message: str
    ):
        """
        属性测试：设备连接异常被优雅处理
        
        **Feature: healing-pod-system, Property 33: 设备连接容错**
        **Validates: Requirements 16.3**
        
        对于任意设备连接异常，系统应该捕获异常并继续运行。
        """
        # 过滤掉可能导致问题的字符
        assume(len(exception_message.strip()) > 0)
        
        async def failing_connect():
            raise RuntimeError(exception_message)
        
        device_loader = DeviceLoader(
            name="exception_device",
            connect_func=failing_connect,
            required=False,
            timeout_seconds=5.0
        )
        
        # 执行连接（不应该抛出异常）
        result = await device_loader.load()
        
        # 验证连接失败但没有抛出异常
        assert result is False, \
            "异常设备应该返回连接失败"
        assert device_loader.progress.status == LoadingStatus.FAILED, \
            "异常设备应该被标记为 FAILED"
        assert device_loader.progress.error is not None, \
            "异常信息应该被记录"
    
    @given(
        timeout_seconds=st.floats(min_value=0.05, max_value=0.5)
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_device_timeout_handled_as_failure(
        self,
        timeout_seconds: float
    ):
        """
        属性测试：设备连接超时被处理为失败
        
        **Feature: healing-pod-system, Property 33: 设备连接容错**
        **Validates: Requirements 16.3**
        
        对于任意超时设置，如果设备连接超时，应该被处理为连接失败。
        """
        async def slow_connect():
            await asyncio.sleep(timeout_seconds + 1.0)  # 超过超时时间
            return True
        
        device_loader = DeviceLoader(
            name="slow_device",
            connect_func=slow_connect,
            required=False,
            timeout_seconds=timeout_seconds
        )
        
        # 执行连接
        result = await device_loader.load()
        
        # 验证超时被处理为失败
        assert result is False, \
            "超时设备应该返回连接失败"
        assert device_loader.progress.status == LoadingStatus.FAILED, \
            "超时设备应该被标记为 FAILED"
        assert "超时" in device_loader.progress.error, \
            "错误信息应该包含超时说明"


# ============== 边界条件测试 ==============

class TestDeviceFaultToleranceBoundaryConditions:
    """设备容错边界条件测试"""
    
    @pytest.mark.asyncio
    async def test_all_devices_fail(self):
        """测试所有设备都失败的情况"""
        startup_manager = SystemStartupManager(
            model_timeout=5.0,
            device_timeout=3.0
        )
        
        # 添加必需的模型
        startup_manager.add_model(
            "required_model",
            create_mock_model_loader(success=True),
            required=True
        )
        
        # 添加多个失败的可选设备
        for i in range(3):
            startup_manager.add_device(
                f"failing_device_{i}",
                create_mock_device_connector(success=False),
                required=False
            )
        
        # 执行启动
        result = await startup_manager.startup()
        
        # 验证系统仍然启动成功（因为设备都是可选的）
        assert result.success is True, \
            "所有可选设备失败时系统仍应启动成功"
        assert result.degraded_mode is True, \
            "应该进入降级模式"
    
    @pytest.mark.asyncio
    async def test_no_devices_configured(self):
        """测试没有配置设备的情况"""
        startup_manager = SystemStartupManager(
            model_timeout=5.0,
            device_timeout=3.0
        )
        
        # 只添加模型，不添加设备
        startup_manager.add_model(
            "required_model",
            create_mock_model_loader(success=True),
            required=True
        )
        
        # 执行启动
        result = await startup_manager.startup()
        
        # 验证系统启动成功
        assert result.success is True, \
            "没有设备时系统应该启动成功"
        assert result.degraded_mode is False, \
            "没有设备失败时不应该进入降级模式"
    
    @pytest.mark.asyncio
    async def test_required_device_failure_blocks_startup(self):
        """测试必需设备失败阻止启动"""
        startup_manager = SystemStartupManager(
            model_timeout=5.0,
            device_timeout=3.0
        )
        
        # 添加必需的模型
        startup_manager.add_model(
            "required_model",
            create_mock_model_loader(success=True),
            required=True
        )
        
        # 添加必需的设备（失败）
        startup_manager.add_device(
            "required_device",
            create_mock_device_connector(success=False),
            required=True  # 必需设备
        )
        
        # 执行启动
        result = await startup_manager.startup()
        
        # 验证系统启动失败
        assert result.success is False, \
            "必需设备失败时系统应该启动失败"
        assert "required_device" in result.failed_components, \
            "失败的必需设备应该在失败组件列表中"
    
    @pytest.mark.asyncio
    async def test_mixed_required_and_optional_devices(self):
        """测试必需和可选设备混合的情况"""
        startup_manager = SystemStartupManager(
            model_timeout=5.0,
            device_timeout=3.0
        )
        
        # 添加必需的模型
        startup_manager.add_model(
            "required_model",
            create_mock_model_loader(success=True),
            required=True
        )
        
        # 添加必需的设备（成功）
        startup_manager.add_device(
            "required_device",
            create_mock_device_connector(success=True),
            required=True
        )
        
        # 添加可选的设备（失败）
        startup_manager.add_device(
            "optional_device",
            create_mock_device_connector(success=False),
            required=False
        )
        
        # 执行启动
        result = await startup_manager.startup()
        
        # 验证系统启动成功（必需设备成功，可选设备失败）
        assert result.success is True, \
            "必需设备成功时系统应该启动成功"
        assert result.degraded_mode is True, \
            "可选设备失败时应该进入降级模式"
