import json
from langchain.docstore.document import Document
from typing import List, Tuple, Dict, Any

def load_all_documents() -> Tuple[List[Document], List[Dict[str, Any]]]:
    """
    Load structured JSON data and convert it into a list of LangChain Documents,
    chunked by logical units and enriched with metadata.
    """
    print("Loading structured unified data...")
    with open("public/unified_data.json", "r", encoding="utf-8") as f:
        unified_data = json.load(f)

    docs = []
    resume = unified_data.get("resume", {})
    about = unified_data.get("about", {})
    illustrations = unified_data.get("illustrations", [])

    # --- Process Resume: Chunk by logical section ---
    if resume.get("summary"):
        docs.append(Document(
            page_content=f"Summary: {resume['summary']}",
            metadata={"source": "resume", "section": "summary"}
        ))
    if resume.get("experience"):
        for job in resume["experience"]:
            points_str = "\n".join([f"- {p}" for p in job['points']])
            content = (
                f"Company: {job['company']}\n"
                f"Role: {job['role']}\n"
                f"Dates: {job['dates']}\n"
                f"Responsibilities:\n{points_str}"
            )
            docs.append(Document(
                page_content=content,
                metadata={
                    "source": "resume",
                    "section": "experience",
                    "company": job['company'],
                    "role": job['role']
                }
            ))
    if resume.get("education"):
        for edu in resume["education"]:
            content = (
                f"Institution: {edu['institution']}\n"
                f"Degree: {edu['degree']}\n"
                f"Dates: {edu['dates']}"
            )
            docs.append(Document(
                page_content=content,
                metadata={
                    "source": "resume",
                    "section": "education",
                    "institution": edu['institution']
                }
            ))
    if resume.get("accomplishments"):
        for acc in resume["accomplishments"]:
            docs.append(Document(
                page_content=f"{acc['title']}: {acc['description']}",
                metadata={"source": "resume", "section": "accomplishments"}
            ))

    # --- Process About: Chunk by section heading ---
    if about.get("introduction"):
        docs.append(Document(
            page_content=about["introduction"],
            metadata={"source": "about", "section": "introduction"}
        ))
    if about.get("sections"):
        for section in about["sections"]:
            docs.append(Document(
                page_content=f"{section['heading']}: {section['content']}",
                metadata={"source": "about", "section": section['heading']}
            ))

    # --- Process Illustrations: One document per illustration ---
    for img in illustrations:
        tags = ", ".join(img.get("tags", []))
        content = f"Title: {img.get('title', '')}\nTags: {tags}"
        docs.append(Document(
            page_content=content,
            metadata={
                "source": "illustration",
                "file": img.get("file"),
                "title": img.get("title")
            }
        ))

    print(f"Loaded {len(docs)} logical documents from structured data.")
    # The second return value (raw illustrations data) is kept for the IllustrationService
    return docs, illustrations