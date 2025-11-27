#!/usr/bin/env python3
"""
metricx API Startup Script

This script starts the metricx FastAPI server with the complete API documentation.
"""

import uvicorn
import os
import sys
from pathlib import Path

def main():
    """Start the metricx API server."""
    print("🚀 Starting metricx API Server...")
    print("📊 Features:")
    print("   ✅ Complete Swagger Documentation")
    print("   ✅ Authentication Endpoints")
    print("   ✅ Workspace Management")
    print("   ✅ Connection Management (Ad Platforms)")
    print("   ✅ Entity Management (Campaigns/Ads)")
    print("   ✅ Performance Metrics")
    print("   ✅ P&L Analytics")
    print("")
    print("📖 Documentation will be available at:")
    print("   🌐 Swagger UI:  http://localhost:8000/docs")
    print("   📚 ReDoc:       http://localhost:8000/redoc")
    print("   🔧 Admin Panel: http://localhost:8000/admin")
    print("")
    
    # Check for environment file
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  WARNING: No .env file found!")
        print("   Create a .env file with these variables:")
        print("   JWT_SECRET=your-secret-key-here")
        print("   ADMIN_SECRET_KEY=your-admin-secret")
        print("")
    
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=["app"],
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down metricx API server...")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
