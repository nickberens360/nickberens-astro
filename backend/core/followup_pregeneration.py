"""
Pre-generation service for follow-up questions during indexing.

This service analyzes the indexed content and generates a comprehensive set of
follow-up questions that can be served instantly during runtime.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PreGeneratedFollowups(BaseModel):
    """Schema for pre-generated follow-up questions."""

    topic_questions: Dict[str, List[str]] = Field(description="Questions by topic")
    general_questions: List[str] = Field(description="General questions about Nick")
    content_based_questions: List[str] = Field(description="Questions based on specific content")


class FollowupPreGenerator:
    """Service for pre-generating follow-up questions during indexing."""

    def __init__(self, llm: BaseLanguageModel, cache_file: str = "backend/.followup_cache.json"):
        """
        Initialize the pre-generation service.

        Args:
            llm: Language model for question generation
            cache_file: File to store pre-generated questions
        """
        self.llm = llm
        self.cache_file = Path(cache_file)
        self.parser = JsonOutputParser(pydantic_object=PreGeneratedFollowups)

        # Load existing cache if it exists
        self.followup_cache: Dict[str, Any] = self._load_cache()

        # Create the prompt for pre-generation
        self.prompt = PromptTemplate(
            template="""You are creating a comprehensive set of follow-up questions for Nick Berens' portfolio chatbot.

Based on the content analysis below, generate follow-up questions that:
1. Are directly answerable from the indexed content
2. Cover different aspects of Nick's work and experience
3. Would be valuable and interesting to users
4. Are specific enough to provide useful information

Content Analysis:
- Available Topics: {topics}
- Content Types: {content_types}
- Key Entities: {entities}
- Sample Content Snippets: {content_samples}

The knowledge base contains information about:
- Nick's work experience at Wisnet and Hillman Group
- Technical skills (Vue.js, JavaScript, frontend development)
- Creative work (illustrations, art, design)
- Projects and portfolio pieces
- Development philosophy and approach
- Contact information and resume

Generate a comprehensive set of follow-up questions organized by:
1. Topic-specific questions (technical, experience, creative, etc.)
2. General questions about Nick
3. Content-based questions derived from the actual indexed material

{format_instructions}

Response:""",
            input_variables=["topics", "content_types", "entities", "content_samples", "format_instructions"],
        )

    def analyze_and_generate(self, unified_retriever: Any) -> Dict[str, List[str]]:
        """
        Analyze indexed content and generate comprehensive follow-up questions.

        Args:
            unified_retriever: The unified retriever with indexed content

        Returns:
            Dictionary mapping question types to lists of questions
        """
        logger.info("Starting follow-up question pre-generation...")

        try:
            # Analyze the indexed content
            analysis = self._analyze_indexed_content(unified_retriever)

            # Generate a content hash for cache invalidation
            content_hash = self._generate_content_hash(analysis)

            # Check if we have cached results for this content
            if content_hash in self.followup_cache:
                logger.info("Using cached pre-generated follow-up questions")
                cached_questions = self.followup_cache[content_hash]["questions"]
                return cached_questions

            # Generate new questions using LLM
            questions = self._generate_with_llm(analysis)

            # Cache the results
            self.followup_cache[content_hash] = {"questions": questions, "analysis": analysis, "generated_at": "auto"}

            # Save cache to file
            self._save_cache()

            logger.info(f"Generated {sum(len(qs) for qs in questions.values())} follow-up questions")
            return questions

        except Exception as e:
            logger.error(f"Error in follow-up pre-generation: {e}")
            return self._get_fallback_questions()

    def _analyze_indexed_content(self, unified_retriever: Any) -> Dict[str, Any]:
        """Analyze the indexed content to understand what questions can be answered."""

        # Sample different types of queries to understand the content
        sample_queries = [
            "Nick experience",
            "Vue.js projects",
            "illustrations art",
            "technical skills",
            "development philosophy",
            "Wisnet Hillman work",
            "JavaScript frontend",
            "creative process",
            "portfolio projects",
        ]

        topics = set()
        content_types = set()
        entities = set()
        content_samples = []

        for query in sample_queries:
            try:
                # Get relevant documents for this query
                docs = unified_retriever.get_relevant_documents(query, k=5)

                for doc in docs:
                    # Extract metadata
                    if hasattr(doc, "metadata"):
                        metadata = doc.metadata

                        # Collect topics
                        if "topic" in metadata:
                            topics.add(metadata["topic"])
                        if "tags" in metadata:
                            if isinstance(metadata["tags"], list):
                                topics.update(metadata["tags"])

                        # Collect content types
                        if "content_type" in metadata:
                            content_types.add(metadata["content_type"])
                        if "source" in metadata:
                            # Infer content type from source
                            source = metadata["source"].lower()
                            if "experience" in source:
                                content_types.add("experience")
                            elif "skill" in source:
                                content_types.add("skills")
                            elif "project" in source:
                                content_types.add("projects")
                            elif "illustration" in source:
                                content_types.add("creative")

                    # Collect content samples (first 150 chars)
                    if hasattr(doc, "page_content"):
                        sample = doc.page_content[:150].strip()
                        if sample and sample not in content_samples:
                            content_samples.append(sample)

            except Exception as e:
                logger.warning(f"Error analyzing query '{query}': {e}")

        # Extract entities from content samples
        for sample in content_samples:
            # Simple entity extraction (can be enhanced)
            words = sample.split()
            for word in words:
                if word.istitle() and len(word) > 2:
                    entities.add(word)

        return {
            "topics": list(topics),
            "content_types": list(content_types),
            "entities": list(entities)[:20],  # Limit entities
            "content_samples": content_samples[:10],  # Limit samples
            "total_queries_analyzed": len(sample_queries),
        }

    def _generate_with_llm(self, analysis: Dict[str, Any]) -> Dict[str, List[str]]:
        """Generate questions using LLM based on content analysis."""

        try:
            # Format the prompt
            format_instructions = self.parser.get_format_instructions()
            prompt_value = self.prompt.format(
                topics=", ".join(analysis["topics"]),
                content_types=", ".join(analysis["content_types"]),
                entities=", ".join(analysis["entities"]),
                content_samples="\n- ".join(analysis["content_samples"]),
                format_instructions=format_instructions,
            )

            # Generate with LLM
            response = self.llm.invoke(prompt_value)

            # Parse response
            if hasattr(response, "content"):
                content = response.content
            else:
                content = str(response)

            parsed = self.parser.parse(content)

            # Convert to our format
            questions = {}

            # Topic questions
            for topic, topic_questions in parsed["topic_questions"].items():
                questions[f"topic_{topic}"] = topic_questions

            # General questions
            questions["general"] = parsed["general_questions"]

            # Content-based questions
            questions["content_based"] = parsed["content_based_questions"]

            return questions

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return self._get_fallback_questions()

    def _get_fallback_questions(self) -> Dict[str, List[str]]:
        """Get fallback questions if LLM generation fails."""
        return {
            "general": [
                "Show me Nick's illustrations",
                "Tell me about Nick's experience",
                "What technologies does Nick work with?",
                "Show me Nick's recent projects",
                "What's Nick's development philosophy?",
                "How can I contact Nick?",
            ],
            "technical": [
                "What Vue.js projects has Nick worked on?",
                "Tell me about Nick's JavaScript expertise",
                "How does Nick approach frontend architecture?",
                "What's Nick's experience with modern frameworks?",
            ],
            "experience": [
                "What did Nick accomplish at Wisnet?",
                "What's Nick working on at Hillman Group?",
                "Tell me about Nick's career progression",
                "What's been Nick's biggest career achievement?",
            ],
            "creative": [
                "Show me Nick's creative illustrations",
                "Tell me about Nick's artistic process",
                "What inspires Nick's creative work?",
                "Show me different art styles Nick has done",
            ],
        }

    def _generate_content_hash(self, analysis: Dict[str, Any]) -> str:
        """Generate a hash of the content analysis for cache invalidation."""
        # Create a stable representation of the analysis
        stable_repr = {
            "topics": sorted(analysis["topics"]),
            "content_types": sorted(analysis["content_types"]),
            "entities": sorted(analysis["entities"]),
            "sample_count": len(analysis["content_samples"]),
        }

        content_str = json.dumps(stable_repr, sort_keys=True)
        return hashlib.md5(content_str.encode()).hexdigest()[:16]

    def _load_cache(self) -> Dict[str, Any]:
        """Load existing cache from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    loaded_cache = json.load(f)
                    return loaded_cache
            except Exception as e:
                logger.warning(f"Could not load followup cache: {e}")
        return {}

    def _save_cache(self) -> None:
        """Save cache to file."""
        try:
            # Ensure directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.cache_file, "w") as f:
                json.dump(self.followup_cache, f, indent=2)

            logger.info(f"Saved followup cache to {self.cache_file}")

        except Exception as e:
            logger.error(f"Could not save followup cache: {e}")

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the current cache."""
        return {
            "cache_entries": len(self.followup_cache),
            "cache_file": str(self.cache_file),
            "cache_exists": self.cache_file.exists(),
        }
