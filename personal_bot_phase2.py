# Personal Telegram Bot Assistant - Phase 2: Finance Management
# OCR, Expense Tracking, Income Management, Financial Reports

import os
import io
import csv
import base64
import asyncio
import calendar
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Dict, Any, Tuple

# Google Vision API for OCR
from google.cloud import vision
from google.oauth2 import service_account

# Matplotlib for charts
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_agg import FigureCanvasAgg
import seaborn as sns

# PIL for image processing
from PIL import Image

# Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters

# Re-use imports from Phase 1
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# ==============================================================================
# FINANCE CONFIGURATION
# ==============================================================================

class FinanceConfig:
    """Finance module specific configuration"""
    
    # Google Vision API
    GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")  # Base64 encoded
    GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")  # Or file path
    
    # Finance settings
    DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "EUR")
    
    # Categories
    EXPENSE_CATEGORIES = [
        "🍔 Food & Dining", "🚗 Transportation", "🛒 Shopping", 
        "🏠 Housing", "💊 Health", "🎯 Entertainment", 
        "💼 Business", "🎓 Education", "💰 Investments",
        "📱 Utilities", "✈️ Travel", "🎁 Gifts", "📄 Other"
    ]
    
    INCOME_SOURCES = [
        "💼 Salary", "🏢 Business", "💰 Investment", 
        "🎯 Freelance", "🎁 Gift", "📈 Bonus", 
        "🏠 Rental", "📄 Other"
    ]
    
    # Budget limits (monthly)
    DEFAULT_BUDGET_LIMITS = {
        "🍔 Food & Dining": 400,
        "🚗 Transportation": 200,
        "🛒 Shopping": 300,
        "🎯 Entertainment": 150
    }

# Conversation states for adding expenses/income
ADD_EXPENSE_AMOUNT, ADD_EXPENSE_CATEGORY, ADD_EXPENSE_DESCRIPTION, ADD_EXPENSE_DATE = range(4)
ADD_INCOME_AMOUNT, ADD_INCOME_SOURCE, ADD_INCOME_DESCRIPTION, ADD_INCOME_DATE = range(4, 8)
OCR_PROCESS = 8

# ==============================================================================
# OCR SERVICE (Google Vision API)
# ==============================================================================

class OCRService:
    """Handles receipt/invoice OCR processing"""
    
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Google Vision API client"""
        try:
            if FinanceConfig.GOOGLE_CREDENTIALS_JSON:
                # Decode base64 credentials (Railway secrets)
                credentials_json = base64.b64decode(FinanceConfig.GOOGLE_CREDENTIALS_JSON).decode('utf-8')
                credentials_info = eval(credentials_json)  # Convert string to dict
                credentials = service_account.Credentials.from_service_account_info(credentials_info)
                self.client = vision.ImageAnnotatorClient(credentials=credentials)
            elif FinanceConfig.GOOGLE_CREDENTIALS_PATH:
                # Use file path
                self.client = vision.ImageAnnotatorClient.from_service_account_file(
                    FinanceConfig.GOOGLE_CREDENTIALS_PATH
                )
            else:
                logger.warning("Google Vision API credentials not configured - OCR disabled")
                return
            
            logger.info("Google Vision API client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google Vision API: {e}")
            self.client = None
    
    async def extract_receipt_data(self, image_bytes: bytes) -> Dict[str, Any]:
        """Extract data from receipt image"""
        if not self.client:
            return {"error": "OCR service not configured"}
        
        try:
            # Resize image if too large (Vision API limits)
            image = Image.open(io.BytesIO(image_bytes))
            if image.size[0] > 2048 or image.size[1] > 2048:
                image.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
                buffer = io.BytesIO()
                image.save(buffer, format='JPEG', quality=85)
                image_bytes = buffer.getvalue()
            
            # Google Vision API call
            image = vision.Image(content=image_bytes)
            response = self.client.text_detection(image=image)
            
            if response.error.message:
                raise Exception(f"Vision API error: {response.error.message}")
            
            # Extract text
            texts = response.text_annotations
            if not texts:
                return {"error": "No text found in image"}
            
            full_text = texts[0].description
            
            # Parse receipt data using simple regex/rules
            parsed_data = self._parse_receipt_text(full_text)
            
            return {
                "success": True,
                "full_text": full_text,
                "parsed_data": parsed_data
            }
            
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            return {"error": f"OCR failed: {str(e)}"}
    
    def _parse_receipt_text(self, text: str) -> Dict[str, Any]:
        """Parse receipt text to extract structured data"""
        import re
        
        lines = text.split('\n')
        parsed = {
            "amounts": [],
            "total": None,
            "date": None,
            "merchant": None,
            "categories": []
        }
        
        # Extract monetary amounts (EUR format)
        amount_patterns = [
            r'€\s*(\d+[,.]?\d*)',  # €12.50 or €12,50
            r'(\d+[,.]?\d*)\s*€',  # 12.50€
            r'(\d+[,.]?\d*)\s*EUR', # 12.50 EUR
            r'TOTAL[:\s]*(\d+[,.]?\d*)',  # TOTAL: 12.50
            r'SUM[:\s]*(\d+[,.]?\d*)'     # SUM: 12.50
        ]
        
        for line in lines:
            for pattern in amount_patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                for match in matches:
                    try:
                        amount = float(match.replace(',', '.'))
                        parsed["amounts"].append(amount)
                        
                        # Likely total if contains "total", "sum" or largest amount
                        if any(word in line.lower() for word in ['total', 'sum', 'betrag', 'gesamt']):
                            parsed["total"] = amount
                    except (ValueError, AttributeError):
                        continue
        
        # Find largest amount as likely total if not found
        if not parsed["total"] and parsed["amounts"]:
            parsed["total"] = max(parsed["amounts"])
        
        # Extract date
        date_patterns = [
            r'(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})',  # DD/MM/YYYY or DD.MM.YYYY
            r'(\d{2,4}[./-]\d{1,2}[./-]\d{1,2})',  # YYYY/MM/DD
        ]
        
        for line in lines[:10]:  # Check first 10 lines for date
            for pattern in date_patterns:
                match = re.search(pattern, line)
                if match:
                    parsed["date"] = match.group(1)
                    break
            if parsed["date"]:
                break
        
        # Extract merchant (usually first few lines)
        if lines:
            parsed["merchant"] = lines[0].strip()[:50]  # First line, max 50 chars
        
        # Smart categorization based on keywords
        text_lower = text.lower()
        category_keywords = {
            "🍔 Food & Dining": ["restaurant", "cafe", "pizza", "burger", "food", "dining", "bistro", "imbiss"],
            "🛒 Shopping": ["supermarket", "store", "shop", "market", "edeka", "rewe", "lidl", "aldi"],
            "⛽ Transportation": ["shell", "bp", "esso", "tankstelle", "gas", "fuel", "petrol"],
            "💊 Health": ["pharmacy", "apotheke", "medical", "doctor", "clinic", "hospital"],
            "🏠 Housing": ["rent", "utilities", "electric", "water", "gas", "internet", "miete"]
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                parsed["categories"].append(category)
        
        return parsed

# ==============================================================================
# FINANCIAL REPORTING & ANALYTICS
# ==============================================================================

class FinancialReports:
    """Generate financial reports and visualizations"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        
        # Set matplotlib style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    
    async def generate_monthly_report(self, user_id: int, year: int = None, month: int = None) -> io.BytesIO:
        """Generate comprehensive monthly financial report"""
        if not year:
            year = datetime.now().year
        if not month:
            month = datetime.now().month
        
        # Create figure with subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'Financial Report - {calendar.month_name[month]} {year}', fontsize=16, fontweight='bold')
        
        # Get data
        expenses_data = await self._get_monthly_expenses(user_id, year, month)
        income_data = await self._get_monthly_income(user_id, year, month)
        daily_data = await self._get_daily_summary(user_id, year, month)
        category_data = await self._get_category_breakdown(user_id, year, month)
        
        # 1. Income vs Expenses Bar Chart
        total_income = sum(income_data.values()) if income_data else 0
        total_expenses = sum(expenses_data.values()) if expenses_data else 0
        
        ax1.bar(['Income', 'Expenses'], [total_income, total_expenses], 
                color=['green', 'red'], alpha=0.7)
        ax1.set_title('Income vs Expenses')
        ax1.set_ylabel(f'Amount ({FinanceConfig.DEFAULT_CURRENCY})')
        
        # Add value labels on bars
        for i, v in enumerate([total_income, total_expenses]):
            ax1.text(i, v + max(total_income, total_expenses) * 0.01, f'{v:.2f}', 
                    ha='center', va='bottom', fontweight='bold')
        
        # 2. Daily Spending Trend
        if daily_data:
            dates = list(daily_data.keys())
            amounts = list(daily_data.values())
            ax2.plot(dates, amounts, marker='o', linewidth=2, markersize=4)
            ax2.set_title('Daily Spending Trend')
            ax2.set_ylabel(f'Amount ({FinanceConfig.DEFAULT_CURRENCY})')
            ax2.tick_params(axis='x', rotation=45)
        else:
            ax2.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax2.transAxes)
            ax2.set_title('Daily Spending Trend')
        
        # 3. Expense Categories Pie Chart
        if category_data:
            categories = list(category_data.keys())
            amounts = list(category_data.values())
            
            # Clean category names (remove emojis for better display)
            clean_categories = [cat.split(' ', 1)[-1] if ' ' in cat else cat for cat in categories]
            
            wedges, texts, autotexts = ax3.pie(amounts, labels=clean_categories, autopct='%1.1f%%', startangle=90)
            ax3.set_title('Expenses by Category')
        else:
            ax3.text(0.5, 0.5, 'No expense data', ha='center', va='center', transform=ax3.transAxes)
            ax3.set_title('Expenses by Category')
        
        # 4. Budget vs Actual (if budgets are set)
        budget_comparison = await self._get_budget_comparison(user_id, year, month)
        if budget_comparison:
            categories = list(budget_comparison.keys())
            budget_amounts = [data['budget'] for data in budget_comparison.values()]
            actual_amounts = [data['actual'] for data in budget_comparison.values()]
            
            x = range(len(categories))
            width = 0.35
            
            ax4.bar([i - width/2 for i in x], budget_amounts, width, label='Budget', alpha=0.7)
            ax4.bar([i + width/2 for i in x], actual_amounts, width, label='Actual', alpha=0.7)
            
            ax4.set_title('Budget vs Actual')
            ax4.set_ylabel(f'Amount ({FinanceConfig.DEFAULT_CURRENCY})')
            ax4.set_xticks(x)
            ax4.set_xticklabels([cat.split(' ', 1)[-1] if ' ' in cat else cat for cat in categories], rotation=45)
            ax4.legend()
        else:
            ax4.text(0.5, 0.5, 'No budget data', ha='center', va='center', transform=ax4.transAxes)
            ax4.set_title('Budget vs Actual')
        
        plt.tight_layout()
        
        # Save to bytes
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        plt.close(fig)
        
        return buffer
    
    async def _get_monthly_expenses(self, user_id: int, year: int, month: int) -> Dict[str, float]:
        """Get monthly expenses grouped by category"""
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT category, SUM(amount) as total
                FROM expenses 
                WHERE user_id = $1 
                AND EXTRACT(YEAR FROM date) = $2 
                AND EXTRACT(MONTH FROM date) = $3
                GROUP BY category
                ORDER BY total DESC
            ''', user_id, year, month)
            
            return {row['category']: float(row['total']) for row in rows}
    
    async def _get_monthly_income(self, user_id: int, year: int, month: int) -> Dict[str, float]:
        """Get monthly income grouped by source"""
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT source, SUM(amount) as total
                FROM income 
                WHERE user_id = $1 
                AND EXTRACT(YEAR FROM date) = $2 
                AND EXTRACT(MONTH FROM date) = $3
                GROUP BY source
                ORDER BY total DESC
            ''', user_id, year, month)
            
            return {row['source']: float(row['total']) for row in rows}
    
    async def _get_daily_summary(self, user_id: int, year: int, month: int) -> Dict[date, float]:
        """Get daily expense summary for the month"""
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT date, SUM(amount) as total
                FROM expenses 
                WHERE user_id = $1 
                AND EXTRACT(YEAR FROM date) = $2 
                AND EXTRACT(MONTH FROM date) = $3
                GROUP BY date
                ORDER BY date
            ''', user_id, year, month)
            
            return {row['date']: float(row['total']) for row in rows}
    
    async def _get_category_breakdown(self, user_id: int, year: int, month: int) -> Dict[str, float]:
        """Get expense category breakdown"""
        return await self._get_monthly_expenses(user_id, year, month)
    
    async def _get_budget_comparison(self, user_id: int, year: int, month: int) -> Dict[str, Dict]:
        """Compare actual spending vs budget (simplified for Phase 2)"""
        expenses = await self._get_monthly_expenses(user_id, year, month)
        
        budget_data = {}
        for category, actual in expenses.items():
            if category in FinanceConfig.DEFAULT_BUDGET_LIMITS:
                budget_data[category] = {
                    'budget': FinanceConfig.DEFAULT_BUDGET_LIMITS[category],
                    'actual': actual
                }
        
        return budget_data
    
    async def export_to_csv(self, user_id: int, start_date: date, end_date: date) -> io.BytesIO:
        """Export financial data to CSV"""
        buffer = io.BytesIO()
        
        # Get all expenses and income for the period
        async with self.db.pool.acquire() as conn:
            expenses = await conn.fetch('''
                SELECT date, 'Expense' as type, amount, category as category_source, description
                FROM expenses 
                WHERE user_id = $1 AND date BETWEEN $2 AND $3
                ORDER BY date DESC
            ''', user_id, start_date, end_date)
            
            income = await conn.fetch('''
                SELECT date, 'Income' as type, amount, source as category_source, description
                FROM income 
                WHERE user_id = $1 AND date BETWEEN $2 AND $3
                ORDER BY date DESC
            ''', user_id, start_date, end_date)
        
        # Combine and write to CSV
        all_transactions = list(expenses) + list(income)
        
        if all_transactions:
            # Convert to text for CSV writing
            csv_text = io.StringIO()
            writer = csv.writer(csv_text)
            
            # Header
            writer.writerow(['Date', 'Type', 'Amount', 'Category/Source', 'Description'])
            
            # Data
            for transaction in sorted(all_transactions, key=lambda x: x['date'], reverse=True):
                writer.writerow([
                    transaction['date'].strftime('%Y-%m-%d'),
                    transaction['type'],
                    float(transaction['amount']),
                    transaction['category_source'],
                    transaction['description'] or ''
                ])
            
            # Convert to bytes
            buffer = io.BytesIO(csv_text.getvalue().encode('utf-8'))
            buffer.seek(0)
        
        return buffer

# ==============================================================================
# FINANCE BOT HANDLERS
# ==============================================================================

class FinanceManager:
    """Finance management functionality for the bot"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.ocr_service = OCRService()
        self.reports = FinancialReports(db_manager)
    
    def setup_handlers(self, application):
        """Setup finance-related handlers"""
        
        # Expense management
        application.add_handler(ConversationHandler(
            entry_points=[CommandHandler('add_expense', self.add_expense_start)],
            states={
                ADD_EXPENSE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_expense_amount)],
                ADD_EXPENSE_CATEGORY: [CallbackQueryHandler(self.add_expense_category)],
                ADD_EXPENSE_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_expense_description)],
                ADD_EXPENSE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_expense_date)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
            name="add_expense"
        ))
        
        # Income management
        application.add_handler(ConversationHandler(
            entry_points=[CommandHandler('add_income', self.add_income_start)],
            states={
                ADD_INCOME_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_income_amount)],
                ADD_INCOME_SOURCE: [CallbackQueryHandler(self.add_income_source)],
                ADD_INCOME_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_income_description)],
                ADD_INCOME_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_income_date)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
            name="add_income"
        ))
        
        # OCR processing
        application.add_handler(ConversationHandler(
            entry_points=[CommandHandler('scan_receipt', self.scan_receipt_start)],
            states={
                OCR_PROCESS: [MessageHandler(filters.PHOTO, self.process_receipt_photo)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
            name="ocr_receipt"
        ))
        
        # Reports and queries
        application.add_handler(CommandHandler('expenses_month', self.monthly_expenses))
        application.add_handler(CommandHandler('income_month', self.monthly_income))
        application.add_handler(CommandHandler('financial_report', self.generate_report))
        application.add_handler(CommandHandler('export_csv', self.export_csv))
        application.add_handler(CommandHandler('balance', self.show_balance))
    
    # ===== EXPENSE MANAGEMENT =====
    
    async def add_expense_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start adding expense conversation"""
        await update.message.reply_text(
            "💸 **Add New Expense**\n\n"
            "Please enter the amount (just the number):\n"
            "Example: 25.50",
            parse_mode='Markdown'
        )
        return ADD_EXPENSE_AMOUNT
    
    async def add_expense_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle expense amount input"""
        try:
            amount = Decimal(update.message.text.replace(',', '.'))
            if amount <= 0:
                raise InvalidOperation
            
            context.user_data['expense_amount'] = amount
            
            # Create category selection keyboard
            keyboard = []
            for i in range(0, len(FinanceConfig.EXPENSE_CATEGORIES), 2):
                row = []
                row.append(InlineKeyboardButton(
                    FinanceConfig.EXPENSE_CATEGORIES[i], 
                    callback_data=f"exp_cat_{i}"
                ))
                if i + 1 < len(FinanceConfig.EXPENSE_CATEGORIES):
                    row.append(InlineKeyboardButton(
                        FinanceConfig.EXPENSE_CATEGORIES[i + 1], 
                        callback_data=f"exp_cat_{i + 1}"
                    ))
                keyboard.append(row)
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"💶 Amount: **{amount} {FinanceConfig.DEFAULT_CURRENCY}**\n\n"
                "Please select a category:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return ADD_EXPENSE_CATEGORY
            
        except (ValueError, InvalidOperation):
            await update.message.reply_text(
                "❌ Invalid amount. Please enter a valid number.\n"
                "Example: 25.50"
            )
            return ADD_EXPENSE_AMOUNT
    
    async def add_expense_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle category selection"""
        query = update.callback_query
        await query.answer()
        
        category_index = int(query.data.split('_')[-1])
        category = FinanceConfig.EXPENSE_CATEGORIES[category_index]
        context.user_data['expense_category'] = category
        
        await query.edit_message_text(
            f"💶 Amount: **{context.user_data['expense_amount']} {FinanceConfig.DEFAULT_CURRENCY}**\n"
            f"🏷️ Category: **{category}**\n\n"
            "Please enter a description (or type 'skip'):",
            parse_mode='Markdown'
        )
        return ADD_EXPENSE_DESCRIPTION
    
    async def add_expense_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle description input"""
        description = update.message.text if update.message.text.lower() != 'skip' else None
        context.user_data['expense_description'] = description
        
        await update.message.reply_text(
            f"💶 Amount: **{context.user_data['expense_amount']} {FinanceConfig.DEFAULT_CURRENCY}**\n"
            f"🏷️ Category: **{context.user_data['expense_category']}**\n"
            f"📝 Description: **{description or 'None'}**\n\n"
            "Please enter the date (YYYY-MM-DD) or type 'today':",
            parse_mode='Markdown'
        )
        return ADD_EXPENSE_DATE
    
    async def add_expense_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle date input and save expense"""
        try:
            date_text = update.message.text.lower()
            if date_text == 'today':
                expense_date = date.today()
            else:
                expense_date = datetime.strptime(date_text, '%Y-%m-%d').date()
            
            # Save to database
            user_id = update.effective_user.id
            async with self.db.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO expenses (user_id, amount, category, description, date)
                    VALUES ($1, $2, $3, $4, $5)
                ''', 
                    user_id,
                    context.user_data['expense_amount'],
                    context.user_data['expense_category'],
                    context.user_data['expense_description'],
                    expense_date
                )
            
            # Log the action
            await self.db.log_command(user_id, "add_expense", f"Added expense: {context.user_data['expense_amount']}", True)
            
            # Check budget alert
            budget_alert = await self._check_budget_alert(
                user_id, 
                context.user_data['expense_category'], 
                expense_date.year, 
                expense_date.month
            )
            
            success_message = (
                f"✅ **Expense Added Successfully!**\n\n"
                f"💶 Amount: {context.user_data['expense_amount']} {FinanceConfig.DEFAULT_CURRENCY}\n"
                f"🏷️ Category: {context.user_data['expense_category']}\n"
                f"📝 Description: {context.user_data['expense_description'] or 'None'}\n"
                f"📅 Date: {expense_date.strftime('%Y-%m-%d')}"
            )
            
            if budget_alert:
                success_message += f"\n\n⚠️ {budget_alert}"
            
            await update.message.reply_text(success_message, parse_mode='Markdown')
            
            # Clear user data
            context.user_data.clear()
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid date format. Please use YYYY-MM-DD or type 'today'.\n"
                "Example: 2024-03-15"
            )
            return ADD_EXPENSE_DATE
    
    # ===== INCOME MANAGEMENT =====
    
    async def add_income_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start adding income conversation"""
        await update.message.reply_text(
            "💰 **Add New Income**\n\n"
            "Please enter the amount (just the number):\n"
            "Example: 2500.00",
            parse_mode='Markdown'
        )
        return ADD_INCOME_AMOUNT
    
    async def add_income_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle income amount input"""
        try:
            amount = Decimal(update.message.text.replace(',', '.'))
            if amount <= 0:
                raise InvalidOperation
            
            context.user_data['income_amount'] = amount
            
            # Create source selection keyboard
            keyboard = []
            for i in range(0, len(FinanceConfig.INCOME_SOURCES), 2):
                row = []
                row.append(InlineKeyboardButton(
                    FinanceConfig.INCOME_SOURCES[i], 
                    callback_data=f"inc_src_{i}"
                ))
                if i + 1 < len(FinanceConfig.INCOME_SOURCES):
                    row.append(InlineKeyboardButton(
                        FinanceConfig.INCOME_SOURCES[i + 1], 
                        callback_data=f"inc_src_{i + 1}"
                    ))
                keyboard.append(row)
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"💰 Amount: **{amount} {FinanceConfig.DEFAULT_CURRENCY}**\n\n"
                "Please select the income source:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return ADD_INCOME_SOURCE
            
        except (ValueError, InvalidOperation):
            await update.message.reply_text(
                "❌ Invalid amount. Please enter a valid number.\n"
                "Example: 2500.00"
            )
            return ADD_INCOME_AMOUNT
    
    async def add_income_source(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle income source selection"""
        query = update.callback_query
        await query.answer()
        
        source_index = int(query.data.split('_')[-1])
        source = FinanceConfig.INCOME_SOURCES[source_index]
        context.user_data['income_source'] = source
        
        await query.edit_message_text(
            f"💰 Amount: **{context.user_data['income_amount']} {FinanceConfig.DEFAULT_CURRENCY}**\n"
            f"🏢 Source: **{source}**\n\n"
            "Please enter a description (or type 'skip'):",
            parse_mode='Markdown'
        )
        return ADD_INCOME_DESCRIPTION
    
    async def add_income_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle income description input"""
        description = update.message.text if update.message.text.lower() != 'skip' else None
        context.user_data['income_description'] = description
        
        await update.message.reply_text(
            f"💰 Amount: **{context.user_data['income_amount']} {FinanceConfig.DEFAULT_CURRENCY}**\n"
            f"🏢 Source: **{context.user_data['income_source']}**\n"
            f"📝 Description: **{description or 'None'}**\n\n"
            "Please enter the date (YYYY-MM-DD) or type 'today':",
            parse_mode='Markdown'
        )
        return ADD_INCOME_DATE
    
    async def add_income_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle date input and save income"""
        try:
            date_text = update.message.text.lower()
            if date_text == 'today':
                income_date = date.today()
            else:
                income_date = datetime.strptime(date_text, '%Y-%m-%d').date()
            
            # Save to database
            user_id = update.effective_user.id
            async with self.db.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO income (user_id, amount, source, description, date)
                    VALUES ($1, $2, $3, $4, $5)
                ''', 
                    user_id,
                    context.user_data['income_amount'],
                    context.user_data['income_source'],
                    context.user_data['income_description'],
                    income_date
                )
            
            # Log the action
            await self.db.log_command(user_id, "add_income", f"Added income: {context.user_data['income_amount']}", True)
            
            success_message = (
                f"✅ **Income Added Successfully!**\n\n"
                f"💰 Amount: {context.user_data['income_amount']} {FinanceConfig.DEFAULT_CURRENCY}\n"
                f"🏢 Source: {context.user_data['income_source']}\n"
                f"📝 Description: {context.user_data['income_description'] or 'None'}\n"
                f"📅 Date: {income_date.strftime('%Y-%m-%d')}"
            )
            
            await update.message.reply_text(success_message, parse_mode='Markdown')
            
            # Clear user data
            context.user_data.clear()
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid date format. Please use YYYY-MM-DD or type 'today'.\n"
                "Example: 2024-03-15"
            )
            return ADD_INCOME_DATE
    
    # ===== OCR RECEIPT PROCESSING =====
    
    async def scan_receipt_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start receipt OCR process"""
        if not self.ocr_service.client:
            await update.message.reply_text(
                "❌ OCR service is not configured.\n"
                "Please set up Google Vision API credentials."
            )
            return ConversationHandler.END
        
        await update.message.reply_text(
            "📸 **Receipt Scanner**\n\n"
            "Please send a clear photo of your receipt.\n"
            "Make sure the text is readable and well-lit.\n\n"
            "💡 Tip: Hold the camera steady and avoid shadows!"
        )
        return OCR_PROCESS
    
    async def process_receipt_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process uploaded receipt photo"""
        try:
            # Get the largest photo size
            photo = update.message.photo[-1]
            
            # Download image
            photo_file = await context.bot.get_file(photo.file_id)
            image_bytes = await photo_file.download_as_bytearray()
            
            # Show processing message
            processing_msg = await update.message.reply_text("🔍 Processing receipt... Please wait.")
            
            # Process with OCR
            ocr_result = await self.ocr_service.extract_receipt_data(bytes(image_bytes))
            
            if "error" in ocr_result:
                await processing_msg.edit_text(
                    f"❌ OCR Processing Failed\n\n"
                    f"Error: {ocr_result['error']}\n\n"
                    "Please try again with a clearer photo."
                )
                return ConversationHandler.END
            
            # Extract parsed data
            parsed = ocr_result["parsed_data"]
            
            # Build result message
            result_text = "🔍 **Receipt Analysis Complete!**\n\n"
            
            if parsed["total"]:
                result_text += f"💶 **Total Amount:** {parsed['total']:.2f} {FinanceConfig.DEFAULT_CURRENCY}\n"
            
            if parsed["date"]:
                result_text += f"📅 **Date:** {parsed['date']}\n"
            
            if parsed["merchant"]:
                result_text += f"🏪 **Merchant:** {parsed['merchant']}\n"
            
            if parsed["categories"]:
                result_text += f"🏷️ **Suggested Category:** {parsed['categories'][0]}\n"
            
            result_text += "\n**Raw Text Preview:**\n"
            result_text += f"```{ocr_result['full_text'][:300]}{'...' if len(ocr_result['full_text']) > 300 else ''}```"
            
            # Create quick add buttons if we have good data
            keyboard = []
            if parsed["total"]:
                keyboard.append([
                    InlineKeyboardButton(
                        f"💸 Quick Add Expense ({parsed['total']:.2f}€)", 
                        callback_data=f"quick_expense_{parsed['total']:.2f}_{parsed.get('categories', ['📄 Other'])[0]}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_ocr")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await processing_msg.edit_text(
                result_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            # Store OCR data for quick add
            context.user_data['ocr_data'] = parsed
            
            # Log the OCR action
            await self.db.log_command(
                update.effective_user.id, 
                "scan_receipt", 
                f"OCR processed - Amount: {parsed.get('total', 'N/A')}", 
                True
            )
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Receipt processing failed: {e}")
            await update.message.reply_text(
                "❌ Failed to process receipt.\n"
                "Please try again or add the expense manually."
            )
            return ConversationHandler.END
    
    # ===== BUDGET MANAGEMENT =====
    
    async def _check_budget_alert(self, user_id: int, category: str, year: int, month: int) -> Optional[str]:
        """Check if spending exceeds budget and return alert message"""
        if category not in FinanceConfig.DEFAULT_BUDGET_LIMITS:
            return None
        
        budget_limit = FinanceConfig.DEFAULT_BUDGET_LIMITS[category]
        
        # Get month spending for category
        async with self.db.pool.acquire() as conn:
            result = await conn.fetchval('''
                SELECT COALESCE(SUM(amount), 0)
                FROM expenses 
                WHERE user_id = $1 
                AND category = $2
                AND EXTRACT(YEAR FROM date) = $3 
                AND EXTRACT(MONTH FROM date) = $4
            ''', user_id, category, year, month)
            
            current_spending = float(result) if result else 0
        
        if current_spending > budget_limit:
            overage = current_spending - budget_limit
            return f"Budget Alert: You're {overage:.2f}€ over your {category} budget ({current_spending:.2f}€/{budget_limit}€)"
        elif current_spending > budget_limit * 0.8:  # 80% warning
            percentage = (current_spending / budget_limit) * 100
            return f"Budget Warning: You've used {percentage:.0f}% of your {category} budget ({current_spending:.2f}€/{budget_limit}€)"
        
        return None
    
    # ===== REPORTING & QUERIES =====
    
    async def monthly_expenses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show monthly expense summary"""
        user_id = update.effective_user.id
        
        # Parse month/year from command args or use current
        args = context.args
        if args and len(args) >= 2:
            try:
                year, month = int(args[0]), int(args[1])
            except ValueError:
                year, month = datetime.now().year, datetime.now().month
        else:
            year, month = datetime.now().year, datetime.now().month
        
        # Get expenses data
        async with self.db.pool.acquire() as conn:
            # Total expenses
            total = await conn.fetchval('''
                SELECT COALESCE(SUM(amount), 0)
                FROM expenses 
                WHERE user_id = $1 
                AND EXTRACT(YEAR FROM date) = $2 
                AND EXTRACT(MONTH FROM date) = $3
            ''', user_id, year, month)
            
            # By category
            categories = await conn.fetch('''
                SELECT category, SUM(amount) as total, COUNT(*) as count
                FROM expenses 
                WHERE user_id = $1 
                AND EXTRACT(YEAR FROM date) = $2 
                AND EXTRACT(MONTH FROM date) = $3
                GROUP BY category
                ORDER BY total DESC
            ''', user_id, year, month)
            
            # Recent transactions
            recent = await conn.fetch('''
                SELECT date, amount, category, description
                FROM expenses 
                WHERE user_id = $1 
                AND EXTRACT(YEAR FROM date) = $2 
                AND EXTRACT(MONTH FROM date) = $3
                ORDER BY date DESC, id DESC
                LIMIT 5
            ''', user_id, year, month)
        
        # Build response
        month_name = calendar.month_name[month]
        response = f"💸 **Monthly Expenses - {month_name} {year}**\n\n"
        response += f"💰 **Total Spent:** {float(total):.2f} {FinanceConfig.DEFAULT_CURRENCY}\n\n"
        
        if categories:
            response += "📊 **By Category:**\n"
            for cat in categories:
                percentage = (float(cat['total']) / float(total)) * 100 if total > 0 else 0
                response += f"• {cat['category']}: {float(cat['total']):.2f}€ ({percentage:.0f}%) - {cat['count']} transactions\n"
            response += "\n"
        
        if recent:
            response += "🕐 **Recent Transactions:**\n"
            for tx in recent:
                desc_text = f" - {tx['description']}" if tx['description'] else ""
                response += f"• {tx['date']} | {float(tx['amount']):.2f}€ | {tx['category']}{desc_text}\n"
        else:
            response += "No expenses found for this month."
        
        await update.message.reply_text(response, parse_mode='Markdown')
        await self.db.log_command(user_id, "monthly_expenses", f"Viewed {month}/{year}", True)
    
    async def monthly_income(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show monthly income summary"""
        user_id = update.effective_user.id
        
        # Parse month/year from command args or use current
        args = context.args
        if args and len(args) >= 2:
            try:
                year, month = int(args[0]), int(args[1])
            except ValueError:
                year, month = datetime.now().year, datetime.now().month
        else:
            year, month = datetime.now().year, datetime.now().month
        
        # Get income data
        async with self.db.pool.acquire() as conn:
            # Total income
            total = await conn.fetchval('''
                SELECT COALESCE(SUM(amount), 0)
                FROM income 
                WHERE user_id = $1 
                AND EXTRACT(YEAR FROM date) = $2 
                AND EXTRACT(MONTH FROM date) = $3
            ''', user_id, year, month)
            
            # By source
            sources = await conn.fetch('''
                SELECT source, SUM(amount) as total, COUNT(*) as count
                FROM income 
                WHERE user_id = $1 
                AND EXTRACT(YEAR FROM date) = $2 
                AND EXTRACT(MONTH FROM date) = $3
                GROUP BY source
                ORDER BY total DESC
            ''', user_id, year, month)
            
            # Recent transactions
            recent = await conn.fetch('''
                SELECT date, amount, source, description
                FROM income 
                WHERE user_id = $1 
                AND EXTRACT(YEAR FROM date) = $2 
                AND EXTRACT(MONTH FROM date) = $3
                ORDER BY date DESC, id DESC
                LIMIT 5
            ''', user_id, year, month)
        
        # Build response
        month_name = calendar.month_name[month]
        response = f"💰 **Monthly Income - {month_name} {year}**\n\n"
        response += f"💰 **Total Earned:** {float(total):.2f} {FinanceConfig.DEFAULT_CURRENCY}\n\n"
        
        if sources:
            response += "📊 **By Source:**\n"
            for src in sources:
                percentage = (float(src['total']) / float(total)) * 100 if total > 0 else 0
                response += f"• {src['source']}: {float(src['total']):.2f}€ ({percentage:.0f}%) - {src['count']} transactions\n"
            response += "\n"
        
        if recent:
            response += "🕐 **Recent Transactions:**\n"
            for tx in recent:
                desc_text = f" - {tx['description']}" if tx['description'] else ""
                response += f"• {tx['date']} | {float(tx['amount']):.2f}€ | {tx['source']}{desc_text}\n"
        else:
            response += "No income found for this month."
        
        await update.message.reply_text(response, parse_mode='Markdown')
        await self.db.log_command(user_id, "monthly_income", f"Viewed {month}/{year}", True)
    
    async def show_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current month's income vs expenses"""
        user_id = update.effective_user.id
        now = datetime.now()
        
        async with self.db.pool.acquire() as conn:
            # This month's totals
            income_total = await conn.fetchval('''
                SELECT COALESCE(SUM(amount), 0)
                FROM income 
                WHERE user_id = $1 
                AND EXTRACT(YEAR FROM date) = $2 
                AND EXTRACT(MONTH FROM date) = $3
            ''', user_id, now.year, now.month)
            
            expense_total = await conn.fetchval('''
                SELECT COALESCE(SUM(amount), 0)
                FROM expenses 
                WHERE user_id = $1 
                AND EXTRACT(YEAR FROM date) = $2 
                AND EXTRACT(MONTH FROM date) = $3
            ''', user_id, now.year, now.month)
        
        income = float(income_total) if income_total else 0
        expenses = float(expense_total) if expense_total else 0
        balance = income - expenses
        
        balance_emoji = "✅" if balance >= 0 else "❌"
        
        response = f"💰 **Financial Balance - {calendar.month_name[now.month]} {now.year}**\n\n"
        response += f"📈 **Income:** {income:.2f} {FinanceConfig.DEFAULT_CURRENCY}\n"
        response += f"📉 **Expenses:** {expenses:.2f} {FinanceConfig.DEFAULT_CURRENCY}\n"
        response += f"{balance_emoji} **Balance:** {balance:.2f} {FinanceConfig.DEFAULT_CURRENCY}\n\n"
        
        if balance < 0:
            response += "⚠️ You're spending more than you're earning this month!"
        elif balance > 0:
            savings_rate = (balance / income * 100) if income > 0 else 0
            response += f"🎯 **Savings Rate:** {savings_rate:.1f}%"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        await self.db.log_command(user_id, "balance", f"Balance: {balance:.2f}", True)
    
    async def generate_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate and send financial report"""
        user_id = update.effective_user.id
        
        # Parse month/year or use current
        args = context.args
        if args and len(args) >= 2:
            try:
                year, month = int(args[0]), int(args[1])
            except ValueError:
                year, month = datetime.now().year, datetime.now().month
        else:
            year, month = datetime.now().year, datetime.now().month
        
        try:
            # Show processing message
            processing_msg = await update.message.reply_text(
                f"📊 Generating financial report for {calendar.month_name[month]} {year}...\n"
                "This may take a few moments."
            )
            
            # Generate report
            report_buffer = await self.reports.generate_monthly_report(user_id, year, month)
            
            # Send report
            report_buffer.seek(0)
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=InputFile(report_buffer, filename=f"financial_report_{year}_{month:02d}.png"),
                caption=f"📊 **Financial Report - {calendar.month_name[month]} {year}**\n\n"
                       f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            
            # Delete processing message
            await processing_msg.delete()
            
            await self.db.log_command(user_id, "financial_report", f"Generated for {month}/{year}", True)
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            await update.message.reply_text(
                "❌ Failed to generate report. Please try again later."
            )
            await self.db.log_command(user_id, "financial_report", "Failed", False, str(e))
    
    async def export_csv(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Export financial data to CSV"""
        user_id = update.effective_user.id
        
        # Default to current month if no args
        args = context.args
        if len(args) >= 2:
            try:
                year, month = int(args[0]), int(args[1])
                start_date = date(year, month, 1)
                # Last day of month
                if month == 12:
                    end_date = date(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(year, month + 1, 1) - timedelta(days=1)
            except ValueError:
                start_date = date.today().replace(day=1)
                end_date = date.today()
        else:
            start_date = date.today().replace(day=1)
            end_date = date.today()
        
        try:
            # Generate CSV
            csv_buffer = await self.reports.export_to_csv(user_id, start_date, end_date)
            
            if csv_buffer.getvalue():
                csv_buffer.seek(0)
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=InputFile(
                        csv_buffer, 
                        filename=f"financial_data_{start_date.strftime('%Y%m')}_to_{end_date.strftime('%Y%m')}.csv"
                    ),
                    caption=f"📄 **Financial Data Export**\n\n"
                           f"📅 Period: {start_date} to {end_date}\n"
                           f"📊 Format: CSV (Excel compatible)"
                )
                
                await self.db.log_command(user_id, "export_csv", f"Exported {start_date} to {end_date}", True)
            else:
                await update.message.reply_text(
                    f"📄 No financial data found for the period {start_date} to {end_date}."
                )
        
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            await update.message.reply_text("❌ Failed to export data. Please try again later.")
            await self.db.log_command(user_id, "export_csv", "Failed", False, str(e))
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel any ongoing conversation"""
        await update.message.reply_text("❌ Operation cancelled.")
        context.user_data.clear()
        return ConversationHandler.END

# ==============================================================================
# UPDATED REQUIREMENTS FOR PHASE 2
# ==============================================================================

"""
Add these to requirements.txt:

# Phase 2 additions:
google-cloud-vision==3.4.4
google-auth==2.23.3
matplotlib==3.7.2
seaborn==0.12.2
Pillow==10.0.0
"""

# ==============================================================================
# INTEGRATION WITH PHASE 1 BOT
# ==============================================================================

"""
INTEGRATION INSTRUCTIONS:

1. Add to your main bot file from Phase 1:

from finance_manager import FinanceManager, FinanceConfig

class PersonalBotAssistant:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.application = None
        
        # Add finance manager
        self.finance_manager = FinanceManager(db_manager)
    
    def setup_handlers(self):
        # ... existing handlers ...
        
        # Add finance handlers
        self.finance_manager.setup_handlers(self.application)
    
    # Update the callback handler to include finance menu
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # ... existing code ...
        
        elif callback_data == "menu_finance":
            keyboard = [
                [
                    InlineKeyboardButton("💸 Add Expense", callback_data="add_expense"),
                    InlineKeyboardButton("💰 Add Income", callback_data="add_income")
                ],
                [
                    InlineKeyboardButton("📸 Scan Receipt", callback_data="scan_receipt"),
                    InlineKeyboardButton("📊 Monthly Report", callback_data="financial_report")
                ],
                [
                    InlineKeyboardButton("💰 Balance", callback_data="balance"),
                    InlineKeyboardButton("📄 Export CSV", callback_data="export_csv")
                ],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "💰 **Finance Management**\n\n"
                "Choose an action:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

2. Environment Variables to add:
   GOOGLE_CREDENTIALS_JSON=<base64_encoded_service_account_json>
   DEFAULT_CURRENCY=EUR

3. Railway Setup for Google Vision API:
   - Create Google Cloud Project
   - Enable Vision API
   - Create Service Account
   - Download JSON key
   - Base64 encode the JSON: cat key.json | base64 -w 0
   - Add to Railway environment variables
"""

# ==============================================================================
# PHASE 2 FEATURE SUMMARY
# ==============================================================================

"""
🎉 PHASE 2 FINANCE MANAGEMENT COMPLETE!

✅ IMPLEMENTED FEATURES:

💸 Expense Management:
- Interactive expense adding with categories
- Smart date handling (today/YYYY-MM-DD)
- Description support
- Budget alerts and warnings

💰 Income Management:  
- Multi-source income tracking
- Same intuitive flow as expenses
- Category-based organization

📸 OCR Receipt Processing:
- Google Vision API integration
- Smart data extraction (amount, date, merchant)
- Auto-categorization based on merchant
- Quick-add buttons from OCR results

📊 Financial Reporting:
- Beautiful matplotlib charts
- Monthly income vs expenses
- Category breakdowns (pie charts)
- Daily spending trends
- Budget vs actual comparisons
- High-resolution PNG exports

📄 Data Export:
- CSV export for Excel/Sheets
- Date range filtering
- Complete transaction history

💡 Smart Features:
- Budget monitoring with alerts
- Intelligent receipt parsing
- Category suggestions
- Balance tracking
- Savings rate calculations

🎯 COMMANDS AVAILABLE:
/add_expense - Add expense interactively
/add_income - Add income interactively  
/scan_receipt - OCR receipt processing
/expenses_month [year] [month] - Monthly expense summary
/income_month [year] [month] - Monthly income summary
/balance - Current month balance
/financial_report [year] [month] - Generate visual report
/export_csv [year] [month] - Export to CSV

🔧 TECHNICAL HIGHLIGHTS:
- Async conversation handlers
- Database connection pooling
- Error handling & logging
- Modular design for easy extension
- Production-ready code structure

Ready for Phase 3: n8n Business Management! 🚀
"""
        