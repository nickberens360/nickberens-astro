"""
Admin authentication system for the main backend.
Migrated from admin/backend/auth.py with improvements.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import bcrypt
from fastapi import HTTPException, Request

from .admin_database import admin_db_manager
from .geolocation_validator import GeolocationValidator
from .session_fingerprint import SessionFingerprinter

logger = logging.getLogger(__name__)

# Initialize security services
session_fingerprinter = SessionFingerprinter()
geo_validator = GeolocationValidator()


class AdminAuthManager:
    """
    Manages admin authentication for the backend system.

    Purpose:
        Provides secure authentication mechanisms for admin users, including password hashing,
        verification, session management, and rate limiting for failed login attempts.

    Main Responsibilities:
        - Hashes and verifies admin passwords using bcrypt.
        - Manages admin sessions, including creation, expiry, and activity tracking.
        - Limits concurrent sessions per user and expires oldest sessions when necessary.
        - Implements rate limiting and lockout for repeated failed authentication attempts.
        - Tracks session metadata such as IP address and user agent for auditing.

    Security Considerations:
        - Enforces minimum password length and uses bcrypt with configurable rounds for hashing.
        - Sessions expire after a configurable period (default: 24 hours) to reduce risk of hijacking.
        - Limits the number of concurrent active sessions per user to mitigate session abuse.
        - Implements lockout after repeated failed login attempts to prevent brute-force attacks.
        - Stores session metadata for monitoring and forensic analysis.
        - Handles exceptions and logs errors for security auditing.
    """

    def __init__(self):

        self._bcrypt_rounds = 12
        # Session expiry time (24 hours)
        self.session_expiry_hours = 24
        # Rate limiting now handled by database - no in-memory storage
        self._lockout_duration_minutes = 5  # 5 minutes lockout

    def validate_password_strength(self, password: str) -> None:
        """Validate password strength with comprehensive checks."""
        if not password:
            raise ValueError("Password cannot be empty")

        if len(password) < 12:
            raise ValueError("Password must be at least 12 characters long")

        has_upper = has_lower = has_digit = has_special = False
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"

        for char in password:
            if char.isupper():
                has_upper = True
            elif char.islower():
                has_lower = True
            elif char.isdigit():
                has_digit = True
            elif char in special_chars:
                has_special = True
            # Early exit if all conditions are met
            if has_upper and has_lower and has_digit and has_special:
                break

        if not has_upper:
            raise ValueError("Password must contain at least one uppercase letter")

        if not has_lower:
            raise ValueError("Password must contain at least one lowercase letter")

        if not has_digit:
            raise ValueError("Password must contain at least one digit")

        if not has_special:
            raise ValueError(f"Password must contain at least one special character: {special_chars}")

        # Check for common weak patterns
        weak_patterns = [
            "password",
            "123456",
            "qwerty",
            "admin",
            "user",
            "login",
            "welcome",
            "letmein",
            "monkey",
            "dragon",
            "master",
        ]
        lower_password = password.lower()
        for pattern in weak_patterns:
            if pattern in lower_password:
                raise ValueError(f"Password cannot contain common weak patterns like '{pattern}'")

        # Check for sequential characters
        if any(
            ord(password[i]) == ord(password[i + 1]) - 1 == ord(password[i + 2]) - 2 for i in range(len(password) - 2)
        ):
            raise ValueError("Password cannot contain sequential characters (e.g., abc, 123)")

        # Check for repeated characters (more than 2 in a row)
        if any(password[i] == password[i + 1] == password[i + 2] for i in range(len(password) - 2)):
            raise ValueError("Password cannot contain more than 2 repeated characters in a row")

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt with validation."""
        # Validate password strength first
        self.validate_password_strength(password)

        try:
            password_bytes = password.encode("utf-8")
            salt = bcrypt.gensalt(rounds=self._bcrypt_rounds)
            hashed = bcrypt.hashpw(password_bytes, salt)
            return hashed.decode("utf-8")
        except Exception as e:
            logger.error(f"Bcrypt hashing failed: {str(e)}", exc_info=True)
            raise ValueError("Failed to hash password")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash with rate limiting."""
        if not plain_password or not hashed_password:
            return False

        try:
            # Try bcrypt directly first (works for both old and new hashes)
            password_bytes = plain_password.encode("utf-8")
            hash_bytes = hashed_password.encode("utf-8")
            return bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception as e:
            logger.error(f"Password verification failed: {str(e)}", exc_info=True)
            return False

    def create_session(self, user_id: int, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> str:
        """Create a new session for a user with validation."""
        if user_id <= 0:
            raise ValueError("Invalid user ID")

        # Clean up expired sessions before creating new one
        self.cleanup_expired_sessions()

        session_id = str(uuid.uuid4())
        now = datetime.now()

        try:
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Limit concurrent sessions per user (max 5)
                cursor.execute("SELECT COUNT(*) FROM admin_sessions WHERE user_id = ? AND is_active = 1", (user_id,))
                active_sessions = cursor.fetchone()[0]

                if active_sessions >= 5:
                    # Expire oldest session - SQLite doesn't support ORDER BY in UPDATE, so use subquery
                    cursor.execute(
                        """
                        UPDATE admin_sessions
                        SET is_active = 0
                        WHERE id = (
                            SELECT id FROM admin_sessions
                            WHERE user_id = ? AND is_active = 1
                            ORDER BY started_at ASC
                            LIMIT 1
                        )
                        """,
                        (user_id,),
                    )

                cursor.execute(
                    """
                    INSERT INTO admin_sessions (id, user_id, started_at, last_active_at, ip_address, user_agent, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, user_id, now, now, ip_address, user_agent[:500] if user_agent else None, True),
                )

                # Create and store session fingerprint
                fingerprint = session_fingerprinter.create_fingerprint(ip_address or "unknown", user_agent or "")
                session_fingerprinter.store_session_fingerprint(session_id, fingerprint)

                logger.info(f"Created session {session_id} for user {user_id} with fingerprint")
                return session_id

        except Exception as e:
            logger.error(f"Error creating session for user {user_id}: {str(e)}", exc_info=True)
            raise

    def get_session(
        self, session_id: str, request_ip: Optional[str] = None, request_user_agent: Optional[str] = None
    ) -> Optional[Dict]:
        """Get session data if valid and active with enhanced validation and suspicious activity monitoring."""
        if not session_id or not session_id.strip():
            return None

        try:
            # Validate UUID format
            uuid.UUID(session_id)
        except ValueError:
            logger.warning(f"Invalid session ID format: {session_id[:8]}...")
            return None

        try:
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT s.*, u.id as user_id, u.username, u.email, u.role, u.is_active as user_active
                    FROM admin_sessions s
                    JOIN admin_users u ON s.user_id = u.id
                    WHERE s.id = ? AND s.is_active = 1 AND u.is_active = 1
                    """,
                    (session_id,),
                )
                row = cursor.fetchone()

                if not row:
                    return None

                session_data = dict(row)

                # Check if session is expired
                last_active = datetime.fromisoformat(session_data["last_active_at"])
                expiry_time = last_active + timedelta(hours=self.session_expiry_hours)

                if datetime.now() > expiry_time:
                    # Expire the session
                    self.expire_session(session_id)
                    return None

                # Session monitoring - check for suspicious patterns
                self._monitor_session_activity(session_data, request_ip, request_user_agent)

                # Session fingerprint monitoring
                from .session_fingerprint import session_fingerprinter

                fingerprint_result = session_fingerprinter.monitor_session_fingerprint(
                    session_id, session_data["username"], request_ip or "unknown", request_user_agent or ""
                )

                # Log high-risk fingerprint changes
                if fingerprint_result.get("validation_result", {}).get("risk_level") == "high":
                    logger.warning(
                        f"High-risk session fingerprint change detected for user {session_data['username']}: {fingerprint_result}"
                    )
                    admin_db_manager.record_security_event(
                        "possible_session_hijacking",
                        session_data["username"],
                        "high",
                        f"High-risk fingerprint change: {fingerprint_result.get('validation_result', {}).get('reason')}",
                        request_ip,
                        request_user_agent,
                    )

                return session_data

        except Exception as e:
            logger.error(f"Error getting session {session_id[:8]}...: {str(e)}", exc_info=True)
            return None

    def update_session_activity(self, session_id: str) -> None:
        """Update the last activity time for a session."""
        if not session_id:
            return

        try:
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE admin_sessions SET last_active_at = ? WHERE id = ? AND is_active = 1",
                    (datetime.now(), session_id),
                )
        except Exception as e:
            logger.error(f"Error updating session activity {session_id[:8]}...: {str(e)}", exc_info=True)

    def expire_session(self, session_id: str) -> None:
        """Expire a session safely."""
        if not session_id:
            return

        try:
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE admin_sessions SET is_active = 0 WHERE id = ?", (session_id,))
                logger.info(f"Expired session {session_id[:8]}...")
        except Exception as e:
            logger.error(f"Error expiring session {session_id[:8]}...: {str(e)}", exc_info=True)

    def expire_user_sessions(self, user_id: int) -> None:
        """Expire all sessions for a user."""
        if user_id <= 0:
            return

        try:
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE admin_sessions SET is_active = 0 WHERE user_id = ?", (user_id,))
                logger.info(f"Expired all sessions for user {user_id}")
        except Exception as e:
            logger.error(f"Error expiring sessions for user {user_id}: {str(e)}", exc_info=True)

    def authenticate_user(
        self, username: str, password: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None
    ) -> Optional[Dict]:
        """Authenticate a user and create a session with persistent rate limiting."""
        if not username or not password:
            return None

        username = username.strip().lower()
        client_ip = ip_address or "unknown"

        # Comprehensive rate limit check
        rate_limit_status = self.check_user_rate_limits(username, client_ip)

        if rate_limit_status["any_rate_limited"]:
            limit_type = rate_limit_status["primary_limit_type"]
            attempts = rate_limit_status.get(f"{limit_type}_attempts", 0)
            lockout_until = rate_limit_status.get(f"{limit_type}_lockout_until")

            logger.warning(
                f"{limit_type.upper()} rate limited authentication attempt for user {username} from {client_ip} ({attempts} attempts)"
            )
            admin_db_manager.record_security_event(
                "rate_limited_login",
                username,
                "medium",
                f"{limit_type.upper()} rate limited ({attempts} attempts) - lockout until {lockout_until}",
                client_ip,
                user_agent,
            )
            return None

        # Validate login location for security
        from .geolocation_validator import geo_validator

        location_validation = geo_validator.validate_login_location(username, client_ip, user_agent)

        if location_validation["action"] == "block":
            logger.warning(f"Blocked login from unusual location for user {username}: {location_validation['reason']}")
            admin_db_manager.record_security_event(
                "blocked_unusual_location",
                username,
                "high",
                f"Login blocked: {location_validation['reason']}",
                client_ip,
                user_agent,
            )
            return None

        user = admin_db_manager.get_admin_user(username)

        if not user or not self.verify_password(password, user["password_hash"]):
            # Record failed attempt for both IP and username
            ip_locked = admin_db_manager.record_rate_limit_attempt(client_ip, "ip", self._lockout_duration_minutes)
            user_locked = admin_db_manager.record_rate_limit_attempt(
                username, "username", self._lockout_duration_minutes
            )

            # Log security event
            severity = "high" if (ip_locked or user_locked) else "medium"
            admin_db_manager.record_security_event(
                "login_failure", username, severity, f"Failed login attempt from {client_ip}", client_ip, user_agent
            )

            if ip_locked or user_locked:
                logger.warning(f"Locked out after failed authentication: user {username} from {client_ip}")
                admin_db_manager.record_security_event(
                    "account_lockout",
                    username,
                    "high",
                    f"Account/IP locked after repeated failures from {client_ip}",
                    client_ip,
                    user_agent,
                )
            else:
                logger.warning(f"Failed authentication attempt for user {username} from {client_ip}")

            return None

        # Reset failed attempts on successful login
        self.reset_user_rate_limits(username, client_ip)

        # Check if user has 2FA enabled
        from .totp_service import totp_service

        totp_status = totp_service.get_2fa_status(user["id"])

        if totp_status["enabled"]:
            # User has 2FA enabled - return partial authentication result
            logger.info(f"2FA required for user {username}")
            return {"user": user, "requires_2fa": True, "message": "2FA verification required"}

        # Log successful login with location information
        location_info = f" - {location_validation.get('reason', 'Normal location')}"
        severity = "medium" if location_validation.get("is_unusual", False) else "low"
        admin_db_manager.record_security_event(
            "successful_login",
            username,
            severity,
            f"Successful login from {client_ip}{location_info}",
            client_ip,
            user_agent,
        )

        try:
            # Update last login time
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE admin_users SET last_login_at = ? WHERE id = ?", (datetime.now(), user["id"]))

            # Create session
            session_id = self.create_session(user["id"], ip_address, user_agent)

            logger.info(f"Successful authentication for user {username}")
            return {"user": user, "session_id": session_id}

        except Exception as e:
            logger.error(f"Error during authentication for user {username}: {str(e)}", exc_info=True)
            admin_db_manager.record_security_event(
                "authentication_error", username, "high", f"Authentication error: {str(e)}", client_ip, user_agent
            )
            return None

    def complete_2fa_authentication(
        self,
        username: str,
        totp_code: str,
        is_backup_code: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[Dict]:
        """Complete authentication with 2FA verification."""
        username = username.strip().lower()
        client_ip = ip_address or "unknown"

        try:
            # Get user info
            user = admin_db_manager.get_admin_user(username)
            if not user:
                return None

            # Verify 2FA token
            from .totp_service import totp_service

            verification_result = totp_service.verify_2fa_token(user["id"], username, totp_code, is_backup_code)

            if not verification_result["success"]:
                logger.warning(f"2FA verification failed for user {username}: {verification_result.get('error')}")
                return None

            # Log successful 2FA completion
            event_type = "2fa_backup_login" if verification_result.get("backup_code_used") else "2fa_login_success"
            admin_db_manager.record_security_event(
                event_type, username, "low", f"2FA authentication completed from {client_ip}", client_ip, user_agent
            )

            # Update last login time
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE admin_users SET last_login_at = ? WHERE id = ?", (datetime.now(), user["id"]))

            # Create session
            session_id = self.create_session(user["id"], ip_address, user_agent)

            logger.info(f"Successful 2FA authentication completed for user {username}")
            return {"user": user, "session_id": session_id, "2fa_used": True}

        except Exception as e:
            logger.error(f"Error during 2FA completion for user {username}: {str(e)}", exc_info=True)
            admin_db_manager.record_security_event(
                "2fa_authentication_error",
                username,
                "high",
                f"2FA authentication error: {str(e)}",
                client_ip,
                user_agent,
            )
            return None

    def create_admin_user(self, username: str, password: str, email: Optional[str] = None, role: str = "viewer") -> int:
        """Create a new admin user with validation."""
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters long")

        # Password validation is now handled in hash_password method
        password_hash = self.hash_password(password)
        return admin_db_manager.create_admin_user(username, email, password_hash, role)

    def get_session_from_request(self, request: Request) -> Optional[Dict]:
        """Extract and validate session from request."""
        # Get session ID from cookie only - no fallbacks
        session_id = request.cookies.get("admin_session")

        if not session_id:
            return None

        # Get request details for monitoring
        request_ip = request.client.host if request.client else None
        request_user_agent = request.headers.get("User-Agent")

        session = self.get_session(session_id, request_ip, request_user_agent)
        if session:
            # Update activity
            self.update_session_activity(session_id)

        return session

    def cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions from the database."""
        try:
            expiry_cutoff = datetime.now() - timedelta(hours=self.session_expiry_hours)

            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE admin_sessions SET is_active = 0 WHERE last_active_at < ? AND is_active = 1",
                    (expiry_cutoff,),
                )
                expired_count = cursor.rowcount
                if expired_count > 0:
                    logger.info(f"Cleaned up {expired_count} expired sessions")
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {str(e)}", exc_info=True)

    def is_rate_limited(self, identifier: str, identifier_type: str = "ip") -> bool:
        """Check if identifier is currently rate limited (proxy to database method)."""
        return admin_db_manager.is_rate_limited(identifier, identifier_type)

    def check_user_rate_limits(self, username: str, ip_address: str) -> Dict[str, Any]:
        """
        Comprehensive rate limit check for both user and IP.

        Returns:
            Dict containing rate limit status and details
        """
        try:
            username = username.strip().lower()
            ip_rate_limited = admin_db_manager.is_rate_limited(ip_address, "ip")
            user_rate_limited = admin_db_manager.is_rate_limited(username, "username")

            # Get attempt counts and lockout info
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Get IP rate limit info
                cursor.execute(
                    "SELECT attempt_count, lockout_until FROM rate_limiting WHERE identifier = ? AND identifier_type = 'ip'",
                    (ip_address,),
                )
                ip_info = cursor.fetchone()

                # Get user rate limit info
                cursor.execute(
                    "SELECT attempt_count, lockout_until FROM rate_limiting WHERE identifier = ? AND identifier_type = 'username'",
                    (username,),
                )
                user_info = cursor.fetchone()

            return {
                "ip_rate_limited": ip_rate_limited,
                "user_rate_limited": user_rate_limited,
                "any_rate_limited": ip_rate_limited or user_rate_limited,
                "ip_attempts": ip_info[0] if ip_info else 0,
                "user_attempts": user_info[0] if user_info else 0,
                "ip_lockout_until": ip_info[1] if ip_info else None,
                "user_lockout_until": user_info[1] if user_info else None,
                "primary_limit_type": "user" if user_rate_limited else ("ip" if ip_rate_limited else None),
            }

        except Exception as e:
            logger.error(f"Error checking user rate limits: {str(e)}", exc_info=True)
            return {"ip_rate_limited": False, "user_rate_limited": False, "any_rate_limited": False, "error": str(e)}

    def reset_user_rate_limits(self, username: str, ip_address: str) -> bool:
        """Reset rate limits for both user and IP after successful login."""
        try:
            username = username.strip().lower()
            ip_reset = admin_db_manager.reset_rate_limit(ip_address, "ip")
            user_reset = admin_db_manager.reset_rate_limit(username, "username")

            if ip_reset or user_reset:
                logger.info(f"Reset rate limits for user {username} and IP {ip_address}")

            return True

        except Exception as e:
            logger.error(f"Error resetting user rate limits: {str(e)}", exc_info=True)
            return False

    def cleanup_old_sessions_and_rate_limits(self) -> None:
        """Clean up old sessions and rate limiting records."""
        self.cleanup_expired_sessions()
        admin_db_manager.cleanup_old_rate_limits()

    def _monitor_session_activity(
        self, session_data: Dict, request_ip: Optional[str], request_user_agent: Optional[str]
    ) -> None:
        """Monitor session activity for suspicious patterns."""
        session_data["id"]
        username = session_data["username"]
        original_ip = session_data.get("ip_address")
        original_user_agent = session_data.get("user_agent")

        try:
            # Check for IP address changes (possible session hijacking)
            if original_ip and request_ip and original_ip != request_ip:
                logger.warning(f"Session IP change detected for user {username}: {original_ip} -> {request_ip}")
                admin_db_manager.record_security_event(
                    "session_ip_change",
                    username,
                    "high",
                    f"Session IP changed from {original_ip} to {request_ip}",
                    request_ip,
                    request_user_agent,
                )

                # Consider terminating session if IP change is from completely different location
                # For now, just log and alert

            # Check for user agent changes (possible session hijacking)
            if original_user_agent and request_user_agent:
                # Simple check - just compare browser types, not exact versions
                original_browser = self._extract_browser_type(original_user_agent)
                request_browser = self._extract_browser_type(request_user_agent)

                if (
                    original_browser != request_browser
                    and original_browser != "unknown"
                    and request_browser != "unknown"
                ):
                    logger.warning(
                        f"Session user agent change detected for user {username}: {original_browser} -> {request_browser}"
                    )
                    admin_db_manager.record_security_event(
                        "session_user_agent_change",
                        username,
                        "medium",
                        f"Session user agent changed from {original_browser} to {request_browser}",
                        request_ip,
                        request_user_agent,
                    )

            # Check for unusual session activity patterns
            self._check_session_activity_patterns(session_data)

        except Exception as e:
            logger.error(f"Error monitoring session activity: {str(e)}", exc_info=True)

    def _extract_browser_type(self, user_agent: str) -> str:
        """Extract browser type from user agent string."""
        if not user_agent:
            return "unknown"

        user_agent_lower = user_agent.lower()

        if "chrome" in user_agent_lower and "edg" not in user_agent_lower:
            return "chrome"
        elif "firefox" in user_agent_lower:
            return "firefox"
        elif "safari" in user_agent_lower and "chrome" not in user_agent_lower:
            return "safari"
        elif "edg" in user_agent_lower:
            return "edge"
        elif "opera" in user_agent_lower:
            return "opera"
        else:
            return "other"

    def _check_session_activity_patterns(self, session_data: Dict) -> None:
        """Check for unusual session activity patterns."""
        session_data["id"]
        user_id = session_data["user_id"]
        username = session_data["username"]
        started_at = datetime.fromisoformat(session_data["started_at"])
        datetime.fromisoformat(session_data["last_active_at"])

        try:
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Check for concurrent sessions from different IPs
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT ip_address) as unique_ips, COUNT(*) as total_sessions
                    FROM admin_sessions
                    WHERE user_id = ? AND is_active = 1
                    """,
                    (user_id,),
                )
                ip_stats = cursor.fetchone()

                if ip_stats and ip_stats[0] > 2:  # More than 2 unique IPs
                    logger.warning(f"User {username} has active sessions from {ip_stats[0]} different IP addresses")
                    admin_db_manager.record_security_event(
                        "multiple_concurrent_ips",
                        username,
                        "high",
                        f"Active sessions from {ip_stats[0]} different IPs ({ip_stats[1]} total sessions)",
                        session_data.get("ip_address"),
                        session_data.get("user_agent"),
                    )

                # Check for abnormally long session duration
                session_duration = (datetime.now() - started_at).total_seconds() / 3600  # Hours
                if session_duration > 48:  # More than 48 hours
                    logger.warning(f"Very long session detected for user {username}: {session_duration:.1f} hours")
                    admin_db_manager.record_security_event(
                        "long_session_duration",
                        username,
                        "medium",
                        f"Session active for {session_duration:.1f} hours",
                        session_data.get("ip_address"),
                        session_data.get("user_agent"),
                    )

                # Check for rapid session creation (possible brute force)
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM admin_sessions
                    WHERE user_id = ? AND started_at > datetime('now', '-1 hour')
                    """,
                    (user_id,),
                )
                recent_sessions = cursor.fetchone()[0]

                if recent_sessions > 10:  # More than 10 sessions in the last hour
                    logger.warning(
                        f"Rapid session creation detected for user {username}: {recent_sessions} sessions in last hour"
                    )
                    admin_db_manager.record_security_event(
                        "rapid_session_creation",
                        username,
                        "high",
                        f"{recent_sessions} sessions created in the last hour",
                        session_data.get("ip_address"),
                        session_data.get("user_agent"),
                    )

        except Exception as e:
            logger.error(f"Error checking session activity patterns: {str(e)}", exc_info=True)

    def get_security_alerts(self, hours: int = 24) -> List[Dict]:
        """Get recent security events for monitoring dashboard."""
        try:
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT event_type, identifier, details, severity, ip_address, created_at, COUNT(*) as count
                    FROM security_events
                    WHERE created_at > datetime('now', '-' || ? || ' hours')
                    GROUP BY event_type, identifier, severity, ip_address
                    ORDER BY severity DESC, created_at DESC
                    LIMIT 50
                    """,
                    (hours,),
                )

                events = []
                for row in cursor.fetchall():
                    events.append(
                        {
                            "event_type": row[0],
                            "identifier": row[1],
                            "details": row[2],
                            "severity": row[3],
                            "ip_address": row[4],
                            "created_at": row[5],
                            "count": row[6],
                        }
                    )

                return events

        except Exception as e:
            logger.error(f"Error getting security alerts: {str(e)}", exc_info=True)
            return []


# Global auth manager instance
admin_auth_manager = AdminAuthManager()


def require_admin_auth(request: Request) -> Dict:
    """Dependency to require authentication for admin routes."""
    session = admin_auth_manager.get_session_from_request(request)
    if not session:
        logger.warning(f"Unauthenticated admin request from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(status_code=401, detail="Authentication required")
    return session


def require_admin_role(request: Request) -> Dict:
    """Dependency to require admin role for routes with logging."""
    session = require_admin_auth(request)
    if session["role"] not in ["admin", "owner"]:
        logger.warning(f"Unauthorized admin access attempt by user {session.get('username', 'unknown')}")
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return session


def get_current_admin_user(request: Request) -> Optional[Dict]:
    """Get current admin user from request if authenticated, None otherwise."""
    try:
        return admin_auth_manager.get_session_from_request(request)
    except Exception as e:
        logger.error(f"Error getting current admin user: {str(e)}", exc_info=True)
        return None
