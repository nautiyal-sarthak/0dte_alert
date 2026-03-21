#!/usr/bin/env python3
"""
Health check script for 0DTE Alert OpenClaw integration
Verifies setup and configuration
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def check_files():
    """Check if required files exist"""
    required_files = [
        'main.py',
        'requirements.txt',
        'config/strategy.yaml',
        '.env'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files present")
    return True

def check_environment():
    """Check environment variables"""
    load_dotenv()
    
    required_vars = ['ANTHROPIC_API_KEY']
    optional_vars = ['TELEGRAM_BOT_TOKEN', 'LOG_LEVEL']
    
    print("\n🔍 Environment Variables:")
    
    # Check required vars
    missing_required = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * 8}...{value[-4:]}")
        else:
            print(f"❌ {var}: NOT SET")
            missing_required.append(var)
    
    # Check optional vars  
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            if 'TOKEN' in var:
                print(f"✅ {var}: {'*' * 8}...{value[-4:]}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"⚠️ {var}: Not set (optional)")
    
    return len(missing_required) == 0

def check_dependencies():
    """Check if Python dependencies are installed"""
    print("\n📦 Checking Dependencies:")
    
    required_modules = [
        'requests',
        'pandas', 
        'numpy',
        'ta',
        'yaml',
        'langchain',
        'anthropic',
        'dotenv'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module}")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"\n💡 Install missing modules: pip install {' '.join(missing_modules)}")
        return False
    
    return True

def main():
    """Run complete health check"""
    print("🏥 0DTE Alert Health Check")
    print("=" * 40)
    
    checks = [
        ("Files", check_files),
        ("Environment", check_environment), 
        ("Dependencies", check_dependencies)
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"\n📋 {name} Check:")
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 All checks passed! Ready for OpenClaw cron execution.")
        return 0
    else:
        print("⚠️ Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())