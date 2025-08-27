"""
Natural Language Processing Module for UmbraSIL Bot
Uses OpenRouter API with free/cheap models for intelligent message understanding
"""

import os
import json
import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import aiohttp

logger = logging.getLogger(__name__)

class NLPManager:
    """Manages natural language processing using OpenRouter API"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
        # Model selection from environment or defaults
        self.models = {
            "intent": os.getenv("NLP_INTENT_MODEL", "meta-llama/llama-3.2-3b-instruct:free"),
            "extraction": os.getenv("NLP_EXTRACTION_MODEL", "mistralai/mistral-7b-instruct:free"),
            "analysis": os.getenv("NLP_ANALYSIS_MODEL", "anthropic/claude-3-haiku"),
            "chat": os.getenv("NLP_CHAT_MODEL", "meta-llama/llama-3.2-3b-instruct:free")
        }
        
        # Common vendor-to-category mappings
        self.vendor_categories = {
            # Groceries
            "coop": "groceries", "migros": "groceries", "lidl": "groceries", 
            "aldi": "groceries", "denner": "groceries", "spar": "groceries",
            "rewe": "groceries", "edeka": "groceries", "carrefour": "groceries",
            
            # Food & Dining
            "mcdonalds": "food", "burger king": "food", "starbucks": "coffee",
            "restaurant": "dining", "cafe": "coffee", "pizza": "food",
            "kebab": "food", "sushi": "dining",
            
            # Transport
            "uber": "transport", "lyft": "transport", "sbb": "transport",
            "taxi": "transport", "gas": "transport", "petrol": "transport",
            "parking": "transport", "train": "transport", "bus": "transport",
            
            # Utilities & Services
            "electricity": "utilities", "water": "utilities", "gas": "utilities",
            "internet": "utilities", "phone": "utilities", "mobile": "utilities",
            
            # Entertainment & Subscriptions
            "netflix": "entertainment", "spotify": "entertainment", "amazon": "shopping",
            "steam": "entertainment", "playstation": "entertainment", "cinema": "entertainment",
            
            # Health & Personal
            "pharmacy": "health", "doctor": "health", "gym": "health",
            "haircut": "personal", "barber": "personal"
        }
        
        # Quick patterns for common messages
        self.quick_patterns = {
            'expense': [
                r'spent?\s+(\d+\.?\d*)\s+(?:at|on|for)?\s*(.+)',
                r'paid?\s+(\d+\.?\d*)\s+(?:at|to|for)?\s*(.+)',
                r'bought?\s+(.+)\s+for\s+(\d+\.?\d*)',
                r'(\d+\.?\d*)\s+(?:at|for|on)\s+(.+)',
            ],
            'income': [
                r'(?:got|received|earned)\s+(\d+\.?\d*)\s*(?:from)?\s*(.+)?',
                r'(?:salary|payment|income)\s+(?:of)?\s*(\d+\.?\d*)',
                r'(\d+\.?\d*)\s+(?:from)\s+(.+)',
            ],
            'balance': [
                r'(?:what\'?s?|show|check)\s+(?:my)?\s*balance',
                r'how much (?:do i have|money)',
                r'(?:balance|total|summary)',
            ]
        }
    
    def is_operational(self) -> bool:
        """Check if NLP is configured and operational"""
        return bool(self.api_key)
    
    async def process_message(self, message: str, user_context: Dict = None) -> Dict[str, Any]:
        """
        Process a natural language message and extract intent and entities
        
        Returns:
            {
                "intent": "expense|income|balance|report|chat",
                "confidence": 0.95,
                "entities": {
                    "amount": 12.50,
                    "vendor": "coop",
                    "category": "groceries",
                    "description": "shopping at coop"
                },
                "response": "Added expense: 12.50 EUR at Coop (groceries)"
            }
        """
        
        # First try quick pattern matching for common formats
        quick_result = self._quick_parse(message)
        if quick_result and quick_result.get('confidence', 0) > 0.8:
            return quick_result
        
        # If no quick match or low confidence, use AI
        if self.is_operational():
            return await self._ai_parse(message, user_context)
        
        # Fallback to basic pattern matching
        return self._fallback_parse(message)
    
    def _quick_parse(self, message: str) -> Optional[Dict[str, Any]]:
        """Quick pattern matching for common expense/income formats"""
        message_lower = message.lower().strip()
        
        # Check expense patterns
        for pattern in self.quick_patterns['expense']:
            match = re.search(pattern, message_lower)
            if match:
                groups = match.groups()
                amount = self._extract_amount(groups[0] if groups[0] else groups[1])
                vendor_text = groups[1] if len(groups) > 1 and groups[1] else groups[0]
                
                if amount:
                    vendor = self._clean_vendor(vendor_text)
                    category = self._get_category(vendor)
                    
                    return {
                        "intent": "expense",
                        "confidence": 0.9,
                        "entities": {
                            "amount": amount,
                            "vendor": vendor,
                            "category": category,
                            "description": f"{vendor} purchase"
                        }
                    }
        
        # Check income patterns
        for pattern in self.quick_patterns['income']:
            match = re.search(pattern, message_lower)
            if match:
                groups = match.groups()
                amount = self._extract_amount(groups[0])
                source = groups[1] if len(groups) > 1 and groups[1] else "income"
                
                if amount:
                    return {
                        "intent": "income",
                        "confidence": 0.9,
                        "entities": {
                            "amount": amount,
                            "source": self._clean_vendor(source),
                            "description": f"Income from {source}"
                        }
                    }
        
        # Check balance patterns
        for pattern in self.quick_patterns['balance']:
            if re.search(pattern, message_lower):
                return {
                    "intent": "balance",
                    "confidence": 0.95,
                    "entities": {}
                }
        
        return None
    
    async def _ai_parse(self, message: str, user_context: Dict = None) -> Dict[str, Any]:
        """Use AI model to parse complex messages"""
        
        # Select model based on message complexity
        model = self._select_model(message)
        
        # Build prompt for the AI
        prompt = self._build_prompt(message, user_context)
        
        try:
            # Call OpenRouter API
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/silvioiatech/UmbraSIL",
                    "X-Title": "UmbraSIL Bot"
                }
                
                payload = {
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a financial assistant that extracts transaction details from messages. Always respond with valid JSON only."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 200
                }
                
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        ai_response = data['choices'][0]['message']['content']
                        
                        # Parse AI response
                        try:
                            # Clean up response if it has markdown
                            ai_response = ai_response.replace('```json', '').replace('```', '').strip()
                            result = json.loads(ai_response)
                            
                            # Enhance with category detection
                            if result.get('intent') == 'expense' and result.get('entities', {}).get('vendor'):
                                vendor = result['entities']['vendor']
                                if not result['entities'].get('category'):
                                    result['entities']['category'] = self._get_category(vendor)
                            
                            return result
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse AI response: {ai_response}")
                            return self._fallback_parse(message)
                    else:
                        logger.error(f"OpenRouter API error: {response.status}")
                        return self._fallback_parse(message)
                        
        except Exception as e:
            logger.error(f"AI parsing error: {e}")
            return self._fallback_parse(message)
    
    def _select_model(self, message: str) -> str:
        """Select appropriate model based on message complexity"""
        words = len(message.split())
        
        if words < 10:
            return self.models["intent"]  # Use free model for simple messages
        elif "analyze" in message.lower() or "report" in message.lower():
            return self.models["analysis"]  # Use better model for complex analysis
        else:
            return self.models["extraction"]  # Default to extraction model
    
    def _build_prompt(self, message: str, user_context: Dict = None) -> str:
        """Build prompt for AI model"""
        
        context_str = ""
        if user_context:
            context_str = f"\nUser context: Currency is {user_context.get('currency', 'EUR')}"
        
        return f"""Analyze this message and extract financial transaction information.{context_str}

Message: "{message}"

Respond with JSON only:
{{
    "intent": "expense|income|balance|report|chat",
    "confidence": 0.0 to 1.0,
    "entities": {{
        "amount": number or null,
        "vendor": "string" or null (for expenses),
        "source": "string" or null (for income),
        "category": "groceries|food|transport|utilities|entertainment|health|personal|other",
        "description": "brief description"
    }}
}}

Examples:
"spent 20 at starbucks" -> {{"intent":"expense","confidence":0.95,"entities":{{"amount":20,"vendor":"starbucks","category":"coffee","description":"Coffee at Starbucks"}}}}
"got paid 3000" -> {{"intent":"income","confidence":0.9,"entities":{{"amount":3000,"source":"salary","description":"Salary payment"}}}}
"show balance" -> {{"intent":"balance","confidence":1.0,"entities":{{}}}}

Only output valid JSON, no other text."""
    
    def _fallback_parse(self, message: str) -> Dict[str, Any]:
        """Fallback parsing when AI is not available"""
        message_lower = message.lower().strip()
        
        # Simple keyword detection
        if any(word in message_lower for word in ['spent', 'paid', 'bought', 'expense']):
            amount = self._extract_amount(message)
            if amount:
                return {
                    "intent": "expense",
                    "confidence": 0.6,
                    "entities": {
                        "amount": amount,
                        "category": "other",
                        "description": message[:50]
                    }
                }
        
        elif any(word in message_lower for word in ['received', 'got', 'earned', 'income', 'salary']):
            amount = self._extract_amount(message)
            if amount:
                return {
                    "intent": "income",
                    "confidence": 0.6,
                    "entities": {
                        "amount": amount,
                        "source": "income",
                        "description": message[:50]
                    }
                }
        
        elif any(word in message_lower for word in ['balance', 'total', 'how much']):
            return {
                "intent": "balance",
                "confidence": 0.7,
                "entities": {}
            }
        
        # Default to chat
        return {
            "intent": "chat",
            "confidence": 0.5,
            "entities": {},
            "original_message": message
        }
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract numeric amount from text"""
        if isinstance(text, (int, float)):
            return float(text)
        
        # Find all numbers in the text
        numbers = re.findall(r'\d+\.?\d*', str(text))
        if numbers:
            try:
                # Return the first valid number
                return float(numbers[0])
            except ValueError:
                pass
        return None
    
    def _clean_vendor(self, vendor: str) -> str:
        """Clean and normalize vendor name"""
        if not vendor:
            return "unknown"
        
        # Remove common words and clean up
        vendor = re.sub(r'\b(at|for|to|from|in|on)\b', '', vendor)
        vendor = vendor.strip().title()
        return vendor if vendor else "unknown"
    
    def _get_category(self, vendor: str) -> str:
        """Get category based on vendor name"""
        vendor_lower = vendor.lower()
        
        # Check vendor mappings
        for vendor_key, category in self.vendor_categories.items():
            if vendor_key in vendor_lower:
                return category
        
        # Check for category keywords in vendor name
        category_keywords = {
            "groceries": ["market", "grocery", "supermarket"],
            "food": ["restaurant", "food", "eat", "lunch", "dinner", "breakfast"],
            "coffee": ["coffee", "cafe", "starbucks"],
            "transport": ["uber", "taxi", "bus", "train", "gas", "petrol"],
            "utilities": ["electric", "water", "internet", "phone"],
            "health": ["pharmacy", "doctor", "hospital", "clinic"],
            "entertainment": ["cinema", "movie", "game", "play"]
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in vendor_lower for keyword in keywords):
                return category
        
        return "other"
    
    async def process_receipt_image(self, image_data: bytes) -> Dict[str, Any]:
        """Process receipt image (placeholder for OCR integration)"""
        # This would integrate with OCR service
        # For now, return a placeholder
        return {
            "intent": "expense",
            "confidence": 0.5,
            "entities": {
                "amount": 0,
                "vendor": "receipt",
                "category": "other",
                "description": "Receipt scan pending OCR integration"
            },
            "note": "Receipt processing requires OCR setup"
        }
