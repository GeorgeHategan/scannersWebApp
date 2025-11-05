#!/usr/bin/env python3
"""
Pre-deployment test script for Market Analysis Platform
Run this locally to ensure everything works before deploying to Render
"""

import os
import sys
import requests
import time
import subprocess
from pathlib import Path

def test_database_connection():
    """Test if database is accessible"""
    try:
        import duckdb
        
        # Try multiple database paths
        db_paths = ["./taq_data.duckdb", "../taq_data.duckdb", "taq_data.duckdb"]
        
        for path in db_paths:
            if os.path.exists(path):
                con = duckdb.connect(path)
                result = con.execute("SELECT COUNT(*) FROM taq_1min").fetchone()
                print(f"✅ Database found at {path} with {result[0]} records")
                return True
        
        print("❌ Database not found in any expected location")
        return False
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_imports():
    """Test if all required packages can be imported"""
    required_packages = [
        "fastapi", "uvicorn", "duckdb", "pandas", "jinja2"
    ]
    
    success = True
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} imported successfully")
        except ImportError as e:
            print(f"❌ {package} import failed: {e}")
            success = False
    
    return success

def start_test_server():
    """Start server for testing"""
    try:
        # Change to the correct directory
        if os.path.exists("tradingview_app"):
            os.chdir("tradingview_app")
        
        print("🚀 Starting test server...")
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8001"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        time.sleep(3)
        
        return process
        
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return None

def test_endpoints():
    """Test API endpoints"""
    base_url = "http://127.0.0.1:8001"
    endpoints = [
        "/test",
        "/api/history?symbol=AAPL",
        "/api/spread?symbol=AAPL",
        "/api/indicators?symbol=AAPL"
    ]
    
    success = True
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            if response.status_code == 200:
                print(f"✅ {endpoint} - Status: {response.status_code}")
            else:
                print(f"⚠️  {endpoint} - Status: {response.status_code}")
                success = False
        except Exception as e:
            print(f"❌ {endpoint} - Error: {e}")
            success = False
    
    return success

def main():
    """Run all tests"""
    print("🧪 Pre-Deployment Test Suite for Market Analysis Platform\n")
    
    # Test 1: Database connection
    print("1️⃣ Testing Database Connection:")
    db_ok = test_database_connection()
    
    # Test 2: Package imports
    print("\n2️⃣ Testing Package Imports:")
    imports_ok = test_imports()
    
    # Test 3: Server startup and endpoints
    print("\n3️⃣ Testing Server and Endpoints:")
    server = start_test_server()
    
    if server:
        endpoints_ok = test_endpoints()
        
        # Cleanup
        server.terminate()
        server.wait()
    else:
        endpoints_ok = False
    
    # Summary
    print(f"\n📊 Test Results:")
    print(f"   Database: {'✅ PASS' if db_ok else '❌ FAIL'}")
    print(f"   Imports:  {'✅ PASS' if imports_ok else '❌ FAIL'}")
    print(f"   Server:   {'✅ PASS' if endpoints_ok else '❌ FAIL'}")
    
    if db_ok and imports_ok and endpoints_ok:
        print(f"\n🎉 All tests passed! Ready for Render deployment.")
        print(f"🚀 Next: Push to GitHub and deploy on Render")
        return 0
    else:
        print(f"\n⚠️  Some tests failed. Fix issues before deployment.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)