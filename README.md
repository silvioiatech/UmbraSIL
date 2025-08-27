# UmbraSIL - Intelligent Telegram Bot Assistant

A comprehensive and modular Telegram bot for personal and business automation, system monitoring, and AI-powered assistance.

## 🌟 Features

### ✅ Active Features (Core)
- **🤖 Telegram Bot Interface**: Interactive commands and button menus
- **🔐 User Authentication**: Secure access control via user ID whitelist
- **📊 System Monitoring**: Real-time CPU, memory, and disk usage
- **⚡ Performance Metrics**: Command tracking, response times, and uptime
- **💬 Natural Language Processing**: Basic intent recognition and responses
- **🏠 Interactive Menus**: User-friendly navigation with inline keyboards

### 🔧 Ready for Activation (Modular)
- **💰 Finance Management**: Expense tracking, income recording, balance reports
- **⚙️ Business Operations**: n8n workflow management, Docker monitoring
- **🖥️ VPS Management**: SSH-based remote server administration
- **🤖 AI Integration**: OpenAI GPT-4 and Anthropic Claude support
- **📈 Analytics**: Performance tracking and business intelligence

### 🛠️ Infrastructure Ready
- **🚀 Railway Deployment**: Configured for one-click deployment
- **🐳 Docker Support**: Containerized deployment option
- **📝 Comprehensive Logging**: Structured logging with configurable levels
- **🔄 Health Checks**: Monitoring endpoints for deployment platforms

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Your Telegram User ID

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/silvioiatech/UmbraSIL.git
   cd UmbraSIL
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

## ⚙️ Configuration

### Essential Environment Variables
```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
ALLOWED_USER_IDS=your_telegram_user_id

# Optional Features
ENABLE_FINANCE=true
ENABLE_BUSINESS=true
ENABLE_MONITORING=true
ENABLE_AI=false
```

### Optional AI Configuration
```bash
# AI Features (optional)
OPENAI_API_KEY=your_openai_api_key
CLAUDE_API_KEY=your_claude_api_key
```

### VPS Management (optional)
```bash
# VPS Management
VPS_HOST=your.server.com
VPS_PORT=22
VPS_USERNAME=your_username
VPS_PRIVATE_KEY=base64_encoded_private_key
```

## 📱 Usage

### Basic Commands
- `/start` - Initialize bot and show welcome message
- `/help` - Display available commands and features
- `/status` - Show system status and performance metrics
- `/menu` - Open interactive main menu

### Interactive Navigation
The bot provides intuitive button-based navigation:
- **📊 System Status** - View bot and server metrics
- **ℹ️ Bot Info** - Version and configuration details
- **❓ Help** - Command reference and feature overview

### Natural Language
Send text messages for basic interactions:
- "hello" → Greeting response
- "status" → System status
- "help" → Help information
- "menu" → Main menu

## 🏗️ Architecture

### Core Components
```
UmbraSIL/
├── main.py              # Primary bot implementation
├── bot/                 # Modular bot components
│   ├── core.py         # Core bot utilities
│   └── modules/        # Feature modules
│       ├── finance.py  # Financial management
│       ├── business.py # Business operations
│       ├── ai.py       # AI integration
│       └── monitoring.py # System monitoring
├── core/               # System infrastructure
│   ├── config.py       # Configuration management
│   ├── database.py     # Database abstraction
│   ├── logger.py       # Logging configuration
│   └── security.py     # Security utilities
└── requirements.txt    # Python dependencies
```

### Module Status

| Module | Status | Description | Activation |
|--------|--------|-------------|------------|
| **Core Bot** | ✅ Active | Basic commands, authentication, menus | Always on |
| **System Monitoring** | ✅ Active | CPU, memory, disk monitoring | Always on |
| **Finance Manager** | 🔧 Ready | Expense tracking, income, reports | Set `ENABLE_FINANCE=true` |
| **Business Ops** | 🔧 Ready | n8n, Docker, VPS management | Set `ENABLE_BUSINESS=true` |
| **AI Assistant** | 🔧 Ready | OpenAI/Claude integration | Add API keys |
| **VPS Management** | 🔧 Ready | SSH remote administration | Add VPS credentials |

## 🚀 Deployment

### Railway (Recommended)
1. Fork this repository
2. Connect to Railway
3. Set environment variables
4. Deploy automatically

### Docker
```bash
docker build -t umbrasil-bot .
docker run -d --env-file .env umbrasil-bot
```

### Manual Server
```bash
# Install dependencies
pip install -r requirements.txt

# Run with systemd (recommended)
sudo systemctl start umbrasil-bot
```

## 🔧 Development

### Testing
```bash
# Run basic functionality test
python test_bot.py

# Test individual modules
python -c "from bot.modules.finance import FinanceManager; print('Finance OK')"
```

### Adding Features
1. Create module in `bot/modules/`
2. Implement required methods (`get_menu()`, `setup_handlers()`)
3. Register in main bot initialization
4. Add environment configuration
5. Update documentation

### Code Structure
- **Authentication**: All commands protected by user ID whitelist
- **Error Handling**: Comprehensive exception management
- **Logging**: Structured logging with performance metrics
- **Modularity**: Clean separation of concerns

## 📊 Monitoring

### Performance Metrics
- Command execution count
- Response time tracking  
- Success/error rates
- User activity monitoring
- System resource usage

### Health Checks
- `/health` endpoint for deployment monitoring
- Service availability checks
- Resource threshold monitoring
- Automated alerting (when configured)

## 🔒 Security

### Access Control
- User ID-based authentication
- Command-level authorization
- Environment variable protection
- Input validation and sanitization

### Best Practices
- No hardcoded secrets
- Encrypted SSH key storage (base64)
- Rate limiting (configurable)
- Audit logging for security events

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow existing code patterns
- Add tests for new features
- Update documentation
- Maintain modularity
- Use type hints

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**silvioiatech**
- Telegram: [@silvioiatech](https://t.me/silvioiatech)
- GitHub: [@silvioiatech](https://github.com/silvioiatech)

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Excellent Telegram Bot API wrapper
- [Railway](https://railway.app) - Seamless deployment platform
- [OpenAI](https://openai.com) & [Anthropic](https://anthropic.com) - AI capabilities

## 📈 Version History

- **v1.1.0** - Current: Core bot with modular architecture
- **v1.0.0** - Initial release with basic functionality

---

**Ready to deploy and use! 🚀**

For support or questions, please open an issue or contact the author.