import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from telegram import Update, Message
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from openai import AsyncOpenAI
import anthropic
from ...core import DatabaseManager, require_auth
from .config import AIConfig

logger = logging.getLogger(__name__)

class AIManager:
    """Manages AI Assistant functionality"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.config = AIConfig
        self.openai_client = AsyncOpenAI(api_key=self.config.OPENAI_API_KEY)
        self.claude_client = anthropic.AsyncAnthropic(api_key=self.config.CLAUDE_API_KEY)
        self.context_store: Dict[int, List[Dict]] = {}
        self.last_interaction: Dict[int, datetime] = {}
    
    def setup_handlers(self, application):
        """Setup AI-related command handlers"""
        application.add_handler(CommandHandler("ask", self.ask_command))
        application.add_handler(CommandHandler("clear", self.clear_context_command))
        application.add_handler(MessageHandler(
            filters.VOICE & ~filters.COMMAND,
            self.handle_voice
        ))
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_message
        ))
        
        logger.info("AI handlers initialized")
    
    def _update_context(self, user_id: int, role: str, content: str):
        """Update conversation context"""
        now = datetime.now()
        
        # Initialize or clean expired context
        if user_id not in self.context_store:
            self.context_store[user_id] = []
        else:
            # Remove expired messages
            cutoff = now - timedelta(seconds=self.config.CONTEXT_EXPIRY)
            self.context_store[user_id] = [
                msg for msg in self.context_store[user_id]
                if msg.get('timestamp', now) > cutoff
            ]
        
        # Add new message
        self.context_store[user_id].append({
            'role': role,
            'content': content,
            'timestamp': now
        })
        
        # Trim to max context length
        if len(self.context_store[user_id]) > self.config.MAX_CONTEXT_MESSAGES:
            self.context_store[user_id] = self.context_store[user_id][-self.config.MAX_CONTEXT_MESSAGES:]
    
    async def _get_ai_response(self, messages: List[Dict]) -> str:
        """Get response from AI model"""
        try:
            # Try OpenAI first
            response = await self.openai_client.chat.completions.create(
                model=self.config.OPENAI_MODEL,
                messages=[{'role': m['role'], 'content': m['content']} for m in messages],
                temperature=self.config.TEMPERATURE,
                max_tokens=self.config.MAX_TOKENS,
                stream=self.config.STREAM
            )
            
            full_response = ""
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
            
            return full_response
            
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            
            # Fallback to Claude
            try:
                response = await self.claude_client.messages.create(
                    model=self.config.CLAUDE_MODEL,
                    max_tokens=self.config.MAX_TOKENS,
                    messages=[
                        {'role': m['role'], 'content': m['content']}
                        for m in messages
                    ]
                )
                return response.content[0].text
                
            except Exception as e:
                logger.error(f"Claude error: {e}")
                return "Sorry, I'm having trouble accessing AI services right now. Please try again later."
    
    @require_auth
    async def ask_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ask command"""
        if not update.message or not update.message.text:
            return
        
        query = update.message.text.replace("/ask", "").strip()
        if not query:
            await update.message.reply_text(
                "Please provide a question after /ask command."
            )
            return
        
        await self._process_query(update.message, query)
    
    @require_auth
    async def clear_context_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Clear conversation context"""
        if not update.effective_user:
            return
            
        user_id = update.effective_user.id
        self.context_store.pop(user_id, None)
        self.last_interaction.pop(user_id, None)
        
        await update.message.reply_text(
            "✨ Conversation context cleared! Starting fresh."
        )
    
    @require_auth
    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle voice messages"""
        if not self.config.VOICE_ENABLED:
            await update.message.reply_text(
                "Voice message processing is currently disabled."
            )
            return
        
        if not update.message or not update.message.voice:
            return
            
        # Download voice file
        voice = update.message.voice
        if voice.duration > self.config.MAX_VOICE_LENGTH:
            await update.message.reply_text(
                f"Voice message too long. Maximum duration is {self.config.MAX_VOICE_LENGTH} seconds."
            )
            return
            
        voice_file = await context.bot.get_file(voice.file_id)
        
        # Convert to text using Whisper
        try:
            transcript = await self.openai_client.audio.transcriptions.create(
                model=self.config.VOICE_MODEL,
                file=voice_file.file_path
            )
            
            text = transcript.text
            await update.message.reply_text(f"🎯 Transcribed: {text}")
            await self._process_query(update.message, text)
            
        except Exception as e:
            logger.error(f"Voice processing error: {e}")
            await update.message.reply_text(
                "Sorry, I couldn't process your voice message. Please try again."
            )
    
    @require_auth
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        if not update.message or not update.message.text:
            return
            
        await self._process_query(update.message, update.message.text)
    
    async def _process_query(self, message: Message, query: str):
        """Process user query and generate response"""
        if not message.from_user:
            return
            
        user_id = message.from_user.id
        
        # Check rate limit
        now = datetime.now()
        last_time = self.last_interaction.get(user_id)
        if last_time and (now - last_time).total_seconds() < self.config.COOLDOWN_PERIOD:
            await message.reply_text(
                "Please wait a moment before sending another message."
            )
            return
        
        # Update context with user message
        self._update_context(user_id, "user", query)
        
        # Get AI response
        response = await self._get_ai_response(self.context_store[user_id])
        
        # Update context with AI response
        self._update_context(user_id, "assistant", response)
        
        # Send response
        await message.reply_text(response)
        
        # Update last interaction time
        self.last_interaction[user_id] = now
