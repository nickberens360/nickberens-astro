# backend/core/data_loader.py

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

from langchain.docstore.document import Document

# Get the logger instance
logger = logging.getLogger(__name__)


def load_structured_data() -> List[Document]:
    """
    Load structured JSON data and convert it into a list of LangChain Documents,
    chunked by logical units and enriched with metadata.

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

    # Process Resume: Chunk by logical section
    resume = unified_data.get("resume", {})
    if resume:
        logger.info(f"Processing resume data: {type(resume).__name__}")

        # Handle summary
        if resume.get("summary"):
            docs.append(
                Document(
                    page_content=f"Summary: {resume['summary']}",
                    metadata={"source": "resume", "section": "summary"},
                )
            )

        # Handle experience
        if resume.get("experience"):
            for job in resume["experience"]:
                points = job.get("points", [])
                points_str = "\n".join([f"- {p}" for p in points]) if points else "No points listed"
                content = (
                    f"Company: {job.get('company', 'Unknown')}\n"
                    f"Role: {job.get('role', 'Unknown')}\n"
                    f"Dates: {job.get('dates', 'Unknown')}\n"
                    f"Responsibilities:\n{points_str}"
                )
                docs.append(
                    Document(
                        page_content=content,
                        metadata={
                            "source": "resume",
                            "section": "experience",
                            "company": job.get("company", "Unknown"),
                            "role": job.get("role", "Unknown"),
                        },
                    )
                )

        # Handle education
        if resume.get("education"):
            for edu in resume["education"]:
                content = (
                    f"Institution: {edu.get('institution', 'Unknown')}\n"
                    f"Degree: {edu.get('degree', 'Unknown')}\n"
                    f"Dates: {edu.get('dates', 'Unknown')}"
                )
                docs.append(
                    Document(
                        page_content=content,
                        metadata={
                            "source": "resume",
                            "section": "education",
                            "institution": edu.get("institution", "Unknown"),
                        },
                    )
                )

        # Handle accomplishments
        if resume.get("accomplishments"):
            for acc in resume["accomplishments"]:
                content = f"{acc.get('title', 'Accomplishment')}: {acc.get('description', '')}"
                docs.append(
                    Document(
                        page_content=content,
                        metadata={"source": "resume", "section": "accomplishments"},
                    )
                )
    else:
        logger.warning("No resume data found in unified data")

    # Process About: Chunk by section heading
    about = unified_data.get("about", {})
    if about:
        logger.info(f"Processing about data: {type(about).__name__}")

        if about.get("introduction"):
            docs.append(
                Document(
                    page_content=about["introduction"],
                    metadata={"source": "about", "section": "introduction"},
                )
            )

        if about.get("sections"):
            for section in about["sections"]:
                content = f"{section.get('heading', 'Section')}: {section.get('content', '')}"
                docs.append(
                    Document(
                        page_content=content,
                        metadata={"source": "about", "section": section.get("heading", "unknown")},
                    )
                )
    else:
        logger.warning("No about data found in unified data")

    # Process Illustrations: One document per illustration
    illustrations = unified_data.get("illustration", [])  # Note: using "illustration" not "illustrations"
    if not illustrations:
        # Try alternative key name
        illustrations = unified_data.get("illustrations", [])

    if illustrations:
        logger.info(f"Processing {len(illustrations)} illustrations")
        for img in illustrations:
            tags = ", ".join(img.get("tags", []))
            title = img.get("title", "Untitled")
            content = f"Title: {title}\nTags: {tags}"
            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "source": "illustration",
                        "file": img.get("file"),
                        "title": title,
                    },
                )
            )
    else:
        logger.warning("No illustration data found in unified data")

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
