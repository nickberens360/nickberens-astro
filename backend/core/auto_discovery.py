"""
Auto-discovery system for RAG data sources.

This module provides functionality to automatically discover and configure
JSON data sources with minimal manual configuration required.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)

# Common stop words to filter from text extraction
_STOP_WORDS = {
    "the",
    "and",
    "for",
    "are",
    "but",
    "not",
    "you",
    "all",
    "can",
    "had",
    "her",
    "was",
    "one",
    "our",
    "out",
    "day",
    "get",
    "has",
    "him",
    "his",
    "how",
    "its",
    "may",
    "new",
    "now",
    "old",
    "see",
    "two",
    "who",
    "boy",
    "did",
    "she",
    "use",
    "way",
    "what",
    "when",
    "with",
}


class AutoDataSourceDiscovery:
    """Handles automatic discovery and configuration of JSON data sources."""

    def __init__(self, data_dir: Union[str, Path] = "public"):
        """Initialize the auto-discovery system.

        Args:
            data_dir: Directory to scan for JSON files
        """
        self.data_dir = Path(data_dir)
        self.field_priorities = {
            # High priority fields for templates
            "title": 1,
            "name": 1,
            "heading": 1,
            "description": 2,
            "content": 2,
            "summary": 2,
            "introduction": 2,
            "company": 3,
            "role": 3,
            "institution": 3,
            "degree": 3,
            "dates": 4,
            "year": 4,
            "period": 4,
            "location": 4,
            "tags": 5,
            "skills": 5,
            "technologies": 5,
            "points": 6,
            "responsibilities": 6,
            "notes": 6,
        }

    def discover_sources(self, exclude_files: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Discover all JSON files and generate configurations.

        Args:
            exclude_files: List of filenames to exclude from discovery

        Returns:
            List of auto-generated source configurations
        """
        if exclude_files is None:
            exclude_files = ["unified_data.json"]

        discovered_sources: List[Dict[str, Any]] = []

        if not self.data_dir.exists():
            logger.warning(f"Data directory {self.data_dir} does not exist")
            return discovered_sources

        for json_file in self.data_dir.glob("*.json"):
            if json_file.name in exclude_files:
                continue

            try:
                source_config = self._analyze_json_file(json_file)
                if source_config:
                    discovered_sources.append(source_config)
                    logger.info(f"Auto-discovered source: {json_file.name}")
            except Exception as e:
                logger.warning(f"Failed to analyze {json_file.name}: {e}")

        return discovered_sources

    def _analyze_json_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze a JSON file and generate configuration.

        Args:
            file_path: Path to the JSON file

        Returns:
            Generated source configuration or None if analysis fails
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load {file_path}: {e}")
            return None

        source_name = file_path.stem

        # Determine the structure type and generate config
        if isinstance(data, list):
            return self._generate_list_source_config(source_name, file_path.name, data)
        elif isinstance(data, dict):
            return self._generate_object_source_config(source_name, file_path.name, data)
        else:
            logger.warning(f"Unsupported data type in {file_path.name}: {type(data)}")
            return None

    def _generate_list_source_config(self, source_name: str, filename: str, data: List[Any]) -> Dict[str, Any]:
        """Generate configuration for list-based sources (like illustrations.json).

        Args:
            source_name: Name of the source
            filename: Name of the file
            data: The JSON data (list)

        Returns:
            Generated source configuration
        """
        config = {"name": source_name, "file": filename, "is_list_source": True, "auto_discovered": True}

        if data:
            # Analyze first item to determine structure
            first_item = data[0]
            if isinstance(first_item, dict):
                # Extract common fields from all items
                common_fields = self._get_common_fields(data)
                config["item_fields"] = list(common_fields)

                # Generate template
                template_name = f"{source_name}_template"
                config["template"] = template_name

                # Determine metadata fields (important identifying fields)
                metadata_fields = self._select_metadata_fields(common_fields)
                if metadata_fields:
                    config["metadata_fields"] = metadata_fields

                # Check for special processing needs
                special_processing = self._detect_special_processing(data)
                if special_processing:
                    config["special_processing"] = special_processing

        return config

    def _generate_object_source_config(self, source_name: str, filename: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate configuration for object-based sources (like resume.json, about.json).

        Args:
            source_name: Name of the source
            filename: Name of the file
            data: The JSON data (dict)

        Returns:
            Generated source configuration
        """
        config: Dict[str, Any] = {"name": source_name, "file": filename, "auto_discovered": True, "sections": []}

        # Analyze each top-level field
        for field_name, field_value in data.items():
            section_config = self._generate_section_config(field_name, field_value, source_name)
            if section_config:
                config["sections"].append(section_config)

        return config

    def _generate_section_config(self, field_name: str, field_value: Any, source_name: str) -> Optional[Dict[str, Any]]:
        """Generate section configuration for a field.

        Args:
            field_name: Name of the field
            field_value: Value of the field
            source_name: Name of the source

        Returns:
            Generated section configuration
        """
        section_config: Dict[str, Any] = {
            "name": field_name,
            "field": field_name,
            "template": f"{source_name}_{field_name}_template",
        }

        if isinstance(field_value, list):
            section_config["is_list"] = True

            if field_value and isinstance(field_value[0], dict):
                # Extract common fields from list items
                common_fields = self._get_common_fields(field_value)
                section_config["item_fields"] = list(common_fields)

                # Determine metadata fields
                metadata_fields = self._select_metadata_fields(common_fields)
                if metadata_fields:
                    section_config["metadata_fields"] = metadata_fields

                # Special handling for sections with heading field
                if "heading" in common_fields:
                    section_config["metadata_section_field"] = "heading"

        elif isinstance(field_value, dict):
            # Handle nested objects (less common)
            section_config["is_object"] = True
        # For strings and primitives, use default handling

        return section_config

    def _get_common_fields(self, items: List[Dict[str, Any]]) -> Set[str]:
        """Get fields that are common across all items in a list.

        Args:
            items: List of dictionary items

        Returns:
            Set of common field names
        """
        if not items:
            return set()

        # Start with fields from first item
        common_fields = set(items[0].keys())

        # Intersect with fields from other items
        for item in items[1:]:
            if isinstance(item, dict):
                common_fields &= set(item.keys())

        return common_fields

    def _select_metadata_fields(self, fields: Set[str]) -> List[str]:
        """Select important fields to use as metadata.

        Args:
            fields: Available field names

        Returns:
            List of selected metadata fields
        """
        metadata_fields = []

        # Prioritize important identifying fields
        priority_fields = ["title", "name", "company", "role", "institution", "file"]

        for field in priority_fields:
            if field in fields:
                metadata_fields.append(field)

        return metadata_fields

    def _detect_special_processing(self, data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Detect fields that need special processing by analyzing all items.

        Args:
            data: List of items to analyze

        Returns:
            Dictionary of special processing configurations
        """
        special_processing = {}

        # Collect all field names that are lists across all items
        list_fields: Set[str] = set()
        for item in data:
            if not isinstance(item, dict):
                continue
            for field_name, field_value in item.items():
                if isinstance(field_value, list):
                    list_fields.add(field_name)

        # Apply special processing rules to detected list fields
        for field_name in list_fields:
            if field_name in ["tags", "skills", "technologies"]:
                # Join arrays with commas
                special_processing[field_name] = {"type": "join_array", "separator": ", "}
            elif field_name in ["points", "responsibilities"]:
                # Format as bullet points
                special_processing[field_name] = {
                    "type": "format_list",
                    "format": "bullet_points",
                    "empty_message": "No points listed",
                }

        return special_processing

    def generate_templates(self, sources: List[Dict[str, Any]]) -> Dict[str, str]:
        """Generate templates for auto-discovered sources.

        Args:
            sources: List of source configurations

        Returns:
            Dictionary of template name to template content
        """
        templates = {}

        for source in sources:
            if source.get("is_list_source"):
                # Generate template for list source
                template_name = source.get("template")
                if template_name:
                    template_content = self._generate_list_template(source)
                    templates[template_name] = template_content
            else:
                # Generate templates for object source sections
                for section in source.get("sections", []):
                    template_name = section.get("template")
                    if template_name:
                        template_content = self._generate_section_template(section)
                        templates[template_name] = template_content

        return templates

    def _generate_list_template(self, source_config: Dict[str, Any]) -> str:
        """Generate template for a list-based source.

        Args:
            source_config: Source configuration

        Returns:
            Generated template string
        """
        item_fields = source_config.get("item_fields", [])

        # Sort fields by priority
        sorted_fields = sorted(item_fields, key=lambda x: self.field_priorities.get(x, 10))

        template_parts = []
        for field in sorted_fields[:4]:  # Limit to top 4 fields
            if field in ["tags", "skills", "technologies"]:
                template_parts.append(f"{field.title()}: {{{field}}}")
            else:
                template_parts.append(f"{field.title()}: {{{field}}}")

        if template_parts:
            return "\n".join(template_parts)
        if sorted_fields:
            return f"{{{sorted_fields[0]}}}"
        logger.warning(f"Could not generate a template for source {source_config['name']}")
        return ""

    def _generate_section_template(self, section_config: Dict[str, Any]) -> str:
        """Generate template for a section.

        Args:
            section_config: Section configuration

        Returns:
            Generated template string
        """
        field_name = section_config["field"]

        if section_config.get("is_list"):
            item_fields = section_config.get("item_fields", [])

            # Sort fields by priority
            sorted_fields = sorted(item_fields, key=lambda x: self.field_priorities.get(x, 10))

            template_parts = []
            for field in sorted_fields[:4]:  # Limit to top 4 fields
                if field == "points":
                    template_parts.append(f"{field.title()}:\n{{points_formatted}}")
                elif field in ["tags", "skills"]:
                    template_parts.append(f"{field.title()}: {{{field}}}")
                else:
                    template_parts.append(f"{field.title()}: {{{field}}}")

            return "\n".join(template_parts) if template_parts else f"{{{field_name}}}"
        else:
            # Simple field template
            return f"{{{field_name}}}"

    def generate_retriever_config(self, source_name: str, sample_data: Any) -> Dict[str, Any]:
        """Generate retriever configuration for a source.

        Args:
            source_name: Name of the source
            sample_data: Sample data to analyze for keywords

        Returns:
            Generated retriever configuration
        """
        # Generate description
        description = f"Good for answering questions about {source_name.replace('_', ' ')}"

        # Extract keywords from source name and content
        keywords = self._extract_keywords(source_name, sample_data)

        return {"description": description, "search_kwargs": {"k": 5}, "keywords": keywords}  # Reasonable default

    def _extract_keywords(self, source_name: str, data: Any) -> List[str]:
        """Extract relevant keywords from source name and data.

        Args:
            source_name: Name of the source
            data: Sample data

        Returns:
            List of extracted keywords
        """
        keywords = []

        # Add source name variations
        keywords.append(source_name)
        keywords.extend(source_name.split("_"))

        # Add common keywords based on source name
        keyword_mapping = {
            "resume": ["experience", "job", "work", "skill", "cv", "career"],
            "about": ["background", "who is", "philosophy", "approach"],
            "projects": ["project", "portfolio", "built", "created", "developed"],
            "illustrations": ["art", "illustration", "drawing", "creative", "design"],
            "experience": ["job", "work", "career", "role", "company"],
            "education": ["school", "degree", "study", "learning"],
            "skills": ["ability", "expertise", "technology", "tool"],
        }

        for key, values in keyword_mapping.items():
            if key in source_name.lower():
                keywords.extend(values)

        # Extract keywords from data content
        if isinstance(data, list) and data:
            sample_size = min(len(data), 5)  # Analyze up to 5 items
            for i in range(sample_size):
                sample_item = data[i]
                if isinstance(sample_item, dict):
                    # Look for common fields that might contain keywords
                    for field in ["title", "name", "tags", "category"]:
                        if field in sample_item:
                            value = sample_item[field]
                            if isinstance(value, str):
                                keywords.extend(self._extract_words_from_text(value))
                            elif isinstance(value, list):
                                for item in value:
                                    if isinstance(item, str):
                                        keywords.extend(self._extract_words_from_text(item))

        return list(set(keywords))  # Remove duplicates

    def _extract_words_from_text(self, text: str) -> List[str]:
        """Extract meaningful words from text.

        Args:
            text: Text to analyze

        Returns:
            List of extracted words
        """
        # Extract words including technical terms (e.g., Node.js, C++, C#)
        words = re.findall(r"\b[a-zA-Z0-9_+#.-]{2,}\b", text.lower())

        # Filter out common stop words
        return [word for word in words if word not in _STOP_WORDS]
