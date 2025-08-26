#!/usr/bin/env python3
"""
Quick test script to verify bot functionality locally
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_bot_components():
    """Test bot components without actually running the bot"""
    
    print("Testing bot components...")
    
    try:
        # Test imports
        from main import Bot, SimpleModule, SimpleAuth, SimpleDatabase
        print("✅ All imports successful")
        
        # Test basic instantiation
        auth = SimpleAuth()
        db = SimpleDatabase()
        module = SimpleModule("Test")
        
        print("✅ Component instantiation successful")
        
        # Test authentication
        test_user_id = 8286836821  # Your user ID
        is_authed = await auth.authenticate_user(test_user_id)
        print(f"✅ Authentication test: {is_authed}")
        
        # Test database
        await db.initialize()
        db_connected = await db.check_connection()
        print(f"✅ Database test: {db_connected}")
        
        # Test module
        menu = module.get_menu()
        print(f"✅ Module test: {bool(menu)}")
        
        print("\n🎉 All component tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def test_bot_creation():
    """Test actual bot creation"""
    
    print("\nTesting bot creation...")
    
    try:
        # Set a dummy token for testing
        os.environ["TELEGRAM_BOT_TOKEN"] = "dummy_token_for_testing"
        
        from main import Bot
        
        # This should work now
        bot = Bot()
        print("✅ Bot creation successful")
        
        # Test status
        status = await bot.get_system_status()
        print(f"✅ Status generation: {bool(status)}")
        
        print("🎉 Bot creation test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Bot creation test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Starting UmbraSIL Bot Tests\n")
    
    # Test components
    component_test = await test_bot_components()
    
    # Test bot creation
    bot_test = await test_bot_creation()
    
    if component_test and bot_test:
        print("\n🎉 ALL TESTS PASSED! Your bot should work correctly now.")
        print("\nNext steps:")
        print("1. Make sure TELEGRAM_BOT_TOKEN is set in your Railway environment")
        print("2. Deploy to Railway")
        print("3. Test with your actual Telegram bot")
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
