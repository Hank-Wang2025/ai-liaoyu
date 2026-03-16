"""
疗愈方案管理器
Therapy Plan Manager - handles plan loading, matching, and selection
"""
from typing import List, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

from models.emotion import EmotionCategory, EmotionState
from models.therapy import (
    TherapyPlan,
    TherapyStyle,
    TherapyIntensity,
    TherapyPlanParser
)


@dataclass
class UserPreferences:
    """用户偏好设置"""
    preferred_style: Optional[TherapyStyle] = None  # 偏好风格
    preferred_intensity: Optional[TherapyIntensity] = None  # 偏好强度
    history_plan_ids: List[str] = field(default_factory=list)  # 历史使用的方案ID
    effectiveness_scores: Dict[str, float] = field(default_factory=dict)  # 方案效果评分


@dataclass
class MatchResult:
    """方案匹配结果"""
    plan: TherapyPlan
    score: float  # 匹配分数 0-1
    match_reasons: List[str]  # 匹配原因


class PlanManager:
    """疗愈方案管理器"""
    
    DEFAULT_PLANS_DIR = "content/plans"
    
    def __init__(self, plans_dir: str = None):
        """
        初始化方案管理器
        
        Args:
            plans_dir: 方案配置文件目录路径
        """
        self.plans_dir = plans_dir or self.DEFAULT_PLANS_DIR
        self.plans: List[TherapyPlan] = []
        self.default_plan: Optional[TherapyPlan] = None
        self._load_plans()
    
    def _load_plans(self) -> None:
        """从目录加载所有疗愈方案"""
        self.plans = TherapyPlanParser.load_from_directory(self.plans_dir)
        
        # 设置默认方案（选择第一个低强度方案或第一个方案）
        if self.plans:
            low_intensity_plans = [
                p for p in self.plans 
                if p.intensity == TherapyIntensity.LOW
            ]
            self.default_plan = low_intensity_plans[0] if low_intensity_plans else self.plans[0]
    
    def reload_plans(self) -> int:
        """重新加载方案，返回加载的方案数量"""
        self._load_plans()
        return len(self.plans)
    
    def get_all_plans(self) -> List[TherapyPlan]:
        """获取所有方案"""
        return self.plans.copy()
    
    def get_plan_by_id(self, plan_id: str) -> Optional[TherapyPlan]:
        """根据ID获取方案"""
        for plan in self.plans:
            if plan.id == plan_id:
                return plan
        return None

    def _filter_by_emotion(
        self, 
        plans: List[TherapyPlan], 
        emotion: EmotionState
    ) -> List[TherapyPlan]:
        """根据情绪类别筛选方案"""
        return [
            p for p in plans 
            if emotion.category in p.target_emotions
        ]
    
    def _filter_by_intensity(
        self, 
        plans: List[TherapyPlan], 
        emotion: EmotionState
    ) -> List[TherapyPlan]:
        """
        根据情绪强度筛选方案
        
        强度映射:
        - 情绪强度 > 0.7 -> 高强度方案
        - 情绪强度 0.4-0.7 -> 中等强度方案
        - 情绪强度 < 0.4 -> 低强度方案
        """
        if emotion.intensity > 0.7:
            target_intensity = TherapyIntensity.HIGH
        elif emotion.intensity > 0.4:
            target_intensity = TherapyIntensity.MEDIUM
        else:
            target_intensity = TherapyIntensity.LOW
        
        filtered = [p for p in plans if p.intensity == target_intensity]
        
        # 如果没有匹配的强度，返回所有方案
        return filtered if filtered else plans
    
    def _filter_by_style(
        self, 
        plans: List[TherapyPlan], 
        style: Optional[TherapyStyle]
    ) -> List[TherapyPlan]:
        """根据风格筛选方案"""
        if style is None:
            return plans
        
        filtered = [p for p in plans if p.style == style]
        return filtered if filtered else plans
    
    def _calculate_match_score(
        self,
        plan: TherapyPlan,
        emotion: EmotionState,
        preferences: Optional[UserPreferences] = None
    ) -> tuple[float, List[str]]:
        """
        计算方案匹配分数
        
        Returns:
            (score, reasons): 匹配分数和匹配原因列表
        """
        score = 0.0
        reasons = []
        
        # 情绪类别匹配 (权重: 0.4)
        if emotion.category in plan.target_emotions:
            score += 0.4
            reasons.append(f"目标情绪匹配: {emotion.category.value}")
        
        # 情绪强度匹配 (权重: 0.3)
        intensity_match = self._get_intensity_match_score(plan.intensity, emotion.intensity)
        score += 0.3 * intensity_match
        if intensity_match > 0.5:
            reasons.append(f"强度匹配: {plan.intensity.value}")
        
        # 用户偏好匹配 (权重: 0.2)
        if preferences:
            pref_score, pref_reasons = self._calculate_preference_score(plan, preferences)
            score += 0.2 * pref_score
            reasons.extend(pref_reasons)
        else:
            score += 0.1  # 无偏好时给予基础分
        
        # 历史效果加成 (权重: 0.1)
        if preferences and plan.id in preferences.effectiveness_scores:
            effectiveness = preferences.effectiveness_scores[plan.id]
            score += 0.1 * effectiveness
            if effectiveness > 0.7:
                reasons.append("历史效果良好")
        
        return min(score, 1.0), reasons
    
    def _get_intensity_match_score(
        self, 
        plan_intensity: TherapyIntensity, 
        emotion_intensity: float
    ) -> float:
        """计算强度匹配分数"""
        if emotion_intensity > 0.7:
            target = TherapyIntensity.HIGH
        elif emotion_intensity > 0.4:
            target = TherapyIntensity.MEDIUM
        else:
            target = TherapyIntensity.LOW
        
        if plan_intensity == target:
            return 1.0
        
        # 相邻强度给予部分分数
        intensity_order = [TherapyIntensity.LOW, TherapyIntensity.MEDIUM, TherapyIntensity.HIGH]
        plan_idx = intensity_order.index(plan_intensity)
        target_idx = intensity_order.index(target)
        
        if abs(plan_idx - target_idx) == 1:
            return 0.5
        return 0.2
    
    def _calculate_preference_score(
        self,
        plan: TherapyPlan,
        preferences: UserPreferences
    ) -> tuple[float, List[str]]:
        """计算用户偏好匹配分数"""
        score = 0.0
        reasons = []
        
        # 风格偏好
        if preferences.preferred_style and plan.style == preferences.preferred_style:
            score += 0.5
            reasons.append(f"符合偏好风格: {plan.style.value}")
        
        # 强度偏好
        if preferences.preferred_intensity and plan.intensity == preferences.preferred_intensity:
            score += 0.5
            reasons.append(f"符合偏好强度: {plan.intensity.value}")
        
        return score, reasons

    def match(
        self,
        emotion: EmotionState,
        style: Optional[TherapyStyle] = None,
        preferences: Optional[UserPreferences] = None
    ) -> TherapyPlan:
        """
        根据情绪状态匹配最合适的疗愈方案
        
        匹配逻辑:
        1. 根据主要情绪类别筛选候选方案
        2. 根据情绪强度选择方案强度
        3. 根据用户偏好选择风格（中式/现代）
        4. 计算综合匹配分数，返回最佳方案
        
        Args:
            emotion: 用户当前情绪状态
            style: 指定的疗愈风格（可选）
            preferences: 用户偏好设置（可选）
        
        Returns:
            最匹配的疗愈方案
        """
        if not self.plans:
            raise ValueError("No therapy plans available")
        
        # 第一步：根据情绪类别筛选
        candidates = self._filter_by_emotion(self.plans, emotion)
        
        # 如果没有匹配的情绪类别，使用所有方案
        if not candidates:
            candidates = self.plans.copy()
        
        # 第二步：根据情绪强度筛选
        candidates = self._filter_by_intensity(candidates, emotion)
        
        # 第三步：根据风格筛选
        effective_style = style
        if effective_style is None and preferences and preferences.preferred_style:
            effective_style = preferences.preferred_style
        candidates = self._filter_by_style(candidates, effective_style)
        
        # 第四步：计算匹配分数并排序
        scored_plans = []
        for plan in candidates:
            score, reasons = self._calculate_match_score(plan, emotion, preferences)
            scored_plans.append(MatchResult(plan=plan, score=score, match_reasons=reasons))
        
        # 按分数降序排序
        scored_plans.sort(key=lambda x: x.score, reverse=True)
        
        # 返回最佳匹配
        return scored_plans[0].plan if scored_plans else self.default_plan
    
    def match_with_details(
        self,
        emotion: EmotionState,
        style: Optional[TherapyStyle] = None,
        preferences: Optional[UserPreferences] = None,
        top_n: int = 3
    ) -> List[MatchResult]:
        """
        匹配方案并返回详细结果
        
        Args:
            emotion: 用户当前情绪状态
            style: 指定的疗愈风格（可选）
            preferences: 用户偏好设置（可选）
            top_n: 返回前N个匹配结果
        
        Returns:
            匹配结果列表，按分数降序排列
        """
        if not self.plans:
            return []
        
        # 筛选候选方案
        candidates = self._filter_by_emotion(self.plans, emotion)
        if not candidates:
            candidates = self.plans.copy()
        
        candidates = self._filter_by_intensity(candidates, emotion)
        
        effective_style = style
        if effective_style is None and preferences and preferences.preferred_style:
            effective_style = preferences.preferred_style
        candidates = self._filter_by_style(candidates, effective_style)
        
        # 计算所有方案的匹配分数
        results = []
        for plan in candidates:
            score, reasons = self._calculate_match_score(plan, emotion, preferences)
            results.append(MatchResult(plan=plan, score=score, match_reasons=reasons))
        
        # 排序并返回前N个
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_n]
    
    def get_plans_by_emotion(self, emotion_category: EmotionCategory) -> List[TherapyPlan]:
        """获取针对特定情绪的所有方案"""
        return [p for p in self.plans if emotion_category in p.target_emotions]
    
    def get_plans_by_style(self, style: TherapyStyle) -> List[TherapyPlan]:
        """获取特定风格的所有方案"""
        return [p for p in self.plans if p.style == style]
    
    def get_plans_by_intensity(self, intensity: TherapyIntensity) -> List[TherapyPlan]:
        """获取特定强度的所有方案"""
        return [p for p in self.plans if p.intensity == intensity]


class TherapyPlanSelector:
    """
    疗愈方案选择器
    
    处理用户手动选择和自动匹配的优先级逻辑
    确保用户选择始终覆盖自动匹配结果
    """
    
    def __init__(self, plan_manager: PlanManager):
        """
        初始化选择器
        
        Args:
            plan_manager: 方案管理器实例
        """
        self.plan_manager = plan_manager
        self._user_selected_plan_id: Optional[str] = None
        self._auto_matched_plan: Optional[TherapyPlan] = None
    
    @property
    def has_user_selection(self) -> bool:
        """是否有用户手动选择的方案"""
        return self._user_selected_plan_id is not None
    
    @property
    def user_selected_plan_id(self) -> Optional[str]:
        """获取用户选择的方案ID"""
        return self._user_selected_plan_id
    
    def select_plan(self, plan_id: str) -> Optional[TherapyPlan]:
        """
        用户手动选择方案
        
        Args:
            plan_id: 方案ID
        
        Returns:
            选择的方案，如果ID无效则返回None
        """
        plan = self.plan_manager.get_plan_by_id(plan_id)
        if plan:
            self._user_selected_plan_id = plan_id
            return plan
        return None
    
    def clear_selection(self) -> None:
        """清除用户选择，恢复自动匹配"""
        self._user_selected_plan_id = None
    
    def get_effective_plan(
        self,
        emotion: EmotionState,
        style: Optional[TherapyStyle] = None,
        preferences: Optional[UserPreferences] = None
    ) -> TherapyPlan:
        """
        获取有效的疗愈方案
        
        优先级: 用户手动选择 > 自动匹配
        
        Args:
            emotion: 用户当前情绪状态
            style: 指定的疗愈风格（可选）
            preferences: 用户偏好设置（可选）
        
        Returns:
            有效的疗愈方案（用户选择或自动匹配）
        """
        # 优先返回用户手动选择的方案
        if self._user_selected_plan_id:
            user_plan = self.plan_manager.get_plan_by_id(self._user_selected_plan_id)
            if user_plan:
                return user_plan
            # 如果用户选择的方案不存在，清除选择
            self._user_selected_plan_id = None
        
        # 自动匹配方案
        self._auto_matched_plan = self.plan_manager.match(emotion, style, preferences)
        return self._auto_matched_plan
    
    def get_selection_info(self) -> Dict[str, Any]:
        """
        获取当前选择信息
        
        Returns:
            包含选择状态的字典
        """
        info = {
            "has_user_selection": self.has_user_selection,
            "user_selected_plan_id": self._user_selected_plan_id,
            "auto_matched_plan_id": self._auto_matched_plan.id if self._auto_matched_plan else None
        }
        
        if self._user_selected_plan_id:
            plan = self.plan_manager.get_plan_by_id(self._user_selected_plan_id)
            if plan:
                info["effective_plan"] = {
                    "id": plan.id,
                    "name": plan.name,
                    "source": "user_selection"
                }
        elif self._auto_matched_plan:
            info["effective_plan"] = {
                "id": self._auto_matched_plan.id,
                "name": self._auto_matched_plan.name,
                "source": "auto_match"
            }
        
        return info
    
    def get_available_plans_for_selection(
        self,
        emotion: Optional[EmotionState] = None
    ) -> List[Dict[str, Any]]:
        """
        获取可供用户选择的方案列表
        
        Args:
            emotion: 当前情绪状态（可选，用于标记推荐方案）
        
        Returns:
            方案信息列表
        """
        plans = self.plan_manager.get_all_plans()
        result = []
        
        # 如果有情绪状态，计算推荐分数
        recommended_ids = set()
        if emotion:
            matches = self.plan_manager.match_with_details(emotion, top_n=3)
            recommended_ids = {m.plan.id for m in matches}
        
        for plan in plans:
            plan_info = {
                "id": plan.id,
                "name": plan.name,
                "description": plan.description,
                "style": plan.style.value,
                "intensity": plan.intensity.value,
                "duration": plan.duration,
                "target_emotions": [e.value for e in plan.target_emotions],
                "is_recommended": plan.id in recommended_ids,
                "is_selected": plan.id == self._user_selected_plan_id
            }
            result.append(plan_info)
        
        # 推荐的方案排在前面
        result.sort(key=lambda x: (not x["is_recommended"], x["name"]))
        
        return result
