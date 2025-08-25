class BotError(Exception):
    """Base error class"""
    pass

class DatabaseError(BotError):
    """Database related errors"""
    pass

class AuthenticationError(BotError):
    """Authentication related errors"""
    pass

class BusinessError(BotError):
    """Business logic related errors"""
    pass
