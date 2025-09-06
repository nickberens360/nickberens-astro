#!/usr/bin/env python3
"""
Test script to verify Railway persistent volume access and database initialization.
Run this on your Railway deployment to diagnose database path issues.
"""

import logging
import os
import sqlite3
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_path_access(path: Path) -> bool:
    """Test if we can read/write to a path."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".write_test"
        test_file.write_text("Railway volume test")
        content = test_file.read_text()
        test_file.unlink()
        logger.info(f"✅ Path {path} is writable")
        return True
    except Exception as e:
        logger.error(f"❌ Path {path} failed: {e}")
        return False


def test_sqlite_creation(path: Path) -> bool:
    """Test SQLite database creation."""
    try:
        db_path = path / "test_admin.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute("INSERT INTO test (name) VALUES ('Railway Test')")
        conn.commit()
        conn.close()

        # Verify we can read back
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM test WHERE id = 1")
        result = cursor.fetchone()
        conn.close()

        # Clean up
        db_path.unlink()

        if result and result[0] == "Railway Test":
            logger.info(f"✅ SQLite database works at {path}")
            return True
        else:
            logger.error(f"❌ SQLite database read/write failed at {path}")
            return False
    except Exception as e:
        logger.error(f"❌ SQLite test failed at {path}: {e}")
        return False


def main():
    """Run Railway volume tests."""
    logger.info("🚀 Starting Railway persistent volume tests...")

    # Check environment
    railway_env = os.getenv("RAILWAY_ENVIRONMENT_NAME")
    if railway_env:
        logger.info(f"📍 Running in Railway environment: {railway_env}")
    else:
        logger.info("📍 Running in local development environment")

    # Test various paths
    test_paths = [
        Path("/data"),  # Standard Railway volume mount
        Path("/app/data"),  # Alternative mount
        Path("/tmp"),  # Temporary fallback
        Path("/app/backend/logs"),  # Application directory
        Path.cwd() / "backend" / "logs",  # Current working directory
    ]

    working_paths = []

    for path in test_paths:
        logger.info(f"🔍 Testing path: {path}")
        if test_path_access(path) and test_sqlite_creation(path):
            working_paths.append(path)

    logger.info("\n" + "=" * 50)
    if working_paths:
        logger.info("✅ Working paths found:")
        for path in working_paths:
            logger.info(f"   - {path}")
        logger.info(f"\n💡 Recommended: Use {working_paths[0]} for database storage")
    else:
        logger.error("❌ No working paths found for database storage!")
        logger.error("🔧 Check Railway persistent volume configuration")

    # Show current directory and permissions
    cwd = Path.cwd()
    logger.info(f"\n📂 Current working directory: {cwd}")
    logger.info(f"📂 Directory exists: {cwd.exists()}")
    logger.info(f"📂 Directory is writable: {os.access(cwd, os.W_OK)}")

    # Check Railway volume mount
    data_path = Path("/data")
    logger.info(f"💾 /data exists: {data_path.exists()}")
    if data_path.exists():
        logger.info(f"💾 /data is writable: {os.access(data_path, os.W_OK)}")
        try:
            contents = list(data_path.iterdir())
            logger.info(f"💾 /data contents: {contents}")
        except PermissionError:
            logger.error("💾 /data permission denied for listing contents")


if __name__ == "__main__":
    main()
