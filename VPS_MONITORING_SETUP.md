# VPS Monitoring Setup 🖥️

## ✅ What Was Changed

I've updated the bot to monitor your **external VPS** (not the Railway container) via SSH connection. The Health Check now shows:

- **VPS System Resources** (CPU, Memory, Disk)
- **VPS Uptime & Load Average** 
- **Connection Status**
- **Error Handling** for connection issues

## 🔧 VPS Configuration Required

To make this work, you need to set these environment variables in Railway:

### Required Environment Variables:
```bash
VPS_HOST=your.vps.ip.or.hostname
VPS_PORT=22
VPS_USERNAME=your_vps_username
VPS_PRIVATE_KEY=<base64_encoded_private_key>
```

### How to Get VPS_PRIVATE_KEY:
1. **Generate SSH key pair** (if you don't have one):
   ```bash
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/vps_key
   ```

2. **Copy public key to VPS**:
   ```bash
   ssh-copy-id -i ~/.ssh/vps_key.pub user@your-vps-host
   ```

3. **Base64 encode the private key**:
   ```bash
   base64 -i ~/.ssh/vps_key | tr -d '\n'
   ```

4. **Set in Railway**: Copy the base64 output to `VPS_PRIVATE_KEY` variable

## 🚀 Deploy Instructions:

```bash
cd /Users/silviocorreia/Documents/GitHub/UmbraSIL
git add .
git commit -m "Add VPS monitoring via SSH - monitor external VPS not Railway container"
git push
```

## ✅ What the Health Check Now Shows:

### **When VPS Connected** 🟢
- ✅ Real VPS CPU, Memory, Disk usage
- 🖥️ VPS uptime and load average  
- 📊 Health status (HEALTHY/WARNING/CRITICAL)
- 🔄 Live refresh capability

### **When VPS Not Connected** 🔴  
- 🚨 Connection error details
- 🔧 Troubleshooting steps
- ⚙️ Configuration guidance

## 🎯 Testing:

1. **Deploy the code first**
2. **Set VPS environment variables in Railway**
3. **Test**: Main Menu → 📊 Monitoring → ❤️ Health
4. **Should show VPS stats or helpful error messages**

## 📝 Notes:

- **SSH Key Security**: Use a dedicated key for bot monitoring
- **Firewall**: Ensure Railway can reach your VPS on SSH port
- **User Permissions**: VPS user needs access to system stats commands
- **Connection Timeout**: 10 seconds timeout for SSH connections

Your bot now monitors your actual business VPS where your n8n clients and other services run! 🎉
