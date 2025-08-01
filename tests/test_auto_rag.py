"""
Tests for core.auto_rag module.

This module contains unit tests for the AutoRAGSystem class,
ensuring that document discovery, indexing, and querying work as expected.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.core.auto_rag import AutoRAGSystem

# Mark the entire module for unit tests
pytestmark = pytest.mark.unit


@pytest.fixture
def mock_paths():
    """Fixture to create mock file paths and stats for testing."""
    mock_file_1 = MagicMock(spec=Path)
    mock_file_1.is_file.return_value = True
    mock_file_1.name = "doc1.md"
    mock_file_1.suffix = ".md"
    mock_file_1.stat.return_value = MagicMock(st_size=100, st_mtime=1672531200)
    mock_file_1.relative_to.return_value = Path("doc1.md")
    mock_file_1.configure_mock(**{"__str__.return_value": "public/doc1.md"})

    mock_file_2 = MagicMock(spec=Path)
    mock_file_2.is_file.return_value = True
    mock_file_2.name = "data.json"
    mock_file_2.suffix = ".json"
    mock_file_2.stat.return_value = MagicMock(st_size=200, st_mtime=1672617600)
    mock_file_2.relative_to.return_value = Path("data.json")
    mock_file_2.configure_mock(**{"__str__.return_value": "public/data.json"})

    return [mock_file_1, mock_file_2]


# This patch prevents the noisy index building from running during initialization tests
@patch("backend.core.auto_rag.AutoRAGSystem._load_or_build_index", MagicMock())
@patch("backend.core.auto_rag.LLAMA_INDEX_AVAILABLE", True)
@patch("backend.core.auto_rag.Anthropic")
@patch("backend.core.auto_rag.HuggingFaceEmbedding")
@patch("backend.core.auto_rag.SimpleNodeParser")
@patch("backend.core.auto_rag.Settings")
class TestAutoRAGSystem:
    """Test cases for the AutoRAGSystem class."""

    def test_initialization_no_api_key(self, mock_settings, mock_parser, mock_hf_embedding, mock_anthropic):
        """Test that the system initializes in embeddings-only mode when no API key is present."""
        # We only need to mock getenv for the ANTHROPIC_API_KEY check
        with patch("os.getenv") as mock_getenv:
            mock_getenv.return_value = None
            rag = AutoRAGSystem()
            assert rag.llm is None
            assert rag.model_name == "embeddings-only"
            mock_anthropic.assert_not_called()
            # Verify it specifically checked for the ANTHROPIC_API_KEY
            mock_getenv.assert_called_with("ANTHROPIC_API_KEY")

    def test_initialization_with_api_key(self, mock_settings, mock_parser, mock_hf_embedding, mock_anthropic):
        """Test that the system initializes the LLM when an API key is present."""
        with patch("os.getenv", return_value="DUMMY_API_KEY"):
            rag = AutoRAGSystem()
            assert rag.llm is not None
            mock_anthropic.assert_called_once()
            assert rag.model_name != "embeddings-only"

    def test_get_file_info(self, mock_settings, mock_parser, mock_hf_embedding, mock_anthropic, mock_paths):
        """Test the _get_file_info method for correct metadata extraction."""
        with (
            patch("pathlib.Path.rglob", return_value=mock_paths),
            patch("os.getenv", return_value="DUMMY_API_KEY"),
            patch("mimetypes.guess_type") as mock_guess_type,
        ):
            mock_guess_type.side_effect = [("text/markdown", None), ("application/json", None)]

            rag = AutoRAGSystem()
            file_info = rag._get_file_info()

            assert len(file_info) == 2
            assert "doc1.md" in file_info
            assert file_info["doc1.md"]["size"] == 100
            assert file_info["data.json"]["type"] == "application/json"

    def test_has_changes_no_registry(self, mock_settings, mock_parser, mock_hf_embedding, mock_anthropic):
        """Test _has_changes returns True when no registry file exists."""
        with patch("pathlib.Path.exists", return_value=False), patch("os.getenv", return_value="DUMMY_API_KEY"):
            rag = AutoRAGSystem()
            assert rag._has_changes() is True

    def test_query_no_llm(self, mock_settings, mock_parser, mock_hf_embedding, mock_anthropic):
        """Test that querying returns an appropriate message when the LLM is not available."""
        with patch("os.getenv", return_value=None):
            rag = AutoRAGSystem()
            rag.index = MagicMock()  # Mock the index to avoid building it
            response_text, source_nodes = rag.query("test question")
            assert "LLM not available" in response_text
            assert source_nodes == []  # Should return empty source nodes

    @patch("backend.core.auto_rag.VectorStoreIndex")
    def test_query_successful(
            self, mock_vector_store_index, mock_settings, mock_parser, mock_hf_embedding, mock_anthropic
    ):
        """Test a successful query call."""
        mock_query_engine = MagicMock()
        mock_response = MagicMock()
        mock_response.response = "Mocked response"
        mock_response.source_nodes = []
        mock_response.configure_mock(**{"__str__.return_value": "Mocked response"})
        mock_query_engine.query.return_value = mock_response

        mock_index_instance = MagicMock()
        mock_index_instance.as_query_engine.return_value = mock_query_engine

        with patch("os.getenv", return_value="DUMMY_API_KEY"):
            rag = AutoRAGSystem()
            rag.index = mock_index_instance

            response_text, source_nodes = rag.query("test question")

            assert response_text == "Mocked response"
            assert source_nodes == []
            mock_index_instance.as_query_engine.assert_called_once_with(similarity_top_k=5)
            mock_query_engine.query.assert_called_once_with("test question")

    def test_get_document_stats(self, mock_settings, mock_parser, mock_hf_embedding, mock_anthropic, mock_paths):
        """Test the get_document_stats method."""
        with (
            patch("pathlib.Path.rglob", return_value=mock_paths),
            patch("os.getenv", return_value="DUMMY_API_KEY"),
            patch("mimetypes.guess_type") as mock_guess_type,
        ):
            mock_guess_type.side_effect = [("text/markdown", None), ("application/json", None)]

            rag = AutoRAGSystem()
            stats = rag.get_document_stats()

            assert stats["total_files"] == 2
            assert stats["total_size"] == 300
            assert stats["file_types"]["text/markdown"] == 1
            assert stats["file_types"]["application/json"] == 1
