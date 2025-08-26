#!/usr/bin/env python3
"""
Script to set admin password without interactive prompts
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import backend modules
sys.path.insert(0, str(Path(__file__).parent))

from backend.auth import auth_manager
from backend.database import db_manager


def set_admin_password():
    """
    Set a default password for the admin user.

    WARNING: This sets a weak default password and should ONLY be used for development.
    For production, use the create_admin.py script with a strong password.
    """
    username = "admin"
    password = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin123")  # Use env var or weak default

    if password == "admin123":
        print("WARNING: Using weak default password. Set ADMIN_DEFAULT_PASSWORD env var for better security.")
        print("This should NEVER be used in production!")

    # Check if user exists
    user = db_manager.get_admin_user(username)
    if not user:
        print(f"Error: User '{username}' not found.")
        return False

    print(f"Setting password for user '{username}' to 'admin123'")

    # Hash the new password
    password_hash = auth_manager.hash_password(password)

    # Update the password in the database
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE admin_users SET password_hash = ? WHERE username = ?", (password_hash, username))
        conn.commit()

    print(f"✓ Password set successfully for user '{username}'")
    print("You can now login with:")
    print(f"  Username: {username}")
    print(f"  Password: {password}")

    # Expire all existing sessions for this user
    auth_manager.expire_user_sessions(user["id"])
    print("✓ All existing sessions expired.")

    return True


if __name__ == "__main__":
    set_admin_password()
