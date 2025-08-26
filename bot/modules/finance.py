from telegram.ext import Application

class FinanceManager:
    def __init__(self, db):
        self.db = db
    
    def is_operational(self) -> bool:
        return True
    
    async def setup_handlers(self, app: Application):
        pass

    def get_menu(self):
        return {
            "text": "💰 Finance Menu",
            "keyboard": [
                # Add your finance menu buttons here
            ]
        }
