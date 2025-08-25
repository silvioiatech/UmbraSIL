# bot/core/database.py
import asyncpg
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from .config import SystemConfig

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles PostgreSQL connections and operations"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool = None
    
    async def initialize(self):
        """Initialize connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool initialized")
            await self.create_tables()
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def create_tables(self):
        """Create necessary database tables"""
        async with self.pool.acquire() as conn:
            # Users table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_user_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    is_authorized BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_login TIMESTAMP WITH TIME ZONE
                )
            ''')
            
            # Bot logs
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS bot_logs (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    command VARCHAR(255),
                    message TEXT,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                )
            ''')
            
            # System metrics
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id SERIAL PRIMARY KEY,
                    metric_type VARCHAR(100) NOT NULL,
                    metric_value FLOAT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    metadata JSONB
                )
            ''')
            
            # Expenses table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS expenses (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    description TEXT,
                    date DATE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    receipt_path VARCHAR(500)
                )
            ''')
            
            # Income table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS income (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    source VARCHAR(100) NOT NULL,
                    description TEXT,
                    date DATE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            logger.info("Database tables created/verified")
    
    async def log_command(self, user_id: int, command: str, message: str, success: bool = True, error: str = None):
        """Log bot commands"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO bot_logs (user_id, command, message, success, error_message)
                VALUES ($1, $2, $3, $4, $5)
            ''', user_id, command, message, success, error)
    
    async def get_user(self, telegram_user_id: int) -> Optional[Dict[str, Any]]:
        """Get user from database"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT * FROM users WHERE telegram_user_id = $1',
                telegram_user_id
            )
            return dict(row) if row else None
    
    async def create_or_update_user(self, telegram_user_id: int, username: str = None, 
                                  first_name: str = None, last_name: str = None) -> Dict[str, Any]:
        """Create or update user"""
        async with self.pool.acquire() as conn:
            # Check if authorized
            is_authorized = telegram_user_id in SystemConfig.ALLOWED_USER_IDS
            
            await conn.execute('''
                INSERT INTO users (telegram_user_id, username, first_name, last_name, is_authorized, last_login)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (telegram_user_id)
                DO UPDATE SET 
                    username = $2,
                    first_name = $3,
                    last_name = $4,
                    last_login = NOW()
            ''', telegram_user_id, username, first_name, last_name, is_authorized)
            
            return await self.get_user(telegram_user_id)
