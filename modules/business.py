from telegram.ext import Application

class BusinessManager:
    def __init__(self, db):
        self.db = db
    
    def is_operational(self) -> bool:
        return True
    
    async def setup_handlers(self, app: Application):
        pass

    def get_menu(self):
        return {
            "text": "⚙️ Business Menu",
            "keyboard": [
                # Add your business menu buttons here
            ]
        }

    def get_analytics_menu(self):
        return {
            "text": "📈 Analytics Menu",
            "keyboard": [
                # Add your analytics menu buttons here
            ]
        }
