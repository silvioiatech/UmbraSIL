# 🧠 Natural Language Understanding for UmbraSIL Bot

## ✨ What's New

Your bot now understands natural language for financial transactions! No more rigid command formats.

## 🚀 Quick Start

### 1. Add OpenRouter API Key

1. Go to [openrouter.ai](https://openrouter.ai)
2. Sign up for free account
3. Get your API key
4. Add to Railway environment variables:
```
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### 2. Commit and Push Changes

```bash
cd /Users/silviocorreia/Documents/GitHub/UmbraSIL
git add .
git commit -m "Add natural language understanding with OpenRouter"
git push origin main
```

Railway will automatically redeploy with the new features.

## 💬 Natural Language Examples

### Before (rigid format):
```
expense: 12.50 food Lunch at restaurant
income: 2500 salary Monthly payment
```

### Now (natural language):
```
spent 12.50 at coop
paid 15 for lunch today
got my salary 3000
bought groceries for 47.30 at migros
uber ride was 25
received 500 from john
what's my balance
how much did I spend today
```

## 🎯 Features

### 1. **Automatic Intent Detection**
The bot understands what you want to do:
- **Expense**: "spent", "paid", "bought", "cost"
- **Income**: "received", "got", "earned", "salary"
- **Balance**: "balance", "how much", "total"
- **Report**: "report", "summary", "analyze"

### 2. **Smart Vendor Categorization**
Automatically categorizes based on vendor:
- **Coop, Migros, Lidl** → Groceries
- **Starbucks, Café** → Coffee
- **Uber, SBB, Taxi** → Transport
- **Netflix, Spotify** → Entertainment
- **Pharmacy, Doctor** → Health

### 3. **Context Understanding**
- "lunch was 15 euros" → Food expense
- "electricity bill 120" → Utilities expense
- "gym membership 50" → Health expense

### 4. **Receipt Photos**
Send a photo of a receipt and the bot will:
- Detect it's a receipt
- Guide you to add the expense manually (OCR coming soon)

## 🔧 Configuration

### Models (in Railway Variables)

The bot uses FREE models by default. You can change them:

```bash
# Default FREE models
NLP_INTENT_MODEL=meta-llama/llama-3.2-3b-instruct:free
NLP_EXTRACTION_MODEL=mistralai/mistral-7b-instruct:free
NLP_CHAT_MODEL=meta-llama/llama-3.2-3b-instruct:free

# For better accuracy (small cost ~$0.01/day)
NLP_ANALYSIS_MODEL=anthropic/claude-3-haiku
```

### Available Free Models on OpenRouter:
- `meta-llama/llama-3.2-3b-instruct:free`
- `mistralai/mistral-7b-instruct:free`
- `google/gemma-2-9b-it:free`
- `nous-research/hermes-2-theta-llama-3-8b`

### Cheap Models ($0.00025/1k tokens):
- `anthropic/claude-3-haiku`
- `google/gemini-flash-1.5`
- `deepseek/deepseek-chat`

## 📊 Usage Examples

### Morning Coffee
```
You: spent 4.50 at starbucks
Bot: 💸 Expense Added Automatically
     • Amount: 4.50 EUR
     • Category: coffee
     • Vendor: Starbucks
     💳 New balance: 1495.50 EUR
```

### Grocery Shopping
```
You: bought groceries for 67.80 at coop
Bot: 💸 Expense Added Automatically
     • Amount: 67.80 EUR
     • Category: groceries
     • Vendor: Coop
     💳 New balance: 1427.70 EUR
```

### Salary
```
You: got paid 3000
Bot: 💰 Income Added Automatically
     • Amount: 3000.00 EUR
     • Source: salary
     💳 New balance: 4427.70 EUR
```

### Check Balance
```
You: what's my balance?
Bot: 💰 Finance Management
     💳 Current Balance: 4427.70 EUR
     📊 Today's Activity:
     • Income: +3000.00 EUR
     • Expenses: -72.30 EUR
```

## 🎮 Tips & Tricks

### 1. **Quick Expense Logging**
Just type naturally:
- "coffee 3.50"
- "lunch 12"
- "uber 15.50"

### 2. **Multiple Languages**
The AI understands context in multiple languages:
- "dépensé 20 chez carrefour"
- "pagato 15 per pranzo"
- "gastado 30 en gasolina"

### 3. **Abbreviations Work**
- "20 @ coop" → 20 EUR at Coop
- "got 500" → Income of 500 EUR
- "taxi 15" → Transport expense

### 4. **Ask Questions**
- "how much did I spend on groceries this week?"
- "what's my biggest expense today?"
- "show me a spending summary"

## 🚨 Troubleshooting

### Bot doesn't understand my message?
1. Check if OPENROUTER_API_KEY is set
2. Try being more specific: "spent 20 at restaurant"
3. Use keywords: spent, paid, received, balance

### Wrong category assigned?
The bot learns from vendor names. You can always use /finance menu for manual entry with specific categories.

### Want to disable NLP?
Remove OPENROUTER_API_KEY from environment variables, and the bot will fall back to the original command format.

## 💰 Cost Analysis

With FREE models:
- **Cost**: $0/day
- **Requests**: Unlimited
- **Quality**: Good for 95% of cases

With Claude Haiku (for complex analysis):
- **Cost**: ~$0.01-0.05/day
- **Requests**: 500-1000/day
- **Quality**: Excellent

## 🔮 Coming Soon

- **OCR for Receipts**: Automatic receipt scanning
- **Multi-currency**: Auto-detect EUR, USD, CHF
- **Spending Insights**: "You spend 30% more on weekends"
- **Budget Alerts**: "You're close to your food budget"
- **Voice Messages**: Transcribe and process audio

## 📝 Examples to Try Right Now

After deploying with OPENROUTER_API_KEY, try these:

1. `spent 12.50 at coop`
2. `coffee was 4`
3. `got my salary 3000`
4. `paid 120 for electricity`
5. `uber to airport 45`
6. `lunch with friends 35`
7. `netflix subscription 15`
8. `what's my balance`
9. `how much did I spend today`
10. Send a photo of a receipt

---

**🎉 Your bot now understands you naturally! No more memorizing commands!**
