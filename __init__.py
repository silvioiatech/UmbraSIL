"""
UmbraSIL Bot Package
Created by: silvioiatech
Created at: 2025-08-26 00:31:13
"""

from .core import (
    DatabaseManager,
    SecurityManager,
    BotError,
    DatabaseError,
    AuthenticationError,
    require_auth,
    logger
)

from .modules.finance import FinanceManager
from .modules.business import BusinessManager
from .modules.monitoring import MonitoringManager
from .modules.ai import AIManager, AIConfig

__version__ = "1.0.0"
__author__ = "silvioiatech"
__created_at__ = "2025-08-26 00:31:13"

# Make common classes available at package level
__all__ = [
    'DatabaseManager',
    'SecurityManager',
    'FinanceManager',
    'BusinessManager',
    'MonitoringManager',
    'AIManager',
    'AIConfig',
    'BotError',
    'DatabaseError',
    'AuthenticationError',
    'require_auth',
    'logger'
]
