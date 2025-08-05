import logging
from typing import Any, Dict, List, Optional

from langchain_core.retrievers import BaseRetriever

logger = logging.getLogger(__name__)


class IllustrationService:
    """Service for managing and searching illustration data using a dedicated vector retriever."""

    def __init__(self, retriever: Optional[BaseRetriever], illustrations_data: List[Dict[str, Any]]):
        """
        Args:
            retriever: A LangChain vector retriever pre-configured for illustration data.
            illustrations_data: Raw illustrations JSON data (for `get_all` and validation).
        """
        self.retriever = retriever
        self.illustrations_data = illustrations_data

    def validate_data(self):
        """Validate that the illustration data seems correct."""
        if not self.illustrations_data:
            msg = "❌ No illustrations data loaded."
            logger.warning(msg)
            return False, msg
        return True, f"✅ {len(self.illustrations_data)} illustrations loaded."

    def get_all(self) -> List[Dict[str, str]]:
        """Return all illustrations without filtering."""
        return [{"file": img["file"]} for img in self.illustrations_data if "file" in img]

    def search(self, search_term: str, top_k: int = 10) -> List[Dict[str, str]]:
        """
        Search illustrations using vector similarity.
        Args:
            search_term: The user's text query.
            top_k: The maximum number of results to return.
        Returns:
            A list of dictionaries, each with a 'file' key.
        """
        if not search_term or not isinstance(search_term, str):
            logger.warning("Invalid search term provided to illustration search.")
            return []

        logger.info(f"Vector searching illustrations for: '{search_term}'")
        try:
            # The retriever is already scoped to illustrations, so no extra filtering is needed.
            if self.retriever is None:
                logger.warning("No retriever available for illustration search")
                return []
            results = self.retriever.get_relevant_documents(search_term)

            # Extract unique file paths from the retrieved documents' metadata
            unique_files = []
            seen_files = set()
            for doc in results[:top_k]:
                file_path = doc.metadata.get("file")
                if file_path and file_path not in seen_files:
                    unique_files.append({"file": file_path})
                    seen_files.add(file_path)

            return unique_files

        except Exception as e:
            logger.error(f"Error during illustration vector search: {e}")
            return []
