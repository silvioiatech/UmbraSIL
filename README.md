# UmbraSIL - Intelligent Telegram Bot Assistant

A comprehensive and modular Telegram bot for personal and business automation, system monitoring, and AI-powered assistance. **Ready for one-click Railway deployment!**

## 🌟 Features

### ✅ Fully Active Features
- **🤖 Telegram Bot Interface**: Interactive commands and button menus
- **🔐 User Authentication**: Secure access control via user ID whitelist
- **📊 System Monitoring**: Real-time CPU, memory, and disk usage tracking
- **⚡ Performance Metrics**: Command tracking, response times, and uptime monitoring
- **💬 Natural Language Processing**: Advanced text processing and command recognition
- **🏠 Interactive Menus**: User-friendly navigation with inline keyboards
- **🤖 AI Integration**: OpenAI GPT-4 and Anthropic Claude support with context management
- **💰 Finance Management**: Complete expense tracking, income recording, and balance reports
- **⚙️ Business Operations**: n8n workflow management, Docker container monitoring
- **🖥️ VPS Management**: SSH-based remote server administration
- **📈 Advanced Monitoring**: System health checks, alerts, and performance analytics

### 🛠️ Infrastructure Ready
- **🚀 Railway Deployment**: Configured for instant one-click deployment
- **🐳 Docker Support**: Complete containerized deployment option
- **📝 Comprehensive Logging**: Structured logging with configurable levels
- **🔄 Health Checks**: Built-in monitoring endpoints for deployment platforms
- **⚙️ Environment Configuration**: Complete .env example with all possible variables
- **📦 Dependency Management**: Full requirements.txt with all necessary packages

## 🚀 Railway Deployment (Recommended)

### One-Click Deployment Steps

1. **Fork this repository** to your GitHub account

2. **Create a Railway account** at [railway.app](https://railway.app)

3. **Deploy from GitHub**:
   - Click "New Project" in Railway
   - Select "Deploy from GitHub repo"
   - Choose your forked UmbraSIL repository
   - Railway will automatically detect the configuration

4. **Set Environment Variables** in Railway:
   
   **Required (Minimum for basic functionality):**
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
   ALLOWED_USER_IDS=your_telegram_user_id
   ```

   **Optional (Enable specific features):**
   ```
   # AI Features
   OPENAI_API_KEY=your_openai_api_key
   CLAUDE_API_KEY=your_claude_api_key
   
   # VPS Management
   VPS_HOST=your.server.ip
   VPS_USERNAME=your_username
   VPS_PASSWORD=your_password
   
   # Feature Toggles (all default to true)
   ENABLE_AI=true
   ENABLE_FINANCE=true
   ENABLE_BUSINESS=true
   ENABLE_MONITORING=true
   ```

5. **Deploy**:
   - Railway will automatically build and deploy
   - Check the deployment logs for any issues
   - Your bot will be live and ready to use!

### Getting Your Bot Token

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Type `/newbot` and follow the instructions
3. Choose a name and username for your bot
4. Copy the API token provided
5. Use this token as your `TELEGRAM_BOT_TOKEN`

### Getting Your User ID

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. Copy the User ID number
3. Use this as your `ALLOWED_USER_IDS`

## 💬 Bot Usage

### Basic Commands
- `/start` - Initialize the bot and see welcome message
- `/help` - Complete help with all features
- `/menu` - Main navigation menu
- `/status` - System status and metrics
- `/ai` - Access AI Assistant (if enabled)
- `/finance` - Finance management (if enabled)
- `/business` - Business operations (if enabled)

### Text Interactions
- **AI Chat**: `ai: your question here`
- **Add Expense**: `expense: 25.50 food Pizza for lunch`
- **Add Income**: `income: 2500 salary Monthly payment`
- **Natural language**: The bot responds to greetings and common phrases

### Interactive Features
- **Button Navigation**: All features accessible via inline keyboards
- **Real-time Monitoring**: Live system metrics and health checks
- **Contextual AI**: Maintains conversation context across messages
- **Secure Access**: Only authorized users can access the bot

## 🔧 Local Development

### Prerequisites
- Python 3.11+
- Telegram Bot Token
- Your Telegram User ID

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/silvioiatech/UmbraSIL.git
   cd UmbraSIL
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   # Copy the example environment file
   cp .env .env.local
   # Edit .env.local with your values
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

## 📋 Environment Variables Reference

See the `.env` file for a complete list of all possible environment variables. Key categories:

- **Core Settings**: Bot token, user IDs, security keys
- **Feature Flags**: Enable/disable modules independently
- **AI Configuration**: OpenAI and Claude API settings
- **Finance Settings**: Currency, Google Cloud Vision for receipt scanning
- **Business Settings**: VPS credentials, Docker configuration
- **Monitoring**: Alert thresholds, notification settings

## 🏗️ Architecture

### Modular Design
- **Core Bot**: Authentication, commands, basic functionality
- **AI Manager**: OpenAI and Claude integration with context management
- **Finance Manager**: Transaction tracking and financial analytics
- **Business Manager**: VPS and Docker operations
- **Monitoring Manager**: System health and performance tracking

### Module Status

| Module | Status | Description | Activation |
|--------|--------|-------------|------------|
| **Core Bot** | ✅ Active | Basic commands, authentication, menus | Always on |
| **System Monitoring** | ✅ Active | CPU, memory, disk monitoring | Always on |
| **AI Assistant** | ✅ Active | OpenAI/Claude integration | Add API keys |
| **Finance Manager** | ✅ Active | Expense tracking, income, reports | Set `ENABLE_FINANCE=true` |
| **Business Ops** | ✅ Active | Docker, VPS management | Set `ENABLE_BUSINESS=true` |
| **Advanced Monitoring** | ✅ Active | Health checks, alerts | Set `ENABLE_MONITORING=true` |

## 🐳 Docker Deployment

```bash
# Build the image
docker build -t umbrasil-bot .

# Run with environment file
docker run -d --env-file .env --name umbrasil umbrasil-bot

# View logs
docker logs -f umbrasil
```

## 📊 Monitoring & Health Checks

The bot includes comprehensive monitoring:

- **System Metrics**: CPU, memory, disk usage
- **Performance Tracking**: Command count, success rate, uptime
- **Health Endpoints**: Ready for platform monitoring
- **Error Handling**: Comprehensive exception management
- **Logging**: Structured logs with configurable levels

## 🔒 Security Features

- **User Authentication**: Whitelist-based access control
- **Rate Limiting**: Built-in protection against spam
- **Secure Configuration**: Environment-based secret management
- **Error Isolation**: Module failures don't crash the bot
- **Input Validation**: Sanitized user input processing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is open source and available under the MIT License.

## 👨‍💻 Author

**silvioiatech**
- Telegram: [@silvioiatech](https://t.me/silvioiatech)
- GitHub: [@silvioiatech](https://github.com/silvioiatech)

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Excellent Telegram Bot API wrapper
- [Railway](https://railway.app) - Seamless deployment platform
- [OpenAI](https://openai.com) & [Anthropic](https://anthropic.com) - AI capabilities

## 🚨 Support

For support or questions:
1. Check the [Issues](https://github.com/silvioiatech/UmbraSIL/issues) page
2. Contact [@silvioiatech](https://t.me/silvioiatech) on Telegram
3. Open a new issue with detailed information

## 📈 Version History

- **v1.2.0** - Current: Full feature integration, Railway-ready deployment
- **v1.1.0** - Core bot with modular architecture
- **v1.0.0** - Initial release with basic functionality

---

## 🚀 **Ready to Deploy on Railway!**

This bot is fully configured for one-click Railway deployment with all features activated and working. Simply fork, deploy, and add your bot token to get started!

**Happy automating! 🤖✨**
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