"""
IP Geolocation service for determining location from IP addresses.

This module provides functionality to:
- Look up geolocation data for IP addresses
- Cache results for performance
- Handle errors gracefully
"""

import ipaddress
import json
import logging
from collections import OrderedDict
from typing import Dict, Optional

import requests


class GeolocationService:
    """Service for IP geolocation lookups with caching."""

    def __init__(self, cache_size: int = 1000):
        """Initialize the GeolocationService."""
        self.logger = logging.getLogger(__name__)
        # Using ipapi.co free tier (1000 requests/day, no API key needed)
        self.base_url = "https://ipapi.co"
        self.timeout = 5  # seconds
        self._cache: OrderedDict[str, Dict[str, Optional[str]]] = OrderedDict()
        self._cache_size = cache_size

    def get_location(self, ip_address: str) -> Dict[str, Optional[str]]:
        """
        Get geolocation data for an IP address.

        Args:
            ip_address: The IP address to look up (can be anonymized hash)

        Returns:
            Dictionary with city, region (state), country_name, and country_code
        """
        # Check cache first
        if ip_address in self._cache:
            # Move to end (mark as recently used)
            self._cache.move_to_end(ip_address)
            return self._cache[ip_address]

        # If it's an anonymized IP (starts with "anon_"), return empty location
        if ip_address.startswith("anon_"):
            result = {"city": None, "region": None, "country_name": None, "country_code": None, "error": "Anonymized IP"}
            self._cache_result(ip_address, result)
            return result

        # Handle local IPs
        if self._is_local_ip(ip_address):
            result = {
                "city": "Local",
                "region": "Local",
                "country_name": "Local Network",
                "country_code": "LOCAL",
                "error": None,
            }
            self._cache_result(ip_address, result)
            return result

        try:
            # Make API request
            url = f"{self.base_url}/{ip_address}/json/"
            response = requests.get(url, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()

                # Check for errors in response
                if data.get("error"):
                    self.logger.warning(f"Geolocation API error for {ip_address}: {data.get('reason')}")
                    result = {
                        "city": None,
                        "region": None,
                        "country_name": None,
                        "country_code": None,
                        "error": data.get("reason", "Unknown error"),
                    }
                    self._cache_result(ip_address, result)
                    return result

                result = {
                    "city": data.get("city"),
                    "region": data.get("region"),  # State/Province
                    "country_name": data.get("country_name"),
                    "country_code": data.get("country_code"),
                    "error": None,
                }
                self._cache_result(ip_address, result)
                return result
            else:
                self.logger.warning(f"Geolocation API returned status {response.status_code} for {ip_address}")
                return self._empty_location("API error")

        except requests.RequestException as e:
            self.logger.error(f"Failed to get geolocation for {ip_address}: {e}")
            return self._empty_location("Request failed")
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse geolocation response for {ip_address}: {e}")
            return self._empty_location("Invalid response")
        except Exception as e:
            self.logger.error(f"Unexpected error getting geolocation for {ip_address}: {e}")
            return self._empty_location("Unexpected error")

    def _is_local_ip(self, ip_address: str) -> bool:
        """Check if an IP address is local/private."""
        if ip_address.lower() == "localhost":
            return True
        try:
            ip = ipaddress.ip_address(ip_address)
            return ip.is_private or ip.is_loopback or ip.is_link_local
        except ValueError:
            # Not a valid IP address, so not a local one we can handle.
            return False

    def _cache_result(self, ip_address: str, result: Dict[str, Optional[str]]) -> None:
        """Cache a geolocation result with LRU eviction."""
        # Remove oldest item if cache is full
        if len(self._cache) >= self._cache_size:
            self._cache.popitem(last=False)
        self._cache[ip_address] = result

    def _empty_location(self, error: Optional[str] = None) -> Dict[str, Optional[str]]:
        """Return an empty location dictionary."""
        return {"city": None, "region": None, "country_name": None, "country_code": None, "error": error}

    def format_location(self, location_data: Dict[str, Optional[str]]) -> str:
        """
        Format location data into a readable string.

        Args:
            location_data: Dictionary with location fields

        Returns:
            Formatted location string
        """
        if location_data.get("error"):
            if location_data["error"] == "Anonymized IP":
                return "Location Hidden (Anonymized)"
            return "Location Unknown"

        parts = []

        if location_data.get("city"):
            parts.append(location_data["city"])

        if location_data.get("region"):
            parts.append(location_data["region"])

        if location_data.get("country_name"):
            parts.append(location_data["country_name"])
        elif location_data.get("country_code"):
            parts.append(location_data["country_code"])

        if parts:
            return ", ".join([p for p in parts if p is not None])

        return "Location Unknown"


# Global instance
_geolocation_instance = None


def get_geolocation_service() -> GeolocationService:
    """Get the global GeolocationService instance."""
    global _geolocation_instance
    if _geolocation_instance is None:
        _geolocation_instance = GeolocationService()
    return _geolocation_instance
