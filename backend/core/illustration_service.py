import json
import os
import os.path
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from thefuzz import process

logger = logging.getLogger(__name__)

class IllustrationService:
    """Service for managing and searching illustration data."""

    def __init__(self, illustrations_path: str, search_threshold: int = 55, max_results: int = 15):
        # Validate and secure the file path
        self.illustrations_path = self._validate_path(illustrations_path)
        self.search_threshold = search_threshold
        self.max_results = max_results
        self.illustrations_data = []
        self._load_illustrations()

    def _validate_path(self, path: str) -> Optional[str]:
        """
        Validate and sanitize the illustrations file path to prevent path traversal attacks.

        Args:
            path: The path to validate

        Returns:
            Validated absolute path or None if invalid

        Raises:
            ValueError: If path is unsafe
        """
        try:
            # Convert to Path object for better handling
            requested_path = Path(path)

            # Get absolute path to resolve any relative components
            abs_path = requested_path.resolve()

            # Define allowed base directories (adjust these to your app's structure)
            allowed_base_dirs = [
                Path.cwd(),  # Current working directory
                Path.cwd() / "public",  # Public directory
                Path.cwd() / "data",   # Data directory
                Path("/app/public") if Path("/app").exists() else None,
            ]

            # Remove None values
            allowed_base_dirs = [d for d in allowed_base_dirs if d is not None]

            # Check if the resolved path is within allowed directories
            path_is_safe = False
            for base_dir in allowed_base_dirs:
                try:
                    abs_base = base_dir.resolve()
                    # Check if the path is within this base directory
                    abs_path.relative_to(abs_base)
                    path_is_safe = True
                    break
                except ValueError:
                    # Path is not within this base directory
                    continue

            if not path_is_safe:
                logger.error(f"Path traversal attempt detected: {path} -> {abs_path}")
                raise ValueError(f"Invalid file path: path must be within allowed directories")

            # Additional security checks
            path_str = str(abs_path)

            # Check for suspicious path components
            suspicious_components = ['..', './', '\\', '\x00']
            if any(component in path for component in suspicious_components):
                logger.error(f"Suspicious path components detected in: {path}")
                raise ValueError("Invalid file path: contains suspicious components")

            # Ensure it's a JSON file
            if not path_str.lower().endswith('.json'):
                logger.error(f"Invalid file type: {path} (must be .json)")
                raise ValueError("Invalid file type: must be a JSON file")

            # Check file size if it exists
            if abs_path.exists():
                file_size = abs_path.stat().st_size
                max_size = 10 * 1024 * 1024  # 10MB limit
                if file_size > max_size:
                    logger.error(f"File too large: {file_size} bytes (max: {max_size})")
                    raise ValueError(f"File too large: {file_size} bytes")

            logger.info(f"Path validated successfully: {abs_path}")
            return str(abs_path)

        except (OSError, ValueError) as e:
            logger.error(f"Path validation failed for '{path}': {e}")
            raise ValueError(f"Invalid file path: {e}")

    def _load_illustrations(self) -> None:
        """Load illustrations data from JSON file with enhanced security."""
        if not self.illustrations_path:
            logger.warning("No valid illustrations path provided")
            self.illustrations_data = []
            return

        try:
            # Double-check path exists and is readable
            if not os.path.exists(self.illustrations_path):
                logger.warning(f"Illustrations file not found at {self.illustrations_path}")
                self.illustrations_data = []
                return

            if not os.access(self.illustrations_path, os.R_OK):
                logger.error(f"No read permission for {self.illustrations_path}")
                self.illustrations_data = []
                return

            # Check file size again before loading
            file_size = os.path.getsize(self.illustrations_path)
            max_size = 10 * 1024 * 1024  # 10MB limit
            if file_size > max_size:
                logger.error(f"File too large to load: {file_size} bytes")
                self.illustrations_data = []
                return

            # Load with security measures
            with open(self.illustrations_path, "r", encoding="utf-8") as f:
                # Load JSON with size limit (additional protection)
                content = f.read(max_size)
                self.illustrations_data = json.loads(content)

                # Validate loaded data structure
                if not isinstance(self.illustrations_data, list):
                    logger.error("Invalid data format: expected list")
                    self.illustrations_data = []
                    return

                logger.info(f"Loaded {len(self.illustrations_data)} illustrations")

        except FileNotFoundError:
            logger.warning(f"Illustrations file not found at {self.illustrations_path}")
            self.illustrations_data = []
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in illustrations file: {str(e)[:100]}")  # Limit error message
            self.illustrations_data = []
        except PermissionError:
            logger.error(f"Permission denied accessing {self.illustrations_path}")
            self.illustrations_data = []
        except Exception as e:
            logger.error(f"Unexpected error loading illustrations: {str(e)[:100]}")  # Limit error message
            self.illustrations_data = []

    def validate_data(self) -> Tuple[bool, str]:
        """Validate the loaded illustrations data structure."""
        if not self.illustrations_data:
            message = "❌ No illustrations data loaded"
            logger.warning(message)
            return False, message

        valid_count = 0
        issues = []

        for i, img in enumerate(self.illustrations_data):
            if not isinstance(img, dict):
                issues.append(f"Item {i}: Not a dictionary")
                continue

            if 'file' not in img:
                issues.append(f"Item {i}: Missing 'file' field")
                continue

            # Validate file field contains safe filename
            file_value = img.get('file', '')
            if not isinstance(file_value, str) or not file_value:
                issues.append(f"Item {i}: Invalid file field")
                continue

            # Check for path traversal in file names
            if '..' in file_value or '/' in file_value or '\\' in file_value:
                issues.append(f"Item {i}: Suspicious file path: {file_value}")
                continue

            if not img.get('title') and not img.get('tags'):
                issues.append(f"Item {i}: No title or tags for searching")
                continue

            valid_count += 1

        if issues and len(issues) <= 5:
            logger.warning(f"Illustrations validation issues: {issues}")
        elif issues:
            logger.warning(f"Illustrations validation issues: {issues[:5]}... ({len(issues)} total)")

        message = f"✅ Illustrations: {valid_count}/{len(self.illustrations_data)} valid entries"
        logger.info(message)

        if valid_count == 0:
            error_msg = "❌ No valid illustration entries found!"
            logger.error(error_msg)
            return False, error_msg
        elif valid_count < len(self.illustrations_data):
            warning_msg = f"⚠️ Some illustration entries are missing required fields"
            logger.warning(warning_msg)

        return valid_count > 0, message

    def search(self, search_term: str) -> List[Dict[str, str]]:
        """
        Search illustrations using fuzzy matching.

        Args:
            search_term: The search term to match against illustrations

        Returns:
            List of dictionaries containing file paths of matching illustrations
        """
        try:
            if not self.illustrations_data:
                logger.warning("No illustrations data available")
                return []

            # Sanitize search term to prevent injection
            if not search_term or not isinstance(search_term, str):
                logger.warning("Invalid search term provided")
                return []

            # Limit search term length
            if len(search_term) > 100:
                logger.warning("Search term too long, truncating")
                search_term = search_term[:100]

            if search_term.lower().strip() in ["all", ""]:
                logger.info(f"Returning all {len(self.illustrations_data)} illustrations")
                return [{"file": img["file"]} for img in self.illustrations_data
                        if isinstance(img, dict) and "file" in img]

            search_term = search_term.strip().lower()
            logger.info(f"Searching illustrations for term: '{search_term}'")

            # Handle multiple search terms joined by "and"
            if " and " in search_term:
                terms = [term.strip() for term in search_term.split(" and ") if term.strip()]
                logger.info(f"Multi-term search with {len(terms)} terms: {terms}")

                all_matches = []
                for term in terms:
                    matches = self._search_single_term(term)
                    all_matches.extend(matches)

                # Deduplicate while preserving order
                unique_files = list(dict.fromkeys(all_matches))
                results = [{"file": file} for file in unique_files[:self.max_results]]
                logger.info(f"Multi-term search returned {len(results)} results")
                return results
            else:
                # Single-term search
                matches = self._search_single_term(search_term)
                results = [{"file": file} for file in matches[:self.max_results]]
                logger.info(f"Single-term search returned {len(results)} results")
                return results

        except Exception as e:
            logger.error(f"Error searching illustrations for '{search_term}': {str(e)[:100]}")
            return []

    def _search_single_term(self, term: str) -> List[str]:
        """Helper function to search for a single term."""
        try:
            # Create searchable content for each illustration
            choices = {}
            for img in self.illustrations_data:
                if not isinstance(img, dict) or 'file' not in img:
                    continue

                # Combine title and tags for searching
                title = img.get('title', '').lower()
                tags = ' '.join(img.get('tags', [])).lower() if img.get('tags') else ''
                searchable_content = f"{title} {tags}".strip()

                if searchable_content:  # Only include if there's content to search
                    choices[img["file"]] = searchable_content

            if not choices:
                logger.warning("No searchable content found in illustrations")
                return []

            # Handle singular/plural forms
            search_terms = [term]
            if term.endswith('s'):
                # Add singular form (remove trailing 's')
                search_terms.append(term[:-1])
            else:
                # Add plural form (add 's')
                search_terms.append(term + 's')

            logger.debug(f"Searching with terms: {search_terms}")

            all_matches = []
            for search_term in search_terms:
                # Use fuzzy matching
                found_matches = process.extract(search_term, choices, limit=15)

                # Filter by threshold
                for match_text, score, file_key in found_matches:
                    if score >= self.search_threshold:
                        all_matches.append((file_key, score))
                        logger.debug(f"Match: {file_key} (score: {score})")

            # Remove duplicates while keeping highest score
            unique_matches = {}
            for file_key, score in all_matches:
                if file_key not in unique_matches or score > unique_matches[file_key]:
                    unique_matches[file_key] = score

            high_quality_matches = list(unique_matches.keys())

            logger.info(f"Found {len(high_quality_matches)} unique matches above threshold {self.search_threshold}")
            return high_quality_matches

        except Exception as e:
            logger.error(f"Error in single term search for '{term}': {str(e)[:100]}")
            return []

    def get_all(self) -> List[Dict[str, str]]:
        """Get all illustrations as file references."""
        return [{"file": img["file"]} for img in self.illustrations_data
                if isinstance(img, dict) and "file" in img]

    def get_count(self) -> int:
        """Get the total number of illustrations."""
        return len(self.illustrations_data)

    def reload(self) -> bool:
        """Reload illustrations data from file."""
        try:
            self._load_illustrations()
            return True
        except Exception as e:
            logger.error(f"Failed to reload illustrations: {str(e)[:100]}")
            return False