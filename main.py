#!/usr/bin/env python3
"""
AI Email Manager - Main Entry Point
Launches the AI-powered email management application with intelligent inbox dashboard.

This application implements Phase 1 of the AI Email Manager system:
- Email triage and classification using Google's Gemini AI
- User-friendly GUI built with CustomTkinter
- Learning system that improves with user feedback
- Secure Google Workspace integration

Usage:
    python main.py

Make sure to set up your .env file with the required API keys before running.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import required modules
from loguru import logger
from src.gui.main_app import main as run_app


def check_requirements():
    """Check if all required packages are available."""
    required_packages = [
        'customtkinter',
        'google',
        'loguru',
        'pydantic',
        'dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Missing required packages: {', '.join(missing_packages)}")
        print("Please install them using: pip install -r requirements.txt")
        return False
    
    return True


def setup_environment():
    """Setup the environment and check configuration."""
    # Check for .env file
    env_file = Path(".env")
    if not env_file.exists():
        print("Warning: .env file not found.")
        print("Please copy .env.template to .env and fill in your API keys.")
        print("The application may not work properly without proper configuration.")
        
        # Ask if user wants to continue
        response = input("Do you want to continue anyway? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Exiting...")
            return False
    
    # Create necessary directories
    directories = ['data', 'logs']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    return True


def main():
    """Main entry point."""
    print("=" * 60)
    print("AI Email Manager - Phase 1: Intelligent Email Triage")
    print("=" * 60)
    print()
    
    # Check requirements
    print("Checking requirements...")
    if not check_requirements():
        sys.exit(1)
    
    # Setup environment
    print("Setting up environment...")
    if not setup_environment():
        sys.exit(1)
    
    print("Starting AI Email Manager...")
    print()
    
    try:
        # Run the application
        run_app()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user.")
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"Error: {e}")
        print("Check the logs for more details.")
    finally:
        print("AI Email Manager closed.")


if __name__ == "__main__":
    main()
