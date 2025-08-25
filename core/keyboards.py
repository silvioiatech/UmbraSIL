# bot/core/keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class BotKeyboards:
    """Centralized keyboard layouts"""
    
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Main menu keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("💰 Finance", callback_data="menu_finance"),
                InlineKeyboardButton("⚙️ Business", callback_data="menu_business")
            ],
            [
                InlineKeyboardButton("📊 Monitor", callback_data="menu_monitoring"),
                InlineKeyboardButton("🧠 AI", callback_data="menu_ai")
            ],
            [
                InlineKeyboardButton("📈 Reports", callback_data="menu_bi"),
                InlineKeyboardButton("ℹ️ Status", callback_data="menu_status")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def finance_menu() -> InlineKeyboardMarkup:
        """Finance section keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("💸 Add Expense", callback_data="add_expense"),
                InlineKeyboardButton("💰 Add Income", callback_data="add_income")
            ],
            [
                InlineKeyboardButton("📊 Reports", callback_data="finance_reports"),
                InlineKeyboardButton("💳 Balance", callback_data="show_balance")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def business_menu() -> InlineKeyboardMarkup:
        """Business section keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("➕ New Client", callback_data="create_client"),
                InlineKeyboardButton("📋 List Clients", callback_data="list_clients")
            ],
            [
                InlineKeyboardButton("🖥️ VPS Status", callback_data="vps_status"),
                InlineKeyboardButton("📊 Metrics", callback_data="system_metrics")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="main_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
