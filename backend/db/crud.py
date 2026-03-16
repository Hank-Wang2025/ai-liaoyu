"""
基础 CRUD 操作
Basic CRUD operations for database
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from loguru import logger

from .database import get_db


class BaseCRUD:
    """Base CRUD class for database operations"""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
    
    async def create(self, data: Dict[str, Any]) -> str:
        """Create a new record"""
        db = await get_db()
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        values = list(data.values())
        
        query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
        cursor = await db.execute(query, values)
        await db.commit()
        
        record_id = data.get("id") or cursor.lastrowid
        logger.debug(f"Created record in {self.table_name}: {record_id}")
        return str(record_id)
    
    async def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a record by ID"""
        db = await get_db()
        query = f"SELECT * FROM {self.table_name} WHERE id = ?"
        cursor = await db.execute(query, (record_id,))
        row = await cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all records with pagination"""
        db = await get_db()
        query = f"SELECT * FROM {self.table_name} LIMIT ? OFFSET ?"
        cursor = await db.execute(query, (limit, offset))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def update(self, record_id: str, data: Dict[str, Any]) -> bool:
        """Update a record"""
        db = await get_db()
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        values = list(data.values()) + [record_id]
        
        query = f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?"
        cursor = await db.execute(query, values)
        await db.commit()
        
        success = cursor.rowcount > 0
        if success:
            logger.debug(f"Updated record in {self.table_name}: {record_id}")
        return success
    
    async def delete(self, record_id: str) -> bool:
        """Delete a record"""
        db = await get_db()
        query = f"DELETE FROM {self.table_name} WHERE id = ?"
        cursor = await db.execute(query, (record_id,))
        await db.commit()
        
        success = cursor.rowcount > 0
        if success:
            logger.debug(f"Deleted record from {self.table_name}: {record_id}")
        return success
    
    async def count(self) -> int:
        """Count total records"""
        db = await get_db()
        query = f"SELECT COUNT(*) as count FROM {self.table_name}"
        cursor = await db.execute(query)
        row = await cursor.fetchone()
        return row["count"] if row else 0


class SessionCRUD(BaseCRUD):
    """CRUD operations for sessions"""
    
    def __init__(self):
        super().__init__("sessions")
    
    async def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sessions"""
        db = await get_db()
        query = f"""
            SELECT * FROM {self.table_name} 
            ORDER BY start_time DESC 
            LIMIT ?
        """
        cursor = await db.execute(query, (limit,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def get_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get sessions within date range"""
        db = await get_db()
        query = f"""
            SELECT * FROM {self.table_name}
            WHERE start_time >= ? AND start_time <= ?
            ORDER BY start_time DESC
        """
        cursor = await db.execute(query, (start_date, end_date))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


class EmotionHistoryCRUD(BaseCRUD):
    """CRUD operations for emotion history"""
    
    def __init__(self):
        super().__init__("emotion_history")
    
    async def get_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get emotion history for a session"""
        db = await get_db()
        query = f"""
            SELECT * FROM {self.table_name}
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """
        cursor = await db.execute(query, (session_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


class TherapyPlanCRUD(BaseCRUD):
    """CRUD operations for therapy plans"""
    
    def __init__(self):
        super().__init__("therapy_plans")
    
    async def get_by_emotion(self, emotion: str) -> List[Dict[str, Any]]:
        """Get plans targeting specific emotion"""
        db = await get_db()
        query = f"""
            SELECT * FROM {self.table_name}
            WHERE target_emotions LIKE ?
        """
        cursor = await db.execute(query, (f"%{emotion}%",))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def get_by_style(self, style: str) -> List[Dict[str, Any]]:
        """Get plans by style (chinese/modern)"""
        db = await get_db()
        query = f"""
            SELECT * FROM {self.table_name}
            WHERE style = ?
        """
        cursor = await db.execute(query, (style,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


class SystemLogCRUD(BaseCRUD):
    """CRUD operations for system logs"""
    
    def __init__(self):
        super().__init__("system_logs")
    
    async def log(
        self, 
        level: str, 
        module: str, 
        message: str, 
        details: Optional[Dict] = None
    ) -> str:
        """Add a log entry"""
        data = {
            "level": level,
            "module": module,
            "message": message,
            "details": json.dumps(details) if details else None,
            "timestamp": datetime.now().isoformat()
        }
        return await self.create(data)
    
    async def get_by_level(self, level: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get logs by level"""
        db = await get_db()
        query = f"""
            SELECT * FROM {self.table_name}
            WHERE level = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        cursor = await db.execute(query, (level, limit))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


class AdjustmentRecordCRUD(BaseCRUD):
    """CRUD operations for adjustment records
    
    Requirements: 10.4 - 记录每次调整的时间、原因、内容
    """
    
    def __init__(self):
        super().__init__("adjustment_records")
    
    async def create_adjustment(
        self,
        session_id: str,
        reason: str,
        adjustment_type: str,
        details: Optional[Dict] = None,
        previous_state: Optional[Dict] = None,
        new_state: Optional[Dict] = None
    ) -> str:
        """Create an adjustment record"""
        data = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "adjustment_type": adjustment_type,
            "details": json.dumps(details) if details else None,
            "previous_state": json.dumps(previous_state) if previous_state else None,
            "new_state": json.dumps(new_state) if new_state else None
        }
        return await self.create(data)
    
    async def get_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all adjustments for a session"""
        db = await get_db()
        query = f"""
            SELECT * FROM {self.table_name}
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """
        cursor = await db.execute(query, (session_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def get_by_type(
        self, 
        adjustment_type: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get adjustments by type"""
        db = await get_db()
        query = f"""
            SELECT * FROM {self.table_name}
            WHERE adjustment_type = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        cursor = await db.execute(query, (adjustment_type, limit))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent adjustments"""
        db = await get_db()
        query = f"""
            SELECT * FROM {self.table_name}
            ORDER BY timestamp DESC
            LIMIT ?
        """
        cursor = await db.execute(query, (limit,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# Singleton instances
session_crud = SessionCRUD()
emotion_history_crud = EmotionHistoryCRUD()
therapy_plan_crud = TherapyPlanCRUD()
system_log_crud = SystemLogCRUD()
adjustment_record_crud = AdjustmentRecordCRUD()
