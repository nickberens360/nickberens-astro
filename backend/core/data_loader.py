# backend/core/data_loader.py

import json
import logging
from typing import Any, Dict, List, Tuple

from langchain.docstore.document import Document

# Get the logger instance
logger = logging.getLogger(__name__)


def load_all_documents() -> Tuple[List[Document], List[Dict[str, Any]]]:
    """
    Load structured JSON data and convert it into a list of LangChain Documents,
    chunked by logical units and enriched with metadata.
    """
    logger.info("Loading structured unified data from public/unified_data.json...")

    # Wrap file loading in a try-except block for resilience
    try:
        with open("public/unified_data.json", "r", encoding="utf-8") as f:
            unified_data = json.load(f)
    except FileNotFoundError:
        logger.critical(
            "The unified_data.json file was not found. The application cannot load its knowledge base. Please run the build script using 'python backend/scripts/build_unified_data.py'."
        )

        # Return empty data to allow the app to start in a degraded state
        return [], []
    except json.JSONDecodeError:
        logger.critical(
            "CRITICAL: The unified_data.json file is corrupted or not valid JSON. The application cannot load its knowledge base."
        )
        return [], []
    # --- END OF UPDATE ---

    docs = []
    illustrations = unified_data.get("illustrations", [])

    # Process Resume: Chunk by logical section
    resume = unified_data.get("resume", {})
    if resume:
        if resume.get("summary"):
            docs.append(
                Document(
                    page_content=f"Summary: {resume['summary']}",
                    metadata={"source": "resume", "section": "summary"},
                )
            )
        if resume.get("experience"):
            for job in resume["experience"]:
                points = job.get("points", [])
                points_str = "\n".join([f"- {p}" for p in points]) if points else "No points listed"
                content = (
                    f"Company: {job['company']}\n"
                    f"Role: {job['role']}\n"
                    f"Dates: {job['dates']}\n"
                    f"Responsibilities:\n{points_str}"
                )
                docs.append(
                    Document(
                        page_content=content,
                        metadata={
                            "source": "resume",
                            "section": "experience",
                            "company": job["company"],
                            "role": job["role"],
                        },
                    )
                )
        if resume.get("education"):
            for edu in resume["education"]:
                content = f"Institution: {edu['institution']}\n" f"Degree: {edu['degree']}\n" f"Dates: {edu['dates']}"
                docs.append(
                    Document(
                        page_content=content,
                        metadata={
                            "source": "resume",
                            "section": "education",
                            "institution": edu["institution"],
                        },
                    )
                )
        if resume.get("accomplishments"):
            for acc in resume["accomplishments"]:
                docs.append(
                    Document(
                        page_content=f"{acc['title']}: {acc['description']}",
                        metadata={"source": "resume", "section": "accomplishments"},
                    )
                )

    # Process About: Chunk by section heading
    about = unified_data.get("about", {})
    if about:
        if about.get("introduction"):
            docs.append(
                Document(
                    page_content=about["introduction"],
                    metadata={"source": "about", "section": "introduction"},
                )
            )
        if about.get("sections"):
            for section in about["sections"]:
                docs.append(
                    Document(
                        page_content=f"{section['heading']}: {section['content']}",
                        metadata={"source": "about", "section": section["heading"]},
                    )
                )

    # Process Illustrations: One document per illustration
    for img in illustrations:
        tags = ", ".join(img.get("tags", []))
        content = f"Title: {img.get('title', '')}\nTags: {tags}"
        docs.append(
            Document(
                page_content=content,
                metadata={
                    "source": "illustration",
                    "file": img.get("file"),
                    "title": img.get("title"),
                },
            )
        )

    logger.info(f"Loaded {len(docs)} logical documents from structured data.")
    return docs, illustrations
