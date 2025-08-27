# 🚀 Railway Deployment Guide - UmbraSIL Bot

## ✅ Files Updated for Deployment

1. **requirements.txt** - Simplified to only essential dependencies
2. **railway.toml** - Fixed configuration for bot deployment
3. **Procfile** - Changed to worker process
4. **.env.example** - Created as template

## 📋 Pre-Deployment Checklist

### 1. Test Locally First
```bash
cd /Users/silviocorreia/Documents/GitHub/UmbraSIL
python test_minimal.py
```

### 2. Commit Changes
```bash
git add .
git commit -m "Fix Railway deployment - minimize dependencies"
git push origin main
```

## 🚂 Railway Deployment Steps

### Step 1: Prepare Railway Account
1. Go to [railway.app](https://railway.app)
2. Sign in with GitHub
3. If you have a failed deployment, delete it first

### Step 2: Create New Project
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose your `UmbraSIL` repository
4. Railway will automatically start deployment

### Step 3: Configure Environment Variables
Go to your project's Variables tab and add:

#### Required Variables:
```
TELEGRAM_BOT_TOKEN=YOUR_ACTUAL_BOT_TOKEN_HERE
ALLOWED_USER_IDS=YOUR_TELEGRAM_USER_ID
```

#### Recommended Settings:
```
LOG_LEVEL=INFO
ENABLE_FINANCE=true
ENABLE_MONITORING=true
ENABLE_AI=false
ENABLE_BUSINESS=false
ENABLE_BI=false
```

### Step 4: Monitor Deployment
1. Go to "Deployments" tab
2. Click on the active deployment
3. Watch the logs for any errors
4. Wait for "Deployment live" status

## 🧪 Test Your Deployed Bot

1. Open Telegram
2. Find your bot
3. Send these commands:
   - `/start` - Should show welcome message
   - `/help` - Should show available commands
   - `/status` - Should show system status
   - `/menu` - Should show interactive menu

## 🔧 Troubleshooting Common Issues

### Issue 1: "Module not found" errors
**Solution:** The requirements.txt has been simplified. Only core modules are installed.

### Issue 2: Bot doesn't respond
**Check:**
- Is TELEGRAM_BOT_TOKEN correct?
- Is your user ID in ALLOWED_USER_IDS?
- Check Railway logs for errors

### Issue 3: Deployment fails
**Try:**
1. Remove all optional dependencies from requirements.txt
2. Set all ENABLE_* flags to false except ENABLE_MONITORING
3. Redeploy

### Issue 4: "Token not set" error
**Fix:** Make sure TELEGRAM_BOT_TOKEN is set in Railway variables, not in code

## 📦 Minimal Working Configuration

If all else fails, use this absolute minimum configuration:

**requirements.txt:**
```
python-telegram-bot>=20.7
python-dotenv>=1.0.0
psutil>=5.9.5
```

**Environment Variables:**
```
TELEGRAM_BOT_TOKEN=your_token
ALLOWED_USER_IDS=your_id
ENABLE_FINANCE=false
ENABLE_BUSINESS=false
ENABLE_MONITORING=true
ENABLE_AI=false
ENABLE_BI=false
```

## ✨ Adding Features Later

Once the bot is working, you can gradually add features:

1. **Enable AI:**
   - Uncomment `openai>=1.3.7` in requirements.txt
   - Set `ENABLE_AI=true`
   - Add `OPENAI_API_KEY=your_key`

2. **Enable VPS Management:**
   - Uncomment `paramiko>=3.3.1` in requirements.txt
   - Set `ENABLE_BUSINESS=true`
   - Add VPS credentials

3. **Enable Database:**
   - Uncomment `asyncpg>=0.29.0` in requirements.txt
   - Add `DATABASE_URL` variable

## 📞 Support

If you still have issues:
1. Check Railway deployment logs
2. Run `test_minimal.py` locally
3. Start with absolute minimum configuration
4. Add features one by one

## 🎉 Success Indicators

Your bot is successfully deployed when:
- Railway shows "Deployment live"
- Bot responds to /start command
- No errors in Railway logs
- System status shows "All systems operational!"

---

**Remember:** Start simple, add complexity gradually!
