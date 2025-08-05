import json
import logging
from typing import Any, Dict, List, Tuple

from langchain.docstore.document import Document

from .data_source_config import config

# Get the logger instance
logger = logging.getLogger(__name__)


def _process_special_field(value: Any, field_name: str, processing_config: Dict[str, Any]) -> str:
    """Process fields with special formatting requirements."""
    field_config = processing_config.get(field_name, {})

    if field_config.get("type") == "format_list":
        if not value:
            return str(field_config.get("empty_message", ""))
        if field_config.get("format") == "bullet_points":
            return "\n".join([f"- {item}" for item in value])
        return "\n".join(str(item) for item in value)

    elif field_config.get("type") == "join_array":
        if not value:
            return str(field_config.get("default", ""))
        separator = str(field_config.get("separator", ", "))
        return separator.join(str(item) for item in value)

    return str(value) if value is not None else ""


def _apply_template(template: str, data: Dict[str, Any], processing_config: Dict[str, Any]) -> str:
    """Apply template formatting to data with special processing."""
    formatted_data = {}

    # Process all existing fields
    for key, value in data.items():
        if key == "points":
            # Special handling for points array
            formatted_data["points_formatted"] = _process_special_field(value, "points", processing_config)
        elif key == "tags":
            # Special handling for tags array
            formatted_data[key] = _process_special_field(value, "tags", processing_config)
        else:
            formatted_data[key] = str(value) if value is not None else ""

    # Add missing fields that might be referenced in template
    import re

    template_vars = re.findall(r"\{(\w+)\}", template)
    for var in template_vars:
        if var not in formatted_data:
            if var == "tags":
                formatted_data[var] = _process_special_field(None, "tags", processing_config)
            elif var == "points_formatted":
                formatted_data[var] = _process_special_field(None, "points", processing_config)
            else:
                formatted_data[var] = ""

    try:
        return template.format(**formatted_data)
    except KeyError as e:
        logger.warning(f"Template formatting failed for key {e}, using fallback")
        # Fallback to simple string representation
        return str(data)


def _extract_metadata(data: Dict[str, Any], source_name: str, section_config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata from data based on section configuration."""
    metadata = {"source": source_name}

    # Add section name to metadata
    if "name" in section_config:
        section_name = section_config["name"]
        metadata["section"] = section_name

        # Handle special metadata field for about sections
        if section_config.get("metadata_section_field"):
            field_name = section_config["metadata_section_field"]
            if field_name in data:
                metadata["section"] = data[field_name]

    # Add configured metadata fields
    metadata_fields = section_config.get("metadata_fields", [])
    for field in metadata_fields:
        if field in data:
            metadata[field] = data[field]

    return metadata


def load_all_documents() -> Tuple[List[Document], List[Dict[str, Any]]]:
    """
    Load structured JSON data and convert it into a list of LangChain Documents,
    chunked by logical units and enriched with metadata.
    """
    # Get the unified data path from config
    unified_data_path = config.get_unified_data_path()
    logger.info(f"Loading structured unified data from {unified_data_path}...")

    # Wrap file loading in a try-except block for resilience
    try:
        with open(unified_data_path, "r", encoding="utf-8") as f:
            unified_data = json.load(f)
    except FileNotFoundError:
        logger.critical(
            f"The {unified_data_path} file was not found. The application cannot load its knowledge base. Please run the build script using 'python backend/scripts/build_unified_data.py'."
        )
        return [], []
    except json.JSONDecodeError:
        logger.critical(
            f"CRITICAL: The {unified_data_path} file is corrupted or not valid JSON. The application cannot load its knowledge base."
        )
        return [], []

    docs = []
    illustrations_data = []

    # Get configuration objects
    data_sources_config = config.data_sources
    templates = config.templates
    processing_config = config.special_processing

    for source_config in data_sources_config.get("sources", []):
        source_name = source_config["name"]
        source_data = unified_data.get(source_name, {} if not source_config.get("is_list_source") else [])

        if source_config.get("is_list_source"):
            # Handle list sources like illustrations
            if source_name == "illustrations":
                illustrations_data = source_data

            template_name = source_config.get("template")
            template = templates.get(template_name, "")

            for item in source_data:
                # Apply template if configured
                if template:
                    content = _apply_template(template, item, processing_config)
                else:
                    # Fallback to legacy logic for illustrations
                    if source_name == "illustrations":
                        tags = ", ".join(item.get("tags", []))
                        content = f"Title: {item.get('title', '')}\nTags: {tags}"
                    else:
                        content = str(item)

                # Extract metadata
                metadata = {"source": "illustration" if source_name == "illustrations" else source_name}
                metadata_fields = source_config.get("metadata_fields", [])
                for field in metadata_fields:
                    if field in item:
                        metadata[field] = item[field]

                docs.append(Document(page_content=content, metadata=metadata))
        else:
            # Handle object sources with sections
            for section_config in source_config.get("sections", []):
                section_name = section_config["name"]
                field_name = section_config["field"]
                template_name = section_config.get("template")
                template = templates.get(template_name, "")

                if section_config.get("is_list"):
                    # Handle list sections
                    items = source_data.get(field_name, [])
                    for item in items:
                        # Apply template if configured
                        if template:
                            content = _apply_template(template, item, processing_config)
                        else:
                            # Fallback to generic handling
                            content = str(item)

                        # Extract metadata
                        metadata = _extract_metadata(item, source_name, section_config)
                        docs.append(Document(page_content=content, metadata=metadata))
                else:
                    # Handle single value sections
                    value = source_data.get(field_name)
                    if value:
                        data = {field_name: value}

                        # Apply template if configured
                        if template:
                            content = _apply_template(template, data, processing_config)
                        else:
                            # Fallback to simple formatting
                            content = f"{section_name}: {value}"

                        # Extract metadata
                        metadata = _extract_metadata(data, source_name, section_config)
                        docs.append(Document(page_content=content, metadata=metadata))

    logger.info(f"Loaded {len(docs)} logical documents from structured data.")
    return docs, illustrations_data
