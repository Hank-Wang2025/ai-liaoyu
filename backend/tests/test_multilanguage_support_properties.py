"""
属性测试：多语言支持

**Feature: healing-pod-system, Property 34: 多语言支持**
**Validates: Requirements 17.6**

验证用户界面支持中文和英文两种语言版本。
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Set

import pytest
from hypothesis import given, settings, strategies as st


# 定义支持的语言
SUPPORTED_LANGUAGES = ["zh", "en"]

# i18n 目录路径
I18N_DIR = Path(__file__).parent.parent.parent / "app" / "src" / "i18n" / "locales"


def parse_typescript_locale(file_path: Path) -> Dict[str, Any]:
    """
    解析 TypeScript 语言文件，提取翻译内容。
    简化解析：读取 export default 后的对象内容。
    """
    content = file_path.read_text(encoding="utf-8")
    
    # 移除 export default 和末尾的分号
    content = content.replace("export default", "").strip()
    if content.endswith(";"):
        content = content[:-1]
    
    # 将 TypeScript 对象转换为 JSON 格式
    # 处理单引号字符串
    import re
    
    # 替换单引号为双引号（但保留转义的单引号）
    # 首先处理转义的单引号
    content = content.replace("\\'", "__ESCAPED_QUOTE__")
    
    # 处理键名（不带引号的键）
    content = re.sub(r"(\s)(\w+)(\s*:)", r'\1"\2"\3', content)
    
    # 处理单引号字符串值
    content = re.sub(r"'([^']*)'", r'"\1"', content)
    
    # 恢复转义的单引号
    content = content.replace("__ESCAPED_QUOTE__", "'")
    
    # 移除尾随逗号
    content = re.sub(r",(\s*[}\]])", r"\1", content)
    
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # 如果 JSON 解析失败，返回空字典
        return {}


def get_all_keys(obj: Dict[str, Any], prefix: str = "") -> Set[str]:
    """
    递归获取嵌套字典中的所有键路径。
    
    例如：{"a": {"b": "value"}} -> {"a", "a.b"}
    """
    keys = set()
    for key, value in obj.items():
        full_key = f"{prefix}.{key}" if prefix else key
        keys.add(full_key)
        if isinstance(value, dict):
            keys.update(get_all_keys(value, full_key))
    return keys


def get_value_by_path(obj: Dict[str, Any], path: str) -> Any:
    """
    通过点分隔的路径获取嵌套字典中的值。
    """
    keys = path.split(".")
    current = obj
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current


def get_all_leaf_values(obj: Dict[str, Any], prefix: str = "") -> List[tuple]:
    """
    获取所有叶子节点的键值对。
    """
    results = []
    for key, value in obj.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            results.extend(get_all_leaf_values(value, full_key))
        else:
            results.append((full_key, value))
    return results


class TestMultilanguageSupport:
    """多语言支持属性测试"""
    
    @pytest.fixture(scope="class")
    def locale_files(self) -> Dict[str, Path]:
        """获取所有语言文件路径"""
        return {
            lang: I18N_DIR / f"{lang}.ts"
            for lang in SUPPORTED_LANGUAGES
        }
    
    @pytest.fixture(scope="class")
    def locale_data(self, locale_files: Dict[str, Path]) -> Dict[str, Dict[str, Any]]:
        """解析所有语言文件内容"""
        return {
            lang: parse_typescript_locale(path)
            for lang, path in locale_files.items()
        }
    
    def test_both_languages_exist(self, locale_files: Dict[str, Path]):
        """
        **Feature: healing-pod-system, Property 34: 多语言支持**
        **Validates: Requirements 17.6**
        
        验证中文和英文两种语言文件都存在。
        """
        for lang, path in locale_files.items():
            assert path.exists(), f"语言文件 {lang}.ts 不存在: {path}"
    
    def test_locale_files_are_parseable(self, locale_files: Dict[str, Path]):
        """
        **Feature: healing-pod-system, Property 34: 多语言支持**
        **Validates: Requirements 17.6**
        
        验证所有语言文件可以被正确解析。
        """
        for lang, path in locale_files.items():
            data = parse_typescript_locale(path)
            assert data, f"语言文件 {lang}.ts 解析失败或为空"
            assert isinstance(data, dict), f"语言文件 {lang}.ts 应该是一个对象"
    
    def test_zh_and_en_have_same_keys(self, locale_data: Dict[str, Dict[str, Any]]):
        """
        **Feature: healing-pod-system, Property 34: 多语言支持**
        **Validates: Requirements 17.6**
        
        验证中文和英文语言文件具有相同的翻译键。
        """
        zh_keys = get_all_keys(locale_data["zh"])
        en_keys = get_all_keys(locale_data["en"])
        
        # 检查中文有但英文没有的键
        zh_only = zh_keys - en_keys
        assert not zh_only, f"以下键只在中文中存在: {zh_only}"
        
        # 检查英文有但中文没有的键
        en_only = en_keys - zh_keys
        assert not en_only, f"以下键只在英文中存在: {en_only}"
    
    def test_all_translations_are_non_empty_strings(self, locale_data: Dict[str, Dict[str, Any]]):
        """
        **Feature: healing-pod-system, Property 34: 多语言支持**
        **Validates: Requirements 17.6**
        
        验证所有翻译值都是非空字符串。
        """
        for lang, data in locale_data.items():
            leaf_values = get_all_leaf_values(data)
            for key, value in leaf_values:
                assert isinstance(value, str), f"[{lang}] 键 '{key}' 的值应该是字符串，实际是 {type(value)}"
                assert value.strip(), f"[{lang}] 键 '{key}' 的翻译值为空"
    
    def test_supported_languages_count(self, locale_data: Dict[str, Dict[str, Any]]):
        """
        **Feature: healing-pod-system, Property 34: 多语言支持**
        **Validates: Requirements 17.6**
        
        验证系统支持至少中文和英文两种语言。
        """
        assert len(locale_data) >= 2, "系统应该支持至少两种语言"
        assert "zh" in locale_data, "系统应该支持中文"
        assert "en" in locale_data, "系统应该支持英文"
    
    def test_language_selector_translations_exist(self, locale_data: Dict[str, Dict[str, Any]]):
        """
        **Feature: healing-pod-system, Property 34: 多语言支持**
        **Validates: Requirements 17.6**
        
        验证语言选择器的翻译存在。
        """
        for lang, data in locale_data.items():
            assert "language" in data, f"[{lang}] 缺少 'language' 翻译组"
            assert "zh" in data["language"], f"[{lang}] 缺少中文语言名称翻译"
            assert "en" in data["language"], f"[{lang}] 缺少英文语言名称翻译"


class TestMultilanguagePropertyBased:
    """基于属性的多语言测试"""
    
    @pytest.fixture(scope="class")
    def locale_data(self) -> Dict[str, Dict[str, Any]]:
        """解析所有语言文件内容"""
        return {
            lang: parse_typescript_locale(I18N_DIR / f"{lang}.ts")
            for lang in SUPPORTED_LANGUAGES
        }
    
    @given(lang=st.sampled_from(SUPPORTED_LANGUAGES))
    @settings(max_examples=100)
    def test_any_language_has_required_sections(self, lang: str):
        """
        **Feature: healing-pod-system, Property 34: 多语言支持**
        **Validates: Requirements 17.6**
        
        *For any* 支持的语言，该语言文件 SHALL 包含所有必需的翻译组。
        """
        locale_path = I18N_DIR / f"{lang}.ts"
        data = parse_typescript_locale(locale_path)
        
        # 必需的顶级翻译组
        required_sections = ["common", "welcome", "assessment", "therapy", "report", "emotions", "language", "admin"]
        
        for section in required_sections:
            assert section in data, f"[{lang}] 缺少必需的翻译组: {section}"
    
    @given(lang=st.sampled_from(SUPPORTED_LANGUAGES))
    @settings(max_examples=100)
    def test_any_language_common_section_complete(self, lang: str):
        """
        **Feature: healing-pod-system, Property 34: 多语言支持**
        **Validates: Requirements 17.6**
        
        *For any* 支持的语言，common 翻译组 SHALL 包含所有通用 UI 文本。
        """
        locale_path = I18N_DIR / f"{lang}.ts"
        data = parse_typescript_locale(locale_path)
        
        # common 组必需的键
        required_common_keys = [
            "appName", "loading", "confirm", "cancel", "back", "next",
            "start", "pause", "resume", "skip", "end", "save", "export"
        ]
        
        assert "common" in data, f"[{lang}] 缺少 common 翻译组"
        
        for key in required_common_keys:
            assert key in data["common"], f"[{lang}] common 组缺少键: {key}"
            assert data["common"][key], f"[{lang}] common.{key} 翻译值为空"
    
    @given(lang=st.sampled_from(SUPPORTED_LANGUAGES))
    @settings(max_examples=100)
    def test_any_language_emotions_complete(self, lang: str):
        """
        **Feature: healing-pod-system, Property 34: 多语言支持**
        **Validates: Requirements 17.6**
        
        *For any* 支持的语言，emotions 翻译组 SHALL 包含所有情绪类型的翻译。
        """
        locale_path = I18N_DIR / f"{lang}.ts"
        data = parse_typescript_locale(locale_path)
        
        # 系统支持的情绪类型
        emotion_types = [
            "happy", "sad", "angry", "anxious", "tired",
            "fearful", "surprised", "disgusted", "neutral"
        ]
        
        assert "emotions" in data, f"[{lang}] 缺少 emotions 翻译组"
        
        for emotion in emotion_types:
            assert emotion in data["emotions"], f"[{lang}] emotions 组缺少情绪类型: {emotion}"
            assert data["emotions"][emotion], f"[{lang}] emotions.{emotion} 翻译值为空"


class TestMultilanguageConsistency:
    """多语言一致性测试"""
    
    @pytest.fixture(scope="class")
    def zh_data(self) -> Dict[str, Any]:
        """获取中文翻译数据"""
        return parse_typescript_locale(I18N_DIR / "zh.ts")
    
    @pytest.fixture(scope="class")
    def en_data(self) -> Dict[str, Any]:
        """获取英文翻译数据"""
        return parse_typescript_locale(I18N_DIR / "en.ts")
    
    @given(section=st.sampled_from(["common", "welcome", "assessment", "therapy", "report", "emotions", "admin"]))
    @settings(max_examples=100)
    def test_section_key_consistency(self, section: str, zh_data: Dict[str, Any], en_data: Dict[str, Any]):
        """
        **Feature: healing-pod-system, Property 34: 多语言支持**
        **Validates: Requirements 17.6**
        
        *For any* 翻译组，中文和英文版本 SHALL 具有相同的键结构。
        """
        if section not in zh_data or section not in en_data:
            pytest.skip(f"翻译组 {section} 不存在")
        
        zh_keys = get_all_keys(zh_data[section])
        en_keys = get_all_keys(en_data[section])
        
        assert zh_keys == en_keys, f"翻译组 {section} 的键结构不一致"
