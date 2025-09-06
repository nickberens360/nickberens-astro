#!/usr/bin/env python3
"""
Test if Railway volume is now working with RAILWAY_RUN_UID=0
"""
import os
import sqlite3
from pathlib import Path


def test_volume_fix():
    """Test if /data volume is now accessible."""
    print("🔧 Testing Railway volume fix with RAILWAY_RUN_UID=0")

    # Check if we're in Railway environment
    if not os.getenv("RAILWAY_ENVIRONMENT_NAME"):
        print("❌ Not in Railway environment - this test should run in production")
        return

    print(f"📍 Railway environment: {os.getenv('RAILWAY_ENVIRONMENT_NAME')}")
    print(f"📍 Volume name: {os.getenv('RAILWAY_VOLUME_NAME', 'Not set')}")
    print(f"📍 Volume mount path: {os.getenv('RAILWAY_VOLUME_MOUNT_PATH', 'Not set')}")

    # Test /data directory
    data_path = Path("/data")
    print(f"\n🔍 Testing {data_path}:")
    print(f"  Exists: {data_path.exists()}")

    if data_path.exists():
        print(f"  Readable: {os.access(data_path, os.R_OK)}")
        print(f"  Writable: {os.access(data_path, os.W_OK)}")
        print(f"  Executable: {os.access(data_path, os.X_OK)}")

        # Test creating a database
        try:
            test_db = data_path / "volume_test.db"
            print(f"\n💾 Testing SQLite database creation at {test_db}")

            with sqlite3.connect(str(test_db)) as conn:
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, message TEXT)")
                cursor.execute("INSERT INTO test (message) VALUES (?)", ("Volume is working!",))
                conn.commit()

                # Read back
                cursor.execute("SELECT message FROM test ORDER BY id DESC LIMIT 1")
                result = cursor.fetchone()

                if result and result[0] == "Volume is working!":
                    print("✅ SUCCESS: Volume is working! Database read/write successful")

                    # Check file exists and is persistent
                    if test_db.exists():
                        print(f"✅ SUCCESS: Database file persisted at {test_db}")
                        print(f"    File size: {test_db.stat().st_size} bytes")

                    return True
                else:
                    print("❌ FAILED: Could not read data back from database")

        except Exception as e:
            print(f"❌ FAILED: Database test failed: {e}")

    else:
        print("❌ FAILED: /data directory does not exist")

        # Try creating it
        try:
            data_path.mkdir(parents=True, exist_ok=True)
            print("✅ SUCCESS: Created /data directory")
            return test_volume_fix()  # Retry the test
        except Exception as e:
            print(f"❌ FAILED: Could not create /data directory: {e}")

    return False


if __name__ == "__main__":
    success = test_volume_fix()
    exit(0 if success else 1)
