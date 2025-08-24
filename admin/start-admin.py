#!/usr/bin/env python3
"""
Simple startup script for the RAG Admin Dashboard backend.
"""
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    # Set default environment variables
    os.environ.setdefault("ADMIN_PORT", "8001")

    # Check if admin token is set
    if not os.environ.get("ADMIN_TOKEN"):
        print("⚠️  WARNING: ADMIN_TOKEN environment variable is not set!")
        print("   Set it with: export ADMIN_TOKEN='your-secure-token-here'")
        print("   Or create a .env file in the admin directory")
        print()

    try:
        import uvicorn

        from admin.backend.main import app

        port = int(os.environ.get("ADMIN_PORT", 8001))

        print("🚀 Starting RAG Admin Dashboard...")
        print(f"   Backend API: http://localhost:{port}/admin/api")
        print(f"   API Docs: http://localhost:{port}/docs")
        print(f"   Health Check: http://localhost:{port}/admin/api/health")
        print()

        if os.environ.get("ADMIN_TOKEN"):
            print("✅ Admin token is configured")

        print("📊 Dashboard will be available at the frontend URL after building")
        print()

        uvicorn.run("admin.backend.main:app", host="0.0.0.0", port=port, reload=True, log_level="info")

    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("   Install with: pip install fastapi uvicorn sqlite3 python-multipart")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
