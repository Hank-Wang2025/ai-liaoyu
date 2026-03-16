"""
Tests for data retention service
测试数据保留服务

Requirements: 14.5 - 支持配置数据保留期限，自动清理过期数据
"""
import pytest
import tempfile
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import importlib.util

# Import directly from the module file to avoid __init__.py import chain
retention_path = Path(__file__).parent.parent / "services" / "data_retention.py"
spec = importlib.util.spec_from_file_location("data_retention", retention_path)
data_retention_module = importlib.util.module_from_spec(spec)

# Mock the backend.db.database import before loading the module
import sys
mock_db_module = MagicMock()
sys.modules['backend.db.database'] = mock_db_module

spec.loader.exec_module(data_retention_module)

DataRetentionConfig = data_retention_module.DataRetentionConfig
DataRetentionService = data_retention_module.DataRetentionService


class TestDataRetentionConfig:
    """Tests for DataRetentionConfig"""
    
    def test_default_config(self):
        """Test default configuration values"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DataRetentionConfig(config_path=Path(tmpdir) / "test_config.yaml")
            
            assert config.get_retention_days("sessions") == 365
            assert config.get_retention_days("emotion_history") == 90
            assert config.get_retention_days("system_logs") == 30
            assert config.cleanup_enabled is True
            assert config.cleanup_interval_hours == 24
            assert config.batch_size == 1000
    
    def test_set_retention_days(self):
        """Test setting retention period"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DataRetentionConfig(config_path=Path(tmpdir) / "test_config.yaml")
            
            config.set_retention_days("sessions", 180)
            assert config.get_retention_days("sessions") == 180
    
    def test_unknown_table_default(self):
        """Test that unknown tables get default retention"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DataRetentionConfig(config_path=Path(tmpdir) / "test_config.yaml")
            
            # Unknown table should return default of 365 days
            assert config.get_retention_days("unknown_table") == 365
    
    def test_cleanup_enabled_toggle(self):
        """Test enabling/disabling cleanup"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DataRetentionConfig(config_path=Path(tmpdir) / "test_config.yaml")
            
            config.cleanup_enabled = False
            assert config.cleanup_enabled is False
            
            config.cleanup_enabled = True
            assert config.cleanup_enabled is True
    
    def test_get_all_settings(self):
        """Test getting all settings"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DataRetentionConfig(config_path=Path(tmpdir) / "test_config.yaml")
            
            settings = config.get_all_settings()
            assert "sessions" in settings
            assert "cleanup_enabled" in settings
            assert "batch_size" in settings
    
    def test_update_settings(self):
        """Test updating multiple settings"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DataRetentionConfig(config_path=Path(tmpdir) / "test_config.yaml")
            
            config.update_settings({
                "sessions": 100,
                "cleanup_interval_hours": 12
            })
            
            assert config.get_retention_days("sessions") == 100
            assert config.cleanup_interval_hours == 12
    
    def test_config_persistence(self):
        """Test that config is persisted to file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yaml"
            
            # Create and modify config
            config1 = DataRetentionConfig(config_path=config_path)
            config1.set_retention_days("sessions", 200)
            
            # Create new instance and verify persistence
            config2 = DataRetentionConfig(config_path=config_path)
            assert config2.get_retention_days("sessions") == 200


class TestDataRetentionService:
    """Tests for DataRetentionService"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database connection"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.rowcount = 5
        mock_cursor.fetchone = AsyncMock(return_value={"count": 10})
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()
        return mock_conn
    
    @pytest.fixture
    def service(self):
        """Create retention service with temp config"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DataRetentionConfig(config_path=Path(tmpdir) / "test_config.yaml")
            yield DataRetentionService(config=config)
    
    @pytest.mark.asyncio
    async def test_cleanup_table(self, service, mock_db):
        """Test cleaning up a single table"""
        # Patch the get_db function in the module
        data_retention_module.get_db = AsyncMock(return_value=mock_db)
        
        deleted = await service.cleanup_table("sessions")
        
        # Should have called execute with DELETE query
        mock_db.execute.assert_called()
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_cleanup_unknown_table(self, service, mock_db):
        """Test cleanup of unknown table returns 0"""
        data_retention_module.get_db = AsyncMock(return_value=mock_db)
        
        deleted = await service.cleanup_table("unknown_table")
        assert deleted == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_all_tables(self, service, mock_db):
        """Test cleaning up all tables"""
        data_retention_module.get_db = AsyncMock(return_value=mock_db)
        
        results = await service.cleanup_all_tables()
        
        # Should have results for all known tables
        assert "sessions" in results
        assert "emotion_history" in results
        assert "system_logs" in results
    
    @pytest.mark.asyncio
    async def test_get_expired_count(self, service, mock_db):
        """Test getting count of expired records"""
        data_retention_module.get_db = AsyncMock(return_value=mock_db)
        
        count = await service.get_expired_count("sessions")
        
        # Should return the count from mock
        assert count == 10
    
    @pytest.mark.asyncio
    async def test_get_expired_count_unknown_table(self, service, mock_db):
        """Test expired count for unknown table returns 0"""
        data_retention_module.get_db = AsyncMock(return_value=mock_db)
        
        count = await service.get_expired_count("unknown_table")
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_get_retention_stats(self, service, mock_db):
        """Test getting retention statistics"""
        data_retention_module.get_db = AsyncMock(return_value=mock_db)
        
        stats = await service.get_retention_stats()
        
        # Should have stats for all tables
        assert "sessions" in stats
        assert "total_records" in stats["sessions"]
        assert "expired_records" in stats["sessions"]
        assert "retention_days" in stats["sessions"]
    
    @pytest.mark.asyncio
    async def test_cleanup_session_cascade(self, service, mock_db):
        """Test cascade deletion of session and related records"""
        data_retention_module.get_db = AsyncMock(return_value=mock_db)
        
        results = await service.cleanup_session_cascade("session_123")
        
        # Should have deleted from multiple tables
        assert "sessions" in results
        assert "emotion_history" in results
        assert "adjustment_records" in results
    
    @pytest.mark.asyncio
    async def test_start_stop_background_cleanup(self, service):
        """Test starting and stopping background cleanup"""
        service.start_background_cleanup()
        assert service._running is True
        assert service._cleanup_task is not None
        
        service.stop_background_cleanup()
        assert service._running is False
    
    @pytest.mark.asyncio
    async def test_manual_cleanup(self, service, mock_db):
        """Test manual cleanup trigger"""
        data_retention_module.get_db = AsyncMock(return_value=mock_db)
        
        results = await service.manual_cleanup()
        
        # Should return results for all tables
        assert isinstance(results, dict)


class TestDataRetentionIntegration:
    """Integration tests for data retention - skipped as they require full database setup"""
    
    @pytest.mark.skip(reason="Requires full database setup")
    @pytest.mark.asyncio
    async def test_cleanup_expired_records(self):
        """Test that expired records are actually deleted"""
        pass
