"""
疗愈报告生成完整性属性测试
Therapy Report Generation Completeness Property Tests

**Feature: healing-pod-system, Property 26: 疗愈报告生成完整性**
**Validates: Requirements 13.2**

Property 26: *For any* 结束的疗愈会话，生成的报告 SHALL 包含初始情绪状态、情绪变化曲线、最终情绪状态和疗愈时长。
"""
import pytest
import asyncio
import os
import sys
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, assume

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.session import Session, EmotionHistoryEntry
from models.emotion import EmotionState, EmotionCategory
from models.report import TherapyReport, ReportStatus
from services.report_generator import ReportDataCollector, TherapyReportGenerator


# 情绪类别策略
emotion_category_strategy = st.sampled_from([
    EmotionCategory.HAPPY,
    EmotionCategory.SAD,
    EmotionCategory.ANGRY,
    EmotionCategory.ANXIOUS,
    EmotionCategory.TIRED,
    EmotionCategory.FEARFUL,
    EmotionCategory.SURPRISED,
    EmotionCategory.DISGUSTED,
    EmotionCategory.NEUTRAL
])

# 情绪强度策略 (0-1)
intensity_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# 效价策略 (-1 到 1)
valence_strategy = st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# 唤醒度策略 (0-1)
arousal_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# 置信度策略 (0-1)
confidence_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# 疗愈时长策略 (60秒 到 3600秒)
duration_strategy = st.integers(min_value=60, max_value=3600)


@st.composite
def emotion_state_strategy(draw):
    """生成随机情绪状态"""
    return EmotionState(
        category=draw(emotion_category_strategy),
        intensity=draw(intensity_strategy),
        valence=draw(valence_strategy),
        arousal=draw(arousal_strategy),
        confidence=draw(confidence_strategy),
        timestamp=datetime.now()
    )


@st.composite
def completed_session_strategy(draw):
    """
    生成已完成的疗愈会话
    
    确保会话具有:
    - 初始情绪状态
    - 最终情绪状态
    - 情绪历史记录
    - 疗愈时长
    """
    # 创建会话
    session = Session.create()
    
    # 设置初始情绪
    initial_emotion = draw(emotion_state_strategy())
    session.set_initial_emotion(initial_emotion)
    
    # 设置疗愈方案名称
    plan_names = ["焦虑缓解方案", "压力释放方案", "情绪平衡方案", "深度放松方案", "正念冥想方案"]
    session.plan_name = draw(st.sampled_from(plan_names))
    
    # 添加情绪历史记录 (1-10 条)
    num_history = draw(st.integers(min_value=1, max_value=10))
    phase_names = ["准备阶段", "引导阶段", "深度放松", "唤醒阶段", "结束阶段"]
    
    for i in range(num_history):
        emotion = draw(emotion_state_strategy())
        phase_name = draw(st.sampled_from(phase_names))
        session.add_emotion_history(emotion, phase_name)
    
    # 设置最终情绪并完成会话
    final_emotion = draw(emotion_state_strategy())
    session.complete(final_emotion)
    
    # 模拟疗愈时长
    duration = draw(duration_strategy)
    session.start_time = datetime.now() - timedelta(seconds=duration)
    session.end_time = datetime.now()
    
    return session


class TestReportCompletenessProperties:
    """
    疗愈报告生成完整性属性测试
    
    **Feature: healing-pod-system, Property 26: 疗愈报告生成完整性**
    **Validates: Requirements 13.2**
    """
    
    @given(session=completed_session_strategy())
    @settings(max_examples=100, deadline=None)
    def test_report_contains_initial_emotion(self, session: Session):
        """
        测试报告包含初始情绪状态
        
        **Feature: healing-pod-system, Property 26: 疗愈报告生成完整性**
        **Validates: Requirements 13.2**
        
        *For any* 结束的疗愈会话，生成的报告 SHALL 包含初始情绪状态
        """
        collector = ReportDataCollector()
        report = collector.collect_from_session(session)
        
        # 验证初始情绪状态存在
        assert report.initial_emotion_category is not None, \
            "报告必须包含初始情绪类别"
        assert report.initial_emotion_intensity is not None, \
            "报告必须包含初始情绪强度"
        assert report.initial_emotion_valence is not None, \
            "报告必须包含初始情绪效价"
        
        # 验证初始情绪与会话一致
        assert report.initial_emotion_category == session.initial_emotion.category, \
            "报告初始情绪类别应与会话一致"
        assert report.initial_emotion_intensity == session.initial_emotion.intensity, \
            "报告初始情绪强度应与会话一致"
    
    @given(session=completed_session_strategy())
    @settings(max_examples=100, deadline=None)
    def test_report_contains_final_emotion(self, session: Session):
        """
        测试报告包含最终情绪状态
        
        **Feature: healing-pod-system, Property 26: 疗愈报告生成完整性**
        **Validates: Requirements 13.2**
        
        *For any* 结束的疗愈会话，生成的报告 SHALL 包含最终情绪状态
        """
        collector = ReportDataCollector()
        report = collector.collect_from_session(session)
        
        # 验证最终情绪状态存在
        assert report.final_emotion_category is not None, \
            "报告必须包含最终情绪类别"
        assert report.final_emotion_intensity is not None, \
            "报告必须包含最终情绪强度"
        assert report.final_emotion_valence is not None, \
            "报告必须包含最终情绪效价"
        
        # 验证最终情绪与会话一致
        assert report.final_emotion_category == session.final_emotion.category, \
            "报告最终情绪类别应与会话一致"
        assert report.final_emotion_intensity == session.final_emotion.intensity, \
            "报告最终情绪强度应与会话一致"
    
    @given(session=completed_session_strategy())
    @settings(max_examples=100, deadline=None)
    def test_report_contains_emotion_curve(self, session: Session):
        """
        测试报告包含情绪变化曲线
        
        **Feature: healing-pod-system, Property 26: 疗愈报告生成完整性**
        **Validates: Requirements 13.2**
        
        *For any* 结束的疗愈会话，生成的报告 SHALL 包含情绪变化曲线
        """
        collector = ReportDataCollector()
        report = collector.collect_from_session(session)
        
        # 验证情绪曲线存在
        assert report.emotion_curve is not None, \
            "报告必须包含情绪变化曲线"
        
        # 验证情绪曲线数据点数量与会话历史一致
        assert len(report.emotion_curve) == len(session.emotion_history), \
            "情绪曲线数据点数量应与会话历史记录一致"
        
        # 验证每个数据点包含必要字段
        for point in report.emotion_curve:
            assert point.timestamp is not None, "曲线数据点必须包含时间戳"
            assert point.category is not None, "曲线数据点必须包含情绪类别"
            assert point.intensity is not None, "曲线数据点必须包含情绪强度"
            assert point.valence is not None, "曲线数据点必须包含效价"
            assert point.arousal is not None, "曲线数据点必须包含唤醒度"
    
    @given(session=completed_session_strategy())
    @settings(max_examples=100, deadline=None)
    def test_report_contains_duration(self, session: Session):
        """
        测试报告包含疗愈时长
        
        **Feature: healing-pod-system, Property 26: 疗愈报告生成完整性**
        **Validates: Requirements 13.2**
        
        *For any* 结束的疗愈会话，生成的报告 SHALL 包含疗愈时长
        """
        collector = ReportDataCollector()
        report = collector.collect_from_session(session)
        
        # 验证疗愈时长存在且有效
        assert report.duration_seconds is not None, \
            "报告必须包含疗愈时长（秒）"
        assert report.duration_seconds >= 0, \
            "疗愈时长必须为非负数"
        
        # 验证时长与会话一致
        assert report.duration_seconds == session.duration_seconds, \
            "报告疗愈时长应与会话一致"
        
        # 验证时间信息完整
        assert report.therapy_start_time is not None, \
            "报告必须包含疗愈开始时间"
        assert report.therapy_end_time is not None, \
            "报告必须包含疗愈结束时间"
    
    @given(session=completed_session_strategy())
    @settings(max_examples=100, deadline=None)
    def test_report_completeness_all_fields(self, session: Session):
        """
        综合测试报告完整性 - 所有必要字段
        
        **Feature: healing-pod-system, Property 26: 疗愈报告生成完整性**
        **Validates: Requirements 13.2**
        
        *For any* 结束的疗愈会话，生成的报告 SHALL 包含:
        - 初始情绪状态
        - 情绪变化曲线
        - 最终情绪状态
        - 疗愈时长
        """
        collector = ReportDataCollector()
        report = collector.collect_from_session(session)
        
        # 1. 验证初始情绪状态完整
        assert report.initial_emotion_category is not None, \
            "报告必须包含初始情绪类别"
        assert report.initial_emotion_intensity is not None, \
            "报告必须包含初始情绪强度"
        assert report.initial_emotion_valence is not None, \
            "报告必须包含初始情绪效价"
        
        # 2. 验证情绪变化曲线完整
        assert report.emotion_curve is not None, \
            "报告必须包含情绪变化曲线"
        assert len(report.emotion_curve) > 0, \
            "情绪变化曲线必须包含至少一个数据点"
        
        # 3. 验证最终情绪状态完整
        assert report.final_emotion_category is not None, \
            "报告必须包含最终情绪类别"
        assert report.final_emotion_intensity is not None, \
            "报告必须包含最终情绪强度"
        assert report.final_emotion_valence is not None, \
            "报告必须包含最终情绪效价"
        
        # 4. 验证疗愈时长完整
        assert report.duration_seconds is not None, \
            "报告必须包含疗愈时长"
        assert report.duration_seconds >= 0, \
            "疗愈时长必须为非负数"
        assert report.therapy_start_time is not None, \
            "报告必须包含开始时间"
        assert report.therapy_end_time is not None, \
            "报告必须包含结束时间"
        
        # 5. 验证报告状态为已完成
        assert report.status == ReportStatus.COMPLETED, \
            "报告状态应为已完成"
        
        # 6. 验证报告基本信息
        assert report.id is not None, "报告必须有唯一ID"
        assert report.session_id == session.id, "报告会话ID应与会话一致"


class TestReportCompletenessAsync:
    """
    异步报告生成完整性测试
    
    **Feature: healing-pod-system, Property 26: 疗愈报告生成完整性**
    **Validates: Requirements 13.2**
    """
    
    @pytest.mark.asyncio
    @given(session=completed_session_strategy())
    @settings(max_examples=50, deadline=None)
    async def test_full_report_generation_completeness(self, session: Session):
        """
        测试完整报告生成流程的完整性
        
        **Feature: healing-pod-system, Property 26: 疗愈报告生成完整性**
        **Validates: Requirements 13.2**
        
        *For any* 结束的疗愈会话，通过 TherapyReportGenerator 生成的完整报告
        SHALL 包含初始情绪状态、情绪变化曲线、最终情绪状态和疗愈时长
        """
        generator = TherapyReportGenerator()
        report = await generator.generate_report(session)
        
        # 验证报告完整性
        # 1. 初始情绪状态
        assert report.initial_emotion_category is not None
        assert report.initial_emotion_intensity is not None
        assert report.initial_emotion_valence is not None
        
        # 2. 情绪变化曲线
        assert report.emotion_curve is not None
        assert len(report.emotion_curve) > 0
        
        # 3. 最终情绪状态
        assert report.final_emotion_category is not None
        assert report.final_emotion_intensity is not None
        assert report.final_emotion_valence is not None
        
        # 4. 疗愈时长
        assert report.duration_seconds is not None
        assert report.duration_seconds >= 0
        
        # 5. 额外验证：总结文字和建议（Requirements 13.3）
        assert report.summary_text is not None
        assert len(report.summary_text) > 0
        assert report.recommendations is not None
        assert len(report.recommendations) >= 3
        
        # 6. 报告状态
        assert report.status == ReportStatus.COMPLETED
