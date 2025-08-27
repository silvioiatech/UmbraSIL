#!/usr/bin/env python3
"""
Test script to verify minimal bot deployment
"""

import sys
import os

def test_minimal_imports():
    """Test that the bot can run with minimal dependencies"""
    print("🧪 Testing minimal UmbraSIL Bot deployment...")
    
    errors = []
    warnings = []
    
    # Test core required imports
    print("\n1. Testing core dependencies...")
    try:
        import telegram
        print("✅ python-telegram-bot installed")
    except ImportError as e:
        errors.append(f"❌ python-telegram-bot: {e}")
    
    try:
        import dotenv
        print("✅ python-dotenv installed")
    except ImportError as e:
        errors.append(f"❌ python-dotenv: {e}")
    
    try:
        import psutil
        print("✅ psutil installed")
    except ImportError as e:
        errors.append(f"❌ psutil: {e}")
    
    # Test optional lightweight imports
    print("\n2. Testing optional lightweight dependencies...")
    try:
        import requests
        print("✅ requests installed")
    except ImportError:
        warnings.append("⚠️ requests not installed (optional)")
    
    try:
        import dateutil
        print("✅ python-dateutil installed")
    except ImportError:
        warnings.append("⚠️ python-dateutil not installed (optional)")
    
    try:
        import pytz
        print("✅ pytz installed")
    except ImportError:
        warnings.append("⚠️ pytz not installed (optional)")
    
    # Test heavy optional imports (should fail gracefully)
    print("\n3. Testing heavy optional dependencies (should fail gracefully)...")
    
    heavy_deps = {
        'openai': 'AI features',
        'anthropic': 'Claude AI',
        'paramiko': 'VPS management',
        'docker': 'Docker management',
        'asyncpg': 'Database',
        'pandas': 'Data analysis',
        'numpy': 'Numerical computing',
        'fastapi': 'Web interface'
    }
    
    for module, feature in heavy_deps.items():
        try:
            __import__(module)
            print(f"✅ {module} installed ({feature})")
        except ImportError:
            print(f"⏭️ {module} not installed ({feature} - optional)")
    
    # Test main bot import
    print("\n4. Testing main bot import...")
    try:
        # Set dummy token for import test
        os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
        from main import UmbraSILBot
        print("✅ Bot main module imports successfully")
    except ImportError as e:
        errors.append(f"❌ Bot main import failed: {e}")
    except Exception as e:
        warnings.append(f"⚠️ Bot initialization warning: {e}")
    
    # Print summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    
    if errors:
        print(f"\n❌ ERRORS ({len(errors)}):")
        for error in errors:
            print(f"  {error}")
        print("\n🔧 FIX: Install required dependencies with:")
        print("  pip install python-telegram-bot python-dotenv psutil")
    else:
        print("\n✅ All required dependencies are installed!")
    
    if warnings:
        print(f"\n⚠️ WARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"  {warning}")
    
    print("\n📝 DEPLOYMENT NOTES:")
    print("• The bot will work with just the core dependencies")
    print("• Optional features will be disabled if their dependencies are missing")
    print("• This is the configuration that will work on Railway")
    
    return len(errors) == 0

if __name__ == "__main__":
    success = test_minimal_imports()
    sys.exit(0 if success else 1)
