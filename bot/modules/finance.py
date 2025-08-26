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
            "text": "💰 **Finance Management**\n\nTrack your financial activities:",
            "keyboard": [
                [
                    {"text": "💸 Add Expense", "callback_data": "add_expense"},
                    {"text": "💰 Add Income", "callback_data": "add_income"}
                ],
                [
                    {"text": "📊 Balance", "callback_data": "show_balance"},
                    {"text": "📈 Report", "callback_data": "finance_report"}
                ]
            ]
        }
