"""
数据保留策略服务
Data Retention Policy Service

Requirements: 14.5 - 支持配置数据保留期限，自动清理过期数据
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
from loguru import logger
import yaml

from db.database import get_db


class DataRetentionConfig:
    """
    数据保留配置
    Configuration for data retention policies
    
    Requirements: 14.5 - 实现数据保留期限配置
    """
    
    DEFAULT_CONFIG = {
        # Retention periods in days
        "sessions": 365,  # 1 year
        "emotion_history": 90,  # 3 months
        "adjustment_records": 180,  # 6 months
        "system_logs": 30,  # 1 month
        "usage_stats": 365,  # 1 year
        
        # Cleanup settings
        "cleanup_enabled": True,
        "cleanup_interval_hours": 24,  # Run cleanup every 24 hours
        "batch_size": 1000,  # Delete records in batches
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize retention config
        
        Args:
            config_path: Path to YAML config file
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "data_retention.yaml"
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file or use defaults"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f) or {}
                self._config = {**self.DEFAULT_CONFIG, **file_config}
                logger.info(f"Loaded data retention config from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}, using defaults")
                self._config = self.DEFAULT_CONFIG.copy()
        else:
            self._config = self.DEFAULT_CONFIG.copy()
            self._save_config()
            logger.info("Created default data retention config")
    
    def _save_config(self) -> None:
        """Save current configuration to file"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def get_retention_days(self, table_name: str) -> int:
        """
        Get retention period for a table
        
        Args:
            table_name: Name of the database table
            
        Returns:
            Retention period in days
        """
        return self._config.get(table_name, 365)
    
    def set_retention_days(self, table_name: str, days: int) -> None:
        """
        Set retention period for a table
        
        Args:
            table_name: Name of the database table
            days: Retention period in days
        """
        self._config[table_name] = days
        self._save_config()
        logger.info(f"Set retention for {table_name} to {days} days")
    
    @property
    def cleanup_enabled(self) -> bool:
        """Check if automatic cleanup is enabled"""
        return self._config.get("cleanup_enabled", True)
    
    @cleanup_enabled.setter
    def cleanup_enabled(self, value: bool) -> None:
        """Enable or disable automatic cleanup"""
        self._config["cleanup_enabled"] = value
        self._save_config()
    
    @property
    def cleanup_interval_hours(self) -> int:
        """Get cleanup interval in hours"""
        return self._config.get("cleanup_interval_hours", 24)
    
    @property
    def batch_size(self) -> int:
        """Get batch size for deletion"""
        return self._config.get("batch_size", 1000)
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all configuration settings"""
        return self._config.copy()
    
    def update_settings(self, settings: Dict[str, Any]) -> None:
        """
        Update multiple settings at once
        
        Args:
            settings: Dictionary of settings to update
        """
        self._config.update(settings)
        self._save_config()
        logger.info("Updated data retention settings")


class DataRetentionService:
    """
    数据保留服务
    Service for managing data retention and cleanup
    
    Requirements: 14.5 - 实现自动清理任务
    """
    
    # Tables with timestamp columns for cleanup
    TABLE_TIMESTAMP_COLUMNS = {
        "sessions": "start_time",
        "emotion_history": "timestamp",
        "adjustment_records": "timestamp",
        "system_logs": "timestamp",
        "usage_stats": "date",
    }
    
    def __init__(self, config: Optional[DataRetentionConfig] = None):
        """
        Initialize data retention service
        
        Args:
            config: Optional retention configuration
        """
        self.config = config or DataRetentionConfig()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def cleanup_table(self, table_name: str) -> int:
        """
        Clean up expired records from a table
        
        Args:
            table_name: Name of the table to clean
            
        Returns:
            Number of records deleted
        """
        if table_name not in self.TABLE_TIMESTAMP_COLUMNS:
            logger.warning(f"Unknown table for cleanup: {table_name}")
            return 0
        
        timestamp_column = self.TABLE_TIMESTAMP_COLUMNS[table_name]
        retention_days = self.config.get_retention_days(table_name)
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        db = await get_db()
        total_deleted = 0
        
        try:
            # Delete in batches to avoid locking
            while True:
                query = f"""
                    DELETE FROM {table_name}
                    WHERE {timestamp_column} < ?
                    LIMIT ?
                """
                cursor = await db.execute(
                    query, 
                    (cutoff_date.isoformat(), self.config.batch_size)
                )
                await db.commit()
                
                deleted = cursor.rowcount
                total_deleted += deleted
                
                if deleted < self.config.batch_size:
                    break
                
                # Small delay between batches
                await asyncio.sleep(0.1)
            
            if total_deleted > 0:
                logger.info(
                    f"Cleaned up {total_deleted} expired records from {table_name} "
                    f"(retention: {retention_days} days)"
                )
            
            return total_deleted
            
        except Exception as e:
            logger.error(f"Error cleaning up {table_name}: {e}")
            return 0
    
    async def cleanup_all_tables(self) -> Dict[str, int]:
        """
        Clean up all tables with retention policies
        
        Returns:
            Dictionary mapping table names to number of deleted records
        """
        results = {}
        
        for table_name in self.TABLE_TIMESTAMP_COLUMNS:
            deleted = await self.cleanup_table(table_name)
            results[table_name] = deleted
        
        total = sum(results.values())
        if total > 0:
            logger.info(f"Total cleanup: {total} records deleted")
        
        return results
    
    async def cleanup_session_cascade(self, session_id: str) -> Dict[str, int]:
        """
        Delete a session and all related records
        
        Args:
            session_id: ID of the session to delete
            
        Returns:
            Dictionary mapping table names to number of deleted records
        """
        db = await get_db()
        results = {}
        
        try:
            # Delete related emotion history
            cursor = await db.execute(
                "DELETE FROM emotion_history WHERE session_id = ?",
                (session_id,)
            )
            results["emotion_history"] = cursor.rowcount
            
            # Delete related adjustment records
            cursor = await db.execute(
                "DELETE FROM adjustment_records WHERE session_id = ?",
                (session_id,)
            )
            results["adjustment_records"] = cursor.rowcount
            
            # Delete the session itself
            cursor = await db.execute(
                "DELETE FROM sessions WHERE id = ?",
                (session_id,)
            )
            results["sessions"] = cursor.rowcount
            
            await db.commit()
            
            logger.info(f"Cascade deleted session {session_id}: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error in cascade delete for session {session_id}: {e}")
            return {}
    
    async def get_expired_count(self, table_name: str) -> int:
        """
        Get count of expired records in a table
        
        Args:
            table_name: Name of the table
            
        Returns:
            Number of expired records
        """
        if table_name not in self.TABLE_TIMESTAMP_COLUMNS:
            return 0
        
        timestamp_column = self.TABLE_TIMESTAMP_COLUMNS[table_name]
        retention_days = self.config.get_retention_days(table_name)
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        db = await get_db()
        
        try:
            query = f"""
                SELECT COUNT(*) as count FROM {table_name}
                WHERE {timestamp_column} < ?
            """
            cursor = await db.execute(query, (cutoff_date.isoformat(),))
            row = await cursor.fetchone()
            return row["count"] if row else 0
        except Exception as e:
            logger.error(f"Error counting expired records in {table_name}: {e}")
            return 0
    
    async def get_retention_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get retention statistics for all tables
        
        Returns:
            Dictionary with stats for each table
        """
        stats = {}
        
        for table_name in self.TABLE_TIMESTAMP_COLUMNS:
            expired_count = await self.get_expired_count(table_name)
            retention_days = self.config.get_retention_days(table_name)
            
            db = await get_db()
            cursor = await db.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            row = await cursor.fetchone()
            total_count = row["count"] if row else 0
            
            stats[table_name] = {
                "total_records": total_count,
                "expired_records": expired_count,
                "retention_days": retention_days,
                "cutoff_date": (datetime.now() - timedelta(days=retention_days)).isoformat()
            }
        
        return stats
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop"""
        while self._running:
            try:
                if self.config.cleanup_enabled:
                    await self.cleanup_all_tables()
                
                # Wait for next cleanup interval
                await asyncio.sleep(self.config.cleanup_interval_hours * 3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(60)
    
    def start_background_cleanup(self) -> None:
        """Start the background cleanup task"""
        if self._cleanup_task is not None and not self._cleanup_task.done():
            logger.warning("Cleanup task already running")
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(
            f"Started background cleanup task "
            f"(interval: {self.config.cleanup_interval_hours} hours)"
        )
    
    def stop_background_cleanup(self) -> None:
        """Stop the background cleanup task"""
        self._running = False
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            self._cleanup_task = None
            logger.info("Stopped background cleanup task")
    
    async def manual_cleanup(self) -> Dict[str, int]:
        """
        Trigger a manual cleanup
        
        Returns:
            Dictionary mapping table names to number of deleted records
        """
        logger.info("Manual cleanup triggered")
        return await self.cleanup_all_tables()


# Singleton instance
_retention_service: Optional[DataRetentionService] = None


def get_retention_service() -> DataRetentionService:
    """Get the singleton retention service instance"""
    global _retention_service
    if _retention_service is None:
        _retention_service = DataRetentionService()
    return _retention_service


async def init_data_retention() -> None:
    """Initialize and start the data retention service"""
    service = get_retention_service()
    service.start_background_cleanup()
    logger.info("Data retention service initialized")


async def cleanup_data_retention() -> None:
    """Stop the data retention service"""
    service = get_retention_service()
    service.stop_background_cleanup()
    logger.info("Data retention service stopped")
