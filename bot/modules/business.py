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
            "text": "⚙️ **Business Operations**\n\nManage your business workflows:",
            "keyboard": [
                [
                    {"text": "🏭 n8n Clients", "callback_data": "n8n_clients"},
                    {"text": "🐳 Docker Status", "callback_data": "docker_status"}
                ],
                [
                    {"text": "🖥️ VPS Status", "callback_data": "vps_status"},
                    {"text": "📊 System Metrics", "callback_data": "system_metrics"}
                ]
            ]
        }

    def get_analytics_menu(self):
        return {
            "text": "📈 **Business Analytics**\n\nAnalyze your business performance:",
            "keyboard": [
                [
                    {"text": "📊 Performance", "callback_data": "business_performance"},
                    {"text": "📈 Trends", "callback_data": "business_trends"}
                ]
            ]
        }
