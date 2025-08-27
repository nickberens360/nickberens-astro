#!/usr/bin/env python3
"""
Simple script to create a test admin user for testing authentication.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the Python path so we can import admin modules
sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.core.admin_auth import admin_auth_manager as auth_manager
from backend.core.admin_database import admin_db_manager as db_manager


def create_test_user():
    """
    Create a test admin user.

    WARNING: This creates a test user with weak credentials for development only.
    NEVER use this in production. Use create_admin.py with strong credentials instead.
    """
    username = "admin"
    password = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin123")
    email = "admin@localhost"
    role = "owner"

    if password == "admin123":
        print("WARNING: Creating test user with weak default password!")
        print("Set ADMIN_DEFAULT_PASSWORD env var for better security.")
        print("This should NEVER be used in production!")

    try:
        # Check if user already exists
        existing_user = db_manager.get_admin_user(username)
        if existing_user:
            print(f"User '{username}' already exists!")
            return

        # Create the user
        user_id = auth_manager.create_admin_user(username=username, password=password, email=email, role=role)

        print("✅ Successfully created admin user:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   Email: {email}")
        print(f"   Role: {role}")
        print(f"   User ID: {user_id}")

    except Exception as e:
        print(f"❌ Error creating user: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_test_user()
