"""Tests for core.data_loader module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from langchain.docstore.document import Document

from backend.core.data_loader import load_all_documents


class TestDataLoader:
    """Test cases for data loader module."""

    @pytest.fixture
    def sample_unified_data(self):
        """Sample unified data for testing."""
        return {
            "resume": {
                "summary": "Test summary content",
                "experience": [
                    {
                        "company": "Test Company",
                        "role": "Test Role",
                        "dates": "2023-2024",
                        "points": ["Point 1", "Point 2"],
                    }
                ],
                "education": [{"institution": "Test University", "degree": "Test Degree", "dates": "2020-2024"}],
                "accomplishments": [{"title": "Test Achievement", "description": "Test description"}],
            },
            "about": {
                "introduction": "Test introduction",
                "sections": [{"heading": "Test Heading", "content": "Test content"}],
            },
            "illustrations": [{"title": "Test Illustration", "file": "test.jpg", "tags": ["tag1", "tag2"]}],
        }

    @pytest.fixture
    def temp_unified_data_file(self, sample_unified_data):
        """Create temporary unified data file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_unified_data, f)
            return Path(f.name)

    @pytest.mark.unit
    def test_load_all_documents_success(self, temp_unified_data_file):
        """Test successful loading of documents."""
        with patch("backend.core.data_loader.config.get_unified_data_path", return_value=temp_unified_data_file):
            docs, illustrations = load_all_documents()

        # Verify we get expected number of documents
        assert len(docs) > 0
        assert len(illustrations) == 1

        # Verify illustrations data structure
        assert illustrations[0]["title"] == "Test Illustration"
        assert illustrations[0]["file"] == "test.jpg"
        assert illustrations[0]["tags"] == ["tag1", "tag2"]

        # Verify document types
        assert all(isinstance(doc, Document) for doc in docs)

        # Find specific documents and verify their content/metadata
        resume_summary_docs = [
            d for d in docs if d.metadata.get("source") == "resume" and d.metadata.get("section") == "summary"
        ]
        assert len(resume_summary_docs) == 1
        assert "Summary: Test summary content" in resume_summary_docs[0].page_content

        experience_docs = [
            d for d in docs if d.metadata.get("source") == "resume" and d.metadata.get("section") == "experience"
        ]
        assert len(experience_docs) == 1
        exp_doc = experience_docs[0]
        assert "Company: Test Company" in exp_doc.page_content
        assert "Role: Test Role" in exp_doc.page_content
        assert "Dates: 2023-2024" in exp_doc.page_content
        assert "- Point 1" in exp_doc.page_content
        assert "- Point 2" in exp_doc.page_content
        assert exp_doc.metadata["company"] == "Test Company"
        assert exp_doc.metadata["role"] == "Test Role"

        education_docs = [
            d for d in docs if d.metadata.get("source") == "resume" and d.metadata.get("section") == "education"
        ]
        assert len(education_docs) == 1
        edu_doc = education_docs[0]
        assert "Institution: Test University" in edu_doc.page_content
        assert "Degree: Test Degree" in edu_doc.page_content
        assert "Dates: 2020-2024" in edu_doc.page_content
        assert edu_doc.metadata["institution"] == "Test University"

        accomplishment_docs = [
            d for d in docs if d.metadata.get("source") == "resume" and d.metadata.get("section") == "accomplishments"
        ]
        assert len(accomplishment_docs) == 1
        acc_doc = accomplishment_docs[0]
        assert "Test Achievement: Test description" in acc_doc.page_content

        about_intro_docs = [
            d for d in docs if d.metadata.get("source") == "about" and d.metadata.get("section") == "introduction"
        ]
        assert len(about_intro_docs) == 1
        assert "Test introduction" in about_intro_docs[0].page_content

        about_section_docs = [
            d for d in docs if d.metadata.get("source") == "about" and d.metadata.get("section") == "Test Heading"
        ]
        assert len(about_section_docs) == 1
        assert "Test Heading: Test content" in about_section_docs[0].page_content

        illustration_docs = [d for d in docs if d.metadata.get("source") == "illustration"]
        assert len(illustration_docs) == 1
        ill_doc = illustration_docs[0]
        assert "Title: Test Illustration" in ill_doc.page_content
        assert "Tags: tag1, tag2" in ill_doc.page_content
        assert ill_doc.metadata["file"] == "test.jpg"
        assert ill_doc.metadata["title"] == "Test Illustration"

    @pytest.mark.unit
    def test_load_all_documents_file_not_found(self):
        """Test handling of missing unified data file."""
        with patch(
            "backend.core.data_loader.config.get_unified_data_path", return_value=Path("/nonexistent/file.json")
        ):
            docs, illustrations = load_all_documents()

        assert docs == []
        assert illustrations == []

    @pytest.mark.unit
    def test_load_all_documents_invalid_json(self):
        """Test handling of corrupted JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            temp_path = Path(f.name)

        with patch("backend.core.data_loader.config.get_unified_data_path", return_value=temp_path):
            docs, illustrations = load_all_documents()

        assert docs == []
        assert illustrations == []

    @pytest.mark.unit
    def test_load_all_documents_empty_points_array(self, temp_unified_data_file):
        """Test handling of experience with empty points array."""
        data = {
            "resume": {
                "experience": [{"company": "Test Company", "role": "Test Role", "dates": "2023-2024", "points": []}]
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)

        with patch("backend.core.data_loader.config.get_unified_data_path", return_value=temp_path):
            docs, illustrations = load_all_documents()

        experience_docs = [d for d in docs if d.metadata.get("section") == "experience"]
        assert len(experience_docs) == 1
        assert "No points listed" in experience_docs[0].page_content

    @pytest.mark.unit
    def test_load_all_documents_missing_tags(self, temp_unified_data_file):
        """Test handling of illustrations with missing tags."""
        data = {
            "illustrations": [
                {
                    "title": "Test Illustration",
                    "file": "test.jpg",
                    # tags missing
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = Path(f.name)

        with patch("backend.core.data_loader.config.get_unified_data_path", return_value=temp_path):
            docs, illustrations = load_all_documents()

        illustration_docs = [d for d in docs if d.metadata.get("source") == "illustration"]
        assert len(illustration_docs) == 1
        assert "Tags: " in illustration_docs[0].page_content  # Empty tags
