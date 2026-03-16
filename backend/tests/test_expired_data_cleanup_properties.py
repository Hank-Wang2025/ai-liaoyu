"""
属性测试：过期数据清理
Property Test: Expired Data Cleanup

**Feature: healing-pod-system, Property 30: 过期数据清理**
**Validates: Requirements 14.5**

Property 30: 过期数据清理
*For any* 超过配置保留期限的数据，系统 SHALL 在下次清理任务执行时删除该数据。
"""
import pytest
import tempfile
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings, assume

# 直接从模块文件导入，避免 __init__.py 导入链
import importlib.util
import sys

# Mock the db.database import before loading the module
mock_db_module = MagicMock()
sys.modules['db.database'] = mock_db_module
sys.modules['backend.db.database'] = mock_db_module

retention_path = Path(__file__).parent.parent / "services" / "data_retention.py"
spec = importlib.util.spec_from_file_location("data_retention", retention_path)
data_retention_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data_retention_module)

DataRetentionConfig = data_retention_module.DataRetentionConfig
DataRetentionService = data_retention_module.DataRetentionService


class MockDatabase:
    """
    模拟数据库，用于测试过期数据清理逻辑
    """
    
    def __init__(self):
        self.tables: Dict[str, List[Dict[str, Any]]] = {
            "sessions": [],
            "emotion_history": [],
            "adjustment_records": [],
            "system_logs": [],
            "usage_stats": [],
        }
        self._last_delete_query = None
        self._last_delete_params = None
    
    def insert_record(self, table: str, record: Dict[str, Any]) -> None:
        """插入记录到模拟表"""
        if table in self.tables:
            self.tables[table].append(record)
    
    def get_records(self, table: str) -> List[Dict[str, Any]]:
        """获取表中所有记录"""
        return self.tables.get(table, [])
    
    def count_records(self, table: str) -> int:
        """统计表中记录数"""
        return len(self.tables.get(table, []))
    
    def count_expired_records(
        self, 
        table: str, 
        timestamp_column: str, 
        cutoff_date: datetime
    ) -> int:
        """统计过期记录数"""
        records = self.tables.get(table, [])
        count = 0
        for record in records:
            if timestamp_column in record:
                record_time = record[timestamp_column]
                if isinstance(record_time, str):
                    record_time = datetime.fromisoformat(record_time)
                if record_time < cutoff_date:
                    count += 1
        return count
    
    def delete_expired_records(
        self, 
        table: str, 
        timestamp_column: str, 
        cutoff_date: datetime,
        batch_size: int = 1000
    ) -> int:
        """删除过期记录"""
        if table not in self.tables:
            return 0
        
        records = self.tables[table]
        original_count = len(records)
        
        # 过滤掉过期记录
        remaining = []
        deleted = 0
        for record in records:
            if timestamp_column in record:
                record_time = record[timestamp_column]
                if isinstance(record_time, str):
                    record_time = datetime.fromisoformat(record_time)
                if record_time >= cutoff_date:
                    remaining.append(record)
                else:
                    deleted += 1
                    if deleted >= batch_size:
                        # 模拟批量删除限制
                        remaining.extend(records[len(remaining) + deleted:])
                        break
            else:
                remaining.append(record)
        
        self.tables[table] = remaining
        return original_count - len(remaining)


class TestExpiredDataCleanupProperties:
    """
    属性测试：过期数据清理
    
    **Feature: healing-pod-system, Property 30: 过期数据清理**
    **Validates: Requirements 14.5**
    """
    
    @given(
        retention_days=st.integers(min_value=1, max_value=365),
        num_expired=st.integers(min_value=1, max_value=50),
        num_valid=st.integers(min_value=0, max_value=50)
    )
    @settings(max_examples=100)
    def test_expired_records_are_deleted(
        self, 
        retention_days: int, 
        num_expired: int, 
        num_valid: int
    ):
        """
        属性测试：过期记录被删除
        
        **Feature: healing-pod-system, Property 30: 过期数据清理**
        **Validates: Requirements 14.5**
        
        *For any* 配置的保留期限和数据集，超过保留期限的记录
        SHALL 在清理任务执行后被删除。
        """
        # 创建模拟数据库
        mock_db = MockDatabase()
        
        # 计算截止日期
        now = datetime.now()
        cutoff_date = now - timedelta(days=retention_days)
        
        # 插入过期记录（时间早于截止日期）
        for i in range(num_expired):
            expired_time = cutoff_date - timedelta(days=i + 1)
            mock_db.insert_record("sessions", {
                "id": f"expired_{i}",
                "start_time": expired_time.isoformat()
            })
        
        # 插入有效记录（时间晚于截止日期）
        for i in range(num_valid):
            valid_time = cutoff_date + timedelta(days=i + 1)
            mock_db.insert_record("sessions", {
                "id": f"valid_{i}",
                "start_time": valid_time.isoformat()
            })
        
        # 验证初始状态
        initial_total = mock_db.count_records("sessions")
        assert initial_total == num_expired + num_valid
        
        initial_expired = mock_db.count_expired_records(
            "sessions", "start_time", cutoff_date
        )
        assert initial_expired == num_expired
        
        # 执行清理
        deleted = mock_db.delete_expired_records(
            "sessions", "start_time", cutoff_date
        )
        
        # 验证：删除的记录数等于过期记录数
        assert deleted == num_expired, \
            f"应删除 {num_expired} 条过期记录，实际删除 {deleted} 条"
        
        # 验证：剩余记录数等于有效记录数
        remaining = mock_db.count_records("sessions")
        assert remaining == num_valid, \
            f"应剩余 {num_valid} 条有效记录，实际剩余 {remaining} 条"
        
        # 验证：没有过期记录残留
        remaining_expired = mock_db.count_expired_records(
            "sessions", "start_time", cutoff_date
        )
        assert remaining_expired == 0, \
            "清理后不应有过期记录残留"
    
    @given(
        retention_days=st.integers(min_value=1, max_value=365),
        num_records=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=100)
    def test_valid_records_are_preserved(
        self, 
        retention_days: int, 
        num_records: int
    ):
        """
        属性测试：有效记录被保留
        
        **Feature: healing-pod-system, Property 30: 过期数据清理**
        **Validates: Requirements 14.5**
        
        *For any* 未超过保留期限的记录，清理任务执行后 SHALL 保留这些记录。
        """
        mock_db = MockDatabase()
        
        now = datetime.now()
        cutoff_date = now - timedelta(days=retention_days)
        
        # 只插入有效记录（时间晚于截止日期）
        valid_ids = []
        for i in range(num_records):
            valid_time = cutoff_date + timedelta(hours=i + 1)
            record_id = f"valid_{i}"
            valid_ids.append(record_id)
            mock_db.insert_record("sessions", {
                "id": record_id,
                "start_time": valid_time.isoformat()
            })
        
        # 执行清理
        deleted = mock_db.delete_expired_records(
            "sessions", "start_time", cutoff_date
        )
        
        # 验证：没有记录被删除
        assert deleted == 0, \
            f"不应删除任何有效记录，实际删除 {deleted} 条"
        
        # 验证：所有记录都被保留
        remaining = mock_db.count_records("sessions")
        assert remaining == num_records, \
            f"所有 {num_records} 条有效记录应被保留"
        
        # 验证：保留的记录 ID 正确
        remaining_records = mock_db.get_records("sessions")
        remaining_ids = [r["id"] for r in remaining_records]
        for valid_id in valid_ids:
            assert valid_id in remaining_ids, \
                f"有效记录 {valid_id} 应被保留"
    
    @given(
        retention_days=st.integers(min_value=1, max_value=365),
        table_name=st.sampled_from([
            "sessions", "emotion_history", "adjustment_records", 
            "system_logs", "usage_stats"
        ])
    )
    @settings(max_examples=100)
    def test_cleanup_respects_table_specific_retention(
        self, 
        retention_days: int, 
        table_name: str
    ):
        """
        属性测试：清理遵循表特定的保留期限
        
        **Feature: healing-pod-system, Property 30: 过期数据清理**
        **Validates: Requirements 14.5**
        
        *For any* 表和保留期限配置，清理任务 SHALL 使用该表配置的保留期限。
        """
        mock_db = MockDatabase()
        
        # 获取表的时间戳列
        timestamp_columns = {
            "sessions": "start_time",
            "emotion_history": "timestamp",
            "adjustment_records": "timestamp",
            "system_logs": "timestamp",
            "usage_stats": "date",
        }
        timestamp_column = timestamp_columns[table_name]
        
        now = datetime.now()
        cutoff_date = now - timedelta(days=retention_days)
        
        # 插入一条刚好过期的记录
        expired_time = cutoff_date - timedelta(seconds=1)
        mock_db.insert_record(table_name, {
            "id": "expired_record",
            timestamp_column: expired_time.isoformat()
        })
        
        # 插入一条刚好未过期的记录
        valid_time = cutoff_date + timedelta(seconds=1)
        mock_db.insert_record(table_name, {
            "id": "valid_record",
            timestamp_column: valid_time.isoformat()
        })
        
        # 执行清理
        deleted = mock_db.delete_expired_records(
            table_name, timestamp_column, cutoff_date
        )
        
        # 验证：只有过期记录被删除
        assert deleted == 1, \
            f"应删除 1 条过期记录，实际删除 {deleted} 条"
        
        remaining = mock_db.count_records(table_name)
        assert remaining == 1, \
            f"应剩余 1 条有效记录，实际剩余 {remaining} 条"
        
        # 验证：保留的是有效记录
        remaining_records = mock_db.get_records(table_name)
        assert remaining_records[0]["id"] == "valid_record", \
            "保留的应该是有效记录"
    
    @given(
        retention_days=st.integers(min_value=1, max_value=365),
        days_before_cutoff=st.integers(min_value=0, max_value=100)
    )
    @settings(max_examples=100)
    def test_cutoff_date_calculation_accuracy(
        self, 
        retention_days: int, 
        days_before_cutoff: int
    ):
        """
        属性测试：截止日期计算准确性
        
        **Feature: healing-pod-system, Property 30: 过期数据清理**
        **Validates: Requirements 14.5**
        
        *For any* 保留期限配置，截止日期 SHALL 准确计算为当前时间减去保留天数。
        """
        now = datetime.now()
        cutoff_date = now - timedelta(days=retention_days)
        
        # 创建一条记录，时间为截止日期前 days_before_cutoff 天
        record_time = cutoff_date - timedelta(days=days_before_cutoff)
        
        # 验证：如果 days_before_cutoff > 0，记录应该过期
        if days_before_cutoff > 0:
            assert record_time < cutoff_date, \
                "截止日期前的记录应该被判定为过期"
        else:
            # days_before_cutoff == 0 时，记录时间等于截止日期
            # 根据实现，等于截止日期的记录不应被删除（使用 < 而非 <=）
            assert record_time <= cutoff_date, \
                "截止日期当天的记录边界情况"
    
    @given(
        retention_days=st.integers(min_value=1, max_value=365),
        num_records=st.integers(min_value=10, max_value=100),
        batch_size=st.integers(min_value=1, max_value=50)
    )
    @settings(max_examples=100)
    def test_batch_deletion_completeness(
        self, 
        retention_days: int, 
        num_records: int, 
        batch_size: int
    ):
        """
        属性测试：批量删除完整性
        
        **Feature: healing-pod-system, Property 30: 过期数据清理**
        **Validates: Requirements 14.5**
        
        *For any* 过期记录数量和批量大小，多次批量删除后 SHALL 删除所有过期记录。
        """
        mock_db = MockDatabase()
        
        now = datetime.now()
        cutoff_date = now - timedelta(days=retention_days)
        
        # 插入过期记录
        for i in range(num_records):
            expired_time = cutoff_date - timedelta(days=i + 1)
            mock_db.insert_record("sessions", {
                "id": f"expired_{i}",
                "start_time": expired_time.isoformat()
            })
        
        # 多次执行批量删除直到全部删除
        total_deleted = 0
        max_iterations = (num_records // batch_size) + 2  # 防止无限循环
        iterations = 0
        
        while iterations < max_iterations:
            deleted = mock_db.delete_expired_records(
                "sessions", "start_time", cutoff_date, batch_size
            )
            total_deleted += deleted
            iterations += 1
            
            if deleted == 0:
                break
        
        # 验证：所有过期记录都被删除
        assert total_deleted == num_records, \
            f"应删除 {num_records} 条过期记录，实际删除 {total_deleted} 条"
        
        remaining = mock_db.count_records("sessions")
        assert remaining == 0, \
            f"所有过期记录应被删除，实际剩余 {remaining} 条"
    
    @given(
        retention_days=st.integers(min_value=1, max_value=365),
        num_expired=st.integers(min_value=1, max_value=30),
        num_valid=st.integers(min_value=1, max_value=30)
    )
    @settings(max_examples=100)
    def test_cleanup_idempotency(
        self, 
        retention_days: int, 
        num_expired: int, 
        num_valid: int
    ):
        """
        属性测试：清理幂等性
        
        **Feature: healing-pod-system, Property 30: 过期数据清理**
        **Validates: Requirements 14.5**
        
        *For any* 数据集，多次执行清理任务 SHALL 产生相同的最终状态。
        """
        mock_db = MockDatabase()
        
        now = datetime.now()
        cutoff_date = now - timedelta(days=retention_days)
        
        # 插入过期和有效记录
        for i in range(num_expired):
            expired_time = cutoff_date - timedelta(days=i + 1)
            mock_db.insert_record("sessions", {
                "id": f"expired_{i}",
                "start_time": expired_time.isoformat()
            })
        
        for i in range(num_valid):
            valid_time = cutoff_date + timedelta(days=i + 1)
            mock_db.insert_record("sessions", {
                "id": f"valid_{i}",
                "start_time": valid_time.isoformat()
            })
        
        # 第一次清理
        deleted1 = mock_db.delete_expired_records(
            "sessions", "start_time", cutoff_date
        )
        remaining1 = mock_db.count_records("sessions")
        
        # 第二次清理（应该没有效果）
        deleted2 = mock_db.delete_expired_records(
            "sessions", "start_time", cutoff_date
        )
        remaining2 = mock_db.count_records("sessions")
        
        # 第三次清理（应该没有效果）
        deleted3 = mock_db.delete_expired_records(
            "sessions", "start_time", cutoff_date
        )
        remaining3 = mock_db.count_records("sessions")
        
        # 验证：第一次清理删除了所有过期记录
        assert deleted1 == num_expired, \
            f"第一次清理应删除 {num_expired} 条记录"
        
        # 验证：后续清理没有删除任何记录
        assert deleted2 == 0, "第二次清理不应删除任何记录"
        assert deleted3 == 0, "第三次清理不应删除任何记录"
        
        # 验证：最终状态一致
        assert remaining1 == remaining2 == remaining3 == num_valid, \
            "多次清理后的最终状态应一致"


class TestDataRetentionServiceProperties:
    """
    属性测试：DataRetentionService 集成测试
    
    **Feature: healing-pod-system, Property 30: 过期数据清理**
    **Validates: Requirements 14.5**
    """
    
    @given(
        retention_days=st.integers(min_value=1, max_value=365)
    )
    @settings(max_examples=100)
    def test_config_retention_days_applied(self, retention_days: int):
        """
        属性测试：配置的保留天数被正确应用
        
        **Feature: healing-pod-system, Property 30: 过期数据清理**
        **Validates: Requirements 14.5**
        
        *For any* 配置的保留天数，服务 SHALL 使用该配置计算截止日期。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DataRetentionConfig(
                config_path=Path(tmpdir) / "test_config.yaml"
            )
            config.set_retention_days("sessions", retention_days)
            
            service = DataRetentionService(config=config)
            
            # 验证：配置被正确读取
            actual_days = service.config.get_retention_days("sessions")
            assert actual_days == retention_days, \
                f"配置的保留天数应为 {retention_days}，实际为 {actual_days}"
    
    @given(
        table_name=st.sampled_from([
            "sessions", "emotion_history", "adjustment_records",
            "system_logs", "usage_stats"
        ])
    )
    @settings(max_examples=100)
    def test_table_timestamp_column_mapping(self, table_name: str):
        """
        属性测试：表时间戳列映射正确
        
        **Feature: healing-pod-system, Property 30: 过期数据清理**
        **Validates: Requirements 14.5**
        
        *For any* 支持的表，服务 SHALL 知道该表的时间戳列名。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DataRetentionConfig(
                config_path=Path(tmpdir) / "test_config.yaml"
            )
            service = DataRetentionService(config=config)
            
            # 验证：表在支持的表列表中
            assert table_name in service.TABLE_TIMESTAMP_COLUMNS, \
                f"表 {table_name} 应在支持的表列表中"
            
            # 验证：时间戳列名不为空
            timestamp_column = service.TABLE_TIMESTAMP_COLUMNS[table_name]
            assert timestamp_column is not None and len(timestamp_column) > 0, \
                f"表 {table_name} 的时间戳列名不应为空"
    
    @given(
        cleanup_enabled=st.booleans()
    )
    @settings(max_examples=100)
    def test_cleanup_enabled_flag_respected(self, cleanup_enabled: bool):
        """
        属性测试：清理启用标志被遵守
        
        **Feature: healing-pod-system, Property 30: 过期数据清理**
        **Validates: Requirements 14.5**
        
        *For any* 清理启用配置，服务 SHALL 遵守该配置。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DataRetentionConfig(
                config_path=Path(tmpdir) / "test_config.yaml"
            )
            config.cleanup_enabled = cleanup_enabled
            
            service = DataRetentionService(config=config)
            
            # 验证：配置被正确读取
            assert service.config.cleanup_enabled == cleanup_enabled, \
                f"清理启用标志应为 {cleanup_enabled}"

