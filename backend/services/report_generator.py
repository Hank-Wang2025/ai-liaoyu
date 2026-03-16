"""
疗愈报告生成器
Therapy Report Generator

实现报告数据收集、文字生成、隐私保护和 PDF 导出
Requirements: 13.2, 13.3, 13.5, 13.6
"""
import re
import json
import statistics
from datetime import datetime
from typing import Optional, List, Dict, Any
from loguru import logger

from models.session import Session, EmotionHistoryEntry
from models.emotion import EmotionState, EmotionCategory
from models.report import (
    TherapyReport,
    ReportStatus,
    EmotionCurvePoint,
    EffectivenessMetrics
)


class PrivacyFilter:
    """
    隐私信息过滤器
    
    Requirements: 13.6 - 确保报告不包含可识别身份的信息
    """
    
    # 敏感信息正则表达式模式 (按优先级排序，长模式优先)
    # 使用有序列表确保正确的匹配顺序
    PATTERNS_ORDERED = [
        # 中国身份证号 (18位或15位) - 优先匹配
        ("id_card_cn", r"\b\d{17}[\dXx]\b|\b\d{15}\b"),
        # 银行卡号 (16-19位数字)
        ("bank_card", r"\b\d{16,19}\b"),
        # 中国手机号 (11位)
        ("phone_cn", r"\b1[3-9]\d{9}\b"),
        # 电子邮件
        ("email", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
        # IP 地址
        ("ip_address", r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
        # 国际电话号码 (带国家代码)
        ("phone_intl", r"\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}"),
    ]
    
    # 替换文本
    REPLACEMENTS = {
        "phone_cn": "[电话号码已隐藏]",
        "phone_intl": "[电话号码已隐藏]",
        "email": "[邮箱已隐藏]",
        "id_card_cn": "[身份证号已隐藏]",
        "bank_card": "[银行卡号已隐藏]",
        "ip_address": "[IP地址已隐藏]",
    }
    
    @classmethod
    def filter_text(cls, text: str) -> str:
        """
        过滤文本中的敏感信息
        
        Args:
            text: 原始文本
            
        Returns:
            过滤后的文本
        """
        if not text:
            return text
        
        filtered = text
        for pattern_name, pattern in cls.PATTERNS_ORDERED:
            replacement = cls.REPLACEMENTS.get(pattern_name, "[已隐藏]")
            filtered = re.sub(pattern, replacement, filtered)
        
        return filtered
    
    @classmethod
    def filter_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        递归过滤字典中的敏感信息
        
        Args:
            data: 原始字典
            
        Returns:
            过滤后的字典
        """
        if not data:
            return data
        
        filtered = {}
        for key, value in data.items():
            if isinstance(value, str):
                filtered[key] = cls.filter_text(value)
            elif isinstance(value, dict):
                filtered[key] = cls.filter_dict(value)
            elif isinstance(value, list):
                filtered[key] = [
                    cls.filter_text(item) if isinstance(item, str)
                    else cls.filter_dict(item) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                filtered[key] = value
        
        return filtered
    
    @classmethod
    def contains_sensitive_info(cls, text: str) -> bool:
        """
        检查文本是否包含敏感信息
        
        Args:
            text: 待检查文本
            
        Returns:
            是否包含敏感信息
        """
        if not text:
            return False
        
        for pattern_name, pattern in cls.PATTERNS_ORDERED:
            if re.search(pattern, text):
                return True
        return False


class ReportDataCollector:
    """
    报告数据收集器
    
    Requirements: 13.2 - 收集初始和最终情绪状态、生成情绪变化曲线、计算疗愈时长和效果指标
    """
    
    # 效果评级阈值
    EFFECTIVENESS_THRESHOLDS = {
        "excellent": 0.5,   # 显著改善
        "good": 0.3,        # 明显改善
        "moderate": 0.15,   # 中等改善
        "minimal": 0.05,    # 轻微改善
        "none": 0.0         # 无改善或恶化
    }
    
    def collect_from_session(self, session: Session) -> TherapyReport:
        """
        从会话收集报告数据
        
        Args:
            session: 疗愈会话
            
        Returns:
            TherapyReport 报告对象
        """
        report = TherapyReport.create(session.id)
        
        # 基本时间信息
        report.therapy_start_time = session.start_time
        report.therapy_end_time = session.end_time or datetime.now()
        report.duration_seconds = session.duration_seconds
        
        # 初始情绪状态
        if session.initial_emotion:
            report.initial_emotion_category = session.initial_emotion.category
            report.initial_emotion_intensity = session.initial_emotion.intensity
            report.initial_emotion_valence = session.initial_emotion.valence
        
        # 最终情绪状态
        if session.final_emotion:
            report.final_emotion_category = session.final_emotion.category
            report.final_emotion_intensity = session.final_emotion.intensity
            report.final_emotion_valence = session.final_emotion.valence
        
        # 疗愈方案信息
        report.plan_name = session.plan_name
        report.phases_completed = session.current_phase_index
        
        # 调整记录
        report.adjustment_count = len(session.adjustments)
        
        # 生成情绪变化曲线
        report.emotion_curve = self._generate_emotion_curve(session.emotion_history)
        
        # 计算效果指标
        report.effectiveness_metrics = self._calculate_effectiveness(
            session.initial_emotion,
            session.final_emotion,
            session.emotion_history
        )
        
        report.status = ReportStatus.COMPLETED
        return report
    
    def _generate_emotion_curve(
        self, 
        emotion_history: List[EmotionHistoryEntry]
    ) -> List[EmotionCurvePoint]:
        """
        生成情绪变化曲线数据
        
        Args:
            emotion_history: 情绪历史记录
            
        Returns:
            情绪曲线数据点列表
        """
        curve_points = []
        
        for entry in emotion_history:
            point = EmotionCurvePoint(
                timestamp=entry.timestamp,
                category=entry.emotion_state.category,
                intensity=entry.emotion_state.intensity,
                valence=entry.emotion_state.valence,
                arousal=entry.emotion_state.arousal,
                phase_name=entry.phase_name
            )
            curve_points.append(point)
        
        return curve_points
    
    def _calculate_effectiveness(
        self,
        initial_emotion: Optional[EmotionState],
        final_emotion: Optional[EmotionState],
        emotion_history: List[EmotionHistoryEntry]
    ) -> Optional[EffectivenessMetrics]:
        """
        计算疗愈效果指标
        
        Args:
            initial_emotion: 初始情绪状态
            final_emotion: 最终情绪状态
            emotion_history: 情绪历史记录
            
        Returns:
            EffectivenessMetrics 效果指标
        """
        if not initial_emotion:
            return None
        
        # 使用最终情绪或历史中最后一条
        final = final_emotion
        if not final and emotion_history:
            final = emotion_history[-1].emotion_state
        
        if not final:
            return None
        
        # 计算效价变化
        valence_change = final.valence - initial_emotion.valence
        
        # 计算唤醒度变化
        arousal_change = final.arousal - initial_emotion.arousal
        
        # 计算强度变化（负面情绪强度降低为正向改善）
        if initial_emotion.valence < 0:
            # 负面情绪：强度降低是好事
            intensity_change = initial_emotion.intensity - final.intensity
        else:
            # 正面情绪：强度增加是好事
            intensity_change = final.intensity - initial_emotion.intensity
        
        # 综合情绪改善程度
        emotion_improvement = (valence_change * 0.5) + (intensity_change * 0.3) + (-arousal_change * 0.2)
        emotion_improvement = max(-1.0, min(1.0, emotion_improvement))
        
        # 计算稳定性指数
        stability_index = self._calculate_stability(emotion_history)
        
        # 确定效果评级
        effectiveness_rating = self._get_effectiveness_rating(emotion_improvement)
        
        return EffectivenessMetrics(
            emotion_improvement=round(emotion_improvement, 3),
            valence_change=round(valence_change, 3),
            arousal_change=round(arousal_change, 3),
            intensity_change=round(intensity_change, 3),
            stability_index=round(stability_index, 3),
            effectiveness_rating=effectiveness_rating
        )
    
    def _calculate_stability(
        self, 
        emotion_history: List[EmotionHistoryEntry]
    ) -> float:
        """
        计算情绪稳定性指数
        
        基于情绪历史中效价的标准差计算
        标准差越小，稳定性越高
        
        Args:
            emotion_history: 情绪历史记录
            
        Returns:
            稳定性指数 (0-1)
        """
        if len(emotion_history) < 2:
            return 1.0
        
        valences = [entry.emotion_state.valence for entry in emotion_history]
        
        try:
            std_dev = statistics.stdev(valences)
            # 将标准差转换为稳定性指数 (0-1)
            # 标准差范围约 0-2，转换为 1-0
            stability = max(0.0, 1.0 - (std_dev / 2.0))
            return stability
        except statistics.StatisticsError:
            return 1.0
    
    def _get_effectiveness_rating(self, improvement: float) -> str:
        """
        根据改善程度获取效果评级
        
        Args:
            improvement: 改善程度 (-1 到 1)
            
        Returns:
            效果评级字符串
        """
        if improvement >= self.EFFECTIVENESS_THRESHOLDS["excellent"]:
            return "excellent"
        elif improvement >= self.EFFECTIVENESS_THRESHOLDS["good"]:
            return "good"
        elif improvement >= self.EFFECTIVENESS_THRESHOLDS["moderate"]:
            return "moderate"
        elif improvement >= self.EFFECTIVENESS_THRESHOLDS["minimal"]:
            return "minimal"
        else:
            return "none"


class ReportTextGenerator:
    """
    报告文字生成器
    
    Requirements: 13.3 - 使用 Qwen3 生成总结文字和个性化建议
    """
    
    # 情绪类别中文映射
    EMOTION_NAMES_ZH = {
        EmotionCategory.HAPPY: "愉悦",
        EmotionCategory.SAD: "低落",
        EmotionCategory.ANGRY: "愤怒",
        EmotionCategory.ANXIOUS: "焦虑",
        EmotionCategory.TIRED: "疲惫",
        EmotionCategory.FEARFUL: "恐惧",
        EmotionCategory.SURPRISED: "惊讶",
        EmotionCategory.DISGUSTED: "厌恶",
        EmotionCategory.NEUTRAL: "平静"
    }
    
    # 效果评级中文映射
    EFFECTIVENESS_NAMES_ZH = {
        "excellent": "显著改善",
        "good": "明显改善",
        "moderate": "中等改善",
        "minimal": "轻微改善",
        "none": "效果不明显"
    }
    
    # 默认建议模板
    DEFAULT_RECOMMENDATIONS = {
        EmotionCategory.ANXIOUS: [
            "建议每天进行 10-15 分钟的深呼吸练习",
            "尝试减少咖啡因摄入，保持规律作息",
            "可以尝试渐进式肌肉放松法缓解紧张"
        ],
        EmotionCategory.SAD: [
            "建议适当增加户外活动和阳光照射",
            "与信任的朋友或家人保持联系",
            "尝试记录每天的三件好事"
        ],
        EmotionCategory.TIRED: [
            "建议保证每晚 7-8 小时的睡眠",
            "适当进行轻度运动如散步或瑜伽",
            "注意工作与休息的平衡"
        ],
        EmotionCategory.ANGRY: [
            "当感到愤怒时，尝试深呼吸数到十",
            "可以通过运动释放负面情绪",
            "学习表达情绪的健康方式"
        ],
        EmotionCategory.FEARFUL: [
            "尝试正念冥想来安抚内心",
            "逐步面对让你感到恐惧的事物",
            "与专业人士交流可能会有帮助"
        ],
        EmotionCategory.NEUTRAL: [
            "继续保持良好的生活习惯",
            "可以尝试新的放松方式丰富体验",
            "定期进行自我情绪检查"
        ]
    }
    
    def __init__(self, dialog_engine=None):
        """
        初始化文字生成器
        
        Args:
            dialog_engine: Qwen3 对话引擎（可选）
        """
        self.dialog_engine = dialog_engine
    
    async def generate_summary(self, report: TherapyReport) -> str:
        """
        生成报告总结文字
        
        Args:
            report: 疗愈报告
            
        Returns:
            总结文字
        """
        # 如果有 AI 引擎，使用 AI 生成
        if self.dialog_engine and self.dialog_engine.is_initialized():
            return await self._generate_ai_summary(report)
        
        # 否则使用模板生成
        return self._generate_template_summary(report)
    
    async def generate_recommendations(
        self, 
        report: TherapyReport
    ) -> List[str]:
        """
        生成个性化建议
        
        Args:
            report: 疗愈报告
            
        Returns:
            建议列表
        """
        # 如果有 AI 引擎，使用 AI 生成
        if self.dialog_engine and self.dialog_engine.is_initialized():
            return await self._generate_ai_recommendations(report)
        
        # 否则使用默认建议
        return self._get_default_recommendations(report)
    
    def _generate_template_summary(self, report: TherapyReport) -> str:
        """
        使用模板生成总结文字
        
        Args:
            report: 疗愈报告
            
        Returns:
            总结文字
        """
        initial_emotion_name = self.EMOTION_NAMES_ZH.get(
            report.initial_emotion_category, "未知"
        )
        
        final_emotion_name = self.EMOTION_NAMES_ZH.get(
            report.final_emotion_category, "未知"
        ) if report.final_emotion_category else "未记录"
        
        duration_minutes = int(report.duration_minutes)
        
        # 构建总结
        summary_parts = []
        
        # 开场
        summary_parts.append(
            f"本次疗愈会话持续了 {duration_minutes} 分钟。"
        )
        
        # 初始状态
        summary_parts.append(
            f"开始时，您的情绪状态为{initial_emotion_name}，"
            f"情绪强度为 {report.initial_emotion_intensity:.0%}。"
        )
        
        # 疗愈方案
        if report.plan_name:
            summary_parts.append(
                f"我们为您选择了「{report.plan_name}」疗愈方案。"
            )
        
        # 最终状态和效果
        if report.effectiveness_metrics:
            effectiveness_name = self.EFFECTIVENESS_NAMES_ZH.get(
                report.effectiveness_metrics.effectiveness_rating, "未知"
            )
            
            if report.effectiveness_metrics.emotion_improvement > 0:
                summary_parts.append(
                    f"疗愈结束后，您的情绪状态变为{final_emotion_name}，"
                    f"整体效果评估为「{effectiveness_name}」。"
                )
            else:
                summary_parts.append(
                    f"疗愈结束后，您的情绪状态为{final_emotion_name}。"
                    f"本次疗愈效果有限，建议您尝试其他疗愈方案或寻求专业帮助。"
                )
        
        # 调整记录
        if report.adjustment_count > 0:
            summary_parts.append(
                f"疗愈过程中进行了 {report.adjustment_count} 次方案调整，"
                f"以更好地适应您的状态变化。"
            )
        
        # 结语
        summary_parts.append(
            "感谢您使用智能疗愈仓，希望您能感受到内心的平静与放松。"
        )
        
        return "".join(summary_parts)
    
    def _get_default_recommendations(self, report: TherapyReport) -> List[str]:
        """
        获取默认建议
        
        Args:
            report: 疗愈报告
            
        Returns:
            建议列表
        """
        # 根据初始情绪获取建议
        emotion = report.initial_emotion_category
        recommendations = self.DEFAULT_RECOMMENDATIONS.get(
            emotion, 
            self.DEFAULT_RECOMMENDATIONS[EmotionCategory.NEUTRAL]
        )
        
        return recommendations.copy()
    
    async def _generate_ai_summary(self, report: TherapyReport) -> str:
        """
        使用 AI 生成总结文字
        
        Args:
            report: 疗愈报告
            
        Returns:
            AI 生成的总结文字
        """
        prompt = self._build_summary_prompt(report)
        
        try:
            response = await self.dialog_engine.chat(prompt, check_crisis=False)
            # 过滤可能的敏感信息
            return PrivacyFilter.filter_text(response.content)
        except Exception as e:
            logger.error(f"AI summary generation failed: {e}")
            return self._generate_template_summary(report)
    
    async def _generate_ai_recommendations(
        self, 
        report: TherapyReport
    ) -> List[str]:
        """
        使用 AI 生成个性化建议
        
        Args:
            report: 疗愈报告
            
        Returns:
            AI 生成的建议列表
        """
        prompt = self._build_recommendations_prompt(report)
        
        try:
            response = await self.dialog_engine.chat(prompt, check_crisis=False)
            # 解析建议列表
            recommendations = self._parse_recommendations(response.content)
            # 过滤敏感信息
            return [PrivacyFilter.filter_text(r) for r in recommendations]
        except Exception as e:
            logger.error(f"AI recommendations generation failed: {e}")
            return self._get_default_recommendations(report)
    
    def _build_summary_prompt(self, report: TherapyReport) -> str:
        """构建总结生成提示词"""
        initial_emotion = self.EMOTION_NAMES_ZH.get(
            report.initial_emotion_category, "未知"
        )
        final_emotion = self.EMOTION_NAMES_ZH.get(
            report.final_emotion_category, "未知"
        ) if report.final_emotion_category else "未记录"
        
        return f"""请为以下疗愈会话生成一段温暖、鼓励的总结文字（100-150字）：

疗愈时长：{int(report.duration_minutes)} 分钟
初始情绪：{initial_emotion}（强度 {report.initial_emotion_intensity:.0%}）
最终情绪：{final_emotion}
使用方案：{report.plan_name or '自动匹配'}
效果评估：{report.effectiveness_metrics.effectiveness_rating if report.effectiveness_metrics else '未评估'}

要求：
1. 语气温暖、积极
2. 肯定用户的努力
3. 不要提及具体的个人信息
4. 不要提供医疗建议"""
    
    def _build_recommendations_prompt(self, report: TherapyReport) -> str:
        """构建建议生成提示词"""
        initial_emotion = self.EMOTION_NAMES_ZH.get(
            report.initial_emotion_category, "未知"
        )
        
        return f"""请根据以下情况，提供 3 条简短的日常建议（每条不超过 30 字）：

用户主要情绪：{initial_emotion}
疗愈效果：{report.effectiveness_metrics.effectiveness_rating if report.effectiveness_metrics else '未评估'}

要求：
1. 建议要具体、可执行
2. 不要提供医疗或药物建议
3. 每条建议单独一行，以数字编号开头
4. 语气温和、鼓励"""
    
    def _parse_recommendations(self, text: str) -> List[str]:
        """
        解析 AI 生成的建议文本
        
        Args:
            text: AI 生成的文本
            
        Returns:
            建议列表
        """
        recommendations = []
        lines = text.strip().split('\n')
        
        for line in lines:
            # 移除编号和多余空格
            cleaned = re.sub(r'^[\d\.\)、]+\s*', '', line.strip())
            if cleaned and len(cleaned) > 5:
                recommendations.append(cleaned)
        
        # 确保至少返回 3 条建议
        if len(recommendations) < 3:
            default = self._get_default_recommendations(
                TherapyReport.create("temp")
            )
            recommendations.extend(default[:3 - len(recommendations)])
        
        return recommendations[:5]  # 最多返回 5 条


class PDFReportExporter:
    """
    PDF 报告导出器
    
    Requirements: 13.5 - 支持将报告导出为 PDF 格式
    """
    
    def __init__(self):
        """初始化 PDF 导出器"""
        self._reportlab_available = False
        self._check_dependencies()
    
    def _check_dependencies(self):
        """检查 reportlab 依赖"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            self._reportlab_available = True
        except ImportError:
            logger.warning(
                "reportlab not installed. PDF export will be limited. "
                "Install with: pip install reportlab"
            )
    
    def export_to_pdf(
        self, 
        report: TherapyReport, 
        output_path: str
    ) -> bool:
        """
        导出报告为 PDF
        
        Args:
            report: 疗愈报告
            output_path: 输出文件路径
            
        Returns:
            是否导出成功
        """
        if not self._reportlab_available:
            logger.error("reportlab not available for PDF export")
            return False
        
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm
            from reportlab.pdfgen import canvas
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib.colors import HexColor
            
            # 创建 PDF
            c = canvas.Canvas(output_path, pagesize=A4)
            width, height = A4
            
            # 尝试注册中文字体
            try:
                # macOS 系统字体路径
                font_paths = [
                    "/System/Library/Fonts/PingFang.ttc",
                    "/System/Library/Fonts/STHeiti Light.ttc",
                    "/Library/Fonts/Arial Unicode.ttf",
                ]
                font_registered = False
                for font_path in font_paths:
                    try:
                        pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                        font_registered = True
                        break
                    except:
                        continue
                
                if not font_registered:
                    # 使用默认字体
                    logger.warning("Chinese font not found, using default font")
            except Exception as e:
                logger.warning(f"Font registration failed: {e}")
            
            # 绘制报告内容
            self._draw_header(c, report, width, height)
            self._draw_emotion_summary(c, report, width, height)
            self._draw_effectiveness(c, report, width, height)
            self._draw_summary_text(c, report, width, height)
            self._draw_recommendations(c, report, width, height)
            self._draw_footer(c, report, width, height)
            
            c.save()
            logger.info(f"PDF report exported to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"PDF export failed: {e}")
            return False
    
    def _draw_header(self, c, report: TherapyReport, width: float, height: float):
        """绘制报告头部"""
        from reportlab.lib.colors import HexColor
        
        # 标题
        c.setFillColor(HexColor("#2C3E50"))
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(width / 2, height - 50, "Therapy Report")
        
        # 副标题
        c.setFont("Helvetica", 12)
        c.setFillColor(HexColor("#7F8C8D"))
        c.drawCentredString(
            width / 2, 
            height - 75, 
            f"Session: {report.session_id[:8]}..."
        )
        
        # 日期
        c.drawCentredString(
            width / 2, 
            height - 95, 
            f"Date: {report.therapy_start_time.strftime('%Y-%m-%d %H:%M')}"
        )
        
        # 分隔线
        c.setStrokeColor(HexColor("#BDC3C7"))
        c.line(50, height - 110, width - 50, height - 110)
    
    def _draw_emotion_summary(
        self, 
        c, 
        report: TherapyReport, 
        width: float, 
        height: float
    ):
        """绘制情绪摘要"""
        from reportlab.lib.colors import HexColor
        
        y_start = height - 150
        
        # 标题
        c.setFillColor(HexColor("#2C3E50"))
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_start, "Emotion Summary")
        
        # 内容
        c.setFont("Helvetica", 11)
        c.setFillColor(HexColor("#34495E"))
        
        y = y_start - 25
        c.drawString(60, y, f"Duration: {int(report.duration_minutes)} minutes")
        
        y -= 20
        c.drawString(
            60, y, 
            f"Initial Emotion: {report.initial_emotion_category.value} "
            f"(Intensity: {report.initial_emotion_intensity:.0%})"
        )
        
        y -= 20
        if report.final_emotion_category:
            c.drawString(
                60, y, 
                f"Final Emotion: {report.final_emotion_category.value} "
                f"(Intensity: {report.final_emotion_intensity:.0%})"
            )
        else:
            c.drawString(60, y, "Final Emotion: Not recorded")
        
        y -= 20
        if report.plan_name:
            c.drawString(60, y, f"Therapy Plan: {report.plan_name}")
    
    def _draw_effectiveness(
        self, 
        c, 
        report: TherapyReport, 
        width: float, 
        height: float
    ):
        """绘制效果评估"""
        from reportlab.lib.colors import HexColor
        
        y_start = height - 280
        
        # 标题
        c.setFillColor(HexColor("#2C3E50"))
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_start, "Effectiveness Assessment")
        
        if not report.effectiveness_metrics:
            c.setFont("Helvetica", 11)
            c.setFillColor(HexColor("#7F8C8D"))
            c.drawString(60, y_start - 25, "No effectiveness data available")
            return
        
        metrics = report.effectiveness_metrics
        
        # 内容
        c.setFont("Helvetica", 11)
        c.setFillColor(HexColor("#34495E"))
        
        y = y_start - 25
        c.drawString(60, y, f"Overall Rating: {metrics.effectiveness_rating.upper()}")
        
        y -= 20
        improvement_pct = metrics.emotion_improvement * 100
        c.drawString(60, y, f"Emotion Improvement: {improvement_pct:+.1f}%")
        
        y -= 20
        c.drawString(60, y, f"Stability Index: {metrics.stability_index:.0%}")
    
    def _draw_summary_text(
        self, 
        c, 
        report: TherapyReport, 
        width: float, 
        height: float
    ):
        """绘制总结文字"""
        from reportlab.lib.colors import HexColor
        
        y_start = height - 400
        
        # 标题
        c.setFillColor(HexColor("#2C3E50"))
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_start, "Summary")
        
        if not report.summary_text:
            c.setFont("Helvetica", 11)
            c.setFillColor(HexColor("#7F8C8D"))
            c.drawString(60, y_start - 25, "No summary available")
            return
        
        # 文字换行处理
        c.setFont("Helvetica", 10)
        c.setFillColor(HexColor("#34495E"))
        
        # 简单的文字换行
        text = report.summary_text
        max_width = width - 120
        y = y_start - 25
        
        # 按字符数简单分行
        chars_per_line = 70
        lines = [text[i:i+chars_per_line] for i in range(0, len(text), chars_per_line)]
        
        for line in lines[:5]:  # 最多显示 5 行
            c.drawString(60, y, line)
            y -= 15
    
    def _draw_recommendations(
        self, 
        c, 
        report: TherapyReport, 
        width: float, 
        height: float
    ):
        """绘制建议"""
        from reportlab.lib.colors import HexColor
        
        y_start = height - 520
        
        # 标题
        c.setFillColor(HexColor("#2C3E50"))
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_start, "Recommendations")
        
        if not report.recommendations:
            c.setFont("Helvetica", 11)
            c.setFillColor(HexColor("#7F8C8D"))
            c.drawString(60, y_start - 25, "No recommendations available")
            return
        
        c.setFont("Helvetica", 10)
        c.setFillColor(HexColor("#34495E"))
        
        y = y_start - 25
        for i, rec in enumerate(report.recommendations[:5], 1):
            c.drawString(60, y, f"{i}. {rec}")
            y -= 18
    
    def _draw_footer(
        self, 
        c, 
        report: TherapyReport, 
        width: float, 
        height: float
    ):
        """绘制页脚"""
        from reportlab.lib.colors import HexColor
        
        # 分隔线
        c.setStrokeColor(HexColor("#BDC3C7"))
        c.line(50, 80, width - 50, 80)
        
        # 免责声明
        c.setFont("Helvetica", 8)
        c.setFillColor(HexColor("#95A5A6"))
        c.drawCentredString(
            width / 2, 
            60, 
            "This report is for reference only and does not constitute medical advice."
        )
        c.drawCentredString(
            width / 2, 
            48, 
            "Please consult a professional if you need psychological support."
        )
        
        # 生成时间
        c.drawCentredString(
            width / 2, 
            30, 
            f"Generated: {report.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )


class TherapyReportGenerator:
    """
    疗愈报告生成器主类
    
    整合数据收集、文字生成、隐私保护和 PDF 导出功能
    """
    
    def __init__(self, dialog_engine=None):
        """
        初始化报告生成器
        
        Args:
            dialog_engine: Qwen3 对话引擎（可选，用于 AI 生成文字）
        """
        self.data_collector = ReportDataCollector()
        self.text_generator = ReportTextGenerator(dialog_engine)
        self.pdf_exporter = PDFReportExporter()
        self.privacy_filter = PrivacyFilter()
    
    async def generate_report(self, session: Session) -> TherapyReport:
        """
        生成完整的疗愈报告
        
        Args:
            session: 疗愈会话
            
        Returns:
            TherapyReport 完整报告
        """
        logger.info(f"Generating report for session: {session.id}")
        
        # 1. 收集数据
        report = self.data_collector.collect_from_session(session)
        
        # 2. 生成总结文字
        report.summary_text = await self.text_generator.generate_summary(report)
        
        # 3. 生成建议
        report.recommendations = await self.text_generator.generate_recommendations(report)
        
        # 4. 隐私过滤
        report.summary_text = self.privacy_filter.filter_text(report.summary_text)
        report.recommendations = [
            self.privacy_filter.filter_text(r) for r in report.recommendations
        ]
        
        report.status = ReportStatus.COMPLETED
        logger.info(f"Report generated successfully: {report.id}")
        
        return report
    
    def export_to_pdf(self, report: TherapyReport, output_path: str) -> bool:
        """
        导出报告为 PDF
        
        Args:
            report: 疗愈报告
            output_path: 输出文件路径
            
        Returns:
            是否导出成功
        """
        return self.pdf_exporter.export_to_pdf(report, output_path)
    
    def filter_sensitive_info(self, text: str) -> str:
        """
        过滤敏感信息
        
        Args:
            text: 原始文本
            
        Returns:
            过滤后的文本
        """
        return self.privacy_filter.filter_text(text)
    
    def check_privacy(self, report: TherapyReport) -> bool:
        """
        检查报告是否包含敏感信息
        
        Args:
            report: 疗愈报告
            
        Returns:
            是否通过隐私检查（True 表示无敏感信息）
        """
        # 检查总结文字
        if report.summary_text and self.privacy_filter.contains_sensitive_info(report.summary_text):
            return False
        
        # 检查建议
        if report.recommendations:
            for rec in report.recommendations:
                if self.privacy_filter.contains_sensitive_info(rec):
                    return False
        
        return True


# 创建默认实例
report_generator = TherapyReportGenerator()
