#!/usr/bin/env python3
"""
Test script to validate the admin dashboard setup.
"""
import os
import sqlite3
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that all required modules can be imported."""
    print("🔍 Testing imports...")

    try:
        from admin.backend.database import DatabaseManager
        from admin.backend.main import create_admin_app
        from admin.backend.models import OverviewStats, QueryLog
        from admin.backend.routes import router

        print("✅ All backend modules import successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_database():
    """Test database creation and basic operations."""
    print("\n📊 Testing database...")

    try:
        # Create a test database
        test_db_path = "admin/test_monitoring.db"

        # Clean up existing test database
        if os.path.exists(test_db_path):
            os.remove(test_db_path)

        from admin.backend.database import DatabaseManager

        # Initialize database
        db_manager = DatabaseManager(test_db_path)

        # Test basic operations
        query_id = db_manager.log_query(
            session_id="test_session",
            user_query="What is a test query?",
            system_response="This is a test response.",
            response_time_ms=1500.0,
            llm_provider="test",
            llm_model="test-model",
            vector_search_score=0.85,
        )

        # Test retrieving data
        queries = db_manager.get_queries(limit=1)
        stats = db_manager.get_overview_stats()

        print(f"✅ Database test successful - Query ID: {query_id}")
        print(f"   Total queries in test: {queries['total']}")

        # Clean up
        os.remove(test_db_path)

        return True

    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


def test_app_creation():
    """Test FastAPI app creation."""
    print("\n🚀 Testing app creation...")

    try:
        from admin.backend.main import create_admin_app

        app = create_admin_app()
        print("✅ FastAPI app created successfully")

        # Check routes
        routes = [route.path for route in app.routes]
        expected_routes = ["/admin/api/stats/overview", "/admin/api/queries", "/admin/api/health"]

        for expected in expected_routes:
            if any(expected in route for route in routes):
                print(f"✅ Route found: {expected}")
            else:
                print(f"⚠️  Route missing: {expected}")

        return True

    except Exception as e:
        print(f"❌ App creation error: {e}")
        return False


def check_frontend_files():
    """Check if frontend files exist."""
    print("\n📱 Checking frontend files...")

    frontend_files = [
        "admin/frontend/package.json",
        "admin/frontend/vite.config.js",
        "admin/frontend/src/main.js",
        "admin/frontend/src/App.vue",
        "admin/frontend/src/views/DashboardView.vue",
    ]

    all_exist = True
    for file_path in frontend_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ Missing: {file_path}")
            all_exist = False

    return all_exist


def main():
    """Run all tests."""
    print("🧪 RAG Admin Dashboard Setup Test")
    print("=" * 40)

    results = []

    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Database", test_database()))
    results.append(("App Creation", test_app_creation()))
    results.append(("Frontend Files", check_frontend_files()))

    # Summary
    print("\n📋 Test Summary:")
    print("=" * 40)

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:15} {status}")
        if result:
            passed += 1

    print(f"\nResults: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("\n🎉 All tests passed! Your admin dashboard is ready to use.")
        print("\nNext steps:")
        print("1. Set ADMIN_TOKEN environment variable")
        print("2. Start backend: python admin/start-admin.py")
        print("3. Build frontend: cd admin/frontend && npm install && npm run build")
        print("4. Access dashboard at http://localhost:8001/admin")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
