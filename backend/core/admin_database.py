"""
Admin database management for the main backend.
Migrated from admin/backend/database.py with improvements.
"""

import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AdminDatabaseManager:
    """Manages admin database operations with proper connection handling."""

    def __init__(self):
        """Initialize the admin database manager."""
        # Use backend/logs directory for admin database
        self.db_path = Path(__file__).parent.parent / "logs" / "admin_monitoring.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._initialize_database()

    @contextmanager
    def get_connection(self):
        """Get a database connection with proper cleanup."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize_database(self):
        """Initialize database tables if they don't exist."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Admin users table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS admin_users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'viewer',
                        is_active INTEGER NOT NULL DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login_at TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Admin sessions table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS admin_sessions (
                        id TEXT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        started_at TIMESTAMP NOT NULL,
                        last_active_at TIMESTAMP NOT NULL,
                        ip_address TEXT,
                        user_agent TEXT,
                        is_active INTEGER NOT NULL DEFAULT 1,
                        FOREIGN KEY (user_id) REFERENCES admin_users (id)
                    )
                """
                )

                # Admin settings table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS admin_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        setting_key TEXT UNIQUE NOT NULL,
                        setting_value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_by INTEGER,
                        FOREIGN KEY (updated_by) REFERENCES admin_users (id)
                    )
                """
                )

                # Rate limiting table for persistent storage
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rate_limiting (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        identifier TEXT NOT NULL,  -- IP address or username
                        identifier_type TEXT NOT NULL,  -- 'ip' or 'username'
                        attempt_count INTEGER NOT NULL DEFAULT 1,
                        first_attempt_at TIMESTAMP NOT NULL,
                        last_attempt_at TIMESTAMP NOT NULL,
                        lockout_until TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(identifier, identifier_type)
                    )
                """
                )

                # Security events table for monitoring
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS security_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,  -- 'login_failure', 'lockout', 'suspicious_session', etc.
                        identifier TEXT NOT NULL,  -- IP address, username, or session_id
                        details TEXT,  -- JSON details
                        severity TEXT NOT NULL DEFAULT 'low',  -- 'low', 'medium', 'high', 'critical'
                        ip_address TEXT,
                        user_agent TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # 2FA (TOTP) table for two-factor authentication
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_2fa (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        secret TEXT NOT NULL,
                        backup_codes TEXT,  -- Comma-separated backup codes
                        used_backup_codes TEXT,  -- Comma-separated used backup codes
                        is_enabled INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        verified_at TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES admin_users (id),
                        UNIQUE(user_id)
                    )
                """
                )

                # Create indices for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_sessions_user_id ON admin_sessions(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_sessions_active ON admin_sessions(is_active)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_users_username ON admin_users(username)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_rate_limiting_identifier ON rate_limiting(identifier, identifier_type)"
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limiting_lockout ON rate_limiting(lockout_until)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type, created_at)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_security_events_ip ON security_events(ip_address, created_at)"
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_2fa_user_id ON user_2fa(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_2fa_enabled ON user_2fa(is_enabled)")

                # Follow-up question categories table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS followup_categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        display_name TEXT NOT NULL,
                        description TEXT,
                        icon TEXT DEFAULT 'help-circle',
                        sort_order INTEGER DEFAULT 0,
                        is_active INTEGER NOT NULL DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Follow-up questions table (normalized)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS followup_questions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category_id INTEGER NOT NULL,
                        question_text TEXT NOT NULL,
                        sort_order INTEGER DEFAULT 0,
                        is_active INTEGER NOT NULL DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by INTEGER,
                        FOREIGN KEY (category_id) REFERENCES followup_categories (id) ON DELETE CASCADE,
                        FOREIGN KEY (created_by) REFERENCES admin_users (id)
                    )
                """
                )

                # Create indices for follow-up categories
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_followup_categories_name ON followup_categories(name)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_followup_categories_active ON followup_categories(is_active)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_followup_categories_order ON followup_categories(sort_order)"
                )

                # Create indices for follow-up questions
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_followup_questions_category ON followup_questions(category_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_followup_questions_active ON followup_questions(is_active)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_followup_questions_order ON followup_questions(category_id, sort_order)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_followup_questions_text ON followup_questions(question_text)"
                )

                # Seed default categories if table is empty
                cursor.execute("SELECT COUNT(*) FROM followup_categories")
                category_count = cursor.fetchone()[0]

                if category_count == 0:
                    logger.info("Creating default followup categories")
                    self._create_default_categories(cursor)

                # Migrate existing questions from JSON to normalized structure
                self._migrate_questions_to_normalized_structure(cursor)

                # Check if we need to create a default admin user
                cursor.execute("SELECT COUNT(*) FROM admin_users")
                user_count = cursor.fetchone()[0]

                if user_count == 0:
                    logger.info("Creating default admin user")
                    self._create_default_admin_user(cursor)
                else:
                    # Check if we need to recreate the default admin user due to password format change
                    self._ensure_default_admin_user(cursor)

                logger.info("Admin database initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing admin database: {str(e)}", exc_info=True)
            raise

    def _create_default_admin_user(self, cursor):
        """Create a default admin user."""
        import secrets
        import string

        import bcrypt

        # Default credentials (require secure password via env var)
        username = os.getenv("ADMIN_DEFAULT_USERNAME", "admin")
        password = os.getenv("ADMIN_DEFAULT_PASSWORD")
        email = os.getenv("ADMIN_DEFAULT_EMAIL", "admin@localhost")
        role = "admin"

        if not password:
            # Generate a secure random password if none provided
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            password = "".join(secrets.choice(alphabet) for _ in range(16))
            logger.warning("No ADMIN_DEFAULT_PASSWORD set. Generated secure random password.")
            logger.warning(f"GENERATED ADMIN PASSWORD: {password}")
            logger.warning("SAVE THIS PASSWORD - IT WILL NOT BE DISPLAYED AGAIN!")
        elif len(password) < 12:
            raise ValueError("ADMIN_DEFAULT_PASSWORD must be at least 12 characters long")

        # Use the same bcrypt method as authentication for consistency
        password_bytes = password.encode("utf-8")
        password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")

        cursor.execute(
            """
            INSERT INTO admin_users (username, email, password_hash, role, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username.lower(), email, password_hash, role, datetime.now(), datetime.now()),
        )

        logger.info(f"Created default admin user: {username}")
        if os.getenv("ADMIN_DEFAULT_PASSWORD"):
            logger.info("Using admin password from ADMIN_DEFAULT_PASSWORD environment variable")
        else:
            logger.warning("Random password generated - check logs above for password")

    def _ensure_default_admin_user(self, cursor):
        """Ensure the default admin user exists and has correct password format."""
        import os

        import bcrypt

        default_username = os.getenv("ADMIN_DEFAULT_USERNAME", "admin").lower()
        default_password = os.getenv("ADMIN_DEFAULT_PASSWORD")

        # SECURITY FIX: Always verify admin user integrity
        # Check if the default admin user exists
        cursor.execute("SELECT id, password_hash, role FROM admin_users WHERE username = ?", (default_username,))
        result = cursor.fetchone()

        if result:
            user_id, current_hash, role = result

            # SECURITY: Ensure admin user has proper role
            if role != "admin":
                logger.warning(f"Default admin user {default_username} has incorrect role: {role}. Fixing...")
                cursor.execute(
                    "UPDATE admin_users SET role = 'admin', updated_at = ? WHERE id = ?",
                    (datetime.now(), user_id),
                )
                logger.info(f"Restored admin role for user: {default_username}")

            # Only update password if one is provided and different
            if default_password:
                # Test if the current hash works with direct bcrypt verification
                try:
                    test_password_bytes = default_password.encode("utf-8")
                    hash_bytes = current_hash.encode("utf-8")
                    bcrypt_works = bcrypt.checkpw(test_password_bytes, hash_bytes)
                except Exception:
                    bcrypt_works = False

                if not bcrypt_works:
                    # Hash is in wrong format (probably passlib), recreate with bcrypt
                    logger.info(f"Updating password hash format for default admin user: {default_username}")
                    new_password_bytes = default_password.encode("utf-8")
                    new_password_hash = bcrypt.hashpw(new_password_bytes, bcrypt.gensalt()).decode("utf-8")

                    cursor.execute(
                        "UPDATE admin_users SET password_hash = ?, updated_at = ? WHERE id = ?",
                        (new_password_hash, datetime.now(), user_id),
                    )
                    logger.info(f"Updated password hash for default admin user: {default_username}")
            else:
                # SECURITY: Log when default admin exists without password validation
                logger.info(f"Default admin user {default_username} exists. No password update requested.")
        else:
            # Default admin user doesn't exist, create it
            logger.info("Default admin user not found, creating it")
            self._create_default_admin_user(cursor)

    def _create_default_categories(self, cursor):
        """Create default follow-up question categories."""
        default_categories = [
            {
                "name": "technical",
                "display_name": "Technical",
                "description": "Development, technologies, and coding questions",
                "icon": "code",
                "sort_order": 1,
            },
            {
                "name": "personal",
                "display_name": "Personal",
                "description": "Experience, background, and contact information",
                "icon": "account",
                "sort_order": 2,
            },
            {
                "name": "creative",
                "display_name": "Creative",
                "description": "Illustrations, art, and design work",
                "icon": "palette",
                "sort_order": 3,
            },
        ]

        for category in default_categories:
            cursor.execute(
                """
                INSERT INTO followup_categories (name, display_name, description, icon, sort_order, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    category["name"],
                    category["display_name"],
                    category["description"],
                    category["icon"],
                    category["sort_order"],
                    datetime.now(),
                    datetime.now(),
                ),
            )

        logger.info(f"Created {len(default_categories)} default followup categories")

    def _migrate_questions_to_normalized_structure(self, cursor):
        """Migrate questions from JSON storage to normalized table structure."""
        try:
            # Check if we have any questions in the normalized table
            cursor.execute("SELECT COUNT(*) FROM followup_questions")
            question_count = cursor.fetchone()[0]

            if question_count > 0:
                logger.info("Questions already migrated to normalized structure")
                return

            # Get existing questions from JSON settings
            cursor.execute("SELECT setting_value FROM admin_settings WHERE setting_key = 'followup_settings'")
            settings_row = cursor.fetchone()

            if not settings_row:
                logger.info("No existing followup settings to migrate")
                return

            import json

            try:
                settings_data = json.loads(settings_row[0])
                custom_questions = settings_data.get("custom_questions", {})

                if not custom_questions:
                    logger.info("No custom questions to migrate")
                    return

                # Migrate questions for each category
                migrated_count = 0
                for category_name, questions in custom_questions.items():
                    if not questions:
                        continue

                    # Get category ID
                    cursor.execute("SELECT id FROM followup_categories WHERE name = ?", (category_name,))
                    category_row = cursor.fetchone()

                    if not category_row:
                        logger.warning(f"Category '{category_name}' not found for migration")
                        continue

                    category_id = category_row[0]

                    # Insert questions
                    for sort_order, question_text in enumerate(questions):
                        cursor.execute(
                            """
                            INSERT INTO followup_questions 
                            (category_id, question_text, sort_order, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (category_id, question_text, sort_order, datetime.now(), datetime.now()),
                        )
                        migrated_count += 1

                if migrated_count > 0:
                    # Clear the custom_questions from JSON settings to avoid confusion
                    del settings_data["custom_questions"]
                    cursor.execute(
                        "UPDATE admin_settings SET setting_value = ? WHERE setting_key = 'followup_settings'",
                        (json.dumps(settings_data),),
                    )
                    logger.info(f"Migrated {migrated_count} questions to normalized structure")
                else:
                    logger.info("No questions needed migration")

            except json.JSONDecodeError as e:
                logger.error(f"Error parsing followup settings JSON: {e}")
            except Exception as e:
                logger.error(f"Error during question migration: {e}")

        except Exception as e:
            logger.error(f"Error in question migration: {str(e)}", exc_info=True)

    # Follow-up category management methods
    def get_followup_categories(self, active_only: bool = True) -> List[Dict]:
        """Get follow-up categories, optionally filtered by active status."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                if active_only:
                    cursor.execute(
                        """
                        SELECT id, name, display_name, description, icon, sort_order, is_active, created_at, updated_at
                        FROM followup_categories 
                        WHERE is_active = 1
                        ORDER BY sort_order, display_name
                        """
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, name, display_name, description, icon, sort_order, is_active, created_at, updated_at
                        FROM followup_categories
                        ORDER BY sort_order, display_name  
                        """
                    )

                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting followup categories: {str(e)}", exc_info=True)
            return []

    def get_followup_category(self, category_id: int) -> Optional[Dict]:
        """Get a single follow-up category by ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, name, display_name, description, icon, sort_order, is_active, created_at, updated_at
                    FROM followup_categories 
                    WHERE id = ?
                    """,
                    (category_id,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting followup category {category_id}: {str(e)}", exc_info=True)
            return None

    def get_followup_category_by_name(self, name: str) -> Optional[Dict]:
        """Get a single follow-up category by name."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, name, display_name, description, icon, sort_order, is_active, created_at, updated_at
                    FROM followup_categories 
                    WHERE name = ?
                    """,
                    (name,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting followup category by name {name}: {str(e)}", exc_info=True)
            return None

    def create_followup_category(
        self,
        name: str,
        display_name: str,
        description: Optional[str] = None,
        icon: str = "help-circle",
        sort_order: int = 0,
    ) -> int:
        """Create a new follow-up category."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO followup_categories (name, display_name, description, icon, sort_order, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (name, display_name, description, icon, sort_order, datetime.now(), datetime.now()),
                )
                category_id = cursor.lastrowid
                logger.info(f"Created followup category: {name} (ID: {category_id})")
                return category_id
        except Exception as e:
            logger.error(f"Error creating followup category {name}: {str(e)}", exc_info=True)
            raise

    def update_followup_category(
        self,
        category_id: int,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        sort_order: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> bool:
        """Update a follow-up category."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Build dynamic update query with field whitelisting to prevent SQL injection
                # Define allowed fields to prevent injection of arbitrary SQL
                allowed_fields = {"display_name", "description", "icon", "sort_order", "is_active"}
                updates: List[str] = []
                params: List[Any] = []

                # Build field updates with validation
                field_values = {
                    "display_name": display_name,
                    "description": description,
                    "icon": icon,
                    "sort_order": sort_order,
                    "is_active": (1 if is_active else 0) if is_active is not None else None,
                }

                for field, value in field_values.items():
                    if value is not None and field in allowed_fields:
                        # Field name is from our whitelist, safe to use
                        updates.append(f"{field} = ?")
                        params.append(value)

                if not updates:
                    return False

                # Always update timestamp
                updates.append("updated_at = ?")
                params.append(datetime.now())
                params.append(category_id)

                # Build and execute query with validated field names only
                query = f"UPDATE followup_categories SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)

                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Updated followup category ID: {category_id}")
                return success
        except Exception as e:
            logger.error(f"Error updating followup category {category_id}: {str(e)}", exc_info=True)
            return False

    def delete_followup_category(self, category_id: int) -> bool:
        """Delete a follow-up category (hard delete - completely removes from database)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # First, delete any associated questions
                cursor.execute("DELETE FROM followup_questions WHERE category_id = ?", (category_id,))
                deleted_questions = cursor.rowcount

                # Then delete the category itself
                cursor.execute("DELETE FROM followup_categories WHERE id = ?", (category_id,))
                success = cursor.rowcount > 0

                if success:
                    logger.info(
                        f"Hard deleted followup category ID: {category_id} and {deleted_questions} associated questions"
                    )
                return success
        except Exception as e:
            logger.error(f"Error deleting followup category {category_id}: {str(e)}", exc_info=True)
            return False

    def reorder_followup_categories(self, category_orders: List[Dict[str, int]]) -> bool:
        """Reorder categories by updating sort_order. Expects list of {id, sort_order}."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                for item in category_orders:
                    cursor.execute(
                        "UPDATE followup_categories SET sort_order = ?, updated_at = ? WHERE id = ?",
                        (item["sort_order"], datetime.now(), item["id"]),
                    )
                logger.info(f"Reordered {len(category_orders)} followup categories")
                return True
        except Exception as e:
            logger.error(f"Error reordering followup categories: {str(e)}", exc_info=True)
            return False

    # Follow-up question management methods (normalized)
    def get_followup_questions(
        self,
        category_id: Optional[int] = None,
        active_only: bool = True,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict]:
        """Get follow-up questions with pagination and filtering."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Build query with filters
                where_conditions: List[str] = []
                params: List[Any] = []

                if active_only:
                    where_conditions.append("fq.is_active = 1")

                if category_id is not None:
                    where_conditions.append("fq.category_id = ?")
                    params.append(category_id)

                if search:
                    where_conditions.append("fq.question_text LIKE ?")
                    params.append(f"%{search}%")

                where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

                # Add pagination params
                params.extend([limit, offset])

                cursor.execute(
                    f"""
                    SELECT 
                        fq.id, fq.category_id, fq.question_text, fq.sort_order, 
                        fq.is_active, fq.created_at, fq.updated_at, fq.created_by,
                        fc.name as category_name, fc.display_name as category_display_name
                    FROM followup_questions fq
                    LEFT JOIN followup_categories fc ON fq.category_id = fc.id
                    {where_clause}
                    ORDER BY fq.category_id, fq.sort_order, fq.id
                    LIMIT ? OFFSET ?
                    """,
                    params,
                )

                results = []
                for row in cursor.fetchall():
                    row_dict = dict(row)
                    # Convert SQLite integer to proper boolean for API consistency
                    row_dict["is_active"] = bool(row_dict["is_active"])
                    results.append(row_dict)
                return results
        except Exception as e:
            logger.error(f"Error getting followup questions: {str(e)}", exc_info=True)
            return []

    def get_followup_question(self, question_id: int) -> Optional[Dict]:
        """Get a single follow-up question by ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT 
                        fq.id, fq.category_id, fq.question_text, fq.sort_order, 
                        fq.is_active, fq.created_at, fq.updated_at, fq.created_by,
                        fc.name as category_name, fc.display_name as category_display_name
                    FROM followup_questions fq
                    LEFT JOIN followup_categories fc ON fq.category_id = fc.id
                    WHERE fq.id = ?
                    """,
                    (question_id,),
                )
                row = cursor.fetchone()
                if row:
                    row_dict = dict(row)
                    # Convert SQLite integer to proper boolean for API consistency
                    row_dict["is_active"] = bool(row_dict["is_active"])
                    return row_dict
                return None
        except Exception as e:
            logger.error(f"Error getting followup question {question_id}: {str(e)}", exc_info=True)
            return None

    def create_followup_question(
        self, category_id: int, question_text: str, sort_order: Optional[int] = None, created_by: Optional[int] = None
    ) -> int:
        """Create a new follow-up question."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Validate category exists and is active
                cursor.execute("SELECT id, is_active FROM followup_categories WHERE id = ?", (category_id,))
                category = cursor.fetchone()

                if not category:
                    raise ValueError(f"Category {category_id} not found")
                if not category["is_active"]:
                    raise ValueError("Cannot add questions to inactive category")

                # Get next sort order if not provided
                if sort_order is None:
                    cursor.execute(
                        "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM followup_questions WHERE category_id = ?",
                        (category_id,),
                    )
                    sort_order = cursor.fetchone()[0]

                # Insert question
                cursor.execute(
                    """
                    INSERT INTO followup_questions 
                    (category_id, question_text, sort_order, created_at, updated_at, created_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (category_id, question_text, sort_order, datetime.now(), datetime.now(), created_by),
                )

                question_id = cursor.lastrowid
                logger.info(f"Created followup question {question_id} in category {category_id}")
                return question_id

        except Exception as e:
            logger.error(f"Error creating followup question: {str(e)}", exc_info=True)
            raise

    def update_followup_question(
        self,
        question_id: int,
        question_text: Optional[str] = None,
        sort_order: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> bool:
        """Update a follow-up question."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Build dynamic update query with field whitelisting to prevent SQL injection
                # Define allowed fields to prevent injection of arbitrary SQL
                allowed_fields = {"question_text", "sort_order", "is_active"}
                updates: List[str] = []
                params: List[Any] = []

                # Build field updates with validation
                field_values = {
                    "question_text": question_text,
                    "sort_order": sort_order,
                    "is_active": (1 if is_active else 0) if is_active is not None else None,
                }

                for field, value in field_values.items():
                    if value is not None and field in allowed_fields:
                        # Field name is from our whitelist, safe to use
                        updates.append(f"{field} = ?")
                        params.append(value)

                if not updates:
                    return False

                # Always update timestamp
                updates.append("updated_at = ?")
                params.append(datetime.now())
                params.append(question_id)

                # Build and execute query with validated field names only
                query = f"UPDATE followup_questions SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)

                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Updated followup question ID: {question_id}")
                return success
        except Exception as e:
            logger.error(f"Error updating followup question {question_id}: {str(e)}", exc_info=True)
            return False

    def delete_followup_question(self, question_id: int) -> bool:
        """Delete a follow-up question (hard delete)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM followup_questions WHERE id = ?", (question_id,))
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Deleted followup question ID: {question_id}")
                return success
        except Exception as e:
            logger.error(f"Error deleting followup question {question_id}: {str(e)}", exc_info=True)
            return False

    def move_questions_to_category(self, source_category_id: int, target_category_id: int) -> int:
        """Move all questions from source category to target category."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Validate target category exists and is active
                cursor.execute("SELECT id, is_active FROM followup_categories WHERE id = ?", (target_category_id,))
                target = cursor.fetchone()

                if not target:
                    raise ValueError(f"Target category {target_category_id} not found")
                if not target["is_active"]:
                    raise ValueError("Cannot move questions to inactive category")

                # Get max sort order in target category
                cursor.execute(
                    "SELECT COALESCE(MAX(sort_order), 0) FROM followup_questions WHERE category_id = ?",
                    (target_category_id,),
                )
                max_sort_order = cursor.fetchone()[0]

                # Update questions with new category and sort orders
                cursor.execute(
                    """
                    UPDATE followup_questions 
                    SET category_id = ?, sort_order = sort_order + ?, updated_at = ?
                    WHERE category_id = ?
                    """,
                    (target_category_id, max_sort_order, datetime.now(), source_category_id),
                )

                moved_count = cursor.rowcount
                logger.info(f"Moved {moved_count} questions from category {source_category_id} to {target_category_id}")
                return moved_count

        except Exception as e:
            logger.error(f"Error moving questions: {str(e)}", exc_info=True)
            raise

    def get_category_question_count(self, category_id: int) -> int:
        """Get the count of questions in a category."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM followup_questions WHERE category_id = ? AND is_active = 1", (category_id,)
                )
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting question count for category {category_id}: {str(e)}", exc_info=True)
            return 0

    def get_admin_user(self, username: str) -> Optional[Dict]:
        """Get admin user by username."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM admin_users WHERE username = ? AND is_active = 1", (username.lower(),))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting admin user {username}: {str(e)}", exc_info=True)
            return None

    def create_admin_user(self, username: str, email: Optional[str], password_hash: str, role: str = "viewer") -> int:
        """Create a new admin user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO admin_users (username, email, password_hash, role, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (username.lower(), email, password_hash, role, datetime.now(), datetime.now()),
                )
                user_id = cursor.lastrowid
                logger.info(f"Created admin user: {username} (ID: {user_id})")
                return user_id
        except Exception as e:
            logger.error(f"Error creating admin user {username}: {str(e)}", exc_info=True)
            raise

    def update_user_password(self, user_id: int, new_password_hash: str) -> bool:
        """Update user password hash."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE admin_users SET password_hash = ?, updated_at = ? WHERE id = ?",
                    (new_password_hash, datetime.now(), user_id),
                )
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Updated password for user ID: {user_id}")
                return success
        except Exception as e:
            logger.error(f"Error updating password for user {user_id}: {str(e)}", exc_info=True)
            return False

    def get_all_admin_users(self) -> List[Dict]:
        """Get all admin users (excluding password hashes)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, username, email, role, is_active, created_at, last_login_at, updated_at
                    FROM admin_users
                    ORDER BY created_at DESC
                    """
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all admin users: {str(e)}", exc_info=True)
            return []

    def deactivate_admin_user(self, user_id: int) -> bool:
        """Deactivate an admin user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE admin_users SET is_active = 0, updated_at = ? WHERE id = ?", (datetime.now(), user_id)
                )
                success = cursor.rowcount > 0
                if success:
                    # Also expire all sessions for this user
                    cursor.execute("UPDATE admin_sessions SET is_active = 0 WHERE user_id = ?", (user_id,))
                    logger.info(f"Deactivated admin user ID: {user_id}")
                return success
        except Exception as e:
            logger.error(f"Error deactivating admin user {user_id}: {str(e)}", exc_info=True)
            return False

    def get_admin_setting(self, setting_key: str) -> Optional[str]:
        """Get an admin setting value."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT setting_value FROM admin_settings WHERE setting_key = ?", (setting_key,))
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Error getting admin setting {setting_key}: {str(e)}", exc_info=True)
            return None

    def set_admin_setting(self, setting_key: str, setting_value: str, updated_by: int) -> bool:
        """Set an admin setting value."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO admin_settings (setting_key, setting_value, updated_at, updated_by)
                    VALUES (?, ?, ?, ?)
                    """,
                    (setting_key, setting_value, datetime.now(), updated_by),
                )
                logger.info(f"Updated admin setting: {setting_key}")
                return True
        except Exception as e:
            logger.error(f"Error setting admin setting {setting_key}: {str(e)}", exc_info=True)
            return False

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and return count of cleaned sessions."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE admin_sessions
                    SET is_active = 0
                    WHERE is_active = 1
                    AND datetime(last_active_at) < datetime('now', '-24 hours')
                    """
                )
                cleaned_count = cursor.rowcount
                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} expired admin sessions")
                return cleaned_count
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {str(e)}", exc_info=True)
            return 0

    def get_active_sessions_count(self) -> int:
        """Get count of active admin sessions."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM admin_sessions WHERE is_active = 1")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting active sessions count: {str(e)}", exc_info=True)
            return 0

    # CSRF token method removed - simplified to session-only authentication

    def record_rate_limit_attempt(
        self, identifier: str, identifier_type: str, lockout_duration_minutes: int = 5
    ) -> bool:
        """Record a failed attempt and return True if identifier should be locked out."""
        import random

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now()
                # SECURITY FIX: Add randomization to prevent timing attacks
                # Add 0-60 seconds of random jitter to lockout duration
                jitter_seconds = random.randint(0, 60)
                lockout_until = now + timedelta(minutes=lockout_duration_minutes, seconds=jitter_seconds)

                # Check if identifier already exists
                cursor.execute(
                    "SELECT attempt_count, lockout_until FROM rate_limiting WHERE identifier = ? AND identifier_type = ?",
                    (identifier, identifier_type),
                )
                row = cursor.fetchone()

                if row:
                    attempt_count, current_lockout = row

                    # Check if still in lockout period
                    if current_lockout and datetime.fromisoformat(current_lockout) > now:
                        return True  # Still locked out

                    # Reset if it's been more than 1 hour since lockout expired
                    if current_lockout and datetime.fromisoformat(current_lockout) < (now - timedelta(hours=1)):
                        attempt_count = 0

                    new_attempt_count = attempt_count + 1
                    should_lockout = new_attempt_count >= 5

                    cursor.execute(
                        """
                        UPDATE rate_limiting
                        SET attempt_count = ?, last_attempt_at = ?, lockout_until = ?
                        WHERE identifier = ? AND identifier_type = ?
                        """,
                        (
                            new_attempt_count,
                            now,
                            lockout_until if should_lockout else None,
                            identifier,
                            identifier_type,
                        ),
                    )
                    return should_lockout
                else:
                    # First attempt for this identifier
                    cursor.execute(
                        """
                        INSERT INTO rate_limiting (identifier, identifier_type, attempt_count, first_attempt_at, last_attempt_at)
                        VALUES (?, ?, 1, ?, ?)
                        """,
                        (identifier, identifier_type, now, now),
                    )
                    return False
        except Exception as e:
            logger.error(f"Error recording rate limit attempt: {str(e)}", exc_info=True)
            return False

    def is_rate_limited(self, identifier: str, identifier_type: str) -> bool:
        """Check if identifier is currently rate limited."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT lockout_until FROM rate_limiting WHERE identifier = ? AND identifier_type = ?",
                    (identifier, identifier_type),
                )
                row = cursor.fetchone()

                if row and row[0]:
                    lockout_until = datetime.fromisoformat(row[0])
                    return lockout_until > datetime.now()
                return False
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}", exc_info=True)
            return False

    def reset_rate_limit(self, identifier: str, identifier_type: str) -> bool:
        """Reset rate limiting for an identifier (e.g., on successful login)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM rate_limiting WHERE identifier = ? AND identifier_type = ?",
                    (identifier, identifier_type),
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error resetting rate limit: {str(e)}", exc_info=True)
            return False

    def record_security_event(
        self,
        event_type: str,
        identifier: str,
        severity: str = "medium",
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Record a security event for monitoring."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO security_events
                    (event_type, identifier, details, severity, ip_address, user_agent, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_type,
                        identifier,
                        details,
                        severity,
                        ip_address,
                        user_agent[:500] if user_agent else None,
                        datetime.now(),
                    ),
                )
                return True
        except Exception as e:
            logger.error(f"Error recording security event: {str(e)}", exc_info=True)
            return False

    def cleanup_old_rate_limits(self, days_old: int = 7) -> int:
        """Clean up old rate limiting records."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cutoff_date = datetime.now() - timedelta(days=days_old)
                cursor.execute("DELETE FROM rate_limiting WHERE last_attempt_at < ?", (cutoff_date,))
                cleaned_count = cursor.rowcount
                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} old rate limiting records")
                return cleaned_count
        except Exception as e:
            logger.error(f"Error cleaning up old rate limits: {str(e)}", exc_info=True)
            return 0


# Global database manager instance
admin_db_manager = AdminDatabaseManager()
