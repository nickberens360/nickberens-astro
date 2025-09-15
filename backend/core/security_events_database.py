"""
Security events SQLite database manager.

This module isolates security/audit event storage into a dedicated SQLite
database (security_events.db) configured with WAL for better concurrency.
"""

import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .database_utils import get_database_path

logger = logging.getLogger(__name__)


class SecurityEventsDatabaseManager:
    """Manage a dedicated SQLite DB for security events with WAL enabled."""

    def __init__(self) -> None:
        # Resolve database path under the shared logs directory
        self.db_path: Path = get_database_path("security_events.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize writes within this process to reduce lock contention
        self._write_lock = threading.RLock()

        # Connection tuning (env-overridable)
        try:
            self.connect_timeout = float(os.getenv("SEC_EVENTS_DB_TIMEOUT_SECONDS", "10.0"))
        except Exception:
            self.connect_timeout = 10.0
        try:
            self.busy_timeout_ms = int(os.getenv("SEC_EVENTS_DB_BUSY_TIMEOUT_MS", "7000"))
        except Exception:
            self.busy_timeout_ms = 7000

        logger.info(f"Security events database path: {self.db_path}")
        self._initialize_database()

    @contextmanager
    def get_connection(self):
        """Get a connection configured for concurrent logging workloads."""
        conn = sqlite3.connect(str(self.db_path), timeout=self.connect_timeout, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            # Configure pragmas for concurrency and reasonable durability
            cur.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms};")
            cur.execute("PRAGMA foreign_keys=ON;")
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA synchronous=NORMAL;")
        except Exception as e:
            logger.warning(f"Failed to apply SQLite PRAGMAs to security events DB: {e}")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize_database(self) -> None:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Security events table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS security_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        identifier TEXT NOT NULL,
                        details TEXT,
                        severity TEXT NOT NULL DEFAULT 'low',
                        ip_address TEXT,
                        user_agent TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                # Indexes for common query patterns
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_sec_events_type_time ON security_events(event_type, created_at)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_sec_events_ip_time ON security_events(ip_address, created_at)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_sec_events_severity_time ON security_events(severity, created_at)"
                )

                logger.info("Security events database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing security events database: {e}", exc_info=True)
            raise

    def record_security_event(
        self,
        event_type: str,
        identifier: str,
        severity: str,
        details: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Insert a security event with retry-on-lock behavior."""
        max_attempts = 5
        backoff = 0.15

        for attempt in range(1, max_attempts + 1):
            try:
                with self._write_lock:
                    with self.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO security_events (event_type, identifier, details, severity, ip_address, user_agent, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                event_type,
                                identifier,
                                details,
                                severity,
                                ip_address,
                                (user_agent[:500] if user_agent else None),
                                datetime.now(),
                            ),
                        )
                        return True
            except sqlite3.OperationalError as e:
                msg = str(e).lower()
                if ("database is locked" in msg or "database table is locked" in msg) and attempt < max_attempts:
                    sleep_for = backoff * attempt
                    logger.warning(f"Security events DB locked; retry {attempt}/{max_attempts} after {sleep_for:.2f}s")
                    time.sleep(sleep_for)
                    continue
                logger.error(f"OperationalError recording security event: {e}", exc_info=True)
                return False
            except Exception as e:
                logger.error(f"Error recording security event: {e}", exc_info=True)
                return False
        return False

    def get_security_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Fetch events within the last N hours ordered by time desc."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, event_type, identifier, details, severity, ip_address, user_agent, created_at
                    FROM security_events
                    WHERE created_at >= datetime('now', ?)
                    ORDER BY created_at DESC
                    """,
                    (f"-{int(hours)} hours",),
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching security alerts: {e}", exc_info=True)
            return []


# Global instance
security_events_db_manager = SecurityEventsDatabaseManager()
