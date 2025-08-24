#!/usr/bin/env python3
"""
Simple script to create a test admin user for testing authentication.
"""

import os
import sys

# Add the parent directory to the Python path so we can import admin modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from admin.backend.auth import auth_manager
from admin.backend.database import db_manager


def create_test_user():
    """Create a test admin user."""
    username = "admin"
    password = "admin123"
    email = "admin@localhost"
    role = "owner"

    try:
        # Check if user already exists
        existing_user = db_manager.get_admin_user(username)
        if existing_user:
            print(f"User '{username}' already exists!")
            return

        # Create the user
        user_id = auth_manager.create_admin_user(username=username, password=password, email=email, role=role)

        print(f"✅ Successfully created admin user:")
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
