# bot/core/messages.py

class BotMessages:
    """Centralized message templates"""
    
    WELCOME = """
🤖 **Personal Bot Assistant v{version}**

Welcome {first_name}! 👋

Your comprehensive business management platform is ready:

🎯 **Available Features:**
💰 **Finance Management** - Expenses, income, reports
⚙️ **Business Workflows** - n8n clients, VPS monitoring
📊 **System Monitoring** - Alerts, health reports
🧠 **AI Assistant** - Natural language, voice, smart responses
📈 **Business Intelligence** - Analytics, forecasting

🚀 **Quick Start:**
• Use /menu for the main interface
• Try natural language commands
• Use /help for all commands

**System Status:** All systems operational ✅
    """
    
    MENU = """
🎛️ **Main Menu** - Choose a category:

Choose an option below to manage your systems:
    """
    
    HELP = """
📚 **Available Commands:**

🔧 **Core Commands:**
/start - Welcome message
/help - Show this help
/menu - Main menu
/status - System status

💰 **Finance:**
/add_expense - Add expense
/add_income - Add income
/balance - Show balance
/expenses_month - Monthly report

⚙️ **Business:**
/create_client - Create n8n client
/list_clients - List all clients
/client_status - Check client status

📊 **Monitoring:**
/alerts - Show active alerts
/start_monitoring - Enable monitoring
/health_report - System health

🧠 **AI & BI:**
Just chat naturally or use /ask
    """
    
    STATUS = """
📊 **System Status Report**

🤖 **Core System:**
• Status: ✅ Online
• Version: {version}
• Environment: {environment}
• Uptime: {uptime}
• Database: {db_status}

🔐 **Security:**
• Auth: ✅ Enabled ({user_count} users)
• Encryption: ✅ Active
• Logs: ✅ Enabled

📈 **Performance:**
• Commands: {total_commands}
• Success Rate: {success_rate}%
• Response Time: <1s
    """
