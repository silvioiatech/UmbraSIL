"""
UmbraSIL Bot Modules Package
Created by: silvioiatech
Created at: 2025-08-26 00:33:19
"""

from .finance import FinanceManager
from .business import BusinessManager
from .monitoring import MonitoringManager
from .ai import AIManager, AIConfig

__version__ = "1.0.0"
__author__ = "silvioiatech"
__created_at__ = "2025-08-26 00:33:19"

# Make module classes available at package level
__all__ = [
    'FinanceManager',
    'BusinessManager',
    'MonitoringManager',
    'AIManager',
    'AIConfig'
]
