            if update.message:
                await update.message.reply_text(error_text, reply_markup=InlineKeyboardMarkup(keyboard))
            elif update.callback_query:
                await update.callback_query.edit_message_text(error_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def show_docker_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show Docker status"""
        try:
            result = await self.vps.execute_command("docker ps -a")
            
            if result["success"]:
                output = result["output"][:2500] if result["output"] else "No containers found"
                status_text = f"""
🐳 **Docker Containers**

```
{output}
```

🔄 **Last Updated**: {datetime.now().strftime('%H:%M:%S')}
"""
            else:
                status_text = f"""
🐳 **Docker Status**

❌ **Error**: {result['error']}

🔧 **Possible Issues**:
• Docker not installed
• Docker service not running
• Permission denied

🔄 **Last Checked**: {datetime.now().strftime('%H:%M:%S')}
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="docker_status"),
                    InlineKeyboardButton("📊 System", callback_data="system_status")
                ],
                [
                    InlineKeyboardButton("🏠 Menu", callback_data="main_menu")
                ]
            ]
            
            if update.callback_query:
                await update.callback_query.edit_message_text(status_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.message.reply_text(status_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        
        except Exception as e:
            logger.error(f"Docker status error: {e}")
            error_text = f"❌ Error getting Docker status: {str(e)[:200]}"
            keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="main_menu")]]
            
            if update.callback_query:
                await update.callback_query.edit_message_text(error_text, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.message.reply_text(error_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def show_vps_control(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show VPS control menu"""
        control_text = """
🖥️ **VPS Control Panel**

Advanced system management:
"""
        
        keyboard = [
            [
                InlineKeyboardButton("⚙️ Execute Command", callback_data="execute_command"),
                InlineKeyboardButton("📋 System Logs", callback_data="system_logs")
            ],
            [
                InlineKeyboardButton("🔄 Restart Service", callback_data="restart_service"),
                InlineKeyboardButton("📁 File Manager", callback_data="file_manager")
            ],
            [
                InlineKeyboardButton("🏠 Menu", callback_data="main_menu")
            ]
        ]
        
        await update.callback_query.edit_message_text(
            control_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        try:
            callback_data = query.data
            
            # Main navigation
            if callback_data == "main_menu":
                await self.main_menu_command(update, context)
            elif callback_data == "show_help":
                await self.help_command(update, context)
            elif callback_data == "system_status":
                await self.show_system_status(update, context)
            elif callback_data == "docker_status":
                await self.show_docker_status(update, context)
            elif callback_data == "vps_control":
                await self.show_vps_control(update, context)
            elif callback_data == "clear_context":
                user_id = update.effective_user.id
                self.ai.clear_context(user_id)
                await query.answer("🧠 Chat context cleared!", show_alert=True)
            elif callback_data == "ai_help":
                await query.edit_message_text(
                    "🤖 **AI Assistant Help**\n\nJust type naturally to me! I can:\n\n• Answer questions about your VPS\n• Execute commands\n• Help with troubleshooting\n• Chat about technical topics\n\nTry: \"How's my server doing?\"",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="main_menu")]])
                )
            else:
                # Coming soon features
                await query.edit_message_text(
                    f"🚧 **Feature Coming Soon**\n\nThe '{callback_data}' feature is under development.\n\nFor now, try chatting with me or use the available system monitoring features!",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="main_menu")]])
                )
                
        except Exception as e:
            logger.error(f"Button handler error: {e}")
            self.metrics.log_error(str(e))
            await query.edit_message_text(
                "❌ An error occurred. Please try again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu", callback_data="main_menu")]])
            )
    
    async def handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        error = context.error
        logger.error(f"Update {update} caused error: {error}")
        self.metrics.log_error(str(error))
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ An error occurred. Please try again or use /start to restart."
                )
            except:
                pass
    
    def cleanup(self):
        """Cleanup resources"""
        self.vps.cleanup()

# Simplified main function without asyncio conflicts
def main():
    """Main function - uses run_polling to avoid event loop conflicts"""
    try:
        logger.info("🚀 Starting UmbraSIL Bot...")
        
        # Create bot instance
        bot = UmbraSILBot()
        
        # Run with polling (Railway handles health checks via PORT)
        logger.info("✅ Bot initialized, starting polling...")
        bot.application.run_polling(
            drop_pending_updates=True,
            close_loop=False  # Important: let the framework manage the loop
        )
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        try:
            if 'bot' in locals():
                bot.cleanup()
        except:
            pass

if __name__ == "__main__":
    main()
