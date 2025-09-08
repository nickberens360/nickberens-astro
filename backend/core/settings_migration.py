"""
Settings migration utilities for Phase 1 consolidation.

Handles migration of duplicate settings that were consolidated into
appropriate schemas as part of the UX cleanup initiative.

Consolidated Settings:
- Caching: All moved to ResponseSettings 
- Smart Routing: Removed from FeatureFlags, kept in QueryRoutingSettings
- Analytics: Moved from FeatureFlags to SecuritySettings  
- Rate Limiting: Moved from FeatureFlags to SecuritySettings
"""

import json
import logging
from typing import Any, Dict

from .admin_database import admin_db_manager

logger = logging.getLogger(__name__)


class SettingsMigrator:
    """Handles migration of settings during schema consolidation."""

    def __init__(self):
        self.migration_log = []

    def migrate_phase1_consolidation(self) -> bool:
        """
        Migrate settings for Phase 1 consolidation.

        Returns:
            bool: True if migration successful, False otherwise
        """
        try:
            logger.info("Starting Phase 1 settings consolidation migration...")

            # Load current settings
            settings_data = self._load_all_current_settings()

            # Perform consolidation migrations
            self._migrate_caching_settings(settings_data)
            self._migrate_analytics_to_security(settings_data)
            self._migrate_rate_limiting_to_security(settings_data)
            self._remove_duplicates_from_features(settings_data)

            # Save migrated settings
            self._save_migrated_settings(settings_data)

            logger.info(f"Phase 1 migration completed successfully. {len(self.migration_log)} changes made.")
            return True

        except Exception as e:
            logger.error(f"Phase 1 migration failed: {e}")
            return False

    def _load_all_current_settings(self) -> Dict[str, Any]:
        """Load all current settings from the database."""
        settings_data = {}

        try:
            # Load each settings category
            categories = [
                "feature_flags",
                "response_settings",
                "routing_settings",
                "security_settings",
                "system_config",
            ]

            for category in categories:
                result = admin_db_manager.get_setting(category)
                if result:
                    try:
                        settings_data[category] = json.loads(result)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse {category} settings, using defaults")
                        settings_data[category] = {}
                else:
                    settings_data[category] = {}

        except Exception as e:
            logger.error(f"Failed to load current settings: {e}")

        return settings_data

    def _migrate_caching_settings(self, settings_data: Dict[str, Any]) -> None:
        """Consolidate all caching settings into ResponseSettings."""
        response_settings = settings_data.get("response_settings", {})
        feature_flags = settings_data.get("feature_flags", {})
        routing_settings = settings_data.get("routing_settings", {})

        # Migrate enable_caching from FeatureFlags
        if "enable_response_caching" in feature_flags:
            if "enable_caching" not in response_settings:
                response_settings["enable_caching"] = feature_flags["enable_response_caching"]
                self.migration_log.append(
                    "Migrated enable_response_caching from FeatureFlags to ResponseSettings as enable_caching"
                )
            del feature_flags["enable_response_caching"]

        if "enable_caching" in feature_flags:
            if "enable_caching" not in response_settings:
                response_settings["enable_caching"] = feature_flags["enable_caching"]
                self.migration_log.append("Migrated enable_caching from FeatureFlags to ResponseSettings")
            del feature_flags["enable_caching"]

        # Migrate cache TTL from routing if present
        if "query_cache_ttl_seconds" in routing_settings:
            if "cache_ttl_seconds" not in response_settings:
                response_settings["cache_ttl_seconds"] = routing_settings["query_cache_ttl_seconds"]
                self.migration_log.append("Migrated cache TTL from routing to response settings")

        # Ensure unified cache TTL
        if "response_cache_ttl_seconds" in response_settings and "cache_ttl_seconds" not in response_settings:
            response_settings["cache_ttl_seconds"] = response_settings["response_cache_ttl_seconds"]
            self.migration_log.append("Set unified cache_ttl_seconds from response_cache_ttl_seconds")

    def _migrate_analytics_to_security(self, settings_data: Dict[str, Any]) -> None:
        """Move analytics from FeatureFlags to SecuritySettings."""
        feature_flags = settings_data.get("feature_flags", {})
        security_settings = settings_data.get("security_settings", {})

        if "enable_analytics" in feature_flags:
            if "enable_analytics" not in security_settings:
                security_settings["enable_analytics"] = feature_flags["enable_analytics"]
                self.migration_log.append("Migrated enable_analytics from FeatureFlags to SecuritySettings")
            del feature_flags["enable_analytics"]

    def _migrate_rate_limiting_to_security(self, settings_data: Dict[str, Any]) -> None:
        """Consolidate rate limiting in SecuritySettings."""
        feature_flags = settings_data.get("feature_flags", {})
        security_settings = settings_data.get("security_settings", {})

        if "enable_rate_limiting" in feature_flags:
            # SecuritySettings already has this field, so we just remove the duplicate
            if security_settings.get("enable_rate_limiting") is None:
                security_settings["enable_rate_limiting"] = feature_flags["enable_rate_limiting"]
                self.migration_log.append("Migrated enable_rate_limiting from FeatureFlags to SecuritySettings")
            del feature_flags["enable_rate_limiting"]

    def _remove_duplicates_from_features(self, settings_data: Dict[str, Any]) -> None:
        """Remove migrated settings from FeatureFlags."""
        feature_flags = settings_data.get("feature_flags", {})

        # Remove settings that have been migrated elsewhere
        duplicates_to_remove = [
            "enable_smart_routing",  # Now only in QueryRoutingSettings
        ]

        for duplicate in duplicates_to_remove:
            if duplicate in feature_flags:
                del feature_flags[duplicate]
                self.migration_log.append(f"Removed duplicate {duplicate} from FeatureFlags")

    def _save_migrated_settings(self, settings_data: Dict[str, Any]) -> None:
        """Save the migrated settings back to the database."""
        for category, data in settings_data.items():
            if data:  # Only save non-empty settings
                try:
                    json_data = json.dumps(data)
                    admin_db_manager.set_setting(category, json_data)
                    logger.debug(f"Saved migrated {category} settings")
                except Exception as e:
                    logger.error(f"Failed to save {category} settings: {e}")

    def validate_migration(self) -> Dict[str, Any]:
        """
        Validate that the migration was successful.

        Returns:
            dict: Validation results with status and details
        """
        validation_results = {"status": "success", "issues": [], "warnings": []}

        try:
            settings_data = self._load_all_current_settings()

            # Check that duplicates were removed
            feature_flags = settings_data.get("feature_flags", {})

            duplicate_checks = [
                ("enable_analytics", "should be in SecuritySettings only"),
                ("enable_rate_limiting", "should be in SecuritySettings only"),
                ("enable_smart_routing", "should be in QueryRoutingSettings only"),
                ("enable_caching", "should be in ResponseSettings only"),
                ("enable_response_caching", "should be in ResponseSettings only"),
            ]

            for setting, message in duplicate_checks:
                if setting in feature_flags:
                    validation_results["issues"].append(f"{setting} still in FeatureFlags - {message}")

            # Check that consolidated settings exist in correct schemas
            security_settings = settings_data.get("security_settings", {})
            if "enable_analytics" not in security_settings:
                validation_results["warnings"].append("enable_analytics not found in SecuritySettings")
            if "enable_rate_limiting" not in security_settings:
                validation_results["warnings"].append("enable_rate_limiting not found in SecuritySettings")

            response_settings = settings_data.get("response_settings", {})
            if "enable_caching" not in response_settings:
                validation_results["warnings"].append("enable_caching not found in ResponseSettings")

            if validation_results["issues"]:
                validation_results["status"] = "failed"
            elif validation_results["warnings"]:
                validation_results["status"] = "warning"

        except Exception as e:
            validation_results["status"] = "error"
            validation_results["issues"].append(f"Validation failed: {e}")

        return validation_results

    def rollback_migration(self) -> bool:
        """
        Rollback the Phase 1 migration if needed.

        Note: This is a simple rollback that doesn't handle complex scenarios.
        For production use, implement more sophisticated backup/restore.
        """
        try:
            logger.warning("Rolling back Phase 1 migration...")

            # This is a simplified rollback - in production you'd restore from backup
            # For now, we'll just log that rollback was requested
            logger.warning("Rollback requested - manual intervention may be required")
            logger.warning("Migration log: " + "; ".join(self.migration_log))

            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False


def run_phase1_migration() -> bool:
    """
    Convenience function to run Phase 1 migration.

    Returns:
        bool: True if migration successful
    """
    migrator = SettingsMigrator()
    success = migrator.migrate_phase1_consolidation()

    if success:
        validation = migrator.validate_migration()
        if validation["status"] == "failed":
            logger.error("Migration validation failed!")
            logger.error("Issues: " + "; ".join(validation["issues"]))
            return False
        elif validation["status"] == "warning":
            logger.warning("Migration completed with warnings:")
            logger.warning("Warnings: " + "; ".join(validation["warnings"]))

    return success


if __name__ == "__main__":
    # CLI interface for running migration
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        migrator = SettingsMigrator()
        success = migrator.rollback_migration()
        sys.exit(0 if success else 1)
    else:
        success = run_phase1_migration()
        sys.exit(0 if success else 1)
