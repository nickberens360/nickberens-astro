#!/usr/bin/env python3
"""
Detailed Railway /data directory permissions diagnosis
"""
import os
import stat
import subprocess
from pathlib import Path


def run_command(cmd):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return f"Exit: {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except Exception as e:
        return f"Error: {e}"


def main():
    """Diagnose /data directory permissions."""
    print("🔍 Detailed /data Directory Diagnosis")
    print("=" * 50)

    # Check if /data exists and detailed info
    data_path = Path("/data")
    print(f"\n📁 /data Path Analysis:")
    print(f"  Exists: {data_path.exists()}")

    if data_path.exists():
        try:
            stat_info = data_path.stat()
            print(f"  Type: {'Directory' if data_path.is_dir() else 'File'}")
            print(f"  Owner UID: {stat_info.st_uid}")
            print(f"  Group GID: {stat_info.st_gid}")
            print(f"  Permissions: {oct(stat_info.st_mode)} ({stat.filemode(stat_info.st_mode)})")
            print(f"  Size: {stat_info.st_size} bytes")
        except Exception as e:
            print(f"  Stat Error: {e}")
    else:
        print("  /data does not exist")

    # Check current process info
    print(f"\n🔧 Current Process:")
    print(f"  UID: {os.getuid()}")
    print(f"  GID: {os.getgid()}")
    print(f"  Working Dir: {os.getcwd()}")

    # Check with ls -la
    print(f"\n📋 Shell Commands:")
    print("ls -la /:")
    print(run_command("ls -la /"))

    print("\nls -la /data:")
    print(run_command("ls -la /data"))

    print("\nwhoami:")
    print(run_command("whoami"))

    print("\nid:")
    print(run_command("id"))

    print("\ndf -h:")
    print(run_command("df -h"))

    print("\nmount | grep data:")
    print(run_command("mount | grep data"))

    # Try different approaches to access /data
    print(f"\n🧪 Access Tests:")

    test_approaches = [
        ("os.access R_OK", lambda: os.access("/data", os.R_OK)),
        ("os.access W_OK", lambda: os.access("/data", os.W_OK)),
        ("os.access X_OK", lambda: os.access("/data", os.X_OK)),
        ("os.listdir", lambda: list(os.listdir("/data"))),
        ("Path.iterdir", lambda: list(Path("/data").iterdir())),
    ]

    for test_name, test_func in test_approaches:
        try:
            result = test_func()
            print(f"  ✅ {test_name}: {result}")
        except Exception as e:
            print(f"  ❌ {test_name}: {e}")

    # Try to create a file with different methods
    print(f"\n📝 Write Tests:")

    write_tests = [
        ("touch /data/test1.txt", "touch /data/test1.txt"),
        ("echo to /data/test2.txt", "echo 'test' > /data/test2.txt"),
        ("mkdir /data/testdir", "mkdir /data/testdir"),
    ]

    for test_name, cmd in write_tests:
        print(f"\n{test_name}:")
        print(run_command(cmd))


if __name__ == "__main__":
    main()
