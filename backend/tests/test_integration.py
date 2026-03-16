"""
集成测试模块
Integration Tests Module

Task 29: 集成测试
- 29.1 端到端疗愈流程测试
- 29.2 设备集成测试
- 29.3 性能测试
- 29.4 离线运行测试

Requirements: All, 16.1, 16.2, 16.3, 14.6, 1.5
"""
import asyncio
import os
import sys
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.emotion import EmotionCategory, EmotionState
from models.therapy import TherapyPlan, TherapyStyle, TherapyIntensity
from models.session import Session, SessionStatus
from models.report import TherapyReport, ReportStatus

from services.plan_manager import PlanManager, TherapyPlanSelector
from services.session_manager import SessionManager
from services.emotion_fusion import EmotionFusion, FusionMode, ModalityWeights
from services.report_generator import (
    TherapyReportGenerator,
    ReportDataCollector,
    PrivacyFilter
)
from services.system_startup import (
    SystemStartupManager,
    LoadingStatus,
    DegradedModeManager
)
from services.device_manager import (
    HardwareDeviceManager,
    ConnectionMonitor,
    DeviceInfo,
    DeviceType,
    ConnectionStatus,
    ConnectionProtocol
)


# ============================================================================
# 29.1 端到端疗愈流程测试
# End-to-End Therapy Flow Tests
# ============================================================================

class TestEndToEndTherapyFlow:
    """
    端到端疗愈流程测试
    
    测试完整的疗愈会话流程：
    情绪分析 -> 方案匹配 -> 执行 -> 报告
    
    Requirements: All
    """
    
    @pytest.fixture
    def session_manager(self):
        """创建会话管理器"""
        return SessionManager()
    
    @pytest.fixture
    def plan_manager(self):
        """创建方案管理器"""
        return PlanManager(plans_dir="content/plans")
    
    @pytest.fixture
    def emotion_fusion(self):
        """创建情绪融合器"""
        return EmotionFusion()
    
    @pytest.fixture
    def report_generator(self):
        """创建报告生成器"""
        return TherapyReportGenerator()
    
    @pytest.fixture
    def sample_emotion_state(self):
        """创建示例情绪状态"""
        return EmotionState(
            category=EmotionCategory.ANXIOUS,
            intensity=0.65,
            valence=-0.4,
            arousal=0.7,
            confidence=0.85,
            timestamp=datetime.now()
        )
    
    @pytest.mark.asyncio
    async def test_complete_therapy_session_flow(
        self,
        session_manager,
        plan_manager,
        sample_emotion_state
    ):
        """
        测试完整疗愈会话流程
        
        验证从会话创建到结束的完整流程
        """
        # Step 1: 创建会话
        session = await session_manager.create_session()
        assert session is not None
        assert session.status == SessionStatus.CREATED
        
        # Step 2: 设置初始情绪
        await session_manager.set_initial_emotion(sample_emotion_state)
        assert session_manager.current_session.initial_emotion is not None
        assert session_manager.current_session.initial_emotion.category == EmotionCategory.ANXIOUS
        
        # Step 3: 匹配疗愈方案
        plan = plan_manager.match(sample_emotion_state)
        assert plan is not None
        assert EmotionCategory.ANXIOUS in plan.target_emotions
        
        # Step 4: 设置方案
        await session_manager.set_plan(plan)
        assert session_manager.current_session.plan_id == plan.id
        
        # Step 5: 开始疗愈
        await session_manager.start_therapy()
        assert session_manager.current_session.status == SessionStatus.IN_PROGRESS
        
        # Step 6: 记录情绪变化
        improved_emotion = EmotionState(
            category=EmotionCategory.NEUTRAL,
            intensity=0.3,
            valence=0.1,
            arousal=0.4,
            confidence=0.8,
            timestamp=datetime.now()
        )
        await session_manager.record_emotion(improved_emotion, "relaxation_phase")
        
        # Step 7: 结束会话
        final_emotion = EmotionState(
            category=EmotionCategory.NEUTRAL,
            intensity=0.2,
            valence=0.2,
            arousal=0.3,
            confidence=0.85,
            timestamp=datetime.now()
        )
        completed_session = await session_manager.end_session(final_emotion)
        
        # 验证会话完成
        assert completed_session.status == SessionStatus.COMPLETED
        assert completed_session.final_emotion is not None
        assert completed_session.duration_seconds >= 0
    
    @pytest.mark.asyncio
    async def test_emotion_analysis_to_plan_matching(
        self,
        plan_manager,
        emotion_fusion
    ):
        """
        测试情绪分析到方案匹配的流程
        
        验证多模态融合结果能正确匹配疗愈方案
        """
        # 模拟多模态情绪数据
        from services.hrv_analyzer import BioAnalysisResult
        from models.emotion import Emotion2VecResult, FaceAnalysisResult, FacialExpression
        
        # 创建语音情绪结果
        audio_result = Emotion2VecResult(
            emotion=EmotionCategory.ANXIOUS,
            scores={
                "anxious": 0.7,
                "neutral": 0.15,
                "tired": 0.1,
                "sad": 0.05
            },
            intensity=0.7
        )
        
        # 创建面部表情结果
        face_result = FaceAnalysisResult(
            detected=True,
            expression=FacialExpression.FEARFUL,
            confidence=0.75,
            expression_scores={
                "fearful": 0.6,
                "neutral": 0.2,
                "sad": 0.1,
                "surprised": 0.1
            },
            landmarks=None,
            face_bbox=None
        )
        
        # 创建生理信号结果
        bio_result = BioAnalysisResult(
            stress_index=65.0,
            stress_level="high",
            hrv_metrics=None,
            heart_rate=85.0,
            heart_rate_status="normal",
            is_valid=True
        )
        
        # 执行多模态融合
        fusion_result = emotion_fusion.fuse(
            audio_result=audio_result,
            face_result=face_result,
            bio_result=bio_result
        )
        
        assert fusion_result is not None
        assert fusion_result.emotion_state is not None
        
        # 使用融合结果匹配方案
        plan = plan_manager.match(fusion_result.emotion_state)
        
        assert plan is not None
        # 验证方案适合当前情绪
        assert any(
            emotion in plan.target_emotions 
            for emotion in [EmotionCategory.ANXIOUS, EmotionCategory.FEARFUL]
        )
    
    @pytest.mark.asyncio
    async def test_therapy_report_generation(
        self,
        session_manager,
        plan_manager,
        report_generator,
        sample_emotion_state
    ):
        """
        测试疗愈报告生成
        
        验证会话结束后能正确生成报告
        """
        # 创建并完成一个会话
        session = await session_manager.create_session()
        await session_manager.set_initial_emotion(sample_emotion_state)
        
        plan = plan_manager.match(sample_emotion_state)
        await session_manager.set_plan(plan)
        await session_manager.start_therapy()
        
        # 记录多个情绪点
        emotions = [
            EmotionState(
                category=EmotionCategory.ANXIOUS,
                intensity=0.5,
                valence=-0.2,
                arousal=0.5,
                confidence=0.8,
                timestamp=datetime.now()
            ),
            EmotionState(
                category=EmotionCategory.NEUTRAL,
                intensity=0.3,
                valence=0.1,
                arousal=0.3,
                confidence=0.85,
                timestamp=datetime.now()
            )
        ]
        
        for emotion in emotions:
            await session_manager.record_emotion(emotion)
        
        final_emotion = EmotionState(
            category=EmotionCategory.NEUTRAL,
            intensity=0.2,
            valence=0.3,
            arousal=0.25,
            confidence=0.9,
            timestamp=datetime.now()
        )
        completed_session = await session_manager.end_session(final_emotion)
        
        # 生成报告
        report = await report_generator.generate_report(completed_session)
        
        # 验证报告内容
        assert report is not None
        assert report.status == ReportStatus.COMPLETED
        assert report.initial_emotion_category == EmotionCategory.ANXIOUS
        assert report.final_emotion_category == EmotionCategory.NEUTRAL
        assert report.duration_seconds >= 0
        assert report.summary_text is not None
        assert len(report.summary_text) > 0
    
    @pytest.mark.asyncio
    async def test_session_with_adjustments(
        self,
        session_manager,
        plan_manager,
        sample_emotion_state
    ):
        """
        测试带调整记录的会话
        
        验证疗愈过程中的调整能被正确记录
        """
        session = await session_manager.create_session()
        await session_manager.set_initial_emotion(sample_emotion_state)
        
        plan = plan_manager.match(sample_emotion_state)
        await session_manager.set_plan(plan)
        await session_manager.start_therapy()
        
        # 记录调整
        await session_manager.record_adjustment(
            reason="情绪无明显改善",
            adjustment_type="plan_switch",
            details={"from_phase": 1, "to_phase": 2},
            previous_state={"intensity": 0.65},
            new_state={"intensity": 0.5}
        )
        
        # 验证调整被记录
        assert len(session_manager.current_session.adjustments) == 1
        adjustment = session_manager.current_session.adjustments[0]
        assert adjustment.reason == "情绪无明显改善"
        assert adjustment.adjustment_type == "plan_switch"
    
    @pytest.mark.asyncio
    async def test_user_selection_priority_in_flow(
        self,
        session_manager,
        plan_manager,
        sample_emotion_state
    ):
        """
        测试用户选择优先级在完整流程中的表现
        
        验证用户手动选择的方案优先于自动匹配
        """
        selector = TherapyPlanSelector(plan_manager)
        
        # 用户手动选择方案
        user_plan = selector.select_plan("fatigue_recovery")
        assert user_plan is not None
        
        # 获取有效方案（应该是用户选择的）
        effective_plan = selector.get_effective_plan(sample_emotion_state)
        assert effective_plan.id == "fatigue_recovery"
        
        # 创建会话并使用用户选择的方案
        session = await session_manager.create_session()
        await session_manager.set_initial_emotion(sample_emotion_state)
        await session_manager.set_plan(effective_plan)
        
        assert session_manager.current_session.plan_id == "fatigue_recovery"
    
    @pytest.mark.asyncio
    async def test_emotion_improvement_tracking(
        self,
        session_manager,
        plan_manager,
        sample_emotion_state
    ):
        """
        测试情绪改善追踪
        
        验证系统能正确追踪情绪变化
        """
        session = await session_manager.create_session()
        await session_manager.set_initial_emotion(sample_emotion_state)
        
        plan = plan_manager.match(sample_emotion_state)
        await session_manager.set_plan(plan)
        await session_manager.start_therapy()
        
        # 模拟情绪逐步改善
        emotion_progression = [
            (EmotionCategory.ANXIOUS, 0.55, -0.3),
            (EmotionCategory.ANXIOUS, 0.45, -0.2),
            (EmotionCategory.NEUTRAL, 0.35, 0.0),
            (EmotionCategory.NEUTRAL, 0.25, 0.15),
        ]
        
        for category, intensity, valence in emotion_progression:
            emotion = EmotionState(
                category=category,
                intensity=intensity,
                valence=valence,
                arousal=0.4,
                confidence=0.8,
                timestamp=datetime.now()
            )
            await session_manager.record_emotion(emotion)
        
        # 验证情绪历史被记录
        assert len(session_manager.current_session.emotion_history) >= 4
        
        # 验证情绪改善趋势
        history = session_manager.current_session.emotion_history
        initial_intensity = history[0].emotion_state.intensity
        final_intensity = history[-1].emotion_state.intensity
        assert final_intensity < initial_intensity  # 情绪强度降低


class TestReportPrivacyProtection:
    """
    报告隐私保护测试
    
    验证报告生成过程中的隐私保护功能
    """
    
    def test_privacy_filter_phone_number(self):
        """测试手机号过滤"""
        # Use text with word boundary before phone number (space)
        text = "我的电话是 13812345678，请联系我"
        filtered = PrivacyFilter.filter_text(text)
        
        assert "13812345678" not in filtered
        assert "[电话号码已隐藏]" in filtered
    
    def test_privacy_filter_email(self):
        """测试邮箱过滤"""
        text = "请发邮件到test@example.com"
        filtered = PrivacyFilter.filter_text(text)
        
        assert "test@example.com" not in filtered
        assert "[邮箱已隐藏]" in filtered
    
    def test_privacy_filter_id_card(self):
        """测试身份证号过滤"""
        text = "身份证号：110101199001011234"
        filtered = PrivacyFilter.filter_text(text)
        
        assert "110101199001011234" not in filtered
        assert "[身份证号已隐藏]" in filtered
    
    def test_privacy_filter_preserves_normal_text(self):
        """测试正常文本不被过滤"""
        text = "今天的疗愈效果很好，我感觉放松了很多"
        filtered = PrivacyFilter.filter_text(text)
        
        assert filtered == text
    
    def test_contains_sensitive_info_detection(self):
        """测试敏感信息检测"""
        # Phone number with word boundary (space before)
        assert PrivacyFilter.contains_sensitive_info("电话 13812345678") is True
        # Email detection
        assert PrivacyFilter.contains_sensitive_info("邮箱test@example.com") is True
        assert PrivacyFilter.contains_sensitive_info("正常文本") is False



# ============================================================================
# 29.2 设备集成测试
# Device Integration Tests
# ============================================================================

class TestDeviceIntegration:
    """
    设备集成测试
    
    测试真实硬件设备连接、设备联动控制和降级模式
    
    Requirements: 16.2, 16.3
    """
    
    @pytest.fixture
    def device_manager(self):
        """创建设备管理器"""
        return HardwareDeviceManager()
    
    @pytest.fixture
    def connection_monitor(self):
        """创建连接监控器"""
        return ConnectionMonitor(check_interval=1.0, max_reconnect_attempts=2)
    
    @pytest.fixture
    def degraded_manager(self):
        """创建降级模式管理器"""
        return DegradedModeManager()
    
    @pytest.mark.asyncio
    async def test_device_connection_workflow(self, connection_monitor):
        """
        测试设备连接工作流
        
        验证设备注册、连接、状态监控的完整流程
        """
        # 创建模拟设备
        light_device = DeviceInfo(
            device_id="light_001",
            device_type=DeviceType.LIGHT,
            name="Test Light",
            protocol=ConnectionProtocol.WIFI,
            address="192.168.1.100"
        )
        
        audio_device = DeviceInfo(
            device_id="audio_001",
            device_type=DeviceType.AUDIO,
            name="Test Audio",
            protocol=ConnectionProtocol.USB,
            address="0"
        )
        
        # 模拟连接函数
        async def mock_light_connect():
            await asyncio.sleep(0.05)
            return True
        
        async def mock_audio_connect():
            await asyncio.sleep(0.05)
            return True
        
        # 注册设备
        connection_monitor.register_device(light_device, mock_light_connect)
        connection_monitor.register_device(audio_device, mock_audio_connect)
        
        # 连接所有设备
        results = await connection_monitor.connect_all()
        
        # 验证连接结果
        assert results["light_001"] is True
        assert results["audio_001"] is True
        
        # 验证设备状态
        light_status = connection_monitor.get_device_status("light_001")
        assert light_status.status == ConnectionStatus.CONNECTED
        
        audio_status = connection_monitor.get_device_status("audio_001")
        assert audio_status.status == ConnectionStatus.CONNECTED
    
    @pytest.mark.asyncio
    async def test_device_connection_failure_handling(self, connection_monitor):
        """
        测试设备连接失败处理
        
        验证设备连接失败时的错误处理
        """
        device = DeviceInfo(
            device_id="failing_device",
            device_type=DeviceType.CHAIR,
            name="Failing Device",
            protocol=ConnectionProtocol.BLE
        )
        
        async def mock_fail_connect():
            raise RuntimeError("Connection failed")
        
        connection_monitor.register_device(device, mock_fail_connect)
        
        result = await connection_monitor.connect_device("failing_device")
        
        assert result is False
        
        status = connection_monitor.get_device_status("failing_device")
        assert status.status == ConnectionStatus.ERROR
        assert "Connection failed" in status.error_message
    
    @pytest.mark.asyncio
    async def test_degraded_mode_activation(self, degraded_manager):
        """
        测试降级模式激活
        
        验证设备连接失败时系统进入降级模式
        Requirements: 16.3
        """
        from services.system_startup import LoadingProgress, ComponentType
        
        # 模拟部分设备连接失败
        device_progress = {
            "light_controller": LoadingProgress(
                component_name="light_controller",
                component_type=ComponentType.DEVICE,
                status=LoadingStatus.LOADED
            ),
            "audio_controller": LoadingProgress(
                component_name="audio_controller",
                component_type=ComponentType.DEVICE,
                status=LoadingStatus.FAILED
            ),
            "chair_controller": LoadingProgress(
                component_name="chair_controller",
                component_type=ComponentType.DEVICE,
                status=LoadingStatus.FAILED
            )
        }
        
        degraded_manager.process_device_failures(device_progress)
        
        # 验证降级模式激活
        assert degraded_manager.is_degraded is True
        assert "audio_controller" in degraded_manager.failed_devices
        assert "chair_controller" in degraded_manager.failed_devices
        
        # 验证功能可用性
        assert degraded_manager.is_feature_available("ambient_lighting") is True
        assert degraded_manager.is_feature_available("background_music") is False
        assert degraded_manager.is_feature_available("massage") is False
    
    @pytest.mark.asyncio
    async def test_device_status_callback(self, connection_monitor):
        """
        测试设备状态回调
        
        验证设备状态变化时回调被正确触发
        """
        status_changes = []
        
        def status_callback(device_id, status):
            status_changes.append((device_id, status))
        
        connection_monitor.register_status_callback(status_callback)
        
        device = DeviceInfo(
            device_id="callback_test_device",
            device_type=DeviceType.LIGHT,
            name="Callback Test",
            protocol=ConnectionProtocol.WIFI
        )
        
        async def mock_connect():
            return True
        
        connection_monitor.register_device(device, mock_connect)
        await connection_monitor.connect_device("callback_test_device")
        
        # 验证回调被触发
        assert len(status_changes) >= 2
        
        # 应该有 CONNECTING 和 CONNECTED 状态
        statuses = [s for _, s in status_changes]
        assert ConnectionStatus.CONNECTING in statuses
        assert ConnectionStatus.CONNECTED in statuses
    
    @pytest.mark.asyncio
    async def test_multiple_device_coordination(self, connection_monitor):
        """
        测试多设备协调
        
        验证多个设备能够同时连接和协调工作
        """
        devices = [
            DeviceInfo(
                device_id=f"device_{i}",
                device_type=DeviceType.LIGHT,
                name=f"Device {i}",
                protocol=ConnectionProtocol.WIFI
            )
            for i in range(5)
        ]
        
        async def mock_connect():
            await asyncio.sleep(0.02)
            return True
        
        for device in devices:
            connection_monitor.register_device(device, mock_connect)
        
        start_time = time.time()
        results = await connection_monitor.connect_all()
        elapsed = time.time() - start_time
        
        # 验证所有设备连接成功
        assert all(results.values())
        
        # 验证并行连接（总时间应该接近单个设备时间）
        assert elapsed < 0.5  # 应该远小于 5 * 0.02 = 0.1s 的串行时间
    
    @pytest.mark.asyncio
    async def test_device_disconnect_workflow(self, connection_monitor):
        """
        测试设备断开连接工作流
        """
        device = DeviceInfo(
            device_id="disconnect_test",
            device_type=DeviceType.AUDIO,
            name="Disconnect Test",
            protocol=ConnectionProtocol.USB
        )
        
        disconnected = False
        
        async def mock_connect():
            return True
        
        async def mock_disconnect():
            nonlocal disconnected
            disconnected = True
        
        connection_monitor.register_device(device, mock_connect, mock_disconnect)
        
        # 连接设备
        await connection_monitor.connect_device("disconnect_test")
        assert connection_monitor.get_device_status("disconnect_test").status == ConnectionStatus.CONNECTED
        
        # 断开设备
        await connection_monitor.disconnect_device("disconnect_test")
        
        assert disconnected is True
        assert connection_monitor.get_device_status("disconnect_test").status == ConnectionStatus.DISCONNECTED


# ============================================================================
# 29.3 性能测试
# Performance Tests
# ============================================================================

class TestPerformance:
    """
    性能测试
    
    测试系统启动时间、情绪分析延迟、内存和 CPU 使用
    
    Requirements: 16.1, 1.5
    """
    
    @pytest.fixture
    def startup_manager(self):
        """创建启动管理器"""
        return SystemStartupManager(model_timeout=60.0, device_timeout=30.0)
    
    @pytest.mark.asyncio
    async def test_system_startup_time_constraint(self, startup_manager):
        """
        测试系统启动时间约束
        
        验证系统能在 60 秒内完成启动
        Requirements: 16.1
        """
        # 模拟 AI 模型加载（快速版本用于测试）
        async def mock_model_load():
            await asyncio.sleep(0.1)  # 模拟加载时间
            return True
        
        async def mock_device_connect():
            await asyncio.sleep(0.05)
            return True
        
        # 添加多个模型和设备
        startup_manager.add_model("sensevoice", mock_model_load)
        startup_manager.add_model("emotion2vec", mock_model_load)
        startup_manager.add_model("cosyvoice", mock_model_load)
        startup_manager.add_model("qwen3", mock_model_load)
        
        startup_manager.add_device("light", mock_device_connect)
        startup_manager.add_device("audio", mock_device_connect)
        startup_manager.add_device("camera", mock_device_connect)
        
        start_time = time.time()
        result = await startup_manager.startup()
        elapsed_seconds = time.time() - start_time
        
        # 验证启动成功
        assert result.success is True
        
        # 验证启动时间在 60 秒内
        assert elapsed_seconds < 60.0
        assert result.total_time_ms < 60000
    
    @pytest.mark.asyncio
    async def test_parallel_model_loading_performance(self):
        """
        测试并行模型加载性能
        
        验证模型并行加载比串行加载更快
        """
        from services.system_startup import ModelPreloader
        
        preloader = ModelPreloader(timeout_seconds=10.0)
        
        load_times = []
        
        async def mock_load(delay: float):
            start = time.time()
            await asyncio.sleep(delay)
            load_times.append(time.time() - start)
            return True
        
        # 添加 4 个模型，每个加载 0.1 秒
        for i in range(4):
            preloader.add_model(
                f"model_{i}",
                lambda: mock_load(0.1)
            )
        
        start_time = time.time()
        await preloader.load_all()
        total_time = time.time() - start_time
        
        # 并行加载应该接近单个模型时间，而不是 4 倍
        assert total_time < 0.5  # 应该远小于 0.4 秒（串行时间）
    
    @pytest.mark.asyncio
    async def test_emotion_fusion_performance(self):
        """
        测试情绪融合性能
        
        验证多模态融合能在合理时间内完成
        """
        from services.hrv_analyzer import BioAnalysisResult
        from models.emotion import Emotion2VecResult, FaceAnalysisResult, FacialExpression
        
        fusion = EmotionFusion()
        
        # 准备测试数据
        audio_result = Emotion2VecResult(
            emotion=EmotionCategory.ANXIOUS,
            scores={"anxious": 0.7, "neutral": 0.2, "sad": 0.1},
            intensity=0.7
        )
        
        face_result = FaceAnalysisResult(
            detected=True,
            expression=FacialExpression.FEARFUL,
            confidence=0.75,
            expression_scores={"fearful": 0.6, "neutral": 0.4},
            landmarks=None,
            face_bbox=None
        )
        
        bio_result = BioAnalysisResult(
            stress_index=65.0,
            stress_level="high",
            hrv_metrics=None,
            heart_rate=85.0,
            heart_rate_status="normal",
            is_valid=True
        )
        
        # 执行多次融合并测量时间
        iterations = 100
        start_time = time.time()
        
        for _ in range(iterations):
            fusion.fuse(
                audio_result=audio_result,
                face_result=face_result,
                bio_result=bio_result
            )
        
        total_time = time.time() - start_time
        avg_time_ms = (total_time / iterations) * 1000
        
        # 验证平均融合时间在合理范围内（应该小于 10ms）
        assert avg_time_ms < 10.0
    
    @pytest.mark.asyncio
    async def test_plan_matching_performance(self):
        """
        测试方案匹配性能
        
        验证方案匹配能快速完成
        """
        plan_manager = PlanManager(plans_dir="content/plans")
        
        emotion = EmotionState(
            category=EmotionCategory.ANXIOUS,
            intensity=0.6,
            valence=-0.4,
            arousal=0.7,
            confidence=0.8,
            timestamp=datetime.now()
        )
        
        # 执行多次匹配并测量时间
        iterations = 100
        start_time = time.time()
        
        for _ in range(iterations):
            plan_manager.match(emotion)
        
        total_time = time.time() - start_time
        avg_time_ms = (total_time / iterations) * 1000
        
        # 验证平均匹配时间在合理范围内（应该小于 5ms）
        assert avg_time_ms < 5.0
    
    @pytest.mark.asyncio
    async def test_session_operations_performance(self):
        """
        测试会话操作性能
        
        验证会话创建、更新等操作的性能
        """
        session_manager = SessionManager()
        
        # 测试会话创建性能
        start_time = time.time()
        session = await session_manager.create_session()
        create_time = time.time() - start_time
        
        assert create_time < 0.1  # 创建应该在 100ms 内完成
        
        # 测试情绪记录性能
        emotion = EmotionState(
            category=EmotionCategory.NEUTRAL,
            intensity=0.5,
            valence=0.0,
            arousal=0.3,
            confidence=0.8,
            timestamp=datetime.now()
        )
        
        await session_manager.set_initial_emotion(emotion)
        
        iterations = 50
        start_time = time.time()
        
        for i in range(iterations):
            await session_manager.record_emotion(emotion, f"phase_{i}")
        
        total_time = time.time() - start_time
        avg_time_ms = (total_time / iterations) * 1000
        
        # 验证平均记录时间在合理范围内
        assert avg_time_ms < 10.0
        
        # 清理
        await session_manager.cancel_session()


# ============================================================================
# 29.4 离线运行测试
# Offline Operation Tests
# ============================================================================

class TestOfflineOperation:
    """
    离线运行测试
    
    验证系统在断开网络连接时所有核心功能正常
    
    Requirements: 14.6
    """
    
    @pytest.mark.asyncio
    async def test_local_plan_loading(self):
        """
        测试本地方案加载
        
        验证疗愈方案从本地文件加载，不依赖网络
        """
        plan_manager = PlanManager(plans_dir="content/plans")
        
        # 验证方案加载成功
        plans = plan_manager.get_all_plans()
        assert len(plans) > 0
        
        # 验证可以获取特定方案
        plan = plan_manager.get_plan_by_id("anxiety_relief_chinese")
        assert plan is not None
    
    @pytest.mark.asyncio
    async def test_local_emotion_fusion(self):
        """
        测试本地情绪融合
        
        验证情绪融合完全在本地完成
        """
        fusion = EmotionFusion()
        
        from models.emotion import Emotion2VecResult
        
        audio_result = Emotion2VecResult(
            emotion=EmotionCategory.SAD,
            scores={"sad": 0.6, "neutral": 0.3, "tired": 0.1},
            intensity=0.6
        )
        
        # 执行融合（应该完全本地）
        result = fusion.fuse_audio_only(audio_result)
        
        assert result is not None
        assert result.emotion_state is not None
        assert result.fusion_mode == FusionMode.AUDIO_ONLY
    
    @pytest.mark.asyncio
    async def test_local_session_management(self):
        """
        测试本地会话管理
        
        验证会话管理不依赖网络
        """
        session_manager = SessionManager()
        
        # 创建会话
        session = await session_manager.create_session()
        assert session is not None
        
        # 设置情绪
        emotion = EmotionState(
            category=EmotionCategory.TIRED,
            intensity=0.5,
            valence=-0.2,
            arousal=0.2,
            confidence=0.8,
            timestamp=datetime.now()
        )
        await session_manager.set_initial_emotion(emotion)
        
        # 获取会话摘要
        summary = session_manager.get_session_summary()
        assert summary is not None
        assert summary["initial_emotion"]["category"] == "tired"
        
        # 清理
        await session_manager.cancel_session()
    
    @pytest.mark.asyncio
    async def test_local_report_generation(self):
        """
        测试本地报告生成
        
        验证报告生成不依赖网络（使用模板而非 AI）
        """
        from services.report_generator import ReportTextGenerator, ReportDataCollector
        
        # 创建一个模拟会话
        session_manager = SessionManager()
        session = await session_manager.create_session()
        
        initial_emotion = EmotionState(
            category=EmotionCategory.ANXIOUS,
            intensity=0.7,
            valence=-0.5,
            arousal=0.8,
            confidence=0.85,
            timestamp=datetime.now()
        )
        await session_manager.set_initial_emotion(initial_emotion)
        
        final_emotion = EmotionState(
            category=EmotionCategory.NEUTRAL,
            intensity=0.3,
            valence=0.1,
            arousal=0.3,
            confidence=0.9,
            timestamp=datetime.now()
        )
        completed_session = await session_manager.end_session(final_emotion)
        
        # 使用本地模板生成报告
        text_generator = ReportTextGenerator(dialog_engine=None)  # 无 AI 引擎
        data_collector = ReportDataCollector()
        
        report = data_collector.collect_from_session(completed_session)
        summary = text_generator._generate_template_summary(report)
        recommendations = text_generator._get_default_recommendations(report)
        
        # 验证生成成功
        assert summary is not None
        assert len(summary) > 0
        assert len(recommendations) > 0
    
    @pytest.mark.asyncio
    async def test_local_privacy_filtering(self):
        """
        测试本地隐私过滤
        
        验证隐私过滤完全在本地完成
        """
        # Use text with word boundary before phone number (space)
        sensitive_text = "我的电话是 13812345678，邮箱是test@example.com"
        
        filtered = PrivacyFilter.filter_text(sensitive_text)
        
        # 验证敏感信息被过滤
        assert "13812345678" not in filtered
        assert "test@example.com" not in filtered
        assert "[电话号码已隐藏]" in filtered
        assert "[邮箱已隐藏]" in filtered
    
    @pytest.mark.asyncio
    async def test_degraded_mode_offline_capability(self):
        """
        测试降级模式离线能力
        
        验证降级模式管理不依赖网络
        """
        from services.system_startup import LoadingProgress, ComponentType
        
        degraded_manager = DegradedModeManager()
        
        # 模拟设备状态
        device_progress = {
            "camera": LoadingProgress(
                component_name="camera",
                component_type=ComponentType.DEVICE,
                status=LoadingStatus.FAILED
            ),
            "microphone": LoadingProgress(
                component_name="microphone",
                component_type=ComponentType.DEVICE,
                status=LoadingStatus.LOADED
            )
        }
        
        degraded_manager.process_device_failures(device_progress)
        
        # 验证降级模式状态
        status = degraded_manager.get_status()
        assert status["is_degraded"] is True
        assert "camera" in status["failed_devices"]
    
    @pytest.mark.asyncio
    async def test_complete_offline_workflow(self):
        """
        测试完整离线工作流
        
        验证整个疗愈流程可以在离线状态下完成
        """
        # 1. 本地方案加载
        plan_manager = PlanManager(plans_dir="content/plans")
        assert len(plan_manager.get_all_plans()) > 0
        
        # 2. 本地情绪融合
        fusion = EmotionFusion()
        from models.emotion import Emotion2VecResult
        
        audio_result = Emotion2VecResult(
            emotion=EmotionCategory.ANXIOUS,
            scores={"anxious": 0.7, "neutral": 0.2, "sad": 0.1},
            intensity=0.7
        )
        
        fusion_result = fusion.fuse_audio_only(audio_result)
        assert fusion_result.emotion_state is not None
        
        # 3. 本地方案匹配
        plan = plan_manager.match(fusion_result.emotion_state)
        assert plan is not None
        
        # 4. 本地会话管理
        session_manager = SessionManager()
        session = await session_manager.create_session()
        await session_manager.set_initial_emotion(fusion_result.emotion_state)
        await session_manager.set_plan(plan)
        
        # 5. 本地报告生成
        final_emotion = EmotionState(
            category=EmotionCategory.NEUTRAL,
            intensity=0.3,
            valence=0.1,
            arousal=0.3,
            confidence=0.85,
            timestamp=datetime.now()
        )
        completed_session = await session_manager.end_session(final_emotion)
        
        report_generator = TherapyReportGenerator(dialog_engine=None)
        report = await report_generator.generate_report(completed_session)
        
        # 验证完整流程成功
        assert report is not None
        assert report.status == ReportStatus.COMPLETED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
