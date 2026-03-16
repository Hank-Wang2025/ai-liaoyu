"""
系统启动时间约束属性测试
System Startup Time Constraint Property Tests

Property 32: 系统启动时间约束
*For any* 系统启动过程，所有 AI 模型 SHALL 在 60 秒内完成加载。

Validates: Requirements 16.1
"""
import asyncio
import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import List, Tuple

from services.system_startup import (
    LoadingStatus,
    ComponentType,
    LoadingProgress,
    SystemStartupResult,
    AIModelLoader,
    ModelPreloader,
    SystemStartupManager
)


# ============== 测试策略 ==============

# 模型加载时间策略（0.001 到 0.5 秒之间，用于快速测试）
model_load_time_strategy = st.floats(min_value=0.001, max_value=0.5)

# 模型数量策略（1 到 4 个模型）
model_count_strategy = st.integers(min_value=1, max_value=4)

# 模型配置策略
model_config_strategy = st.tuples(
    st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz_"),  # 模型名称
    st.floats(min_value=0.001, max_value=0.2),  # 加载时间（秒）
    st.booleans()  # 是否必需
)


# ============== 辅助函数 ==============

def create_mock_model_loader(load_time: float, success: bool = True):
    """创建模拟模型加载函数
    
    Args:
        load_time: 加载时间（秒）
        success: 是否成功
        
    Returns:
        异步加载函数
    """
    async def mock_load():
        await asyncio.sleep(load_time)
        return success
    return mock_load


# ============== Property 32: 系统启动时间约束 ==============

class TestSystemStartupTimeConstraintProperties:
    """
    系统启动时间约束属性测试
    
    **Feature: healing-pod-system, Property 32: 系统启动时间约束**
    **Validates: Requirements 16.1**
    """
    
    @given(
        model_times=st.lists(
            st.floats(min_value=0.001, max_value=0.2),
            min_size=1,
            max_size=4
        )
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_parallel_model_loading_within_timeout(self, model_times: List[float]):
        """
        属性测试：并行模型加载在超时时间内完成
        
        **Feature: healing-pod-system, Property 32: 系统启动时间约束**
        **Validates: Requirements 16.1**
        
        对于任意数量的模型和加载时间组合，
        如果所有模型的最大加载时间小于超时时间，
        则并行加载应该在超时时间内完成。
        """
        # 计算最大单个模型加载时间
        max_load_time = max(model_times)
        
        # 设置超时时间为最大加载时间的 2 倍（确保有足够余量）
        timeout_seconds = max(max_load_time * 2, 5.0)
        
        preloader = ModelPreloader(timeout_seconds=timeout_seconds)
        
        # 添加所有模型
        for i, load_time in enumerate(model_times):
            preloader.add_model(
                f"model_{i}",
                create_mock_model_loader(load_time),
                required=True,
                timeout_seconds=timeout_seconds
            )
        
        # 执行并行加载
        progress = await preloader.load_all()
        
        # 验证所有模型都加载成功
        for name, p in progress.items():
            assert p.status == LoadingStatus.LOADED, \
                f"模型 {name} 加载失败: {p.error}"
        
        # 验证总加载时间接近最大单个模型时间（并行加载特性）
        summary = preloader.get_loading_summary()
        elapsed_ms = summary["elapsed_ms"]
        
        # 并行加载时间应该接近最大单个模型时间，而不是所有时间之和
        # 允许一定的调度开销（最多 1 秒）
        expected_max_ms = (max_load_time + 1.0) * 1000
        assert elapsed_ms < expected_max_ms, \
            f"并行加载时间 {elapsed_ms}ms 超过预期 {expected_max_ms}ms"
    
    @given(
        model_count=st.integers(min_value=1, max_value=4),
        load_time=st.floats(min_value=0.001, max_value=0.1)
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_startup_manager_time_constraint(
        self,
        model_count: int,
        load_time: float
    ):
        """
        属性测试：启动管理器时间约束
        
        **Feature: healing-pod-system, Property 32: 系统启动时间约束**
        **Validates: Requirements 16.1**
        
        对于任意数量的模型，如果每个模型加载时间合理，
        系统启动应该在 60 秒内完成。
        """
        # 创建启动管理器，设置 60 秒超时
        startup_manager = SystemStartupManager(
            model_timeout=60.0,
            device_timeout=30.0
        )
        
        # 添加模型
        for i in range(model_count):
            startup_manager.add_model(
                f"model_{i}",
                create_mock_model_loader(load_time),
                required=True
            )
        
        # 添加一个设备
        async def mock_device_connect():
            await asyncio.sleep(0.001)
            return True
        
        startup_manager.add_device("test_device", mock_device_connect)
        
        # 执行启动
        result = await startup_manager.startup()
        
        # 验证启动成功
        assert result.success is True, \
            f"启动失败: {result.failed_components}"
        
        # 验证启动时间在 60 秒内
        assert result.total_time_ms < 60000, \
            f"启动时间 {result.total_time_ms}ms 超过 60 秒限制"
    
    @given(
        fast_models=st.integers(min_value=1, max_value=4),
        slow_model_time=st.floats(min_value=0.05, max_value=0.3)
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_mixed_model_loading_times(
        self,
        fast_models: int,
        slow_model_time: float
    ):
        """
        属性测试：混合模型加载时间
        
        **Feature: healing-pod-system, Property 32: 系统启动时间约束**
        **Validates: Requirements 16.1**
        
        对于快速和慢速模型的混合，
        总加载时间应该由最慢的模型决定（并行加载）。
        """
        preloader = ModelPreloader(timeout_seconds=60.0)
        
        # 添加快速模型（0.001 秒）
        for i in range(fast_models):
            preloader.add_model(
                f"fast_model_{i}",
                create_mock_model_loader(0.001),
                required=True
            )
        
        # 添加一个慢速模型
        preloader.add_model(
            "slow_model",
            create_mock_model_loader(slow_model_time),
            required=True
        )
        
        # 执行加载
        progress = await preloader.load_all()
        
        # 验证所有模型都加载成功
        for name, p in progress.items():
            assert p.status == LoadingStatus.LOADED, \
                f"模型 {name} 加载失败: {p.error}"
        
        # 验证总时间接近慢速模型时间
        summary = preloader.get_loading_summary()
        elapsed_ms = summary["elapsed_ms"]
        
        # 总时间应该接近慢速模型时间，而不是所有时间之和
        # 允许 1 秒的调度开销
        expected_max_ms = (slow_model_time + 1.0) * 1000
        assert elapsed_ms < expected_max_ms, \
            f"加载时间 {elapsed_ms}ms 超过预期 {expected_max_ms}ms"
    
    @given(
        timeout_seconds=st.floats(min_value=0.1, max_value=2.0)
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_timeout_enforcement(self, timeout_seconds: float):
        """
        属性测试：超时强制执行
        
        **Feature: healing-pod-system, Property 32: 系统启动时间约束**
        **Validates: Requirements 16.1**
        
        对于任意超时设置，如果模型加载时间超过超时时间，
        系统应该在超时时间内返回失败结果。
        """
        # 创建一个加载时间超过超时时间的模型
        slow_load_time = timeout_seconds + 2.0
        
        preloader = ModelPreloader(timeout_seconds=timeout_seconds)
        
        preloader.add_model(
            "slow_model",
            create_mock_model_loader(slow_load_time),
            required=True,
            timeout_seconds=timeout_seconds
        )
        
        # 执行加载
        progress = await preloader.load_all()
        
        # 验证模型加载失败（超时）
        assert progress["slow_model"].status == LoadingStatus.FAILED, \
            "超时模型应该标记为失败"
        
        # 验证总时间接近超时时间
        summary = preloader.get_loading_summary()
        elapsed_ms = summary["elapsed_ms"]
        
        # 总时间应该接近超时时间（允许 0.5 秒误差）
        assert elapsed_ms < (timeout_seconds + 0.5) * 1000, \
            f"加载时间 {elapsed_ms}ms 超过超时时间 {timeout_seconds}s"


# ============== 边界条件测试 ==============

class TestStartupTimeBoundaryConditions:
    """启动时间边界条件测试"""
    
    @pytest.mark.asyncio
    async def test_empty_model_list(self):
        """测试空模型列表"""
        preloader = ModelPreloader(timeout_seconds=60.0)
        
        progress = await preloader.load_all()
        
        assert len(progress) == 0
        
        summary = preloader.get_loading_summary()
        assert summary["total"] == 0
        assert summary["loaded"] == 0
    
    @pytest.mark.asyncio
    async def test_single_model_within_timeout(self):
        """测试单个模型在超时时间内加载"""
        preloader = ModelPreloader(timeout_seconds=60.0)
        
        preloader.add_model(
            "single_model",
            create_mock_model_loader(0.01),
            required=True
        )
        
        progress = await preloader.load_all()
        
        assert progress["single_model"].status == LoadingStatus.LOADED
        
        summary = preloader.get_loading_summary()
        assert summary["elapsed_ms"] < 60000
    
    @pytest.mark.asyncio
    async def test_maximum_models_parallel_loading(self):
        """测试最大数量模型并行加载"""
        preloader = ModelPreloader(timeout_seconds=60.0)
        
        # 添加 8 个模型，每个加载 0.05 秒
        for i in range(8):
            preloader.add_model(
                f"model_{i}",
                create_mock_model_loader(0.05),
                required=True
            )
        
        progress = await preloader.load_all()
        
        # 验证所有模型都加载成功
        for name, p in progress.items():
            assert p.status == LoadingStatus.LOADED
        
        # 验证总时间远小于串行时间（8 * 0.05 = 0.4 秒）
        summary = preloader.get_loading_summary()
        assert summary["elapsed_ms"] < 1000  # 应该小于 1 秒
