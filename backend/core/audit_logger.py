"""
Comprehensive audit logging service for admin actions.
Tracks all administrative operations for security and compliance.
"""

import json
import logging
import os
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from .admin_database import admin_db_manager

logger = logging.getLogger(__name__)


class AuditAction(Enum):
    """Enumeration of auditable admin actions."""

    # Authentication actions
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"

    # User management
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_DEACTIVATE = "user_deactivate"
    USER_REACTIVATE = "user_reactivate"
    USER_ROLE_CHANGE = "user_role_change"

    # 2FA operations
    TOTP_SETUP = "2fa_setup"
    TOTP_ENABLE = "2fa_enable"
    TOTP_DISABLE = "2fa_disable"
    TOTP_VERIFY = "2fa_verify"
    BACKUP_CODE_USE = "backup_code_use"

    # Session management
    SESSION_CREATE = "session_create"
    SESSION_EXPIRE = "session_expire"
    SESSION_TERMINATE = "session_terminate"

    # Data operations
    DATA_VIEW = "data_view"
    DATA_CREATE = "data_create"
    DATA_UPDATE = "data_update"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    DATA_DELETE = "data_delete"

    # Configuration changes
    CONFIG_UPDATE = "config_update"
    SETTING_CHANGE = "setting_change"

    # System operations
    SYSTEM_RESTART = "system_restart"
    CACHE_CLEAR = "cache_clear"

    # Knowledge base operations
    KNOWLEDGE_UPLOAD = "knowledge_upload"
    KNOWLEDGE_DELETE = "knowledge_delete"
    KNOWLEDGE_UPDATE = "knowledge_update"

    # Query operations
    QUERY_VIEW = "query_view"
    QUERY_FEEDBACK = "query_feedback"
    QUERY_DELETE = "query_delete"

    # Security operations
    SECURITY_SCAN = "security_scan"
    ACCESS_GRANT = "access_grant"
    ACCESS_REVOKE = "access_revoke"


class AuditLogger:
    """
    Comprehensive audit logging service.

    Features:
    - Structured audit log entries
    - Action categorization
    - Risk level assessment
    - Contextual information capture
    - Compliance-ready formatting
    """

    def __init__(self):
        """Initialize audit logger."""
        self.high_risk_actions = {
            AuditAction.USER_DELETE,
            AuditAction.USER_DEACTIVATE,
            AuditAction.DATA_DELETE,
            AuditAction.SYSTEM_RESTART,
            AuditAction.ACCESS_REVOKE,
            AuditAction.TOTP_DISABLE,
            AuditAction.CONFIG_UPDATE,
        }

        self.medium_risk_actions = {
            AuditAction.USER_CREATE,
            AuditAction.USER_ROLE_CHANGE,
            AuditAction.PASSWORD_CHANGE,
            AuditAction.DATA_EXPORT,
            AuditAction.KNOWLEDGE_DELETE,
            AuditAction.SETTING_CHANGE,
            AuditAction.ACCESS_GRANT,
        }

    def log_action(
        self,
        action: AuditAction,
        username: str,
        details: Optional[Dict[str, Any]] = None,
        target_resource: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log an admin action with full context.

        Args:
            action: The action being performed
            username: Username of the admin performing the action
            details: Additional context details
            target_resource: The resource being acted upon
            ip_address: IP address of the admin
            user_agent: User agent string
            success: Whether the action was successful
            error_message: Error message if action failed
        """
        try:
            # Determine risk level
            risk_level = self._assess_risk_level(action, success)

            # Build audit entry
            audit_entry = {
                "action": action.value,
                "username": username,
                "target_resource": target_resource,
                "success": success,
                "risk_level": risk_level,
                "timestamp": datetime.now().isoformat(),
                "ip_address": ip_address,
                "user_agent": user_agent[:500] if user_agent else None,
                "details": details or {},
                "error_message": error_message,
            }

            # Store in security events table
            event_type = f"audit_{action.value}"
            severity = self._map_risk_to_severity(risk_level)
            details_json = json.dumps(audit_entry)

            # In fast debug mode, skip DB writes to avoid contention
            if os.getenv("FAST_LOGIN_MODE", "false").lower() in {"1", "true", "yes"}:
                pass
            else:
                admin_db_manager.record_security_event(
                    event_type, username, severity, details_json, ip_address, user_agent
                )

            # Log to application logger as well
            log_message = self._format_log_message(audit_entry)
            if success:
                if risk_level == "high":
                    logger.warning(f"HIGH RISK AUDIT: {log_message}")
                elif risk_level == "medium":
                    logger.info(f"MEDIUM RISK AUDIT: {log_message}")
                else:
                    logger.debug(f"AUDIT: {log_message}")
            else:
                logger.error(f"FAILED AUDIT: {log_message}")

        except Exception as e:
            logger.error(f"Error logging audit action {action.value}: {str(e)}", exc_info=True)

    def _assess_risk_level(self, action: AuditAction, success: bool) -> str:
        """Assess risk level of an action."""
        if not success:
            return "high"  # Failed actions are always high risk

        if action in self.high_risk_actions:
            return "high"
        elif action in self.medium_risk_actions:
            return "medium"
        else:
            return "low"

    def _map_risk_to_severity(self, risk_level: str) -> str:
        """Map risk level to security event severity."""
        mapping = {"low": "low", "medium": "medium", "high": "high"}
        return mapping.get(risk_level, "medium")

    def _format_log_message(self, audit_entry: Dict[str, Any]) -> str:
        """Format audit entry for logging."""
        action = audit_entry["action"]
        username = audit_entry["username"]
        target = audit_entry.get("target_resource", "")
        ip = audit_entry.get("ip_address", "unknown")

        message = f"{username} performed {action}"
        if target:
            message += f" on {target}"
        message += f" from {ip}"

        if audit_entry.get("details"):
            key_details = []
            details = audit_entry["details"]

            # Extract key details for logging
            if "affected_users" in details:
                key_details.append(f"users: {details['affected_users']}")
            if "data_count" in details:
                key_details.append(f"records: {details['data_count']}")
            if "old_value" in details and "new_value" in details:
                key_details.append(f"changed: {details['old_value']} -> {details['new_value']}")

            if key_details:
                message += f" ({', '.join(key_details)})"

        return message

    # Convenience methods for common actions
    def log_login(
        self,
        username: str,
        ip_address: str,
        user_agent: str,
        success: bool = True,
        error_message: str = None,
        method: str = "password",
    ) -> None:
        """Log login attempt."""
        details = {"method": method}
        action = AuditAction.LOGIN if success else AuditAction.LOGIN_FAILED
        self.log_action(action, username, details, None, ip_address, user_agent, success, error_message)

    def log_logout(self, username: str, ip_address: str, user_agent: str) -> None:
        """Log logout action."""
        self.log_action(AuditAction.LOGOUT, username, None, None, ip_address, user_agent)

    def log_password_change(
        self,
        username: str,
        target_user: str,
        ip_address: str,
        user_agent: str,
        success: bool = True,
        error_message: str = None,
    ) -> None:
        """Log password change."""
        details = {"target_user": target_user}
        self.log_action(
            AuditAction.PASSWORD_CHANGE, username, details, target_user, ip_address, user_agent, success, error_message
        )

    def log_user_management(
        self,
        action: AuditAction,
        admin_username: str,
        target_user: str,
        changes: Dict[str, Any],
        ip_address: str,
        user_agent: str,
        success: bool = True,
        error_message: str = None,
    ) -> None:
        """Log user management actions."""
        details = {"changes": changes}
        self.log_action(action, admin_username, details, target_user, ip_address, user_agent, success, error_message)

    def log_data_operation(
        self,
        action: AuditAction,
        username: str,
        resource: str,
        record_count: int,
        ip_address: str,
        user_agent: str,
        success: bool = True,
        error_message: str = None,
    ) -> None:
        """Log data operations."""
        details = {"data_count": record_count}
        self.log_action(action, username, details, resource, ip_address, user_agent, success, error_message)

    def log_2fa_operation(
        self,
        action: AuditAction,
        username: str,
        ip_address: str,
        user_agent: str,
        success: bool = True,
        error_message: str = None,
    ) -> None:
        """Log 2FA operations."""
        self.log_action(action, username, None, "2FA", ip_address, user_agent, success, error_message)

    def log_query_operation(
        self,
        action: AuditAction,
        username: str,
        query_id: str,
        ip_address: str,
        user_agent: str,
        details: Dict[str, Any] = None,
        success: bool = True,
        error_message: str = None,
    ) -> None:
        """Log query-related operations."""
        self.log_action(action, username, details, f"query:{query_id}", ip_address, user_agent, success, error_message)

    def log_knowledge_operation(
        self,
        action: AuditAction,
        username: str,
        filename: str,
        file_size: int,
        ip_address: str,
        user_agent: str,
        success: bool = True,
        error_message: str = None,
    ) -> None:
        """Log knowledge base operations."""
        details = {"file_size": file_size}
        self.log_action(action, username, details, filename, ip_address, user_agent, success, error_message)

    def log_config_change(
        self,
        username: str,
        setting_name: str,
        old_value: Any,
        new_value: Any,
        ip_address: str,
        user_agent: str,
        success: bool = True,
        error_message: str = None,
    ) -> None:
        """Log configuration changes."""
        details = {"setting": setting_name, "old_value": str(old_value), "new_value": str(new_value)}
        self.log_action(
            AuditAction.CONFIG_UPDATE, username, details, setting_name, ip_address, user_agent, success, error_message
        )

    def get_audit_summary(self, username: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """Get audit activity summary."""
        try:
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Build query conditions
                conditions = ["event_type LIKE 'audit_%'"]
                params = []

                if username:
                    conditions.append("identifier = ?")
                    params.append(username)

                conditions.append("created_at > datetime('now', '-' || ? || ' hours')")
                params.append(str(hours))

                where_clause = " AND ".join(conditions)

                # Get action counts by type
                cursor.execute(
                    f"""
                    SELECT
                        REPLACE(event_type, 'audit_', '') as action_type,
                        severity,
                        COUNT(*) as count
                    FROM security_events
                    WHERE {where_clause}
                    GROUP BY action_type, severity
                    ORDER BY count DESC
                """,
                    params,
                )

                actions = []
                for row in cursor.fetchall():
                    actions.append({"action": row[0], "severity": row[1], "count": row[2]})

                # Get total counts by severity
                cursor.execute(
                    f"""
                    SELECT severity, COUNT(*) as count
                    FROM security_events
                    WHERE {where_clause}
                    GROUP BY severity
                """,
                    params,
                )

                severity_counts = {row[0]: row[1] for row in cursor.fetchall()}

                return {
                    "time_range_hours": hours,
                    "username": username,
                    "total_actions": sum(severity_counts.values()),
                    "severity_counts": severity_counts,
                    "action_breakdown": actions,
                }

        except Exception as e:
            logger.error(f"Error getting audit summary: {str(e)}", exc_info=True)
            return {"error": str(e)}


# Global audit logger instance
audit_logger = AuditLogger()
