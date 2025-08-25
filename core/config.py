# bot/core/config.py
import os
from typing import List

class SystemConfig:
    """System-wide configuration management"""
    
    # Core settings
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8351097023:AAGOeOW9IyZU7MDPKK1b76FhlggsjAlqeaQ")
    DATABASE_URL = os.getenv("DATABASE_URL")
    ALLOWED_USER_IDS = [8286836821]  # Your Telegram ID
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this")
    
    # Environment settings
    ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Feature flags
    ENABLE_FINANCE = os.getenv("ENABLE_FINANCE", "true").lower() == "true"
    ENABLE_BUSINESS = os.getenv("ENABLE_BUSINESS", "true").lower() == "true"
    ENABLE_MONITORING = os.getenv("ENABLE_MONITORING", "true").lower() == "true"
    ENABLE_AI = os.getenv("ENABLE_AI", "true").lower() == "true"
    ENABLE_BI = os.getenv("ENABLE_BI", "true").lower() == "true"
    
    # System information
    VERSION = "1.0.0"
    BUILD_DATE = "2025-08-25"
