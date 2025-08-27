# 🚀 Railway Quick Start Guide

## Deploy UmbraSIL Bot in 5 Minutes

### Step 1: Get Your Bot Token
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot`
3. Choose a name and username for your bot
4. **Copy the API token** (looks like: `123456789:ABCDEF...`)

### Step 2: Get Your User ID
1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. **Copy your User ID** (a number like: `123456789`)

### Step 3: Deploy on Railway
1. **Fork this repository** to your GitHub account
2. Go to [railway.app](https://railway.app) and sign up/login
3. Click **"New Project"**
4. Select **"Deploy from GitHub repo"**
5. Choose your forked **UmbraSIL** repository
6. Railway will automatically detect the configuration

### Step 4: Configure Environment Variables
In Railway, go to your project → **Variables** tab and add:

**Required (minimum setup):**
```
TELEGRAM_BOT_TOKEN = your_bot_token_from_step_1
ALLOWED_USER_IDS = your_user_id_from_step_2
```

**Optional (for AI features):**
```
OPENAI_API_KEY = your_openai_api_key
CLAUDE_API_KEY = your_claude_api_key
```

**Optional (for VPS management):**
```
VPS_HOST = your.server.ip.address
VPS_USERNAME = your_server_username
VPS_PASSWORD = your_server_password
```

### Step 5: Deploy and Test
1. Railway will automatically build and deploy
2. Check the **Deployments** tab for status
3. Once deployed, message your bot on Telegram
4. Send `/start` to begin!

## 🎯 What You Get Out of the Box

### Always Available
- ✅ System monitoring and status
- ✅ Interactive button menus
- ✅ Secure user authentication
- ✅ Finance tracking (expenses/income)
- ✅ Business operations monitoring
- ✅ Health checks and alerts

### With API Keys
- 🤖 **AI Chat**: `ai: your question here`
- 🖥️ **VPS Management**: Remote server monitoring
- 📊 **Advanced Analytics**: Performance insights

## 💬 Quick Commands to Try

```
/start          - Welcome and feature overview
/help           - Complete command reference
/menu           - Interactive navigation
/status         - System status and metrics
ai: hello       - AI chat (if configured)
expense: 25 food Pizza for lunch - Add expense
income: 2500 salary Monthly pay - Add income
```

## 🔧 Troubleshooting

**Bot not responding?**
- Check your bot token is correct
- Verify your user ID is in ALLOWED_USER_IDS
- Check Railway deployment logs

**Features missing?**
- Add the corresponding API keys
- Check feature flags (ENABLE_AI=true, etc.)

**Need help?**
- Check the full README.md
- Contact [@silvioiatech](https://t.me/silvioiatech)

---

**🎉 That's it! Your bot is now running with all features active!**