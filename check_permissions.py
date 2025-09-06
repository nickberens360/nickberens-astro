#!/usr/bin/env python3
"""
Check Railway volume permissions and directory structure
"""
import os
import stat
from pathlib import Path


def check_path_details(path):
    """Check detailed path information."""
    path = Path(path)
    print(f"\n🔍 Checking: {path}")

    # Check if path exists
    exists = path.exists()
    print(f"  Exists: {exists}")

    if exists:
        # Get stat info
        stat_info = path.stat()
        print(f"  Owner UID: {stat_info.st_uid}")
        print(f"  Group GID: {stat_info.st_gid}")
        print(f"  Permissions: {oct(stat_info.st_mode)}")

        # Check what user we're running as
        print(f"  Current process UID: {os.getuid()}")
        print(f"  Current process GID: {os.getgid()}")

        # Check readable/writable
        print(f"  Readable: {os.access(path, os.R_OK)}")
        print(f"  Writable: {os.access(path, os.W_OK)}")
        print(f"  Executable: {os.access(path, os.X_OK)}")

        # Try to list contents if it's a directory
        if path.is_dir():
            try:
                contents = list(path.iterdir())
                print(f"  Contents: {[str(c.name) for c in contents[:5]]}")
                if len(contents) > 5:
                    print(f"    ... and {len(contents) - 5} more items")
            except PermissionError as e:
                print(f"  Contents: Permission denied - {e}")
    else:
        # Check parent directory
        parent = path.parent
        if parent.exists():
            print(f"  Parent ({parent}) exists")
            print(f"  Parent writable: {os.access(parent, os.W_OK)}")


def main():
    """Check Railway volume permissions."""
    print("🚀 Railway Volume Permission Analysis")
    print(f"Running as UID: {os.getuid()}, GID: {os.getgid()}")

    # Check key paths
    paths_to_check = ["/data", "/app", "/app/data", "/tmp", "/", "/home", "/app/backend", "/app/backend/logs"]

    for path in paths_to_check:
        check_path_details(path)

    # Check environment variables related to user
    print(f"\n🔧 Environment:")
    for env_var in ["USER", "HOME", "UID", "GID", "RAILWAY_ENVIRONMENT_NAME"]:
        value = os.getenv(env_var, "Not set")
        print(f"  {env_var}: {value}")

    # Test creating directories
    test_dirs = ["/data/test_create", "/app/data", "/tmp/test_create"]
    print(f"\n🧪 Directory Creation Tests:")

    for test_dir in test_dirs:
        test_path = Path(test_dir)
        try:
            test_path.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ Created: {test_dir}")

            # Try to create a file in it
            test_file = test_path / "test.txt"
            test_file.write_text("test")
            print(f"  ✅ File write: {test_file}")

            # Clean up
            test_file.unlink()
            if test_dir != "/tmp/test_create":  # Don't remove /tmp/test_create
                test_path.rmdir()

        except Exception as e:
            print(f"  ❌ Failed: {test_dir} - {e}")


if __name__ == "__main__":
    main()
