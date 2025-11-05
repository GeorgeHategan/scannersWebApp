#!/usr/bin/env python3
"""
Production startup script for Market Analysis Platform
Handles database initialization and server startup for Render deployment
"""

import os
import sys
import uvicorn
from pathlib import Path

def main():
    """Start the application server"""
    
    # Set environment for production
    os.environ.setdefault("PORT", "8000")
    
    # Get port from environment (Render sets this automatically)
    port = int(os.getenv("PORT", 8000))
    
    # Change to tradingview_app directory for app.py and static/
    script_dir = Path(__file__).parent.resolve()
    app_dir = script_dir / "tradingview_app"
    
    if app_dir.exists():
        os.chdir(app_dir)
        # Add current directory to Python path
        sys.path.insert(0, str(app_dir))
        print(f"📁 Changed working directory to: {app_dir}")
    
    print(f"🚀 Starting Market Analysis Platform on port {port}")
    print(f"📊 Current directory: {os.getcwd()}")
    print(f"📊 Python path: {sys.path[:3]}")
    print(f"🦆 USE_MOTHERDUCK: {os.getenv('USE_MOTHERDUCK', 'false')}")
    print(f"🦆 DATABASE_NAME: {os.getenv('DATABASE_NAME', 'not set')}")
    
    # Import the app directly
    try:
        import app as application
        print("✅ App module imported successfully")
    except Exception as e:
        print(f"❌ Failed to import app: {e}")
        sys.exit(1)
    
    # Start the server
    uvicorn.run(
        application.app,
        host="0.0.0.0",
        port=port,
        workers=1,
        log_level="info"
    )


if __name__ == "__main__":
    main()
