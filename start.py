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
    
    # Check if we can find the app module
    app_module = "tradingview_app.app:app"
    
    # For Render deployment, the working directory might be different
    if not os.path.exists("tradingview_app"):
        # If we're in the root directory, use the module path directly
        if os.path.exists("app.py"):
            app_module = "app:app"
    
    print(f"🚀 Starting Market Analysis Platform on port {port}")
    print(f"📊 Using app module: {app_module}")
    
    # Start the server
    uvicorn.run(
        app_module,
        host="0.0.0.0",
        port=port,
        workers=1,
        log_level="info"
    )

if __name__ == "__main__":
    main()