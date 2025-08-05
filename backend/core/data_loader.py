import json
import logging
from typing import Any, Dict, List, Tuple

from langchain.docstore.document import Document

from .data_source_config import config

# Get the logger instance
logger = logging.getLogger(__name__)


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

        # Return empty data to allow the app to start in a degraded state
        return [], []
    except json.JSONDecodeError:
        logger.critical(
            f"CRITICAL: The {unified_data_path} file is corrupted or not valid JSON. The application cannot load its knowledge base."
        )
        return [], []
    # --- END OF UPDATE ---

    docs = []

    # Process each configured source
    illustrations_data = []
    data_sources_config = config.data_sources

    for source_config in data_sources_config.get("sources", []):
        source_name = source_config["name"]
        source_data = unified_data.get(source_name, {} if not source_config.get("is_list_source") else [])

        if source_config.get("is_list_source"):
            # Handle list sources like illustrations
            if source_name == "illustrations":
                illustrations_data = source_data
            for item in source_data:
                if source_name == "illustrations":
                    tags = ", ".join(item.get("tags", []))
                    content = f"Title: {item.get('title', '')}\nTags: {tags}"
                    docs.append(
                        Document(
                            page_content=content,
                            metadata={
                                "source": "illustration",
                                "file": item.get("file"),
                                "title": item.get("title"),
                            },
                        )
                    )
        else:
            # Handle object sources with sections
            for section_config in source_config.get("sections", []):
                section_name = section_config["name"]
                field_name = section_config["field"]

                if section_config.get("is_list"):
                    # Handle list sections
                    items = source_data.get(field_name, [])
                    for item in items:
                        if source_name == "resume" and section_name == "experience":
                            points = item.get("points", [])
                            points_str = "\n".join([f"- {p}" for p in points]) if points else "No points listed"
                            content = (
                                f"Company: {item['company']}\n"
                                f"Role: {item['role']}\n"
                                f"Dates: {item['dates']}\n"
                                f"Responsibilities:\n{points_str}"
                            )
                            metadata = {
                                "source": source_name,
                                "section": section_name,
                                "company": item["company"],
                                "role": item["role"],
                            }
                        elif source_name == "resume" and section_name == "education":
                            content = (
                                f"Institution: {item['institution']}\n"
                                f"Degree: {item['degree']}\n"
                                f"Dates: {item['dates']}"
                            )
                            metadata = {
                                "source": source_name,
                                "section": section_name,
                                "institution": item["institution"],
                            }
                        elif source_name == "resume" and section_name == "accomplishments":
                            content = f"{item['title']}: {item['description']}"
                            metadata = {"source": source_name, "section": section_name}
                        elif source_name == "about" and section_name == "sections":
                            content = f"{item['heading']}: {item['content']}"
                            metadata = {"source": source_name, "section": item["heading"]}
                        else:
                            # Generic handling for other list sections
                            content = str(item)
                            metadata = {"source": source_name, "section": section_name}

                        docs.append(Document(page_content=content, metadata=metadata))
                else:
                    # Handle single value sections
                    value = source_data.get(field_name)
                    if value:
                        if source_name == "resume" and section_name == "summary":
                            content = f"Summary: {value}"
                        elif source_name == "about" and section_name == "introduction":
                            content = value
                        else:
                            content = f"{section_name}: {value}"

                        docs.append(
                            Document(
                                page_content=content,
                                metadata={"source": source_name, "section": section_name},
                            )
                        )

    logger.info(f"Loaded {len(docs)} logical documents from structured data.")
    return docs, illustrations_data
