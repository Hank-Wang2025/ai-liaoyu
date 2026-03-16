"""
疗愈报告生成器测试
Therapy Report Generator Tests

Requirements: 13.2, 13.3, 13.5, 13.6
"""
import pytest
import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.session import Session, EmotionHistoryEntry
from models.emotion import EmotionState, EmotionCategory
from models.report import (
    TherapyReport,
    ReportStatus,
    EmotionCurvePoint,
    EffectivenessMetrics
)
from services.report_generator import (
    PrivacyFilter,
    ReportDataCollector,
    ReportTextGenerator,
    PDFReportExporter,
    TherapyReportGenerator
)


class TestPrivacyFilter:
    """隐私过滤器测试"""
    
    def test_filter_phone_number(self):
        """测试过滤手机号"""
        text = "联系电话: 13812345678"
        filtered = PrivacyFilter.filter_text(text)
        assert "13812345678" not in filtered
        assert "[电话号码已隐藏]" in filtered
    
    def test_filter_email(self):
        """测试过滤邮箱"""
        text = "邮箱: user@example.com"
        filtered = PrivacyFilter.filter_text(text)
        assert "user@example.com" not in filtered
        assert "[邮箱已隐藏]" in filtered
    
    def test_filter_id_card(self):
        """测试过滤身份证号"""
        text = "身份证: 110101199001011234"
        filtered = PrivacyFilter.filter_text(text)
        assert "110101199001011234" not in filtered
        assert "[身份证号已隐藏]" in filtered
    
    def test_filter_ip_address(self):
        """测试过滤IP地址"""
        text = "IP地址: 192.168.1.100"
        filtered = PrivacyFilter.filter_text(text)
        assert "192.168.1.100" not in filtered
        assert "[IP地址已隐藏]" in filtered
    
    def test_no_sensitive_info(self):
        """测试无敏感信息的文本"""
        text = "今天天气很好，疗愈效果良好"
        filtered = PrivacyFilter.filter_text(text)
        assert filtered == text
    
    def test_contains_sensitive_info(self):
        """测试检测敏感信息"""
        assert PrivacyFilter.contains_sensitive_info("电话: 13812345678")
        assert PrivacyFilter.contains_sensitive_info("邮箱: test@example.com")
        assert not PrivacyFilter.contains_sensitive_info("正常文本")
    
    def test_filter_dict(self):
        """测试过滤字典"""
        data = {
            "phone": "13812345678",
            "nested": {"email": "test@example.com"},
            "normal": "正常文本"
        }
        filtered = PrivacyFilter.filter_dict(data)
        assert "[电话号码已隐藏]" in filtered["phone"]
        assert "[邮箱已隐藏]" in filtered["nested"]["email"]
        assert filtered["normal"] == "正常文本"


class TestReportDataCollector:
    """报告数据收集器测试"""
    
    def test_collect_from_session(self):
        """测试从会话收集数据"""
        # 创建测试会话
        session = Session.create()
        session.set_initial_emotion(EmotionState(
            category=EmotionCategory.ANXIOUS,
            intensity=0.7,
            valence=-0.3,
            arousal=0.6,
            confidence=0.9,
            timestamp=datetime.now()
        ))
        session.plan_name = "测试方案"
        session.complete(EmotionState(
            category=EmotionCategory.NEUTRAL,
            intensity=0.4,
            valence=0.1,
            arousal=0.3,
            confidence=0.85,
            timestamp=datetime.now()
        ))
        
        # 收集数据
        collector = ReportDataCollector()
        report = collector.collect_from_session(session)
        
        # 验证报告数据
        assert report.session_id == session.id
        assert report.initial_emotion_category == EmotionCategory.ANXIOUS
        assert report.final_emotion_category == EmotionCategory.NEUTRAL
        assert report.plan_name == "测试方案"
        assert report.status == ReportStatus.COMPLETED
    
    def test_effectiveness_calculation(self):
        """测试效果指标计算"""
        session = Session.create()
        session.set_initial_emotion(EmotionState(
            category=EmotionCategory.ANXIOUS,
            intensity=0.8,
            valence=-0.5,
            arousal=0.7,
            confidence=0.9,
            timestamp=datetime.now()
        ))
        session.complete(EmotionState(
            category=EmotionCategory.NEUTRAL,
            intensity=0.3,
            valence=0.2,
            arousal=0.3,
            confidence=0.85,
            timestamp=datetime.now()
        ))
        
        collector = ReportDataCollector()
        report = collector.collect_from_session(session)
        
        # 验证效果指标
        assert report.effectiveness_metrics is not None
        assert report.effectiveness_metrics.emotion_improvement > 0
        assert report.effectiveness_metrics.valence_change > 0
        assert report.effectiveness_metrics.effectiveness_rating in [
            "excellent", "good", "moderate", "minimal", "none"
        ]
    
    def test_emotion_curve_generation(self):
        """测试情绪曲线生成"""
        session = Session.create()
        
        # 添加多个情绪历史记录
        emotions = [
            (EmotionCategory.ANXIOUS, 0.8, -0.5),
            (EmotionCategory.ANXIOUS, 0.6, -0.3),
            (EmotionCategory.NEUTRAL, 0.4, 0.0),
            (EmotionCategory.NEUTRAL, 0.3, 0.1),
        ]
        
        for category, intensity, valence in emotions:
            emotion = EmotionState(
                category=category,
                intensity=intensity,
                valence=valence,
                arousal=0.5,
                confidence=0.8,
                timestamp=datetime.now()
            )
            session.add_emotion_history(emotion, "test_phase")
        
        session.initial_emotion = session.emotion_history[0].emotion_state
        session.final_emotion = session.emotion_history[-1].emotion_state
        
        collector = ReportDataCollector()
        report = collector.collect_from_session(session)
        
        # 验证情绪曲线
        assert len(report.emotion_curve) == len(emotions)
        assert report.emotion_curve[0].category == EmotionCategory.ANXIOUS
        assert report.emotion_curve[-1].category == EmotionCategory.NEUTRAL


class TestReportTextGenerator:
    """报告文字生成器测试"""
    
    @pytest.fixture
    def sample_report(self):
        """创建示例报告"""
        report = TherapyReport.create("test-session")
        report.initial_emotion_category = EmotionCategory.ANXIOUS
        report.initial_emotion_intensity = 0.7
        report.initial_emotion_valence = -0.3
        report.final_emotion_category = EmotionCategory.NEUTRAL
        report.final_emotion_intensity = 0.4
        report.final_emotion_valence = 0.1
        report.duration_seconds = 1200
        report.plan_name = "焦虑缓解方案"
        report.effectiveness_metrics = EffectivenessMetrics(
            emotion_improvement=0.35,
            valence_change=0.4,
            arousal_change=-0.2,
            intensity_change=0.3,
            stability_index=0.8,
            effectiveness_rating="good"
        )
        return report
    
    @pytest.mark.asyncio
    async def test_generate_summary(self, sample_report):
        """测试生成总结文字"""
        generator = ReportTextGenerator()
        summary = await generator.generate_summary(sample_report)
        
        assert summary is not None
        assert len(summary) > 0
        assert "20" in summary  # 时长
        assert "焦虑" in summary  # 初始情绪
    
    @pytest.mark.asyncio
    async def test_generate_recommendations(self, sample_report):
        """测试生成建议"""
        generator = ReportTextGenerator()
        recommendations = await generator.generate_recommendations(sample_report)
        
        assert recommendations is not None
        assert len(recommendations) >= 3
        for rec in recommendations:
            assert len(rec) > 0


class TestPDFReportExporter:
    """PDF导出器测试"""
    
    @pytest.fixture
    def sample_report(self):
        """创建示例报告"""
        report = TherapyReport.create("test-session-pdf")
        report.therapy_start_time = datetime.now()
        report.therapy_end_time = datetime.now()
        report.initial_emotion_category = EmotionCategory.ANXIOUS
        report.initial_emotion_intensity = 0.7
        report.initial_emotion_valence = -0.3
        report.final_emotion_category = EmotionCategory.NEUTRAL
        report.final_emotion_intensity = 0.4
        report.final_emotion_valence = 0.1
        report.duration_seconds = 1200
        report.plan_name = "Anxiety Relief Plan"
        report.effectiveness_metrics = EffectivenessMetrics(
            emotion_improvement=0.35,
            valence_change=0.4,
            arousal_change=-0.2,
            intensity_change=0.3,
            stability_index=0.8,
            effectiveness_rating="good"
        )
        report.summary_text = "Test summary text for the therapy report."
        report.recommendations = [
            "Recommendation 1",
            "Recommendation 2",
            "Recommendation 3"
        ]
        return report
    
    def test_pdf_export(self, sample_report, tmp_path):
        """测试PDF导出"""
        exporter = PDFReportExporter()
        output_path = str(tmp_path / "test_report.pdf")
        
        success = exporter.export_to_pdf(sample_report, output_path)
        
        # 如果 reportlab 可用，应该成功
        if exporter._reportlab_available:
            assert success
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0


class TestTherapyReportGenerator:
    """疗愈报告生成器集成测试"""
    
    @pytest.mark.asyncio
    async def test_generate_complete_report(self):
        """测试生成完整报告"""
        # 创建测试会话
        session = Session.create()
        session.set_initial_emotion(EmotionState(
            category=EmotionCategory.ANXIOUS,
            intensity=0.7,
            valence=-0.3,
            arousal=0.6,
            confidence=0.9,
            timestamp=datetime.now()
        ))
        session.plan_name = "测试方案"
        session.complete(EmotionState(
            category=EmotionCategory.NEUTRAL,
            intensity=0.4,
            valence=0.1,
            arousal=0.3,
            confidence=0.85,
            timestamp=datetime.now()
        ))
        
        # 生成报告
        generator = TherapyReportGenerator()
        report = await generator.generate_report(session)
        
        # 验证报告完整性
        assert report.id is not None
        assert report.session_id == session.id
        assert report.status == ReportStatus.COMPLETED
        assert report.initial_emotion_category == EmotionCategory.ANXIOUS
        assert report.final_emotion_category == EmotionCategory.NEUTRAL
        assert report.summary_text is not None
        assert report.recommendations is not None
        assert len(report.recommendations) >= 3
    
    @pytest.mark.asyncio
    async def test_privacy_check(self):
        """测试隐私检查"""
        generator = TherapyReportGenerator()
        
        # 创建包含敏感信息的报告
        report = TherapyReport.create("test")
        report.summary_text = "用户电话: 13812345678"
        
        # 检查应该失败
        assert not generator.check_privacy(report)
        
        # 过滤后应该通过
        report.summary_text = generator.filter_sensitive_info(report.summary_text)
        assert generator.check_privacy(report)


class TestEmotionCurvePoint:
    """情绪曲线数据点测试"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        point = EmotionCurvePoint(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            category=EmotionCategory.ANXIOUS,
            intensity=0.7,
            valence=-0.3,
            arousal=0.6,
            phase_name="relaxation"
        )
        
        data = point.to_dict()
        
        assert data["category"] == "anxious"
        assert data["intensity"] == 0.7
        assert data["valence"] == -0.3
        assert data["arousal"] == 0.6
        assert data["phase_name"] == "relaxation"
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "timestamp": "2024-01-01T12:00:00",
            "category": "anxious",
            "intensity": 0.7,
            "valence": -0.3,
            "arousal": 0.6,
            "phase_name": "relaxation"
        }
        
        point = EmotionCurvePoint.from_dict(data)
        
        assert point.category == EmotionCategory.ANXIOUS
        assert point.intensity == 0.7
        assert point.phase_name == "relaxation"


class TestEffectivenessMetrics:
    """效果指标测试"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        metrics = EffectivenessMetrics(
            emotion_improvement=0.35,
            valence_change=0.4,
            arousal_change=-0.2,
            intensity_change=0.3,
            stability_index=0.8,
            effectiveness_rating="good"
        )
        
        data = metrics.to_dict()
        
        assert data["emotion_improvement"] == 0.35
        assert data["effectiveness_rating"] == "good"
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "emotion_improvement": 0.35,
            "valence_change": 0.4,
            "arousal_change": -0.2,
            "intensity_change": 0.3,
            "stability_index": 0.8,
            "effectiveness_rating": "good"
        }
        
        metrics = EffectivenessMetrics.from_dict(data)
        
        assert metrics.emotion_improvement == 0.35
        assert metrics.effectiveness_rating == "good"


class TestTherapyReport:
    """疗愈报告模型测试"""
    
    def test_create(self):
        """测试创建报告"""
        report = TherapyReport.create("test-session")
        
        assert report.id is not None
        assert report.session_id == "test-session"
        assert report.status == ReportStatus.GENERATING
    
    def test_duration_minutes(self):
        """测试时长计算"""
        report = TherapyReport.create("test")
        report.duration_seconds = 1200
        
        assert report.duration_minutes == 20.0
    
    def test_to_dict_and_from_dict(self):
        """测试序列化和反序列化"""
        report = TherapyReport.create("test-session")
        report.initial_emotion_category = EmotionCategory.ANXIOUS
        report.initial_emotion_intensity = 0.7
        report.initial_emotion_valence = -0.3
        report.final_emotion_category = EmotionCategory.NEUTRAL
        report.final_emotion_intensity = 0.4
        report.final_emotion_valence = 0.1
        report.duration_seconds = 1200
        report.summary_text = "Test summary"
        report.recommendations = ["Rec 1", "Rec 2"]
        
        # 转换为字典
        data = report.to_dict()
        
        # 从字典恢复
        restored = TherapyReport.from_dict(data)
        
        assert restored.id == report.id
        assert restored.session_id == report.session_id
        assert restored.initial_emotion_category == report.initial_emotion_category
        assert restored.summary_text == report.summary_text
        assert restored.recommendations == report.recommendations
