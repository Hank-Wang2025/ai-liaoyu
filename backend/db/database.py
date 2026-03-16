"""
数据库连接管理
Database connection management
"""
import aiosqlite
from pathlib import Path
from loguru import logger
from typing import Optional

# Database file path
DB_PATH = Path(__file__).parent.parent.parent / "data" / "healing_pod.db"

# Global connection pool
_db_connection: Optional[aiosqlite.Connection] = None


async def get_db() -> aiosqlite.Connection:
    """Get database connection"""
    global _db_connection
    if _db_connection is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db_connection


async def init_db() -> None:
    """Initialize database and create tables"""
    global _db_connection
    
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    _db_connection = await aiosqlite.connect(DB_PATH)
    _db_connection.row_factory = aiosqlite.Row
    
    # Create tables
    await _create_tables(_db_connection)
    logger.info(f"Database initialized at {DB_PATH}")


async def close_db() -> None:
    """Close database connection"""
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None
        logger.info("Database connection closed")


async def _create_tables(db: aiosqlite.Connection) -> None:
    """Create database tables"""
    
    # Sessions table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            status TEXT DEFAULT 'created',
            start_time DATETIME NOT NULL,
            end_time DATETIME,
            initial_emotion_category TEXT,
            initial_emotion_intensity REAL,
            initial_emotion_valence REAL,
            initial_emotion_arousal REAL,
            final_emotion_category TEXT,
            final_emotion_intensity REAL,
            final_emotion_valence REAL,
            final_emotion_arousal REAL,
            plan_id TEXT,
            plan_name TEXT,
            current_phase_index INTEGER DEFAULT 0,
            duration_seconds INTEGER,
            emotion_history TEXT,
            adjustments TEXT,
            user_feedback TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME
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
    
    # Adjustment records table - Requirements: 10.4
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
    logger.debug("Database tables created")
