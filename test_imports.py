#!/usr/bin/env python3
"""Test script to verify all imports work correctly"""

import sys
import os
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def test_imports():
    print("Testing imports...")
    
    try:
        # Test basic imports
        import fastapi
        print("✓ FastAPI imported successfully")
        
        import twilio
        print(f"✓ Twilio imported successfully (version: {twilio.__version__})")
        
        from twilio.twiml.voice_response import VoiceResponse
        print("✓ VoiceResponse imported successfully")
        
        # Test our service imports (without initialization)
        from services.twilio_service import TwilioService
        print("✓ TwilioService imported successfully")
        
        from services.deepgram_service import DeepgramService
        print("✓ DeepgramService imported successfully")
        
        from services.supabase_service import SupabaseService
        print("✓ SupabaseService imported successfully")
        
        from services.ai_agent import AIAgent
        print("✓ AIAgent imported successfully")
        
        # Test models
        import models
        print("✓ Models imported successfully")
        
        print("\n✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Import error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)