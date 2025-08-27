# bot/core/__init__.py
from .config import SystemConfig
from .logger import logger, setup_logging
from .security import require_auth

# Optional database import
try:
    from .database import DatabaseManager
    DATABASE_AVAILABLE = True
except ImportError:
    DatabaseManager = None
    DATABASE_AVAILABLE = False
    logger.warning("Database functionality not available - install asyncpg for full features")

__all__ = ['SystemConfig', 'DatabaseManager', 'logger', 'setup_logging', 'require_auth', 'DATABASE_AVAILABLE']
