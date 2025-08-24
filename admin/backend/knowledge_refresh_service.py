"""
Knowledge base refresh service for production-ready re-indexing.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

# Add backend to path to import from main backend
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Add project root to path for relative imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from backend.core.app_initializer_v2 import initialize_app_state
    from backend.core.unified_retriever import UnifiedRetriever
except ImportError:
    # Fallback for direct imports
    from core.app_initializer_v2 import initialize_app_state
    from core.unified_retriever import UnifiedRetriever

logger = logging.getLogger(__name__)


class KnowledgeRefreshService:
    """Service for refreshing the knowledge base with production-ready features."""

    def __init__(self):
        self._current_task: Optional[asyncio.Task] = None
        self._last_refresh: Optional[datetime] = None
        self._refresh_status = "idle"  # idle, running, completed, failed
        self._refresh_progress = {"files_processed": 0, "total_files": 0, "current_file": ""}

    async def refresh_knowledge_base(self, force_reindex: bool = True) -> Dict:
        """
        Perform a production-ready knowledge base refresh.

        Args:
            force_reindex: Whether to force re-indexing of all files

        Returns:
            Dict with refresh status and metadata
        """
        if self._current_task and not self._current_task.done():
            return {
                "message": "Knowledge base refresh already in progress",
                "status": "running",
                "started_at": self._last_refresh.isoformat() if self._last_refresh else None,
                "progress": self._refresh_progress,
            }

        # Start the refresh task
        self._current_task = asyncio.create_task(self._perform_refresh(force_reindex))

        # Wait a bit to see if it starts successfully
        await asyncio.sleep(0.1)

        return {
            "message": "Knowledge base refresh started successfully",
            "status": self._refresh_status,
            "started_at": self._last_refresh.isoformat() if self._last_refresh else None,
            "progress": self._refresh_progress,
            "force_reindex": force_reindex,
        }

    async def _perform_refresh(self, force_reindex: bool = True) -> None:
        """Perform the actual refresh operation."""
        try:
            self._refresh_status = "running"
            self._last_refresh = datetime.now()
            self._refresh_progress = {"files_processed": 0, "total_files": 0, "current_file": "Initializing..."}

            logger.info("Starting knowledge base refresh...")

            # Initialize fresh application state
            logger.info("Initializing application state for refresh...")
            self._refresh_progress["current_file"] = "Initializing retriever system..."

            retrievers, illustration_service, llm = initialize_app_state()
            unified_retriever = retrievers.get("unified_retriever")

            if not unified_retriever:
                raise Exception("Failed to initialize unified retriever")

            # Get knowledge directories to index
            knowledge_dirs = [
                str(Path(__file__).parent.parent.parent / "backend" / "knowledge"),
                str(Path(__file__).parent.parent.parent / "public"),
            ]

            total_files_processed = 0
            total_chunks = 0

            for directory in knowledge_dirs:
                if not os.path.exists(directory):
                    logger.warning(f"Directory does not exist: {directory}")
                    continue

                logger.info(f"Refreshing directory: {directory}")
                self._refresh_progress["current_file"] = f"Processing {Path(directory).name}..."

                # Use the unified retriever's index_directory method
                files_processed, chunks_processed = unified_retriever.index_directory(
                    directory, force_reindex=force_reindex
                )

                total_files_processed += files_processed
                total_chunks += chunks_processed

                self._refresh_progress["files_processed"] = total_files_processed
                self._refresh_progress["total_files"] = total_files_processed

                logger.info(f"Completed indexing {directory}: {files_processed} files, {chunks_processed} chunks")

            # Refresh illustration service if needed
            if illustration_service:
                logger.info("Refreshing illustration service...")
                self._refresh_progress["current_file"] = "Refreshing illustrations..."
                # The illustration service should auto-refresh during initialization

            self._refresh_status = "completed"
            self._refresh_progress["current_file"] = "Refresh completed successfully"

            logger.info(
                f"Knowledge base refresh completed successfully: {total_files_processed} files, {total_chunks} chunks"
            )

        except Exception as e:
            logger.error(f"Knowledge base refresh failed: {str(e)}", exc_info=True)
            self._refresh_status = "failed"
            self._refresh_progress["current_file"] = f"Error: {str(e)}"
            raise

    def get_refresh_status(self) -> Dict:
        """Get the current refresh status."""
        return {
            "status": self._refresh_status,
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
            "progress": self._refresh_progress,
            "is_running": self._current_task and not self._current_task.done() if self._current_task else False,
        }

    async def wait_for_completion(self, timeout: int = 300) -> Dict:
        """Wait for the current refresh to complete with timeout."""
        if not self._current_task:
            return self.get_refresh_status()

        try:
            await asyncio.wait_for(self._current_task, timeout=timeout)
            return self.get_refresh_status()
        except asyncio.TimeoutError:
            logger.error(f"Knowledge base refresh timed out after {timeout} seconds")
            self._refresh_status = "failed"
            self._refresh_progress["current_file"] = f"Timeout after {timeout} seconds"
            return self.get_refresh_status()


# Global service instance
knowledge_refresh_service = KnowledgeRefreshService()
