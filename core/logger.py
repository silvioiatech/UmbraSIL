# bot/core/logger.py
import logging
from datetime import datetime
from .config import SystemConfig

def setup_logging():
    """Configure system-wide logging"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    
    logging.basicConfig(
        format=log_format,
        level=getattr(logging, SystemConfig.LOG_LEVEL.upper()),
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('bot.log') if SystemConfig.ENVIRONMENT == 'production' else logging.NullHandler()
        ]
    )
    
    # Set specific logger levels
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Personal Bot Assistant v{SystemConfig.VERSION} starting...")
    logger.info(f"Environment: {SystemConfig.ENVIRONMENT}")
    
    return logger

logger = setup_logging()
