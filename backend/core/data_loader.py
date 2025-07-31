# backend/core/data_loader.py

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
from collections import defaultdict

from langchain.docstore.document import Document
from backend.core.config import AppConfig

# Get the logger instance
logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Handles document processing based on configuration rules."""

    @staticmethod
    def format_template(template: str, data: Dict[str, Any], processors: Optional[Dict[str, str]] = None) -> str:
        """Format a template string with data, applying field processors if available."""
        processed_data = data.copy()

        # Apply field processors
        if processors:
            for field_name, processor_name in processors.items():
                if field_name not in processed_data:
                    # Try to derive from other fields using method references
                    try:
                        if field_name == "points_formatted" and "points" in data:
                            processed_data[field_name] = AppConfig.format_points_list(data["points"])
                        elif field_name == "tags_joined" and "tags" in data:
                            processed_data[field_name] = AppConfig.format_tags_list(data["tags"])
                        elif field_name == "skills_list" and "skills" in data:
                            processed_data[field_name] = AppConfig.format_skills_list(data["skills"])
                    except Exception as e:
                        logger.warning(f"Error processing field {field_name}: {e}")
                        processed_data[field_name] = str(data.get(field_name, ""))

        # Fill in missing fields with empty strings or defaults
        for key in template:
            if key not in processed_data:
                processed_data[key] = data.get(key, "Unknown")

        try:
            return template.format(**processed_data)
        except KeyError as e:
            logger.warning(f"Missing template field {e}, using fallback")
            # Create safe data dict with all missing keys as empty strings
            safe_data = defaultdict(str, processed_data)
            return template.format_map(safe_data)

    @staticmethod
    def format_metadata(metadata_config: Dict[str, str], data: Dict[str, Any]) -> Dict[str, Any]:
        """Format metadata fields with data values."""
        metadata = {"source": data.get("_source_name", "unknown")}

        for key, value_template in metadata_config.items():
            if isinstance(value_template, str) and value_template.startswith("{") and value_template.endswith("}"):
                # Extract field name from template like "{company}"
                field_name = value_template[1:-1]
                metadata[key] = data.get(field_name, "Unknown")
            else:
                metadata[key] = value_template

        return metadata

    @staticmethod
    def process_single_field(source_name: str, section_name: str, section_config: Dict[str, Any], data: Dict[str, Any]) -> List[Document]:
        """Process a single field section."""
        field_value = data.get(section_name)
        if not field_value:
            return []

        content = DocumentProcessor.format_template(
            section_config["content_template"],
            {section_name: field_value, "_source_name": source_name}
        )

        metadata = DocumentProcessor.format_metadata(
            section_config.get("metadata", {}),
            {"_source_name": source_name}
        )

        return [Document(page_content=content, metadata=metadata)]

    @staticmethod
    def process_array_section(source_name: str, section_name: str, section_config: Dict[str, Any], data: Dict[str, Any]) -> List[Document]:
        """Process an array section."""
        array_data = data.get(section_name, [])
        if not array_data:
            return []

        docs = []
        processors = section_config.get("field_processors", {})

        for item in array_data:
            # Add source name for template processing
            item_with_source = {**item, "_source_name": source_name}

            content = DocumentProcessor.format_template(
                section_config["content_template"],
                item_with_source,
                processors
            )

            metadata = DocumentProcessor.format_metadata(
                section_config.get("metadata", {}),
                item_with_source
            )

            docs.append(Document(page_content=content, metadata=metadata))

        return docs

    @staticmethod
    def process_grouped_array_section(source_name: str, section_name: str, section_config: Dict[str, Any], data: Dict[str, Any]) -> List[Document]:
        """Process an array section grouped by a specific field."""
        array_data = data.get(section_name, [])
        if not array_data:
            return []

        group_by_field = section_config.get("group_by")
        if not group_by_field:
            logger.warning(f"grouped_array section {section_name} missing 'group_by' field")
            return []

        # Group items by the specified field
        groups = defaultdict(list)
        for item in array_data:
            group_key = item.get(group_by_field, "Other")
            groups[group_key].append(item)

        docs = []
        list_formatter_name = section_config.get("list_formatter")

        for group_name, group_items in groups.items():
            # Create content for this group
            data_for_template = {
                group_by_field: group_name,
                "skills": group_items,  # For backward compatibility
                "_source_name": source_name
            }

            # Apply list formatter if available
            if list_formatter_name:
                try:
                    if list_formatter_name == "format_skills_list":
                        data_for_template["skills_list"] = AppConfig.format_skills_list(group_items)
                    else:
                        logger.warning(f"Unknown list formatter: {list_formatter_name}")
                        data_for_template["skills_list"] = ", ".join([str(item) for item in group_items])
                except Exception as e:
                    logger.warning(f"Error applying list formatter: {e}")
                    data_for_template["skills_list"] = ", ".join([str(item) for item in group_items])

            content = DocumentProcessor.format_template(
                section_config["content_template"],
                data_for_template
            )

            metadata = DocumentProcessor.format_metadata(
                section_config.get("metadata", {}),
                {**data_for_template, group_by_field: group_name}
            )

            docs.append(Document(page_content=content, metadata=metadata))

        return docs


def load_structured_data() -> List[Document]:
    """
    Load structured JSON data and convert it into a list of LangChain Documents,
    using configuration-driven processing rules.

    Returns:
        List of Document objects ready for vector storage
    """
    logger.info("Loading structured unified data from public/unified_data.json...")

    unified_data_path = Path("public/unified_data.json")

    # Check if unified data file exists
    if not unified_data_path.exists():
        logger.critical(
            f"The unified_data.json file was not found at {unified_data_path}. "
            "Please run the build script: 'python backend/scripts/build_unified_data.py'"
        )
        return []

    # Load the unified data
    try:
        with open(unified_data_path, "r", encoding="utf-8") as f:
            unified_data = json.load(f)
    except json.JSONDecodeError as e:
        logger.critical(f"Invalid JSON in unified_data.json: {e}")
        return []
    except Exception as e:
        logger.critical(f"Error reading unified_data.json: {e}")
        return []

    # Check if data was loaded successfully
    if not unified_data:
        logger.warning("Unified data file is empty")
        return []

    # Log metadata if available
    if "_metadata" in unified_data:
        metadata = unified_data["_metadata"]
        logger.info(f"Loaded unified data with {metadata.get('sources_loaded', 'unknown')} sources")
        if metadata.get("errors"):
            logger.warning(f"Build errors detected: {metadata['errors']}")

    docs = []

    # Process each configured data source
    for source_config in AppConfig.DATA_SOURCES:
        source_name = source_config["name"]
        processing_config = source_config.get("processing_config")

        if not processing_config:
            logger.warning(f"No processing config found for source: {source_name}")
            continue

        source_data = unified_data.get(source_name)
        if not source_data:
            logger.warning(f"No data found for source: {source_name}")
            continue

        logger.info(f"Processing {source_name} data using config-driven approach")

        chunk_strategy = processing_config.get("chunk_strategy", "by_sections")

        if chunk_strategy == "by_sections":
            # Process sections-based data (resume, about)
            sections_config = processing_config.get("sections", {})

            for section_name, section_config in sections_config.items():
                section_type = section_config.get("type", "single_field")

                try:
                    if section_type == "single_field":
                        section_docs = DocumentProcessor.process_single_field(
                            source_name, section_name, section_config, source_data
                        )
                    elif section_type == "array":
                        section_docs = DocumentProcessor.process_array_section(
                            source_name, section_name, section_config, source_data
                        )
                    elif section_type == "grouped_array":
                        section_docs = DocumentProcessor.process_grouped_array_section(
                            source_name, section_name, section_config, source_data
                        )
                    else:
                        logger.warning(f"Unknown section type: {section_type}")
                        continue

                    docs.extend(section_docs)
                    logger.debug(f"Processed {len(section_docs)} documents from {source_name}.{section_name}")

                except Exception as e:
                    logger.error(f"Error processing {source_name}.{section_name}: {e}")

        elif chunk_strategy == "by_items":
            # Process item-based data (illustrations)
            if not isinstance(source_data, list):
                logger.warning(f"Expected list for by_items strategy, got {type(source_data)} for {source_name}")
                continue

            processors = processing_config.get("field_processors", {})

            for item in source_data:
                try:
                    item_with_source = {**item, "_source_name": source_name}

                    content = DocumentProcessor.format_template(
                        processing_config["content_template"],
                        item_with_source,
                        processors
                    )

                    metadata = DocumentProcessor.format_metadata(
                        processing_config.get("metadata", {}),
                        item_with_source
                    )

                    docs.append(Document(page_content=content, metadata=metadata))

                except Exception as e:
                    logger.error(f"Error processing item in {source_name}: {e}")

        else:
            logger.warning(f"Unknown chunk strategy: {chunk_strategy}")

    logger.info(f"Loaded {len(docs)} logical documents from structured data.")

    # Log breakdown by source
    sources: Dict[str, int] = {}
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        sources[source] = sources.get(source, 0) + 1

    for source, count in sources.items():
        logger.info(f"  • {source}: {count} documents")

    return docs


def load_all_documents() -> Tuple[List[Document], List[Dict[str, Any]]]:
    """
    Legacy function for backward compatibility.

    Returns:
        Tuple of (documents, illustrations_data)
    """
    docs = load_structured_data()

    # Extract illustrations data separately for illustration service
    unified_data_path = Path("public/unified_data.json")
    illustrations_data = []

    if unified_data_path.exists():
        try:
            with open(unified_data_path, "r", encoding="utf-8") as f:
                unified_data = json.load(f)

            illustrations_data = unified_data.get("illustration", [])
            if not illustrations_data:
                illustrations_data = unified_data.get("illustrations", [])

        except Exception as e:
            logger.error(f"Error loading illustrations data: {e}")

    return docs, illustrations_data
