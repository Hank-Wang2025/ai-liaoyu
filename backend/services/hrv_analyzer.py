"""
HRV (心率变异性) 分析模块
Heart Rate Variability Analysis Module

实现 RMSSD、SDNN 计算和压力指数评估
Requirements: 3.2, 3.3
"""
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple
from loguru import logger

import numpy as np


@dataclass
class HRVMetrics:
    """HRV 指标数据"""
    rmssd: float  # RMSSD (ms) - 连续RR间期差值的均方根
    sdnn: float  # SDNN (ms) - RR间期的标准差
    mean_rr: float  # 平均RR间期 (ms)
    mean_hr: float  # 平均心率 (bpm)
    nn50: int  # 相邻RR间期差值>50ms的数量
    pnn50: float  # NN50占总数的百分比
    stress_index: float  # 压力指数 (0-100)
    timestamp: datetime = field(default_factory=datetime.now)
    sample_count: int = 0  # 用于计算的RR间期数量
    duration_seconds: float = 0.0  # 数据时间跨度
    
    def is_valid(self) -> bool:
        """检查指标是否有效"""
        return (
            self.rmssd >= 0 and
            self.sdnn >= 0 and
            self.mean_rr > 0 and
            0 <= self.stress_index <= 100 and
            self.sample_count >= 30  # 至少需要30个RR间期
        )


class HRVAnalyzer:
    """
    HRV 分析器
    
    计算心率变异性指标并评估压力水平
    """
    
    # 压力指数计算参数
    # 基于研究文献的参考值
    RMSSD_LOW_STRESS = 50.0  # RMSSD > 50ms 表示低压力
    RMSSD_HIGH_STRESS = 20.0  # RMSSD < 20ms 表示高压力
    
    SDNN_LOW_STRESS = 100.0  # SDNN > 100ms 表示低压力
    SDNN_HIGH_STRESS = 50.0  # SDNN < 50ms 表示高压力
    
    # RR间期有效范围 (ms)
    MIN_RR_INTERVAL = 300  # 最小RR间期 (~200 bpm)
    MAX_RR_INTERVAL = 2000  # 最大RR间期 (~30 bpm)
    
    # 最小数据要求
    MIN_RR_COUNT = 30  # 最少RR间期数量
    MIN_DURATION_SECONDS = 60  # 最少数据时长（秒）
    
    def __init__(
        self,
        filter_outliers: bool = True,
        outlier_threshold: float = 0.2
    ):
        """
        初始化 HRV 分析器
        
        Args:
            filter_outliers: 是否过滤异常值
            outlier_threshold: 异常值阈值（相对于中位数的偏差比例）
        """
        self.filter_outliers = filter_outliers
        self.outlier_threshold = outlier_threshold
    
    def preprocess_rr_intervals(
        self,
        rr_intervals: List[int]
    ) -> Tuple[List[int], int]:
        """
        预处理 RR 间期数据
        
        Args:
            rr_intervals: 原始RR间期列表 (ms)
            
        Returns:
            (处理后的RR间期列表, 移除的异常值数量)
        """
        if not rr_intervals:
            return [], 0
        
        # 过滤超出有效范围的值
        valid_rr = [
            rr for rr in rr_intervals
            if self.MIN_RR_INTERVAL <= rr <= self.MAX_RR_INTERVAL
        ]
        
        removed_count = len(rr_intervals) - len(valid_rr)
        
        if not valid_rr:
            return [], removed_count
        
        # 过滤异常值（基于中位数）
        if self.filter_outliers and len(valid_rr) > 5:
            median_rr = np.median(valid_rr)
            threshold = median_rr * self.outlier_threshold
            
            filtered_rr = [
                rr for rr in valid_rr
                if abs(rr - median_rr) <= threshold
            ]
            
            removed_count += len(valid_rr) - len(filtered_rr)
            valid_rr = filtered_rr
        
        return valid_rr, removed_count
    
    def calculate_rmssd(self, rr_intervals: List[int]) -> float:
        """
        计算 RMSSD (Root Mean Square of Successive Differences)
        
        RMSSD 是连续RR间期差值的均方根，反映短期心率变异性，
        主要受副交感神经（迷走神经）活动影响。
        
        Args:
            rr_intervals: RR间期列表 (ms)
            
        Returns:
            RMSSD 值 (ms)
        """
        if len(rr_intervals) < 2:
            return 0.0
        
        # 计算连续RR间期的差值
        rr_array = np.array(rr_intervals, dtype=np.float64)
        successive_diffs = np.diff(rr_array)
        
        # 计算差值的平方
        squared_diffs = successive_diffs ** 2
        
        # 计算均方根
        rmssd = np.sqrt(np.mean(squared_diffs))
        
        return float(rmssd)
    
    def calculate_sdnn(self, rr_intervals: List[int]) -> float:
        """
        计算 SDNN (Standard Deviation of NN intervals)
        
        SDNN 是所有RR间期的标准差，反映整体心率变异性，
        受交感神经和副交感神经共同影响。
        
        Args:
            rr_intervals: RR间期列表 (ms)
            
        Returns:
            SDNN 值 (ms)
        """
        if len(rr_intervals) < 2:
            return 0.0
        
        rr_array = np.array(rr_intervals, dtype=np.float64)
        sdnn = np.std(rr_array, ddof=1)  # 使用样本标准差
        
        return float(sdnn)
    
    def calculate_nn50_pnn50(
        self,
        rr_intervals: List[int]
    ) -> Tuple[int, float]:
        """
        计算 NN50 和 pNN50
        
        NN50: 相邻RR间期差值大于50ms的数量
        pNN50: NN50占总数的百分比
        
        Args:
            rr_intervals: RR间期列表 (ms)
            
        Returns:
            (NN50, pNN50)
        """
        if len(rr_intervals) < 2:
            return 0, 0.0
        
        rr_array = np.array(rr_intervals, dtype=np.float64)
        successive_diffs = np.abs(np.diff(rr_array))
        
        nn50 = int(np.sum(successive_diffs > 50))
        pnn50 = (nn50 / len(successive_diffs)) * 100
        
        return nn50, float(pnn50)
    
    def calculate_stress_index(
        self,
        rmssd: float,
        sdnn: float,
        mean_hr: Optional[float] = None
    ) -> float:
        """
        计算压力指数 (0-100)
        
        压力指数基于 RMSSD 和 SDNN 计算，值越高表示压力越大。
        
        计算方法:
        1. 将 RMSSD 和 SDNN 映射到 0-100 范围
        2. RMSSD 权重 0.6，SDNN 权重 0.4
        3. 可选：考虑心率因素
        
        Args:
            rmssd: RMSSD 值 (ms)
            sdnn: SDNN 值 (ms)
            mean_hr: 平均心率 (bpm)，可选
            
        Returns:
            压力指数 (0-100)，值越高压力越大
        """
        # 将 RMSSD 映射到压力分数 (RMSSD 越低，压力越高)
        if rmssd >= self.RMSSD_LOW_STRESS:
            rmssd_stress = 0.0
        elif rmssd <= self.RMSSD_HIGH_STRESS:
            rmssd_stress = 100.0
        else:
            # 线性插值
            rmssd_stress = 100.0 * (
                (self.RMSSD_LOW_STRESS - rmssd) /
                (self.RMSSD_LOW_STRESS - self.RMSSD_HIGH_STRESS)
            )
        
        # 将 SDNN 映射到压力分数 (SDNN 越低，压力越高)
        if sdnn >= self.SDNN_LOW_STRESS:
            sdnn_stress = 0.0
        elif sdnn <= self.SDNN_HIGH_STRESS:
            sdnn_stress = 100.0
        else:
            # 线性插值
            sdnn_stress = 100.0 * (
                (self.SDNN_LOW_STRESS - sdnn) /
                (self.SDNN_LOW_STRESS - self.SDNN_HIGH_STRESS)
            )
        
        # 加权平均
        stress_index = 0.6 * rmssd_stress + 0.4 * sdnn_stress
        
        # 考虑心率因素（可选）
        if mean_hr is not None:
            # 心率过高或过低都增加压力分数
            if mean_hr > 100:  # 心率过高
                hr_factor = min((mean_hr - 100) / 50, 1.0) * 10
                stress_index = min(stress_index + hr_factor, 100.0)
            elif mean_hr < 50:  # 心率过低
                hr_factor = min((50 - mean_hr) / 20, 1.0) * 5
                stress_index = min(stress_index + hr_factor, 100.0)
        
        # 确保在 0-100 范围内
        return max(0.0, min(100.0, stress_index))
    
    def analyze(
        self,
        rr_intervals: List[int],
        duration_seconds: Optional[float] = None
    ) -> Optional[HRVMetrics]:
        """
        分析 HRV 指标
        
        Args:
            rr_intervals: RR间期列表 (ms)
            duration_seconds: 数据时间跨度（秒），可选
            
        Returns:
            HRV 指标，数据不足时返回 None
        """
        # 预处理数据
        processed_rr, removed_count = self.preprocess_rr_intervals(rr_intervals)
        
        if removed_count > 0:
            logger.debug(f"Removed {removed_count} outlier RR intervals")
        
        # 检查数据是否足够
        if len(processed_rr) < self.MIN_RR_COUNT:
            logger.warning(
                f"Insufficient RR intervals: {len(processed_rr)} < {self.MIN_RR_COUNT}"
            )
            return None
        
        # 计算数据时长
        if duration_seconds is None:
            duration_seconds = sum(processed_rr) / 1000.0
        
        if duration_seconds < self.MIN_DURATION_SECONDS:
            logger.warning(
                f"Insufficient data duration: {duration_seconds:.1f}s < {self.MIN_DURATION_SECONDS}s"
            )
            return None
        
        # 计算各项指标
        rmssd = self.calculate_rmssd(processed_rr)
        sdnn = self.calculate_sdnn(processed_rr)
        nn50, pnn50 = self.calculate_nn50_pnn50(processed_rr)
        
        mean_rr = float(np.mean(processed_rr))
        mean_hr = 60000.0 / mean_rr  # 转换为 bpm
        
        stress_index = self.calculate_stress_index(rmssd, sdnn, mean_hr)
        
        metrics = HRVMetrics(
            rmssd=rmssd,
            sdnn=sdnn,
            mean_rr=mean_rr,
            mean_hr=mean_hr,
            nn50=nn50,
            pnn50=pnn50,
            stress_index=stress_index,
            sample_count=len(processed_rr),
            duration_seconds=duration_seconds
        )
        
        logger.info(
            f"HRV Analysis: RMSSD={rmssd:.1f}ms, SDNN={sdnn:.1f}ms, "
            f"Stress={stress_index:.1f}, HR={mean_hr:.1f}bpm"
        )
        
        return metrics
    
    def get_stress_level(self, stress_index: float) -> str:
        """
        获取压力等级描述
        
        Args:
            stress_index: 压力指数 (0-100)
            
        Returns:
            压力等级描述
        """
        if stress_index < 25:
            return "low"  # 低压力
        elif stress_index < 50:
            return "moderate"  # 中等压力
        elif stress_index < 75:
            return "high"  # 高压力
        else:
            return "very_high"  # 非常高压力
    
    def is_heart_rate_abnormal(
        self,
        heart_rate: float,
        low_threshold: float = 50,
        high_threshold: float = 120
    ) -> Tuple[bool, str]:
        """
        检查心率是否异常
        
        Args:
            heart_rate: 心率 (bpm)
            low_threshold: 低心率阈值
            high_threshold: 高心率阈值
            
        Returns:
            (是否异常, 异常类型描述)
        """
        if heart_rate < low_threshold:
            return True, "bradycardia"  # 心动过缓
        elif heart_rate > high_threshold:
            return True, "tachycardia"  # 心动过速
        else:
            return False, "normal"


@dataclass
class BioAnalysisResult:
    """生理信号分析结果"""
    stress_index: float  # 压力指数 (0-100)
    stress_level: str  # 压力等级 (low/moderate/high/very_high)
    hrv_metrics: Optional[HRVMetrics]  # HRV 详细指标
    heart_rate: float  # 当前心率 (bpm)
    heart_rate_status: str  # 心率状态 (normal/bradycardia/tachycardia)
    is_valid: bool  # 数据是否有效
    timestamp: datetime = field(default_factory=datetime.now)
    message: str = ""  # 附加信息
    
    @classmethod
    def insufficient_data(cls, message: str = "Insufficient data") -> 'BioAnalysisResult':
        """创建数据不足的结果"""
        return cls(
            stress_index=50.0,  # 默认中等压力
            stress_level="unknown",
            hrv_metrics=None,
            heart_rate=0.0,
            heart_rate_status="unknown",
            is_valid=False,
            message=message
        )
