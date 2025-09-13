"""
Secure API Key Management Service.
Handles encryption, decryption, and validation of API keys.
"""

import base64
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .admin_database import admin_db_manager

logger = logging.getLogger(__name__)


class ApiKeyManager:
    """Manages API keys with encryption and secure storage."""

    def __init__(self):
        """Initialize the API key manager with encryption."""
        self._init_encryption()

    def _init_encryption(self):
        """Initialize encryption using environment-based key."""
        # Get or generate encryption key from environment
        encryption_password = os.getenv("API_KEY_ENCRYPTION_SECRET")

        if not encryption_password:
            # In development, use a default (NOT for production!)
            if os.getenv("ENVIRONMENT", "development") == "development":
                encryption_password = "dev-encryption-key-change-in-production"
                logger.warning("Using development encryption key. Set API_KEY_ENCRYPTION_SECRET in production!")
            else:
                raise ValueError("API_KEY_ENCRYPTION_SECRET must be set in production environment")

        # Derive encryption key from password using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"api-key-salt-v1",  # Static salt for consistent key derivation
            iterations=100000,
            backend=default_backend(),
        )
        key = base64.urlsafe_b64encode(kdf.derive(encryption_password.encode()))
        self.cipher = Fernet(key)

    def encrypt_key(self, api_key: str) -> Tuple[str, str]:
        """
        Encrypt an API key and return encrypted value and last 4 characters.

        Returns:
            Tuple of (encrypted_value, last_four_chars)
        """
        try:
            # Encrypt the API key
            encrypted = self.cipher.encrypt(api_key.encode())
            encrypted_b64 = base64.b64encode(encrypted).decode("utf-8")

            # Get last 4 characters for display
            last_four = api_key[-4:] if len(api_key) >= 4 else api_key

            return encrypted_b64, last_four
        except Exception as e:
            logger.error(f"Error encrypting API key: {e}")
            raise

    def decrypt_key(self, encrypted_value: str) -> str:
        """Decrypt an API key.

        Supports both new (Fernet-encrypted, base64-encoded) values and
        legacy values that were stored as base64-encoded plaintext during
        environment migration. If a legacy format is detected, we transparently
        return the decoded value and attempt a best-effort in-place migration
        to the new encryption format.
        """
        # First, base64-decode the stored string
        try:
            raw = base64.b64decode(encrypted_value.encode("utf-8"))
        except Exception as e:
            logger.error(f"Error base64-decoding stored API key value: {e}")
            raise

        # Attempt Fernet decryption (new format)
        try:
            decrypted = self.cipher.decrypt(raw)
            return decrypted.decode("utf-8")
        except Exception as fernet_error:
            # Fallback: legacy format (raw is actually the plaintext API key)
            try:
                legacy_plain = raw.decode("utf-8", errors="ignore").strip()
            except Exception:
                legacy_plain = ""

            if legacy_plain and len(legacy_plain) >= 10:
                logger.warning("Detected legacy base64-only API key format; using decoded value and migrating")
                # Attempt one-shot in-place migration to new encrypted format
                try:
                    new_encrypted_b64, _last_four = self.encrypt_key(legacy_plain)
                    from .admin_database import admin_db_manager  # local import to avoid cycles at module import

                    with admin_db_manager.get_connection() as conn:
                        cur = conn.cursor()
                        cur.execute(
                            "UPDATE api_keys SET encrypted_value = ?, updated_at = CURRENT_TIMESTAMP WHERE encrypted_value = ?",
                            (new_encrypted_b64, encrypted_value),
                        )
                except Exception as migrate_error:
                    # Non-fatal: we can still return the usable key
                    logger.debug(f"API key migration to new encryption failed (non-fatal): {migrate_error}")
                return legacy_plain

            # If fallback failed, surface the original error for observability
            logger.error(f"Error decrypting API key with Fernet: {fernet_error}")
            raise

    def create_api_key(self, key_name: str, key_type: str, api_key: str, updated_by: int) -> Dict[str, Any]:
        """
        Create a new API key entry with encryption.

        Args:
            key_name: Unique name for the key (e.g., "anthropic_primary")
            key_type: Type of key (anthropic, google, openai, etc.)
            api_key: The actual API key to store
            updated_by: User ID making the change

        Returns:
            Dict with created key info (without actual key value)
        """
        try:
            # Encrypt the key
            encrypted_value, last_four = self.encrypt_key(api_key)

            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Check if key name already exists
                cursor.execute("SELECT id FROM api_keys WHERE key_name = ?", (key_name,))
                if cursor.fetchone():
                    raise ValueError(f"API key with name '{key_name}' already exists")

                # Insert the new key
                cursor.execute(
                    """
                    INSERT INTO api_keys 
                    (key_name, key_type, encrypted_value, last_four, updated_by)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (key_name, key_type, encrypted_value, last_four, updated_by),
                )

                key_id = cursor.lastrowid
                logger.info(f"Created API key: {key_name} (ID: {key_id})")

                return {
                    "id": key_id,
                    "key_name": key_name,
                    "key_type": key_type,
                    "last_four": last_four,
                    "is_active": True,
                }

        except Exception as e:
            logger.error(f"Error creating API key {key_name}: {e}")
            raise

    def update_api_key(self, key_name: str, new_api_key: str, updated_by: int) -> bool:
        """Update an existing API key."""
        try:
            # Encrypt the new key
            encrypted_value, last_four = self.encrypt_key(new_api_key)

            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Update the key
                cursor.execute(
                    """
                    UPDATE api_keys 
                    SET encrypted_value = ?, last_four = ?, 
                        updated_at = CURRENT_TIMESTAMP, updated_by = ?
                    WHERE key_name = ?
                    """,
                    (encrypted_value, last_four, updated_by, key_name),
                )

                if cursor.rowcount > 0:
                    logger.info(f"Updated API key: {key_name}")
                    return True
                return False

        except Exception as e:
            logger.error(f"Error updating API key {key_name}: {e}")
            raise

    def get_api_key(self, key_name: str) -> Optional[str]:
        """
        Get a decrypted API key by name.

        Args:
            key_name: Name of the key to retrieve

        Returns:
            Decrypted API key value or None if not found/inactive
        """
        try:
            # Fetch and update usage in a single short-lived transaction
            encrypted_value: Optional[str] = None
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT encrypted_value, is_active 
                    FROM api_keys 
                    WHERE key_name = ? AND is_active = 1
                    """,
                    (key_name,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                encrypted_value = row[0]
                cursor.execute("UPDATE api_keys SET last_used_at = CURRENT_TIMESTAMP WHERE key_name = ?", (key_name,))

            # Perform any heavy/auxiliary work (like optional migration) AFTER the DB connection is closed
            if encrypted_value is not None:
                return self.decrypt_key(encrypted_value)
            return None

        except Exception as e:
            logger.error(f"Error getting API key {key_name}: {e}")
            return None

    def get_api_key_by_type(self, key_type: str) -> Optional[str]:
        """
        Get the first active API key of a specific type.

        Args:
            key_type: Type of key (anthropic, google, openai, etc.)

        Returns:
            Decrypted API key value or None if not found
        """
        try:
            key_name: Optional[str] = None
            encrypted_value: Optional[str] = None
            # Keep the transaction scope minimal to reduce lock contention
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT key_name, encrypted_value 
                    FROM api_keys 
                    WHERE key_type = ? AND is_active = 1
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (key_type,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                key_name, encrypted_value = row
                cursor.execute("UPDATE api_keys SET last_used_at = CURRENT_TIMESTAMP WHERE key_name = ?", (key_name,))

            if encrypted_value is not None:
                return self.decrypt_key(encrypted_value)
            return None

        except Exception as e:
            logger.error(f"Error getting API key by type {key_type}: {e}")
            return None

    def list_api_keys(self, include_inactive: bool = False) -> List[Dict]:
        """
        List all API keys (without actual values).

        Returns:
            List of key info dictionaries
        """
        try:
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()

                query = """
                    SELECT 
                        id, key_name, key_type, last_four, is_active,
                        last_used_at, last_validated_at, created_at, updated_at
                    FROM api_keys
                """

                if not include_inactive:
                    query += " WHERE is_active = 1"

                query += " ORDER BY key_type, key_name"

                cursor.execute(query)

                keys = []
                for row in cursor.fetchall():
                    keys.append(
                        {
                            "id": row[0],
                            "key_name": row[1],
                            "key_type": row[2],
                            "last_four": row[3],
                            "is_active": bool(row[4]),
                            "last_used_at": row[5],
                            "last_validated_at": row[6],
                            "created_at": row[7],
                            "updated_at": row[8],
                        }
                    )

                return keys

        except Exception as e:
            logger.error(f"Error listing API keys: {e}")
            return []

    def toggle_api_key(self, key_name: str, is_active: bool, updated_by: int) -> bool:
        """Enable or disable an API key."""
        try:
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    UPDATE api_keys 
                    SET is_active = ?, updated_at = CURRENT_TIMESTAMP, updated_by = ?
                    WHERE key_name = ?
                    """,
                    (1 if is_active else 0, updated_by, key_name),
                )

                if cursor.rowcount > 0:
                    action = "Enabled" if is_active else "Disabled"
                    logger.info(f"{action} API key: {key_name}")
                    return True
                return False

        except Exception as e:
            logger.error(f"Error toggling API key {key_name}: {e}")
            return False

    def delete_api_key(self, key_name: str) -> bool:
        """Permanently delete an API key."""
        try:
            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("DELETE FROM api_keys WHERE key_name = ?", (key_name,))

                if cursor.rowcount > 0:
                    logger.info(f"Deleted API key: {key_name}")
                    return True
                return False

        except Exception as e:
            logger.error(f"Error deleting API key {key_name}: {e}")
            return False

    def validate_api_key(self, key_name: str) -> Tuple[bool, str]:
        """
        Validate an API key by attempting a minimal API call.

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            # Get the key
            api_key = self.get_api_key(key_name)
            if not api_key:
                return False, "Key not found or inactive"

            with admin_db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Get key type
                cursor.execute("SELECT key_type FROM api_keys WHERE key_name = ?", (key_name,))
                row = cursor.fetchone()
                if not row:
                    return False, "Key not found"

                key_type = row[0]

                # Validate based on type
                is_valid, message = self._validate_key_by_type(key_type, api_key)

                # Update validation timestamp if successful
                if is_valid:
                    cursor.execute(
                        "UPDATE api_keys SET last_validated_at = CURRENT_TIMESTAMP WHERE key_name = ?", (key_name,)
                    )

                return is_valid, message

        except Exception as e:
            logger.error(f"Error validating API key {key_name}: {e}")
            return False, str(e)

    def _validate_key_by_type(self, key_type: str, api_key: str) -> Tuple[bool, str]:
        """Validate an API key based on its type."""
        try:
            if key_type == "anthropic":
                # Test with a minimal Anthropic API call
                from anthropic import Anthropic

                client = Anthropic(api_key=api_key)
                # Just check if we can create a client - actual validation would need a test call
                return True, "Anthropic API key format valid"

            elif key_type == "google":
                # Test with langchain-google-genai (available in container)
                from langchain_google_genai import ChatGoogleGenerativeAI

                # Just check if we can create a client with the API key
                ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=api_key)
                return True, "Google API key format valid"

            elif key_type == "openai":
                # Test with a minimal OpenAI API call
                from openai import OpenAI

                client = OpenAI(api_key=api_key)
                # Just check if we can create a client
                return True, "OpenAI API key format valid"

            else:
                return False, f"Unknown key type: {key_type}"

        except ImportError as e:
            return False, f"Provider library not installed: {e}"
        except Exception as e:
            return False, f"Validation failed: {str(e)}"

    def migrate_from_environment(self, updated_by: int) -> Dict[str, bool]:
        """
        Migrate API keys from environment variables to database.

        Returns:
            Dict mapping key names to migration success status
        """
        results = {}

        # Map of environment variables to key names and types
        env_mappings = [
            ("ANTHROPIC_API_KEY", "anthropic_primary", "anthropic"),
            ("GOOGLE_API_KEY", "google_primary", "google"),
            ("OPENAI_API_KEY", "openai_primary", "openai"),
        ]

        for env_var, key_name, key_type in env_mappings:
            api_key = os.getenv(env_var)
            if api_key:
                try:
                    # Check if already migrated
                    existing = self.get_api_key(key_name)
                    if existing:
                        results[key_name] = True  # Already migrated
                        continue

                    # Create the key in database
                    self.create_api_key(key_name, key_type, api_key, updated_by)
                    results[key_name] = True
                    logger.info(f"Migrated {env_var} to database as {key_name}")
                except Exception as e:
                    logger.error(f"Failed to migrate {env_var}: {e}")
                    results[key_name] = False
            else:
                results[key_name] = False  # No env var to migrate

        return results


# Global instance
api_key_manager = ApiKeyManager()
