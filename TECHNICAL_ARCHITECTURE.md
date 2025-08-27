# UmbraSIL - Technical Architecture Documentation

## System Overview

UmbraSIL is a modular Telegram bot built with Python 3.11+ that provides comprehensive personal and business management capabilities through a secure, scalable architecture.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    TELEGRAM API                             │
└─────────────────────┬───────────────────────────────────────┘
                      │ Bot API Polling
┌─────────────────────▼───────────────────────────────────────┐
│                 UMBRASIL BOT                                │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              AUTHENTICATION LAYER                      ││
│  │           (User ID-based access control)              ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │                 CORE BOT ENGINE                        ││
│  │  • Command Handlers    • Event Processing             ││
│  │  • Message Router      • Error Management             ││
│  │  • Metrics Collection  • Lifecycle Management        ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                  MODULE SYSTEM                              │
│  ┌───────────┐ ┌────────────┐ ┌──────────┐ ┌──────────────┐ │
│  │    AI     │ │  BUSINESS  │ │ FINANCE  │ │ MONITORING   │ │
│  │ Assistant │ │ Operations │ │ Manager  │ │   System     │ │
│  └───────────┘ └────────────┘ └──────────┘ └──────────────┘ │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              EXTERNAL INTEGRATIONS                          │
│  ┌───────────┐ ┌─────────┐ ┌──────────┐ ┌─────────────────┐ │
│  │  OpenAI   │ │   VPS   │ │ Docker   │ │     Railway     │ │
│  │  Claude   │ │   SSH   │ │   API    │ │  Health Check   │ │
│  └───────────┘ └─────────┘ └──────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Bot Engine (`main.py`)

The central orchestrator that manages:

```python
class UmbraSILBot:
    """Main bot class - simplified and robust"""
    
    def __init__(self):
        self.metrics = BotMetrics()        # Performance tracking
        self.auth = SimpleAuth()           # Authentication system  
        self.application = Application()    # Telegram bot application
```

**Key Responsibilities:**
- Command routing and handling
- User authentication
- Message processing
- Error management
- Metrics collection

### 2. Authentication System

**File:** `bot/core.py`, `core/security.py`

```python
class SimpleAuth:
    def __init__(self):
        self.allowed_users = [int(x) for x in os.getenv("ALLOWED_USER_IDS").split(",")]
    
    async def authenticate_user(self, user_id: int) -> bool:
        return user_id in self.allowed_users
```

**Security Features:**
- User ID whitelist-based access control
- Decorator-based command protection
- Environment variable configuration
- Session tracking

### 3. Module System

#### AI Assistant (`bot/modules/ai/`)

```python
class AIManager:
    def __init__(self, db):
        self.openai_client = AsyncOpenAI()
        self.claude_client = anthropic.AsyncAnthropic()
        self.user_contexts = {}  # Conversation context per user
```

**Capabilities:**
- Multi-provider AI support (OpenAI, Claude)
- Context-aware conversations
- Async API handling
- Error resilience

#### Business Operations (`bot/modules/business/`)

```python
class BusinessManager:
    def get_menu(self):
        return {
            "text": "⚙️ **Business Operations**",
            "keyboard": [
                [{"text": "🏭 n8n Clients", "callback_data": "n8n_clients"}],
                [{"text": "🐳 Docker Status", "callback_data": "docker_status"}]
            ]
        }
```

**Features:**
- n8n workflow management
- Docker container monitoring
- VPS status checking
- Interactive menu system

#### System Monitoring (`bot/modules/monitoring/`)

```python
class MonitoringManager:
    async def get_recent_logs(self, limit: int = 10):
        # Real-time log monitoring
    
    async def check_services(self) -> bool:
        # Service health verification
```

**Monitoring Capabilities:**
- Real-time system metrics
- Service health checks
- Log aggregation
- Alert management

#### Finance Management (`bot/modules/finance/`)

```python
class FinanceManager:
    def get_menu(self):
        return {
            "keyboard": [
                [{"text": "💸 Add Expense"}, {"text": "💰 Add Income"}],
                [{"text": "📊 Balance"}, {"text": "📈 Report"}]
            ]
        }
```

**Financial Features:**
- Expense/income tracking
- Balance management
- Financial reporting
- Receipt processing (OCR ready)

### 4. VPS Management (`main_backup.py`)

```python
class VPSMonitor:
    def __init__(self):
        self.host = os.getenv("VPS_HOST")
        self.ssh_client = None
    
    async def execute_command(self, command: str, timeout: int = 30):
        # Secure SSH command execution
```

**VPS Capabilities:**
- SSH-based remote management
- System statistics collection
- Command execution with timeout
- Network monitoring

## Data Flow

### 1. Message Processing Flow

```
Telegram Message → Authentication → Command Router → Module Handler → Response
                     ↓
                 Metrics Collection → Performance Tracking
                     ↓
                 Error Handling → User Feedback
```

### 2. Command Execution Flow

```python
@require_auth
async def handle_command(update, context):
    # 1. Authenticate user
    # 2. Parse command/callback data
    # 3. Route to appropriate module
    # 4. Execute business logic
    # 5. Format response
    # 6. Send to user
    # 7. Log metrics
```

### 3. Module Integration Flow

```
Bot Core → Module Manager → Specific Module → External API → Response Processing
    ↑                                               ↓
    └─────────── Error Handling ←── Response ←──────┘
```

## Configuration Management

### Environment Variables

```bash
# Core Configuration
TELEGRAM_BOT_TOKEN=bot_token_from_botfather
ALLOWED_USER_IDS=comma_separated_user_ids
SECRET_KEY=secure_secret_key

# Feature Flags
ENABLE_FINANCE=true
ENABLE_BUSINESS=true
ENABLE_MONITORING=true
ENABLE_AI=true

# AI Configuration
OPENAI_API_KEY=your_openai_key
CLAUDE_API_KEY=your_claude_key

# VPS Configuration
VPS_HOST=your.vps.host
VPS_USERNAME=vps_user
VPS_PRIVATE_KEY=base64_encoded_private_key

# Monitoring Configuration
CPU_THRESHOLD=80
MEMORY_THRESHOLD=80
DISK_THRESHOLD=85
```

### Feature Flags System

```python
class SystemConfig:
    ENABLE_FINANCE = os.getenv("ENABLE_FINANCE", "true").lower() == "true"
    ENABLE_BUSINESS = os.getenv("ENABLE_BUSINESS", "true").lower() == "true"
    ENABLE_MONITORING = os.getenv("ENABLE_MONITORING", "true").lower() == "true"
    ENABLE_AI = os.getenv("ENABLE_AI", "true").lower() == "true"
```

## Error Handling Strategy

### 1. Hierarchical Error Management

```python
class BotError(Exception):
    """Base class for bot errors"""

class DatabaseError(BotError):
    """Database related errors"""

class AuthenticationError(BotError):
    """Authentication related errors"""
```

### 2. Graceful Degradation

```python
async def handle_error(self, update, context):
    """Handle errors gracefully"""
    error = context.error
    logger.error(f"Update {update} caused error: {error}")
    
    # User-friendly error message
    await update.effective_message.reply_text(
        "❌ An error occurred. Please try again or use /start to restart."
    )
```

### 3. Circuit Breaker Pattern

```python
async def ai_request_with_fallback(self, message):
    try:
        # Try OpenAI first
        return await self.openai_client.chat.completions.create(...)
    except Exception:
        try:
            # Fallback to Claude
            return await self.claude_client.messages.create(...)
        except Exception:
            # Final fallback
            return "AI services temporarily unavailable"
```

## Performance Considerations

### 1. Async/Await Pattern

All I/O operations use async/await for non-blocking execution:

```python
async def show_system_status(self, update, context):
    """Non-blocking system status collection"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    # ... other operations
```

### 2. Connection Management

```python
class VPSMonitor:
    async def execute_command(self, command, timeout=30):
        """Reuse SSH connections when possible"""
        if not self.ssh_client:
            if not await self.connect():
                return {"success": False, "error": "Connection failed"}
```

### 3. Resource Monitoring

```python
class BotMetrics:
    def __init__(self):
        self.response_times = []
        self.command_count = 0
        self.error_count = 0
    
    def log_command(self, response_time: float):
        self.command_count += 1
        self.response_times.append(response_time)
```

## Security Architecture

### 1. Authentication Layer

```python
def require_auth(func):
    """Authentication decorator for all commands"""
    async def wrapper(update, context):
        if not await self.auth.authenticate_user(user_id):
            await update.message.reply_text("🚫 Access denied")
            return
        return await func(update, context)
    return wrapper
```

### 2. Command Sanitization

```python
async def execute_command(self, command: str):
    """Sanitize and validate commands before execution"""
    # Input validation and sanitization
    sanitized_command = self.sanitize_input(command)
    
    # Execute with timeout
    result = await self.ssh_client.exec_command(
        sanitized_command, timeout=30
    )
```

### 3. Secret Management

- Environment variables for sensitive data
- Base64 encoding for keys
- No hardcoded secrets in code
- Separate configuration for each environment

## Deployment Architecture

### Railway Platform Integration

```yaml
# railway.toml
[deploy]
startCommand = "python main.py"
healthcheckPath = "/"
healthcheckTimeout = 300

[metrics]
enabled = true
path = "/metrics"
```

### Docker Configuration

```dockerfile
FROM python:3.11-slim
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run application
CMD ["python", "main.py"]
```

### Health Check System

```python
async def health_check(request):
    """Health endpoint for Railway"""
    return web.Response(
        text='{"status":"healthy","service":"umbrasil-bot"}'
    )
```

## Scalability Considerations

### Current Limitations
- Single instance deployment
- In-memory state storage
- No horizontal scaling capability

### Scaling Strategies
1. **Database Integration**: Add persistent storage
2. **State Management**: External session storage
3. **Load Balancing**: Multiple bot instances
4. **Microservices**: Split modules into services

## Monitoring & Observability

### Current Metrics
- Command execution count
- Response times
- Error rates
- User activity tracking
- System resource usage

### Logging Strategy
```python
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
```

### Health Monitoring
- Bot uptime tracking
- Service availability checks
- Resource usage alerts
- Error rate monitoring

## Future Architecture Considerations

### Recommended Enhancements
1. **Database Layer**: PostgreSQL integration
2. **Caching**: Redis for session management
3. **Queue System**: Celery for background tasks
4. **API Gateway**: External API management
5. **Service Mesh**: Microservices communication
6. **Observability**: Prometheus + Grafana

---
*Architecture Documentation - Version 1.0*
*Last Updated: 2025-01-27*