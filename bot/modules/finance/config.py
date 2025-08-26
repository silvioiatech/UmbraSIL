import os

class FinanceConfig:
    """Finance module configuration"""
    
    # OCR Settings
    GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS_JSON")
    RECEIPT_STORAGE_PATH = "data/receipts"
    
    # Currency Settings
    DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "EUR")
    
    # Categories
    EXPENSE_CATEGORIES = [
        "Food & Dining",
        "Transportation",
        "Utilities",
        "Rent",
        "Business",
        "Entertainment",
        "Healthcare",
        "Other"
    ]
    
    INCOME_CATEGORIES = [
        "Salary",
        "Business",
        "Investments",
        "Other"
    ]
