#!/usr/bin/env python3
"""
Basic setup test for AI Email Manager.
Tests that all components can be imported and basic functionality works.
"""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test that all core modules can be imported."""
    try:
        print("Testing imports...")
        
        # Test core imports
        from src.core.config import get_settings
        print("✓ Core configuration imported")
        
        from src.ai.gemini_service import GeminiEmailAI, EmailUrgency, EmailCategory
        print("✓ AI service imported")
        
        from src.auth.google_auth import get_auth_service
        print("✓ Authentication service imported")
        
        from src.database.learning_db import get_learning_db
        print("✓ Database service imported")
        
        from src.core.email_service import get_email_service
        print("✓ Email service imported")
        
        print("✓ All core imports successful!")
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_database():
    """Test database initialization."""
    try:
        print("\nTesting database...")
        from src.database.learning_db import get_learning_db
        
        db = get_learning_db()
        stats = db.get_learning_statistics()
        print(f"✓ Database initialized. Stats: {stats}")
        return True
        
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False


def test_ai_enums():
    """Test AI enumeration classes."""
    try:
        print("\nTesting AI enums...")
        from src.ai.gemini_service import EmailUrgency, EmailCategory
        
        # Test urgency enum
        urgency = EmailUrgency.URGENT
        print(f"✓ Urgency enum: {urgency.value}")
        
        # Test category enum
        category = EmailCategory.WORK
        print(f"✓ Category enum: {category.value}")
        
        return True
        
    except Exception as e:
        print(f"✗ Enum error: {e}")
        return False


def test_config():
    """Test configuration loading."""
    try:
        print("\nTesting configuration...")
        from src.core.config import get_settings
        
        # This will likely fail without .env, but shouldn't crash
        settings = get_settings()
        
        if settings:
            print("✓ Configuration loaded successfully")
        else:
            print("⚠ Configuration not loaded (expected without .env file)")
        
        return True
        
    except Exception as e:
        print(f"⚠ Config warning (expected): {e}")
        return True  # This is expected without proper .env


def test_gui_imports():
    """Test GUI imports."""
    try:
        print("\nTesting GUI imports...")
        import customtkinter as ctk
        print("✓ CustomTkinter imported")
        
        # Test our GUI module
        from src.gui.main_app import EmailManagerApp
        print("✓ Main app class imported")
        
        return True
        
    except ImportError as e:
        print(f"✗ GUI import error: {e}")
        return False
    except Exception as e:
        print(f"✗ GUI error: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 50)
    print("AI Email Manager - Setup Test")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Database", test_database),
        ("AI Enums", test_ai_enums),
        ("Configuration", test_config),
        ("GUI", test_gui_imports),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        if test_func():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! Your setup is ready.")
        print("\nNext steps:")
        print("1. Copy .env.template to .env")
        print("2. Add your API keys to the .env file")
        print("3. Run: python main.py")
    else:
        print("⚠ Some tests failed. Check your installation.")
        print("Try: pip install -r requirements.txt")
    
    print("=" * 50)
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
