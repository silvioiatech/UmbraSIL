from telegram.ext import Application

class AIConfig:
    pass

class AIManager:
    def __init__(self, db):
        self.db = db
    
    def is_operational(self) -> bool:
        return True
    
    async def setup_handlers(self, app: Application):
        pass

    async def check_services(self) -> bool:
        return True
