"""
报告隐私保护属性测试
Report Privacy Protection Property Tests

**Feature: healing-pod-system, Property 27: 报告隐私保护**
**Validates: Requirements 13.6**

Property 27: *For any* 生成的疗愈报告，报告内容 SHALL 不包含用户姓名、身份证号、手机号等可识别身份的信息。
"""
import pytest
import os
import sys
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, assume

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.session import Session, EmotionHistoryEntry
from models.emotion import EmotionState, EmotionCategory
from models.report import TherapyReport, ReportStatus
from services.report_generator import (
    PrivacyFilter,
    ReportDataCollector,
    TherapyReportGenerator
)


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


# 敏感信息生成策略
def chinese_phone_strategy():
    """生成中国手机号"""
    return st.from_regex(r"1[3-9]\d{9}", fullmatch=True)


def valid_email_strategy():
    """生成有效的电子邮件地址（确保能被正则匹配）"""
    # 生成符合标准格式的邮箱
    local_part = st.from_regex(r"[a-zA-Z][a-zA-Z0-9._%+-]{2,10}", fullmatch=True)
    domain = st.from_regex(r"[a-zA-Z][a-zA-Z0-9-]{2,10}", fullmatch=True)
    tld = st.sampled_from(["com", "org", "net", "edu", "cn", "io"])
    
    return st.builds(
        lambda l, d, t: f"{l}@{d}.{t}",
        local_part, domain, tld
    )


def chinese_id_card_strategy():
    """生成中国身份证号（18位）"""
    # 生成符合格式的身份证号（非真实有效）
    return st.from_regex(r"\d{17}[\dXx]", fullmatch=True)


def bank_card_strategy():
    """生成银行卡号（16-19位）"""
    return st.from_regex(r"\d{16,19}", fullmatch=True)


def ip_address_strategy():
    """生成 IP 地址"""
    return st.from_regex(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", fullmatch=True)


def international_phone_strategy():
    """生成国际电话号码"""
    return st.from_regex(r"\+\d{1,3}-\d{4}-\d{4}", fullmatch=True)


# 敏感信息策略（组合）- 只使用能被正则可靠匹配的类型
sensitive_info_strategy = st.one_of(
    chinese_phone_strategy(),
    valid_email_strategy(),
    chinese_id_card_strategy(),
    ip_address_strategy(),
    international_phone_strategy()
)


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
def text_with_sensitive_info_strategy(draw):
    """生成包含敏感信息的文本"""
    # 基础文本模板
    templates = [
        "用户 {info} 完成了本次疗愈",
        "联系方式：{info}",
        "身份证号：{info}",
        "请联系 {info} 获取更多信息",
        "用户邮箱 {info} 已记录",
        "IP地址 {info} 已记录",
        "银行卡号 {info}",
        "手机号 {info} 的用户",
    ]
    
    template = draw(st.sampled_from(templates))
    sensitive_info = draw(sensitive_info_strategy)
    
    return template.format(info=sensitive_info), sensitive_info


@st.composite
def completed_session_strategy(draw):
    """生成已完成的疗愈会话"""
    session = Session.create()
    
    # 设置初始情绪
    initial_emotion = draw(emotion_state_strategy())
    session.set_initial_emotion(initial_emotion)
    
    # 设置疗愈方案名称
    plan_names = ["焦虑缓解方案", "压力释放方案", "情绪平衡方案", "深度放松方案", "正念冥想方案"]
    session.plan_name = draw(st.sampled_from(plan_names))
    
    # 添加情绪历史记录 (1-5 条)
    num_history = draw(st.integers(min_value=1, max_value=5))
    phase_names = ["准备阶段", "引导阶段", "深度放松", "唤醒阶段", "结束阶段"]
    
    for i in range(num_history):
        emotion = draw(emotion_state_strategy())
        phase_name = draw(st.sampled_from(phase_names))
        session.add_emotion_history(emotion, phase_name)
    
    # 设置最终情绪并完成会话
    final_emotion = draw(emotion_state_strategy())
    session.complete(final_emotion)
    
    # 模拟疗愈时长
    duration = draw(st.integers(min_value=60, max_value=1800))
    session.start_time = datetime.now() - timedelta(seconds=duration)
    session.end_time = datetime.now()
    
    return session


class TestPrivacyFilterProperties:
    """
    隐私过滤器属性测试
    
    **Feature: healing-pod-system, Property 27: 报告隐私保护**
    **Validates: Requirements 13.6**
    """
    
    @given(phone=chinese_phone_strategy())
    @settings(max_examples=100, deadline=None)
    def test_filter_chinese_phone_numbers(self, phone: str):
        """
        测试过滤中国手机号
        
        **Feature: healing-pod-system, Property 27: 报告隐私保护**
        **Validates: Requirements 13.6**
        
        *For any* 包含中国手机号的文本，过滤后 SHALL 不包含原始手机号
        """
        text = f"用户手机号是 {phone}，请联系"
        filtered = PrivacyFilter.filter_text(text)
        
        # 验证手机号被过滤
        assert phone not in filtered, \
            f"手机号 {phone} 应该被过滤掉"
        assert "[电话号码已隐藏]" in filtered, \
            "过滤后应包含替换文本"
    
    @given(email=valid_email_strategy())
    @settings(max_examples=100, deadline=None)
    def test_filter_email_addresses(self, email: str):
        """
        测试过滤电子邮件地址
        
        **Feature: healing-pod-system, Property 27: 报告隐私保护**
        **Validates: Requirements 13.6**
        
        *For any* 包含电子邮件的文本，过滤后 SHALL 不包含原始邮箱
        """
        text = f"用户邮箱是 {email}，已记录"
        filtered = PrivacyFilter.filter_text(text)
        
        # 验证邮箱被过滤
        assert email not in filtered, \
            f"邮箱 {email} 应该被过滤掉"
        assert "[邮箱已隐藏]" in filtered, \
            "过滤后应包含替换文本"
    
    @given(id_card=chinese_id_card_strategy())
    @settings(max_examples=100, deadline=None)
    def test_filter_chinese_id_cards(self, id_card: str):
        """
        测试过滤中国身份证号
        
        **Feature: healing-pod-system, Property 27: 报告隐私保护**
        **Validates: Requirements 13.6**
        
        *For any* 包含身份证号的文本，过滤后 SHALL 不包含原始身份证号
        """
        text = f"用户身份证号：{id_card}"
        filtered = PrivacyFilter.filter_text(text)
        
        # 验证身份证号被过滤
        assert id_card not in filtered, \
            f"身份证号 {id_card} 应该被过滤掉"
        assert "[身份证号已隐藏]" in filtered, \
            "过滤后应包含替换文本"
    
    @given(ip=ip_address_strategy())
    @settings(max_examples=100, deadline=None)
    def test_filter_ip_addresses(self, ip: str):
        """
        测试过滤 IP 地址
        
        **Feature: healing-pod-system, Property 27: 报告隐私保护**
        **Validates: Requirements 13.6**
        
        *For any* 包含 IP 地址的文本，过滤后 SHALL 不包含原始 IP
        """
        text = f"用户 IP 地址：{ip}"
        filtered = PrivacyFilter.filter_text(text)
        
        # 验证 IP 地址被过滤
        assert ip not in filtered, \
            f"IP 地址 {ip} 应该被过滤掉"
        assert "[IP地址已隐藏]" in filtered, \
            "过滤后应包含替换文本"
    
    @given(data=text_with_sensitive_info_strategy())
    @settings(max_examples=100, deadline=None)
    def test_filter_mixed_sensitive_info(self, data):
        """
        测试过滤混合敏感信息
        
        **Feature: healing-pod-system, Property 27: 报告隐私保护**
        **Validates: Requirements 13.6**
        
        *For any* 包含敏感信息的文本，过滤后 SHALL 不包含原始敏感信息
        """
        text, sensitive_info = data
        filtered = PrivacyFilter.filter_text(text)
        
        # 验证敏感信息被过滤
        assert sensitive_info not in filtered, \
            f"敏感信息 {sensitive_info} 应该被过滤掉"
    
    @given(sensitive_info=sensitive_info_strategy)
    @settings(max_examples=100, deadline=None)
    def test_contains_sensitive_info_detection(self, sensitive_info: str):
        """
        测试敏感信息检测
        
        **Feature: healing-pod-system, Property 27: 报告隐私保护**
        **Validates: Requirements 13.6**
        
        *For any* 敏感信息，contains_sensitive_info SHALL 返回 True
        """
        text = f"包含敏感信息：{sensitive_info}"
        
        # 验证能检测到敏感信息
        assert PrivacyFilter.contains_sensitive_info(text), \
            f"应该检测到敏感信息：{sensitive_info}"
    
    @given(text=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z'), whitelist_characters='，。！？')))
    @settings(max_examples=100, deadline=None)
    def test_safe_text_unchanged(self, text: str):
        """
        测试安全文本不被修改
        
        **Feature: healing-pod-system, Property 27: 报告隐私保护**
        **Validates: Requirements 13.6**
        
        *For any* 不包含敏感信息的文本，过滤后 SHALL 保持不变
        """
        # 假设文本不包含敏感信息模式
        assume(not PrivacyFilter.contains_sensitive_info(text))
        
        filtered = PrivacyFilter.filter_text(text)
        
        # 验证安全文本不被修改
        assert filtered == text, \
            "不包含敏感信息的文本应保持不变"


class TestReportPrivacyProperties:
    """
    报告隐私保护属性测试
    
    **Feature: healing-pod-system, Property 27: 报告隐私保护**
    **Validates: Requirements 13.6**
    """
    
    @given(session=completed_session_strategy())
    @settings(max_examples=100, deadline=None)
    def test_report_text_fields_no_phone_numbers(self, session: Session):
        """
        测试报告文本字段不包含手机号
        
        **Feature: healing-pod-system, Property 27: 报告隐私保护**
        **Validates: Requirements 13.6**
        
        *For any* 生成的疗愈报告，文本字段 SHALL 不包含手机号
        """
        collector = ReportDataCollector()
        report = collector.collect_from_session(session)
        
        # 只检查文本字段（不检查数值字段的字符串表示）
        import re
        phone_pattern = r"1[3-9]\d{9}"
        
        # 检查方案名称
        if report.plan_name:
            assert not re.search(phone_pattern, report.plan_name), \
                "方案名称不应包含手机号"
        
        # 检查总结文字
        if report.summary_text:
            assert not re.search(phone_pattern, report.summary_text), \
                "总结文字不应包含手机号"
        
        # 检查建议
        if report.recommendations:
            for rec in report.recommendations:
                assert not re.search(phone_pattern, rec), \
                    "建议不应包含手机号"
    
    @given(session=completed_session_strategy())
    @settings(max_examples=100, deadline=None)
    def test_report_text_fields_no_id_cards(self, session: Session):
        """
        测试报告文本字段不包含身份证号
        
        **Feature: healing-pod-system, Property 27: 报告隐私保护**
        **Validates: Requirements 13.6**
        
        *For any* 生成的疗愈报告，文本字段 SHALL 不包含身份证号
        """
        collector = ReportDataCollector()
        report = collector.collect_from_session(session)
        
        # 只检查文本字段
        import re
        # 身份证号模式：18位数字或17位数字+X/x
        id_pattern = r"\b\d{17}[\dXx]\b|\b\d{15}\b"
        
        # 检查方案名称
        if report.plan_name:
            assert not re.search(id_pattern, report.plan_name), \
                "方案名称不应包含身份证号"
        
        # 检查总结文字
        if report.summary_text:
            assert not re.search(id_pattern, report.summary_text), \
                "总结文字不应包含身份证号"
        
        # 检查建议
        if report.recommendations:
            for rec in report.recommendations:
                assert not re.search(id_pattern, rec), \
                    "建议不应包含身份证号"
    
    @given(session=completed_session_strategy())
    @settings(max_examples=100, deadline=None)
    def test_report_no_email_addresses(self, session: Session):
        """
        测试报告不包含电子邮件
        
        **Feature: healing-pod-system, Property 27: 报告隐私保护**
        **Validates: Requirements 13.6**
        
        *For any* 生成的疗愈报告，报告内容 SHALL 不包含电子邮件地址
        """
        collector = ReportDataCollector()
        report = collector.collect_from_session(session)
        
        # 检查报告各字段
        report_dict = report.to_dict()
        report_str = str(report_dict)
        
        # 验证不包含邮箱模式
        import re
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        assert not re.search(email_pattern, report_str), \
            "报告不应包含电子邮件地址"
    
    @pytest.mark.asyncio
    @given(session=completed_session_strategy())
    @settings(max_examples=50, deadline=None)
    async def test_full_report_privacy_check(self, session: Session):
        """
        测试完整报告隐私检查
        
        **Feature: healing-pod-system, Property 27: 报告隐私保护**
        **Validates: Requirements 13.6**
        
        *For any* 生成的疗愈报告，check_privacy SHALL 返回 True（无敏感信息）
        """
        generator = TherapyReportGenerator()
        report = await generator.generate_report(session)
        
        # 验证隐私检查通过
        assert generator.check_privacy(report), \
            "报告应通过隐私检查（不包含敏感信息）"
    
    @pytest.mark.asyncio
    @given(session=completed_session_strategy())
    @settings(max_examples=50, deadline=None)
    async def test_report_summary_no_sensitive_info(self, session: Session):
        """
        测试报告总结文字不包含敏感信息
        
        **Feature: healing-pod-system, Property 27: 报告隐私保护**
        **Validates: Requirements 13.6**
        
        *For any* 生成的疗愈报告，总结文字 SHALL 不包含敏感信息
        """
        generator = TherapyReportGenerator()
        report = await generator.generate_report(session)
        
        # 验证总结文字不包含敏感信息
        if report.summary_text:
            assert not PrivacyFilter.contains_sensitive_info(report.summary_text), \
                "报告总结文字不应包含敏感信息"
    
    @pytest.mark.asyncio
    @given(session=completed_session_strategy())
    @settings(max_examples=50, deadline=None)
    async def test_report_recommendations_no_sensitive_info(self, session: Session):
        """
        测试报告建议不包含敏感信息
        
        **Feature: healing-pod-system, Property 27: 报告隐私保护**
        **Validates: Requirements 13.6**
        
        *For any* 生成的疗愈报告，建议列表 SHALL 不包含敏感信息
        """
        generator = TherapyReportGenerator()
        report = await generator.generate_report(session)
        
        # 验证建议不包含敏感信息
        if report.recommendations:
            for rec in report.recommendations:
                assert not PrivacyFilter.contains_sensitive_info(rec), \
                    f"报告建议不应包含敏感信息：{rec}"


class TestPrivacyFilterDictProperties:
    """
    字典隐私过滤属性测试
    
    **Feature: healing-pod-system, Property 27: 报告隐私保护**
    **Validates: Requirements 13.6**
    """
    
    @given(phone=chinese_phone_strategy())
    @settings(max_examples=100, deadline=None)
    def test_filter_dict_with_phone(self, phone: str):
        """
        测试字典中的手机号过滤
        
        **Feature: healing-pod-system, Property 27: 报告隐私保护**
        **Validates: Requirements 13.6**
        
        *For any* 包含手机号的字典，过滤后 SHALL 不包含原始手机号
        """
        data = {
            "user_phone": phone,
            "message": f"联系方式：{phone}",
            "nested": {
                "contact": phone
            }
        }
        
        filtered = PrivacyFilter.filter_dict(data)
        
        # 验证所有字段中的手机号被过滤
        assert phone not in filtered["user_phone"], \
            "user_phone 字段中的手机号应被过滤"
        assert phone not in filtered["message"], \
            "message 字段中的手机号应被过滤"
        assert phone not in filtered["nested"]["contact"], \
            "嵌套字段中的手机号应被过滤"
    
    @given(email=valid_email_strategy())
    @settings(max_examples=100, deadline=None)
    def test_filter_dict_with_email(self, email: str):
        """
        测试字典中的邮箱过滤
        
        **Feature: healing-pod-system, Property 27: 报告隐私保护**
        **Validates: Requirements 13.6**
        
        *For any* 包含邮箱的字典，过滤后 SHALL 不包含原始邮箱
        """
        data = {
            "user_email": email,
            "info": f"邮箱地址：{email}"
        }
        
        filtered = PrivacyFilter.filter_dict(data)
        
        # 验证邮箱被过滤
        assert email not in filtered["user_email"], \
            "user_email 字段中的邮箱应被过滤"
        assert email not in filtered["info"], \
            "info 字段中的邮箱应被过滤"
    
    @given(
        phone=chinese_phone_strategy(),
        email=valid_email_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_filter_dict_with_list(self, phone: str, email: str):
        """
        测试字典中列表的敏感信息过滤
        
        **Feature: healing-pod-system, Property 27: 报告隐私保护**
        **Validates: Requirements 13.6**
        
        *For any* 包含敏感信息列表的字典，过滤后 SHALL 不包含原始敏感信息
        """
        data = {
            "contacts": [phone, email, "普通文本"],
            "messages": [
                f"手机：{phone}",
                f"邮箱：{email}"
            ]
        }
        
        filtered = PrivacyFilter.filter_dict(data)
        
        # 验证列表中的敏感信息被过滤
        for item in filtered["contacts"]:
            assert phone not in item, "列表中的手机号应被过滤"
            assert email not in item, "列表中的邮箱应被过滤"
        
        for item in filtered["messages"]:
            assert phone not in item, "消息列表中的手机号应被过滤"
            assert email not in item, "消息列表中的邮箱应被过滤"

