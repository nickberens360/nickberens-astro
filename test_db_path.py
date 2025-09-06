#!/usr/bin/env python3
"""
Quick Railway database path test - inline script for Railway deployment
"""
import os
import sqlite3
from pathlib import Path


def test_railway_db_paths():
    """Test database paths in Railway environment."""
    print("🚀 Testing Railway database paths...")

    # Check environment
    if os.getenv("RAILWAY_ENVIRONMENT_NAME"):
        print(f"📍 Railway environment: {os.getenv('RAILWAY_ENVIRONMENT_NAME')}")
    else:
        print("📍 Not in Railway environment")

    # Check paths
    paths_to_test = [
        Path("/data"),
        Path("/app/data"),
        Path("/tmp"),
        Path("/app"),
    ]

    for path in paths_to_test:
        exists = path.exists()
        writable = path.exists() and os.access(path, os.W_OK)
        print(f"  {path}: exists={exists}, writable={writable}")

        if writable:
            try:
                test_file = path / "test_write.txt"
                test_file.write_text("Railway test")
                test_file.unlink()
                print(f"    ✅ {path} - write test passed")
            except Exception as e:
                print(f"    ❌ {path} - write test failed: {e}")

    # Test our database utils function
    try:
        print("\n🔍 Testing database_utils.get_database_path()...")
        # Import our function
        import sys

        sys.path.append("/app/backend/core")
        from database_utils import get_database_path

        db_path = get_database_path("test_admin.db")
        print(f"  Database path chosen: {db_path}")
        print(f"  Parent directory exists: {db_path.parent.exists()}")
        print(f"  Parent directory writable: {os.access(db_path.parent, os.W_OK)}")

        # Try to create a test database
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
            cursor.execute("INSERT INTO test (data) VALUES ('Railway works!')")

        # Read it back
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM test WHERE id = 1")
            result = cursor.fetchone()

        if result and result[0] == "Railway works!":
            print("  ✅ Database creation and read/write successful!")
        else:
            print("  ❌ Database read/write failed")

        # Clean up
        db_path.unlink()

    except Exception as e:
        print(f"  ❌ Database test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_railway_db_paths()
