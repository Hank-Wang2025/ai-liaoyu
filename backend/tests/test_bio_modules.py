"""
生理信号模块测试
Bio Signal Module Tests

测试 BLE 心率接收和 HRV 分析功能
Requirements: 3.1, 3.2, 3.3
"""
import os
import sys
from datetime import datetime, timedelta

import pytest
import numpy as np

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ble_heart_rate import (
    HeartRateReading,
    HeartRateBuffer,
    MockBLEHeartRateReceiver,
    BLEAK_AVAILABLE
)
from services.hrv_analyzer import (
    HRVAnalyzer,
    HRVMetrics,
    BioAnalysisResult
)


class TestHeartRateReading:
    """心率读数测试"""
    
    def test_reading_creation(self):
        """测试心率读数创建"""
        reading = HeartRateReading(
            bpm=72,
            rr_intervals=[833, 845, 820],
            sensor_contact=True
        )
        assert reading.bpm == 72
        assert len(reading.rr_intervals) == 3
        assert reading.sensor_contact is True
        assert reading.timestamp is not None
    
    def test_reading_with_energy(self):
        """测试带能量消耗的心率读数"""
        reading = HeartRateReading(
            bpm=85,
            rr_intervals=[706],
            energy_expended=150,
            sensor_contact=True
        )
        assert reading.energy_expended == 150


class TestHeartRateBuffer:
    """心率数据缓冲区测试"""
    
    def test_buffer_creation(self):
        """测试缓冲区创建"""
        buffer = HeartRateBuffer()
        assert len(buffer.readings) == 0
        assert len(buffer.rr_intervals) == 0
    
    def test_add_reading(self):
        """测试添加读数"""
        buffer = HeartRateBuffer()
        reading = HeartRateReading(
            bpm=70,
            rr_intervals=[857, 850]
        )
        buffer.add_reading(reading)
        
        assert len(buffer.readings) == 1
        assert len(buffer.rr_intervals) == 2
    
    def test_get_recent_bpm(self):
        """测试获取最近心率"""
        buffer = HeartRateBuffer()
        for bpm in [70, 72, 75, 73, 71]:
            buffer.add_reading(HeartRateReading(bpm=bpm, rr_intervals=[]))
        
        recent = buffer.get_recent_bpm(3)
        assert len(recent) == 3
        assert recent == [75, 73, 71]
    
    def test_get_rr_intervals(self):
        """测试获取RR间期"""
        buffer = HeartRateBuffer()
        buffer.add_reading(HeartRateReading(bpm=70, rr_intervals=[857, 850]))
        buffer.add_reading(HeartRateReading(bpm=72, rr_intervals=[833]))
        
        intervals = buffer.get_rr_intervals()
        assert len(intervals) == 3
        assert intervals == [857, 850, 833]
    
    def test_get_rr_intervals_min_count(self):
        """测试获取RR间期 - 最小数量要求"""
        buffer = HeartRateBuffer()
        buffer.add_reading(HeartRateReading(bpm=70, rr_intervals=[857]))
        
        # 要求至少5个，但只有1个
        intervals = buffer.get_rr_intervals(min_count=5)
        assert len(intervals) == 0
    
    def test_clear_buffer(self):
        """测试清空缓冲区"""
        buffer = HeartRateBuffer()
        buffer.add_reading(HeartRateReading(bpm=70, rr_intervals=[857]))
        buffer.clear()
        
        assert len(buffer.readings) == 0
        assert len(buffer.rr_intervals) == 0


class TestHRVAnalyzer:
    """HRV 分析器测试"""
    
    def test_analyzer_creation(self):
        """测试分析器创建"""
        analyzer = HRVAnalyzer()
        assert analyzer.filter_outliers is True
        assert analyzer.outlier_threshold == 0.2
    
    def test_preprocess_rr_intervals_valid(self):
        """测试RR间期预处理 - 有效数据"""
        analyzer = HRVAnalyzer()
        rr_intervals = [800, 850, 820, 830, 810]
        processed, removed = analyzer.preprocess_rr_intervals(rr_intervals)
        
        assert len(processed) == 5
        assert removed == 0
    
    def test_preprocess_rr_intervals_outliers(self):
        """测试RR间期预处理 - 过滤异常值"""
        analyzer = HRVAnalyzer()
        # 包含一个明显的异常值
        rr_intervals = [800, 850, 820, 830, 810, 200, 2500]
        processed, removed = analyzer.preprocess_rr_intervals(rr_intervals)
        
        assert removed > 0
        assert 200 not in processed
        assert 2500 not in processed
    
    def test_calculate_rmssd(self):
        """测试 RMSSD 计算"""
        analyzer = HRVAnalyzer()
        # 使用已知数据验证计算
        rr_intervals = [800, 810, 790, 820, 800]
        rmssd = analyzer.calculate_rmssd(rr_intervals)
        
        # 手动计算: diffs = [10, -20, 30, -20]
        # squared = [100, 400, 900, 400]
        # mean = 450, sqrt = ~21.2
        assert 20 < rmssd < 25
    
    def test_calculate_rmssd_insufficient_data(self):
        """测试 RMSSD 计算 - 数据不足"""
        analyzer = HRVAnalyzer()
        rmssd = analyzer.calculate_rmssd([800])
        assert rmssd == 0.0
    
    def test_calculate_sdnn(self):
        """测试 SDNN 计算"""
        analyzer = HRVAnalyzer()
        rr_intervals = [800, 850, 750, 900, 700]
        sdnn = analyzer.calculate_sdnn(rr_intervals)
        
        # SDNN 应该是正数
        assert sdnn > 0
        # 这组数据变异较大，SDNN 应该较高
        assert sdnn > 50
    
    def test_calculate_sdnn_insufficient_data(self):
        """测试 SDNN 计算 - 数据不足"""
        analyzer = HRVAnalyzer()
        sdnn = analyzer.calculate_sdnn([800])
        assert sdnn == 0.0
    
    def test_calculate_nn50_pnn50(self):
        """测试 NN50 和 pNN50 计算"""
        analyzer = HRVAnalyzer()
        # 设计数据使得有明确的 NN50
        rr_intervals = [800, 860, 800, 870, 800]  # diffs: 60, -60, 70, -70
        nn50, pnn50 = analyzer.calculate_nn50_pnn50(rr_intervals)
        
        assert nn50 == 4  # 所有差值都 > 50
        assert pnn50 == 100.0
    
    def test_calculate_stress_index_low(self):
        """测试压力指数计算 - 低压力"""
        analyzer = HRVAnalyzer()
        # 高 RMSSD 和 SDNN 表示低压力
        stress = analyzer.calculate_stress_index(rmssd=60.0, sdnn=120.0)
        assert stress < 25
    
    def test_calculate_stress_index_high(self):
        """测试压力指数计算 - 高压力"""
        analyzer = HRVAnalyzer()
        # 低 RMSSD 和 SDNN 表示高压力
        stress = analyzer.calculate_stress_index(rmssd=15.0, sdnn=40.0)
        assert stress > 75
    
    def test_calculate_stress_index_range(self):
        """测试压力指数范围约束 (Property 8)"""
        analyzer = HRVAnalyzer()
        
        # 测试各种输入组合
        test_cases = [
            (10.0, 30.0),   # 极低 HRV
            (30.0, 70.0),   # 中等 HRV
            (60.0, 120.0),  # 高 HRV
            (100.0, 200.0), # 极高 HRV
        ]
        
        for rmssd, sdnn in test_cases:
            stress = analyzer.calculate_stress_index(rmssd, sdnn)
            assert 0 <= stress <= 100, f"Stress index {stress} out of range for RMSSD={rmssd}, SDNN={sdnn}"
    
    def test_analyze_valid_data(self):
        """测试完整 HRV 分析 - 有效数据"""
        analyzer = HRVAnalyzer()
        
        # 生成足够的模拟数据（至少60秒）
        np.random.seed(42)
        base_rr = 800  # 约75 bpm
        rr_intervals = [
            int(base_rr + np.random.normal(0, 30))
            for _ in range(100)
        ]
        
        metrics = analyzer.analyze(rr_intervals, duration_seconds=80)
        
        assert metrics is not None
        assert metrics.is_valid()
        assert metrics.rmssd > 0
        assert metrics.sdnn > 0
        assert 0 <= metrics.stress_index <= 100
        assert metrics.mean_hr > 0
    
    def test_analyze_insufficient_data(self):
        """测试完整 HRV 分析 - 数据不足"""
        analyzer = HRVAnalyzer()
        
        # 只有10个数据点
        rr_intervals = [800, 810, 790, 820, 800, 815, 795, 825, 805, 810]
        metrics = analyzer.analyze(rr_intervals, duration_seconds=10)
        
        assert metrics is None
    
    def test_get_stress_level(self):
        """测试压力等级获取"""
        analyzer = HRVAnalyzer()
        
        assert analyzer.get_stress_level(10) == "low"
        assert analyzer.get_stress_level(35) == "moderate"
        assert analyzer.get_stress_level(60) == "high"
        assert analyzer.get_stress_level(85) == "very_high"
    
    def test_is_heart_rate_abnormal(self):
        """测试心率异常检测"""
        analyzer = HRVAnalyzer()
        
        # 正常心率
        is_abnormal, status = analyzer.is_heart_rate_abnormal(70)
        assert not is_abnormal
        assert status == "normal"
        
        # 心动过缓
        is_abnormal, status = analyzer.is_heart_rate_abnormal(45)
        assert is_abnormal
        assert status == "bradycardia"
        
        # 心动过速
        is_abnormal, status = analyzer.is_heart_rate_abnormal(130)
        assert is_abnormal
        assert status == "tachycardia"


class TestHRVMetrics:
    """HRV 指标数据测试"""
    
    def test_metrics_creation(self):
        """测试指标创建"""
        metrics = HRVMetrics(
            rmssd=35.0,
            sdnn=80.0,
            mean_rr=800.0,
            mean_hr=75.0,
            nn50=20,
            pnn50=25.0,
            stress_index=45.0,
            sample_count=100,
            duration_seconds=80.0
        )
        
        assert metrics.rmssd == 35.0
        assert metrics.sdnn == 80.0
        assert metrics.stress_index == 45.0
    
    def test_metrics_validity(self):
        """测试指标有效性检查"""
        # 有效指标
        valid_metrics = HRVMetrics(
            rmssd=35.0,
            sdnn=80.0,
            mean_rr=800.0,
            mean_hr=75.0,
            nn50=20,
            pnn50=25.0,
            stress_index=45.0,
            sample_count=100,
            duration_seconds=80.0
        )
        assert valid_metrics.is_valid()
        
        # 无效指标 - 样本数不足
        invalid_metrics = HRVMetrics(
            rmssd=35.0,
            sdnn=80.0,
            mean_rr=800.0,
            mean_hr=75.0,
            nn50=20,
            pnn50=25.0,
            stress_index=45.0,
            sample_count=10,  # 不足30
            duration_seconds=80.0
        )
        assert not invalid_metrics.is_valid()


class TestBioAnalysisResult:
    """生理分析结果测试"""
    
    def test_result_creation(self):
        """测试结果创建"""
        result = BioAnalysisResult(
            stress_index=50.0,
            stress_level="moderate",
            hrv_metrics=None,
            heart_rate=72.0,
            heart_rate_status="normal",
            is_valid=True
        )
        
        assert result.stress_index == 50.0
        assert result.stress_level == "moderate"
        assert result.is_valid
    
    def test_insufficient_data_result(self):
        """测试数据不足结果"""
        result = BioAnalysisResult.insufficient_data("Not enough RR intervals")
        
        assert not result.is_valid
        assert result.stress_level == "unknown"
        assert "Not enough" in result.message


class TestMockBLEHeartRateReceiver:
    """模拟 BLE 心率接收器测试"""
    
    @pytest.mark.asyncio
    async def test_mock_connect(self):
        """测试模拟连接"""
        receiver = MockBLEHeartRateReceiver(base_bpm=70)
        
        assert not receiver.is_connected
        result = await receiver.connect()
        assert result is True
        assert receiver.is_connected
        
        await receiver.disconnect()
        assert not receiver.is_connected
    
    @pytest.mark.asyncio
    async def test_mock_data_generation(self):
        """测试模拟数据生成"""
        import asyncio
        
        receiver = MockBLEHeartRateReceiver(base_bpm=70, variability=5)
        await receiver.connect()
        await receiver.start_receiving()
        
        # 等待一些数据生成
        await asyncio.sleep(2.5)
        
        await receiver.stop_receiving()
        await receiver.disconnect()
        
        # 应该有至少2个读数
        assert len(receiver.buffer.readings) >= 2
        
        # 检查心率范围
        for reading in receiver.buffer.readings:
            assert 60 <= reading.bpm <= 80  # base_bpm ± variability
    
    @pytest.mark.asyncio
    async def test_mock_average_bpm(self):
        """测试模拟平均心率"""
        import asyncio
        
        receiver = MockBLEHeartRateReceiver(base_bpm=75, variability=3)
        await receiver.connect()
        await receiver.start_receiving()
        
        await asyncio.sleep(3)
        
        avg = receiver.get_average_bpm(seconds=60)
        
        await receiver.stop_receiving()
        await receiver.disconnect()
        
        assert avg is not None
        assert 70 <= avg <= 80


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_mock_receiver_with_hrv_analyzer(self):
        """测试模拟接收器与 HRV 分析器集成"""
        import asyncio
        
        receiver = MockBLEHeartRateReceiver(base_bpm=70, variability=10)
        analyzer = HRVAnalyzer()
        
        await receiver.connect()
        await receiver.start_receiving()
        
        # 收集足够的数据（约65秒）
        await asyncio.sleep(65)
        
        await receiver.stop_receiving()
        await receiver.disconnect()
        
        # 获取 RR 间期
        rr_intervals = receiver.buffer.get_rr_intervals()
        
        # 分析 HRV
        if len(rr_intervals) >= 30:
            metrics = analyzer.analyze(rr_intervals)
            
            if metrics is not None:
                assert metrics.is_valid()
                assert 0 <= metrics.stress_index <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
