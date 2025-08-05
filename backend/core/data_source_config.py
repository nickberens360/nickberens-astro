import logging
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Optional, cast

import yaml

logger = logging.getLogger(__name__)


class DataSourceConfig:
    """Manages configuration for RAG data sources."""

    _instance: Optional["DataSourceConfig"] = None
    _config: Optional[Dict[str, Any]] = None
    _lock = RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Second check for thread-safety
                if cls._instance is None:
                    cls._instance = super(DataSourceConfig, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            with self._lock:
                # Second check for thread-safety
                if self._config is None:
                    self._load_config()

    def _load_config(self):
        """Load configuration from YAML file."""
        # Try multiple paths to find the config file
        possible_paths = [
            Path("backend/config/data_sources.yaml"),
            Path("config/data_sources.yaml"),
            Path(__file__).parent.parent / "config" / "data_sources.yaml",
        ]

        config_path = None
        for path in possible_paths:
            if path.exists():
                config_path = path
                break

        if config_path is None:
            logger.error(
                "data_sources.yaml not found in any of the expected locations. "
                "Falling back to default configuration."
            )
            self._config = self._get_default_config()
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
                logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load configuration from {config_path}: {e}")
            self._config = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration matching the original hardcoded values."""
        return {
            "data_sources": {
                "base_path": "public",
                "output_file": "unified_data.json",
                "sources": [
                    {
                        "name": "resume",
                        "file": "resume.json",
                        "sections": [
                            {"name": "summary", "field": "summary"},
                            {
                                "name": "experience",
                                "field": "experience",
                                "is_list": True,
                                "item_fields": ["company", "role", "dates", "points"],
                            },
                            {
                                "name": "education",
                                "field": "education",
                                "is_list": True,
                                "item_fields": ["institution", "degree", "dates"],
                            },
                            {
                                "name": "accomplishments",
                                "field": "accomplishments",
                                "is_list": True,
                                "item_fields": ["title", "description"],
                            },
                        ],
                    },
                    {
                        "name": "about",
                        "file": "about.json",
                        "sections": [
                            {"name": "introduction", "field": "introduction"},
                            {
                                "name": "sections",
                                "field": "sections",
                                "is_list": True,
                                "item_fields": ["heading", "content"],
                            },
                        ],
                    },
                    {
                        "name": "illustrations",
                        "file": "illustrations.json",
                        "is_list_source": True,
                        "item_fields": ["title", "file", "tags"],
                    },
                ],
            },
            "retrievers": {
                "resume": {
                    "description": "Good for answering questions about Nick's professional work experience, previous roles, job history, and technical skills.",
                    "search_kwargs": {"k": 8},
                    "keywords": [
                        "experience",
                        "job",
                        "work",
                        "skill",
                        "resume",
                        "cv",
                        "company",
                        "role",
                        "hillman",
                        "wisnet",
                        "history",
                    ],
                },
                "about": {
                    "description": "Good for answering questions about Nick's background, personal interests, and general professional philosophy.",
                    "search_kwargs": {"k": 5},
                    "keywords": ["about", "background", "who is", "philosophy", "approach"],
                },
                "illustration": {
                    "description": "Good for answering questions about Nick's art, illustrations, creative process, and artistic style.",
                    "search_kwargs": {"k": 5},
                    "keywords": ["art", "illustration", "drawing", "picture", "character", "design"],
                },
            },
            "collection": {"name_pattern": "nickberens_{source}"},
            "prompts": {
                "qa_system": (
                    "You are Nick Berens' expert digital assistant. Your role is to answer questions about his skills, experience, and work based *only* on the provided context. Speak in a helpful and professional tone."
                    "\n\n"
                    "**CRITICAL INSTRUCTIONS:**"
                    "\n"
                    "1.  **Persona:** When the user asks about 'you' or 'your' experience (e.g., 'What is your experience?'), always respond about Nick Berens in the third person (e.g., 'Nick's experience is...')."
                    "\n"
                    "2.  **Resume Requests:** If asked for the resume (e.g., 'Show me your resume'), synthesize the provided resume context into a clear, professional summary. **NEVER** state that you are an AI or do not have a resume. The user is asking for Nick's resume, and the context provided is the source for it."
                    "\n"
                    "3.  **Stick to the Context:** If the answer is not in the provided context, clearly state that the information is not available. Do not make up answers."
                    "\n"
                    "4.  **Formatting:** Use markdown, such as bullet points, to structure information like work experience or skills for readability."
                    "\n\n"
                    "**Provided Context:**\n{context}"
                ),
                "history_aware": (
                    "Given a chat history and the latest user question which might reference the chat history, "
                    "formulate a standalone question which can be understood without the chat history. "
                    "Do NOT answer the question, just reformulate it if needed and otherwise return it as is."
                ),
            },
            "templates": {
                "summary_template": "Summary: {summary}",
                "experience_template": (
                    "Company: {company}\n" "Role: {role}\n" "Dates: {dates}\n" "Responsibilities:\n{points_formatted}"
                ),
                "education_template": ("Institution: {institution}\n" "Degree: {degree}\n" "Dates: {dates}"),
                "accomplishments_template": "{title}: {description}",
                "about_introduction_template": "{introduction}",
                "about_sections_template": "{heading}: {content}",
                "illustrations_template": "Title: {title}\nTags: {tags}",
            },
            "special_processing": {
                "points": {
                    "type": "format_list",
                    "format": "bullet_points",
                    "empty_message": "No points listed",
                },
                "tags": {
                    "type": "join_array",
                    "separator": ", ",
                    "default": "",
                },
            },
        }

    @property
    def data_sources(self) -> Dict[str, Any]:
        """Get data sources configuration."""
        if self._config is None:
            return {}
        return cast(Dict[str, Any], self._config.get("data_sources", {}))

    @property
    def retrievers(self) -> Dict[str, Any]:
        """Get retrievers configuration."""
        if self._config is None:
            return {}
        return cast(Dict[str, Any], self._config.get("retrievers", {}))

    @property
    def collection_config(self) -> Dict[str, Any]:
        """Get collection configuration."""
        if self._config is None:
            return {}
        return cast(Dict[str, Any], self._config.get("collection", {}))

    @property
    def prompts(self) -> Dict[str, str]:
        """Get prompts configuration."""
        if self._config is None:
            return {}
        return cast(Dict[str, str], self._config.get("prompts", {}))

    @property
    def templates(self) -> Dict[str, str]:
        """Get content templates configuration."""
        if self._config is None:
            return {}
        return cast(Dict[str, str], self._config.get("templates", {}))

    @property
    def special_processing(self) -> Dict[str, Any]:
        """Get special processing configuration."""
        if self._config is None:
            return {}
        return cast(Dict[str, Any], self._config.get("special_processing", {}))

    def get_source_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific data source configuration by name."""
        for source in self.data_sources.get("sources", []):
            if source["name"] == name:
                return cast(Dict[str, Any], source)
        return None

    def get_unified_data_path(self) -> Path:
        """Get the full path to the unified data file."""
        data_sources = self.data_sources
        base_path = Path(cast(str, data_sources.get("base_path", "public")))
        output_file = cast(str, data_sources.get("output_file", "unified_data.json"))
        return base_path / output_file

    def get_source_file_path(self, source_name: str) -> Optional[Path]:
        """Get the full path to a source file."""
        source = self.get_source_by_name(source_name)
        if not source:
            return None
        data_sources = self.data_sources
        base_path = Path(cast(str, data_sources.get("base_path", "public")))
        return base_path / cast(str, source["file"])

    @property
    def cache_preload(self) -> Dict[str, Any]:
        """Get cache preload configuration."""
        if self._config is None:
            return {}
        return cast(Dict[str, Any], self._config.get("cache_preload", {}))


# Singleton instance
config = DataSourceConfig()
