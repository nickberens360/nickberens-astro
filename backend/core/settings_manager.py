"""
Settings Manager service for unified DB-driven configuration.
Provides cached access to all runtime settings with fallback to defaults.
"""

import logging
import time
from threading import Lock
from typing import Any, Dict, Optional, TypeVar

from .admin_database import admin_db_manager
from .settings_schemas import (
    FeatureFlags,
    FollowUpSettings,
    QueryRoutingSettings,
    ResponseSettings,
    SettingKeys,
    SystemSettings,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SettingsCache:
    """Thread-safe settings cache with TTL."""

    def __init__(self, ttl_seconds: int = 300):  # 5 minute default TTL
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() - entry["timestamp"] < self.ttl_seconds:
                    return entry["value"]
                else:
                    # Expired, remove from cache
                    del self._cache[key]
            return None

    def set(self, key: str, value: Any) -> None:
        """Set cached value with current timestamp."""
        with self._lock:
            self._cache[key] = {"value": value, "timestamp": time.time()}

    def invalidate(self, key: Optional[str] = None) -> None:
        """Invalidate specific key or all cache."""
        with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()

    def get_status(self) -> Dict[str, Any]:
        """Get cache status information safely."""
        with self._lock:
            cache_keys = list(self._cache.keys())
            cache_size = len(cache_keys)
            return {"keys": cache_keys, "size": cache_size}


class SettingsManager:
    """Unified settings manager with caching and fallback to defaults."""

    def __init__(self, cache_ttl_seconds: int = 300):
        self.cache = SettingsCache(cache_ttl_seconds)
        self._lock = Lock()

    def _get_setting_from_db(self, setting_key: str) -> Optional[str]:
        """Get setting value from database."""
        try:
            return admin_db_manager.get_admin_setting(setting_key)
        except Exception as e:
            logger.error(f"Error getting setting {setting_key} from DB: {e}")
            return None

    def _set_setting_in_db(self, setting_key: str, setting_value: str, updated_by: int) -> bool:
        """Set setting value in database."""
        try:
            success = admin_db_manager.set_admin_setting(setting_key, setting_value, updated_by)
            if success:
                # Invalidate cache for this setting
                self.cache.invalidate(setting_key)
            return success
        except Exception as e:
            logger.error(f"Error setting {setting_key} in DB: {e}")
            return False

    def get_followup_settings(self) -> FollowUpSettings:
        """Get follow-up settings with caching."""
        cached = self.cache.get(SettingKeys.FOLLOWUP_SETTINGS)
        if cached:
            return cached

        # Get from database
        settings_json = self._get_setting_from_db(SettingKeys.FOLLOWUP_SETTINGS)
        if settings_json:
            settings = FollowUpSettings.from_json(settings_json)
        else:
            # Return defaults if no settings exist
            settings = FollowUpSettings()

        # Cache the result
        self.cache.set(SettingKeys.FOLLOWUP_SETTINGS, settings)
        return settings

    def set_followup_settings(self, settings: FollowUpSettings, updated_by: int) -> bool:
        """Set follow-up settings in database."""
        return self._set_setting_in_db(SettingKeys.FOLLOWUP_SETTINGS, settings.to_json(), updated_by)

    def get_response_settings(self) -> ResponseSettings:
        """Get response settings with caching."""
        cached = self.cache.get(SettingKeys.RESPONSE_SETTINGS)
        if cached:
            return cached

        # Get from database
        settings_json = self._get_setting_from_db(SettingKeys.RESPONSE_SETTINGS)
        if settings_json:
            settings = ResponseSettings.from_json(settings_json)
        else:
            # Return defaults if no settings exist
            settings = ResponseSettings()

        # Cache the result
        self.cache.set(SettingKeys.RESPONSE_SETTINGS, settings)
        return settings

    def set_response_settings(self, settings: ResponseSettings, updated_by: int) -> bool:
        """Set response settings in database."""
        return self._set_setting_in_db(SettingKeys.RESPONSE_SETTINGS, settings.to_json(), updated_by)

    def get_routing_settings(self) -> QueryRoutingSettings:
        """Get query routing settings with caching."""
        cached = self.cache.get(SettingKeys.ROUTING_SETTINGS)
        if cached:
            return cached

        # Get from database
        settings_json = self._get_setting_from_db(SettingKeys.ROUTING_SETTINGS)
        if settings_json:
            settings = QueryRoutingSettings.from_json(settings_json)
        else:
            # Return defaults if no settings exist
            settings = QueryRoutingSettings()

        # Cache the result
        self.cache.set(SettingKeys.ROUTING_SETTINGS, settings)
        return settings

    def set_routing_settings(self, settings: QueryRoutingSettings, updated_by: int) -> bool:
        """Set query routing settings in database."""
        return self._set_setting_in_db(SettingKeys.ROUTING_SETTINGS, settings.to_json(), updated_by)

    def get_feature_flags(self) -> FeatureFlags:
        """Get feature flags with caching."""
        cached = self.cache.get(SettingKeys.FEATURE_FLAGS)
        if cached:
            return cached

        # Get from database
        settings_json = self._get_setting_from_db(SettingKeys.FEATURE_FLAGS)
        if settings_json:
            settings = FeatureFlags.from_json(settings_json)
        else:
            # Return defaults if no settings exist
            settings = FeatureFlags()

        # Cache the result
        self.cache.set(SettingKeys.FEATURE_FLAGS, settings)
        return settings

    def set_feature_flags(self, settings: FeatureFlags, updated_by: int) -> bool:
        """Set feature flags in database."""
        return self._set_setting_in_db(SettingKeys.FEATURE_FLAGS, settings.to_json(), updated_by)

    def get_all_settings(self) -> SystemSettings:
        """Get all settings as unified SystemSettings object."""
        return SystemSettings(
            followup=self.get_followup_settings(),
            response=self.get_response_settings(),
            routing=self.get_routing_settings(),
            features=self.get_feature_flags(),
        )

    def invalidate_cache(self, setting_key: Optional[str] = None) -> None:
        """Invalidate specific setting cache or all caches."""
        self.cache.invalidate(setting_key)

    def warmup_cache(self) -> None:
        """Warmup cache by loading all settings."""
        try:
            logger.info("Warming up settings cache...")
            self.get_followup_settings()
            self.get_response_settings()
            self.get_routing_settings()
            self.get_feature_flags()
            logger.info("Settings cache warmed up successfully")
        except Exception as e:
            logger.error(f"Error warming up settings cache: {e}")

    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache status for monitoring."""
        cache_status = self.cache.get_status()
        cache_keys = cache_status["keys"]
        cache_size = cache_status["size"]

        # Check which settings are cached
        cached_settings = {}
        for key in [
            SettingKeys.FOLLOWUP_SETTINGS,
            SettingKeys.RESPONSE_SETTINGS,
            SettingKeys.ROUTING_SETTINGS,
            SettingKeys.FEATURE_FLAGS,
        ]:
            cached_settings[key] = key in cache_keys

        return {
            "cache_size": cache_size,
            "cached_keys": cache_keys,
            "cached_settings": cached_settings,
            "ttl_seconds": self.cache.ttl_seconds,
        }

    # Convenience methods for backward compatibility
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature flag is enabled."""
        features = self.get_feature_flags()
        return getattr(features, feature_name, False)


# Global settings manager instance
settings_manager = SettingsManager()


def get_settings_manager() -> SettingsManager:
    """Get the global settings manager instance."""
    return settings_manager
