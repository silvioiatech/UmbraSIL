import os

class AIConfig:
    """AI Assistant configuration"""
    
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
    
    # Models
    OPENAI_MODEL = "gpt-4-turbo-preview"
    CLAUDE_MODEL = "claude-3-sonnet-20240229"
    
    # Context Management
    MAX_CONTEXT_MESSAGES = 20
    CONTEXT_EXPIRY = 3600  # 1 hour
    MEMORY_TTL = 24 * 3600  # 24 hours
    
    # Voice Settings
    VOICE_ENABLED = True
    MAX_VOICE_LENGTH = 300  # seconds
    VOICE_MODEL = "whisper-1"
    
    # Features
    PROACTIVE_SUGGESTIONS = True
    AUTO_CATEGORIZATION = True
    
    # Rate Limits
    MAX_REQUESTS_PER_MIN = 20
    COOLDOWN_PERIOD = 60  # seconds
    
    # Response Settings
    MAX_TOKENS = 2000
    TEMPERATURE = 0.7
    STREAM = True
