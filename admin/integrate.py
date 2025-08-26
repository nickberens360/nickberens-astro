#!/usr/bin/env python3
"""
Integration script to enable admin dashboard logging in your RAG system.

Run this once to enable logging of queries to the admin dashboard database.
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def integrate_admin_logging():
    """
    Integrate admin dashboard logging into the existing RAG system.
    """
    print("🔗 Integrating RAG Admin Dashboard Logging...")

    try:
        # Import the integration module
        from admin.backend.integration import patch_existing_query_logger

        # Apply the patches
        patch_existing_query_logger()

        print("✅ Admin dashboard logging integration successful!")
        print("\n📊 Your RAG system queries will now be logged to:")
        print(f"   Database: {os.path.abspath('admin/rag_monitoring.db')}")
        print("\n🚀 Start the admin dashboard to view the data:")
        print("   python3 admin/start-admin.py")

        return True

    except ImportError as e:
        print(f"❌ Integration failed - missing modules: {e}")
        print("   Make sure you've installed the admin backend dependencies")
        return False

    except Exception as e:
        print(f"❌ Integration failed: {e}")
        return False


def check_integration_requirements():
    """Check if integration requirements are met."""
    print("🔍 Checking integration requirements...")

    requirements = []

    # Check if existing query logger exists
    try:
        pass

        requirements.append(("Existing Query Logger", True, "Found in backend.core.query_logger"))
    except ImportError:
        requirements.append(("Existing Query Logger", False, "Not found - check your RAG system structure"))

    # Check if admin backend is available
    try:
        pass

        requirements.append(("Admin Database", True, "Admin backend is available"))
    except ImportError:
        requirements.append(("Admin Database", False, "Install admin backend dependencies"))

    # Check if FastAPI is available for admin backend
    try:
        import fastapi

        requirements.append(("FastAPI", True, f"Version {fastapi.__version__}"))
    except ImportError:
        requirements.append(("FastAPI", False, "Install: pip install fastapi"))

    print("\n📋 Requirements Check:")
    print("-" * 50)

    all_good = True
    for name, status, detail in requirements:
        status_icon = "✅" if status else "❌"
        print(f"{name:20} {status_icon} {detail}")
        if not status:
            all_good = False

    return all_good


def main():
    """Main integration process."""
    print("🎯 RAG Admin Dashboard Integration")
    print("=" * 40)

    # Check requirements first
    if not check_integration_requirements():
        print("\n⚠️  Please resolve the requirements above before integrating.")
        return 1

    print("\n" + "=" * 40)

    # Perform integration
    if integrate_admin_logging():
        print("\n🎉 Integration completed successfully!")
        print("\nNext steps:")
        print("1. Restart your RAG application")
        print("2. Set ADMIN_TOKEN environment variable")
        print("3. Start admin dashboard: python3 admin/start-admin.py")
        print("4. Generate some queries to see data in the dashboard")

        return 0
    else:
        print("\n💔 Integration failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
