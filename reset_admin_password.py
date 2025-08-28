#!/usr/bin/env python3
"""
Reset password for an existing admin user.
"""

import getpass
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.core.admin_auth import admin_auth_manager as auth_manager
from backend.core.admin_database import admin_db_manager as db_manager


def reset_password():
    """Reset password for an existing admin user."""

    # Get username
    username = input("Enter username to reset password for: ").strip()
    if not username:
        print("Username cannot be empty")
        return False

    # Check if user exists
    user = db_manager.get_admin_user(username)
    if not user:
        print(f"Error: User '{username}' does not exist")
        return False

    print(f"Found user: {user['username']} (ID: {user['id']}, Role: {user['role']})")

    # Confirm reset
    confirm = input(f"Are you sure you want to reset the password for '{username}'? (yes/no): ").strip().lower()
    if confirm not in ["yes", "y"]:
        print("Password reset cancelled")
        return False

    # Get new password
    while True:
        password = getpass.getpass("Enter new password: ")
        confirm_password = getpass.getpass("Confirm new password: ")

        if not password:
            print("Password cannot be empty")
            continue

        if password != confirm_password:
            print("Passwords do not match")
            continue

        # Use the admin auth manager's password validation
        try:
            auth_manager.validate_password_strength(password)
            break
        except ValueError as e:
            print(f"Password validation failed: {str(e)}")
            continue

    try:
        # Hash the password and update
        password_hash = auth_manager.hash_password(password)
        success = db_manager.update_user_password(user["id"], password_hash)

        if success:
            print("✅ Password updated successfully!")
            print(f"User '{username}' can now log in with the new password.")

            # Expire all existing sessions to force re-login
            auth_manager.expire_user_sessions(user["id"])
            print("All existing sessions have been expired.")

            return True
        else:
            print("❌ Failed to update password in database")
            return False

    except Exception as e:
        print(f"❌ Error updating password: {str(e)}")
        return False


if __name__ == "__main__":
    print("🔐 Admin Password Reset Tool")
    print("=" * 30)

    success = reset_password()
    sys.exit(0 if success else 1)
