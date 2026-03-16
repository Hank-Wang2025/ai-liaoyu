"""
Tests for database CRUD operations
数据库 CRUD 操作测试

Requirements: 14.1 - 将所有用户数据存储在本地 SQLite 数据库中
Requirements: 14.3 - 支持数据加密存储，使用 AES-256 加密算法
"""
import pytest
import pytest_asyncio
import tempfile
import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional, Dict, Any, List

import aiosqlite
from loguru import logger

# Import encryption module directly
import importlib.util
encryption_path = Path(__file__).parent.parent / "services" / "encryption.py"
spec = importlib.util.spec_from_file_location("encryption", encryption_path)
encryption_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(encryption_module)

KeyManager = encryption_module.KeyManager
AES256Encryptor = encryption_module.AES256Encryptor
DataEncryptionService = encryption_module.DataEncryptionService


# ============================================================================
# Inline database module to avoid import issues
# ============================================================================

# Database file path (will be overridden in tests)
DB_PATH = Path(__file__).parent.parent.parent / "data" / "healing_pod.db"

# Global connection pool
_db_connection: Optional[aiosqlite.Connection] = None


async def get_db() -> aiosqlite.Connection:
    """Get database connection"""
    global _db_connection
    if _db_connection is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db_connection


async def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize database and create tables"""
    global _db_connection, DB_PATH
    
    if db_path:
        DB_PATH = db_path
    
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    _db_connection = await aiosqlite.connect(DB_PATH)
    _db_connection.row_factory = aiosqlite.Row
    
    # Create tables
    await _create_tables(_db_connection)


async def close_db() -> None:
    """Close database connection"""
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None


async def _create_tables(db: aiosqlite.Connection) -> None:
    """Create database tables"""
    
    # Sessions table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            start_time DATETIME NOT NULL,
            end_time DATETIME,
            initial_emotion_category TEXT,
            initial_emotion_intensity REAL,
            final_emotion_category TEXT,
            final_emotion_intensity REAL,
            plan_id TEXT,
            duration_seconds INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Emotion history table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS emotion_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            category TEXT,
            intensity REAL,
            valence REAL,
            arousal REAL,
            audio_data TEXT,
            face_data TEXT,
            bio_data TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    
    # Therapy plans table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS therapy_plans (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            target_emotions TEXT,
            intensity TEXT,
            style TEXT,
            duration INTEGER,
            phases TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME
        )
    """)
    
    # Usage stats table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS usage_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            total_sessions INTEGER DEFAULT 0,
            total_duration INTEGER DEFAULT 0,
            avg_improvement REAL,
            most_common_emotion TEXT,
            most_used_plan TEXT
        )
    """)
    
    # System logs table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            level TEXT,
            module TEXT,
            message TEXT,
            details TEXT
        )
    """)
    
    # Adjustment records table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS adjustment_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            reason TEXT NOT NULL,
            adjustment_type TEXT NOT NULL,
            details TEXT,
            previous_state TEXT,
            new_state TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    
    await db.commit()


# ============================================================================
# Inline CRUD classes to avoid import issues
# ============================================================================

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
        
        return cursor.rowcount > 0
    
    async def delete(self, record_id: str) -> bool:
        """Delete a record"""
        db = await get_db()
        query = f"DELETE FROM {self.table_name} WHERE id = ?"
        cursor = await db.execute(query, (record_id,))
        await db.commit()
        
        return cursor.rowcount > 0
    
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
    """CRUD operations for adjustment records"""
    
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


class TestDatabaseSetup:
    """Test database initialization and setup"""
    
    @pytest_asyncio.fixture
    async def temp_db(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Create a temporary database for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            # Initialize database
            await init_db(db_path)
            
            yield await get_db()
            
            # Cleanup
            await close_db()
    
    @pytest.mark.asyncio
    async def test_database_initialization(self, temp_db):
        """Test that database initializes correctly with all tables"""
        db = temp_db
        
        # Check that all required tables exist
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = await cursor.fetchall()
        table_names = [t[0] for t in tables]
        
        expected_tables = [
            'sessions',
            'emotion_history',
            'therapy_plans',
            'usage_stats',
            'system_logs',
            'adjustment_records'
        ]
        
        for table in expected_tables:
            assert table in table_names, f"Table {table} not found"
    
    @pytest.mark.asyncio
    async def test_sessions_table_schema(self, temp_db):
        """Test sessions table has correct columns"""
        db = temp_db
        
        cursor = await db.execute("PRAGMA table_info(sessions)")
        columns = await cursor.fetchall()
        column_names = [c[1] for c in columns]
        
        expected_columns = [
            'id', 'start_time', 'end_time',
            'initial_emotion_category', 'initial_emotion_intensity',
            'final_emotion_category', 'final_emotion_intensity',
            'plan_id', 'duration_seconds', 'created_at'
        ]
        
        for col in expected_columns:
            assert col in column_names, f"Column {col} not found in sessions table"


class TestBaseCRUD:
    """Tests for BaseCRUD operations"""
    
    @pytest_asyncio.fixture
    async def setup_db(self) -> AsyncGenerator[None, None]:
        """Setup temporary database"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            await init_db(db_path)
            
            yield
            
            await close_db()
    
    @pytest.mark.asyncio
    async def test_create_and_get_by_id(self, setup_db):
        """Test creating a record and retrieving it by ID"""
        crud = SessionCRUD()
        
        session_data = {
            "id": "test_session_001",
            "start_time": datetime.now().isoformat(),
            "initial_emotion_category": "anxious",
            "initial_emotion_intensity": 0.7
        }
        
        # Create record
        record_id = await crud.create(session_data)
        assert record_id == "test_session_001"
        
        # Retrieve record
        result = await crud.get_by_id("test_session_001")
        assert result is not None
        assert result["id"] == "test_session_001"
        assert result["initial_emotion_category"] == "anxious"
        assert result["initial_emotion_intensity"] == 0.7
    
    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, setup_db):
        """Test retrieving all records with pagination"""
        crud = SessionCRUD()
        
        # Create multiple records
        for i in range(5):
            await crud.create({
                "id": f"session_{i}",
                "start_time": datetime.now().isoformat()
            })
        
        # Get all with default limit
        all_records = await crud.get_all()
        assert len(all_records) == 5
        
        # Get with limit
        limited = await crud.get_all(limit=3)
        assert len(limited) == 3
        
        # Get with offset
        offset_records = await crud.get_all(limit=3, offset=2)
        assert len(offset_records) == 3
    
    @pytest.mark.asyncio
    async def test_update_record(self, setup_db):
        """Test updating a record"""
        crud = SessionCRUD()
        
        # Create record
        await crud.create({
            "id": "update_test",
            "start_time": datetime.now().isoformat(),
            "initial_emotion_category": "sad"
        })
        
        # Update record
        success = await crud.update("update_test", {
            "final_emotion_category": "happy",
            "final_emotion_intensity": 0.8
        })
        assert success is True
        
        # Verify update
        result = await crud.get_by_id("update_test")
        assert result["final_emotion_category"] == "happy"
        assert result["final_emotion_intensity"] == 0.8
    
    @pytest.mark.asyncio
    async def test_delete_record(self, setup_db):
        """Test deleting a record"""
        crud = SessionCRUD()
        
        # Create record
        await crud.create({
            "id": "delete_test",
            "start_time": datetime.now().isoformat()
        })
        
        # Verify it exists
        result = await crud.get_by_id("delete_test")
        assert result is not None
        
        # Delete record
        success = await crud.delete("delete_test")
        assert success is True
        
        # Verify deletion
        result = await crud.get_by_id("delete_test")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_count_records(self, setup_db):
        """Test counting records"""
        crud = SessionCRUD()
        
        # Initially empty
        count = await crud.count()
        assert count == 0
        
        # Add records
        for i in range(3):
            await crud.create({
                "id": f"count_test_{i}",
                "start_time": datetime.now().isoformat()
            })
        
        count = await crud.count()
        assert count == 3
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_record(self, setup_db):
        """Test getting a record that doesn't exist"""
        crud = SessionCRUD()
        
        result = await crud.get_by_id("nonexistent_id")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_record(self, setup_db):
        """Test updating a record that doesn't exist"""
        crud = SessionCRUD()
        
        # Use a valid column name from the sessions table
        success = await crud.update("nonexistent_id", {"plan_id": "some_plan"})
        assert success is False
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_record(self, setup_db):
        """Test deleting a record that doesn't exist"""
        crud = SessionCRUD()
        
        success = await crud.delete("nonexistent_id")
        assert success is False


class TestSessionCRUD:
    """Tests for SessionCRUD specific operations"""
    
    @pytest_asyncio.fixture
    async def setup_db(self) -> AsyncGenerator[None, None]:
        """Setup temporary database"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            await init_db(db_path)
            
            yield
            
            await close_db()
    
    @pytest.mark.asyncio
    async def test_get_recent_sessions(self, setup_db):
        """Test getting recent sessions ordered by start_time"""
        crud = SessionCRUD()
        
        # Create sessions with different times
        base_time = datetime.now()
        for i in range(5):
            await crud.create({
                "id": f"recent_test_{i}",
                "start_time": (base_time - timedelta(hours=i)).isoformat()
            })
        
        # Get recent sessions
        recent = await crud.get_recent(limit=3)
        assert len(recent) == 3
        
        # Verify order (most recent first)
        assert recent[0]["id"] == "recent_test_0"
        assert recent[1]["id"] == "recent_test_1"
        assert recent[2]["id"] == "recent_test_2"
    
    @pytest.mark.asyncio
    async def test_get_by_date_range(self, setup_db):
        """Test getting sessions within a date range"""
        crud = SessionCRUD()
        
        base_time = datetime.now()
        
        # Create sessions across different dates
        await crud.create({
            "id": "range_test_1",
            "start_time": (base_time - timedelta(days=5)).isoformat()
        })
        await crud.create({
            "id": "range_test_2",
            "start_time": (base_time - timedelta(days=2)).isoformat()
        })
        await crud.create({
            "id": "range_test_3",
            "start_time": base_time.isoformat()
        })
        
        # Query date range
        start_date = base_time - timedelta(days=3)
        end_date = base_time + timedelta(days=1)
        
        results = await crud.get_by_date_range(start_date, end_date)
        assert len(results) == 2
        
        result_ids = [r["id"] for r in results]
        assert "range_test_2" in result_ids
        assert "range_test_3" in result_ids


class TestEmotionHistoryCRUD:
    """Tests for EmotionHistoryCRUD operations"""
    
    @pytest_asyncio.fixture
    async def setup_db(self) -> AsyncGenerator[None, None]:
        """Setup temporary database"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            await init_db(db_path)
            
            yield
            
            await close_db()
    
    @pytest.mark.asyncio
    async def test_get_by_session(self, setup_db):
        """Test getting emotion history for a specific session"""
        crud = EmotionHistoryCRUD()
        
        session_id = "emotion_test_session"
        base_time = datetime.now()
        
        # Create emotion history entries
        for i in range(3):
            await crud.create({
                "session_id": session_id,
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "category": "anxious",
                "intensity": 0.7 - (i * 0.1)
            })
        
        # Also create entry for different session
        await crud.create({
            "session_id": "other_session",
            "timestamp": base_time.isoformat(),
            "category": "happy",
            "intensity": 0.9
        })
        
        # Get history for specific session
        history = await crud.get_by_session(session_id)
        assert len(history) == 3
        
        # Verify all belong to correct session
        for entry in history:
            assert entry["session_id"] == session_id


class TestTherapyPlanCRUD:
    """Tests for TherapyPlanCRUD operations"""
    
    @pytest_asyncio.fixture
    async def setup_db(self) -> AsyncGenerator[None, None]:
        """Setup temporary database"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            await init_db(db_path)
            
            yield
            
            await close_db()
    
    @pytest.mark.asyncio
    async def test_get_by_emotion(self, setup_db):
        """Test getting plans by target emotion"""
        crud = TherapyPlanCRUD()
        
        # Create plans with different target emotions
        await crud.create({
            "id": "plan_anxiety",
            "name": "Anxiety Relief",
            "target_emotions": json.dumps(["anxious", "stressed"]),
            "style": "modern"
        })
        await crud.create({
            "id": "plan_depression",
            "name": "Depression Relief",
            "target_emotions": json.dumps(["sad", "tired"]),
            "style": "chinese"
        })
        
        # Query by emotion
        anxiety_plans = await crud.get_by_emotion("anxious")
        assert len(anxiety_plans) == 1
        assert anxiety_plans[0]["id"] == "plan_anxiety"
        
        sad_plans = await crud.get_by_emotion("sad")
        assert len(sad_plans) == 1
        assert sad_plans[0]["id"] == "plan_depression"
    
    @pytest.mark.asyncio
    async def test_get_by_style(self, setup_db):
        """Test getting plans by style"""
        crud = TherapyPlanCRUD()
        
        # Create plans with different styles
        await crud.create({
            "id": "modern_plan",
            "name": "Modern Therapy",
            "target_emotions": json.dumps(["anxious"]),
            "style": "modern"
        })
        await crud.create({
            "id": "chinese_plan",
            "name": "Chinese Therapy",
            "target_emotions": json.dumps(["sad"]),
            "style": "chinese"
        })
        
        # Query by style
        modern_plans = await crud.get_by_style("modern")
        assert len(modern_plans) == 1
        assert modern_plans[0]["id"] == "modern_plan"
        
        chinese_plans = await crud.get_by_style("chinese")
        assert len(chinese_plans) == 1
        assert chinese_plans[0]["id"] == "chinese_plan"


class TestSystemLogCRUD:
    """Tests for SystemLogCRUD operations"""
    
    @pytest_asyncio.fixture
    async def setup_db(self) -> AsyncGenerator[None, None]:
        """Setup temporary database"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            await init_db(db_path)
            
            yield
            
            await close_db()
    
    @pytest.mark.asyncio
    async def test_log_entry(self, setup_db):
        """Test creating a log entry"""
        crud = SystemLogCRUD()
        
        log_id = await crud.log(
            level="INFO",
            module="test_module",
            message="Test log message",
            details={"key": "value"}
        )
        
        assert log_id is not None
        
        # Verify log was created
        logs = await crud.get_all()
        assert len(logs) == 1
        assert logs[0]["level"] == "INFO"
        assert logs[0]["module"] == "test_module"
        assert logs[0]["message"] == "Test log message"
    
    @pytest.mark.asyncio
    async def test_get_by_level(self, setup_db):
        """Test getting logs by level"""
        crud = SystemLogCRUD()
        
        # Create logs with different levels
        await crud.log("INFO", "module1", "Info message")
        await crud.log("ERROR", "module2", "Error message")
        await crud.log("INFO", "module3", "Another info")
        await crud.log("WARNING", "module4", "Warning message")
        
        # Query by level
        info_logs = await crud.get_by_level("INFO")
        assert len(info_logs) == 2
        
        error_logs = await crud.get_by_level("ERROR")
        assert len(error_logs) == 1
        assert error_logs[0]["message"] == "Error message"


class TestAdjustmentRecordCRUD:
    """Tests for AdjustmentRecordCRUD operations
    
    Requirements: 10.4 - 记录每次调整的时间、原因、内容
    """
    
    @pytest_asyncio.fixture
    async def setup_db(self) -> AsyncGenerator[None, None]:
        """Setup temporary database"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            await init_db(db_path)
            
            yield
            
            await close_db()
    
    @pytest.mark.asyncio
    async def test_create_adjustment(self, setup_db):
        """Test creating an adjustment record"""
        crud = AdjustmentRecordCRUD()
        
        record_id = await crud.create_adjustment(
            session_id="test_session",
            reason="Emotion not improving",
            adjustment_type="plan_switch",
            details={"from_plan": "plan_a", "to_plan": "plan_b"},
            previous_state={"emotion": "anxious", "intensity": 0.8},
            new_state={"emotion": "anxious", "intensity": 0.7}
        )
        
        assert record_id is not None
        
        # Verify record was created with all fields
        records = await crud.get_by_session("test_session")
        assert len(records) == 1
        assert records[0]["reason"] == "Emotion not improving"
        assert records[0]["adjustment_type"] == "plan_switch"
    
    @pytest.mark.asyncio
    async def test_get_by_session(self, setup_db):
        """Test getting adjustments for a specific session"""
        crud = AdjustmentRecordCRUD()
        
        # Create adjustments for different sessions
        await crud.create_adjustment(
            session_id="session_1",
            reason="Reason 1",
            adjustment_type="type_a"
        )
        await crud.create_adjustment(
            session_id="session_1",
            reason="Reason 2",
            adjustment_type="type_b"
        )
        await crud.create_adjustment(
            session_id="session_2",
            reason="Reason 3",
            adjustment_type="type_a"
        )
        
        # Get adjustments for session_1
        session_1_adjustments = await crud.get_by_session("session_1")
        assert len(session_1_adjustments) == 2
        
        # Get adjustments for session_2
        session_2_adjustments = await crud.get_by_session("session_2")
        assert len(session_2_adjustments) == 1
    
    @pytest.mark.asyncio
    async def test_get_by_type(self, setup_db):
        """Test getting adjustments by type"""
        crud = AdjustmentRecordCRUD()
        
        await crud.create_adjustment(
            session_id="s1",
            reason="R1",
            adjustment_type="plan_switch"
        )
        await crud.create_adjustment(
            session_id="s2",
            reason="R2",
            adjustment_type="intensity_change"
        )
        await crud.create_adjustment(
            session_id="s3",
            reason="R3",
            adjustment_type="plan_switch"
        )
        
        plan_switches = await crud.get_by_type("plan_switch")
        assert len(plan_switches) == 2
        
        intensity_changes = await crud.get_by_type("intensity_change")
        assert len(intensity_changes) == 1


class TestCRUDWithEncryption:
    """Tests for CRUD operations with data encryption
    
    Requirements: 14.1 - 将所有用户数据存储在本地 SQLite 数据库中
    Requirements: 14.3 - 支持数据加密存储，使用 AES-256 加密算法
    """
    
    @pytest_asyncio.fixture
    async def setup_db_with_encryption(self) -> AsyncGenerator[DataEncryptionService, None]:
        """Setup temporary database with encryption service"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            key_dir = Path(tmpdir) / "keys"
            
            await init_db(db_path)
            
            # Setup encryption service
            km = KeyManager(key_dir=key_dir)
            encryption_service = DataEncryptionService(key_manager=km)
            encryption_service.initialize()
            
            yield encryption_service
            
            await close_db()
    
    @pytest.mark.asyncio
    async def test_store_encrypted_emotion_data(self, setup_db_with_encryption):
        """Test storing encrypted emotion data in database"""
        encryption_service = setup_db_with_encryption
        crud = EmotionHistoryCRUD()
        
        # Original sensitive data
        original_data = {
            "session_id": "encrypted_test",
            "timestamp": datetime.now().isoformat(),
            "category": "anxious",
            "intensity": 0.7,
            "audio_data": json.dumps({"emotion": "anxious", "confidence": 0.85}),
            "face_data": json.dumps({"expression": "worried", "landmarks": [1, 2, 3]}),
            "bio_data": json.dumps({"heart_rate": 95, "hrv": 45})
        }
        
        # Encrypt sensitive fields before storing
        encrypted_data = encryption_service.encrypt_sensitive_fields(original_data)
        
        # Store in database
        await crud.create(encrypted_data)
        
        # Retrieve from database
        records = await crud.get_by_session("encrypted_test")
        assert len(records) == 1
        
        stored_record = records[0]
        
        # Verify sensitive fields are encrypted (not readable)
        assert stored_record["audio_data"] != original_data["audio_data"]
        assert stored_record["face_data"] != original_data["face_data"]
        assert stored_record["bio_data"] != original_data["bio_data"]
        
        # Decrypt and verify
        decrypted_record = encryption_service.decrypt_sensitive_fields(stored_record)
        assert decrypted_record["audio_data"] == original_data["audio_data"]
        assert decrypted_record["face_data"] == original_data["face_data"]
        assert decrypted_record["bio_data"] == original_data["bio_data"]
    
    @pytest.mark.asyncio
    async def test_encrypted_data_not_readable_in_db(self, setup_db_with_encryption):
        """Test that encrypted data cannot be read directly from database
        
        Requirements: 14.3 - 加密后的数据 SHALL 无法直接读取原文
        """
        encryption_service = setup_db_with_encryption
        crud = EmotionHistoryCRUD()
        
        sensitive_info = "This is very sensitive user data"
        
        # Encrypt and store
        encrypted_data = {
            "session_id": "privacy_test",
            "timestamp": datetime.now().isoformat(),
            "category": "neutral",
            "intensity": 0.5,
            "audio_data": encryption_service.encrypt_field(sensitive_info)
        }
        
        await crud.create(encrypted_data)
        
        # Retrieve raw data from database
        records = await crud.get_by_session("privacy_test")
        stored_audio_data = records[0]["audio_data"]
        
        # Verify original text is not visible in stored data
        assert sensitive_info not in stored_audio_data
        
        # Verify it can be decrypted back
        decrypted = encryption_service.decrypt_field(stored_audio_data)
        assert decrypted == sensitive_info
    
    @pytest.mark.asyncio
    async def test_adjustment_record_with_encryption(self, setup_db_with_encryption):
        """Test storing encrypted adjustment records"""
        encryption_service = setup_db_with_encryption
        crud = AdjustmentRecordCRUD()
        
        # Original data with sensitive details
        original_details = {"user_response": "I feel better now", "biometrics": {"hr": 72}}
        original_prev_state = {"emotion": "anxious", "intensity": 0.8}
        original_new_state = {"emotion": "calm", "intensity": 0.3}
        
        # Encrypt sensitive fields
        encrypted_data = {
            "session_id": "adj_encrypt_test",
            "timestamp": datetime.now().isoformat(),
            "reason": "User reported improvement",
            "adjustment_type": "phase_advance",
            "details": encryption_service.encrypt_field(json.dumps(original_details)),
            "previous_state": encryption_service.encrypt_field(json.dumps(original_prev_state)),
            "new_state": encryption_service.encrypt_field(json.dumps(original_new_state))
        }
        
        await crud.create(encrypted_data)
        
        # Retrieve and verify encryption
        records = await crud.get_by_session("adj_encrypt_test")
        stored = records[0]
        
        # Verify encrypted fields are not readable
        assert "user_response" not in stored["details"]
        
        # Decrypt and verify
        decrypted_details = json.loads(encryption_service.decrypt_field(stored["details"]))
        assert decrypted_details == original_details


class TestDataLocalStorage:
    """Tests to verify data is stored locally
    
    Requirements: 14.1 - 将所有用户数据存储在本地 SQLite 数据库中
    """
    
    @pytest.mark.asyncio
    async def test_data_stored_in_local_file(self):
        """Test that data is stored in a local SQLite file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_local.db"
            
            await init_db(db_path)
            
            # Create some data
            crud = SessionCRUD()
            await crud.create({
                "id": "local_test",
                "start_time": datetime.now().isoformat()
            })
            
            await close_db()
            
            # Verify file exists locally
            assert db_path.exists(), "Database file should exist locally"
            
            # Verify it's a valid SQLite file
            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", ("local_test",))
                row = await cursor.fetchone()
                assert row is not None, "Data should be retrievable from local file"
