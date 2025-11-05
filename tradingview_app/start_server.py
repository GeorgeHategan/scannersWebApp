#!/usr/bin/env python3
import os
import sys
import uvicorn

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

if __name__ == "__main__":
    os.chdir(current_dir)
    print(f"✅ Starting server from: {current_dir}")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)