# backend/core/auto_rag.py

import json
import logging
import mimetypes
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from llama_index.core import (
        Document,
        Settings,
        SimpleDirectoryReader,
        StorageContext,
        VectorStoreIndex,
        load_index_from_storage,
    )
    from llama_index.core.base.response.schema import RESPONSE_TYPE
    from llama_index.core.node_parser import SimpleNodeParser

    # Keep using HuggingFace embeddings but optimize the model choice
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from llama_index.llms.anthropic import Anthropic

    LLAMA_INDEX_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LlamaIndex not installed: {e}")
    logger.warning(
        "Install with: pip install llama-index-core llama-index-llms-anthropic llama-index-embeddings-huggingface"
    )
    LLAMA_INDEX_AVAILABLE = False
    # Add a placeholder for the missing type
    RESPONSE_TYPE = Any


class AutoRAGSystem:
    """
    Zero-configuration RAG system that automatically discovers,
    processes, and indexes any document type in the public directory.
    """

    def __init__(self, data_dir: str = "public", cache_dir: str = ".rag_cache"):
        if not LLAMA_INDEX_AVAILABLE:
            raise ImportError(
                "LlamaIndex is required. Install with: "
                "pip install llama-index-core llama-index-llms-anthropic llama-index-embeddings-huggingface"
            )

        # Handle relative paths when running from different directories
        if not Path(data_dir).is_absolute():
            # Try current directory first
            if Path(data_dir).exists():
                self.data_dir = Path(data_dir)
            # Try parent directory (for when running from backend/)
            elif (Path("..") / data_dir).exists():
                self.data_dir = Path("..") / data_dir
                logger.info(f"📁 Using data directory: {self.data_dir.absolute()}")
            else:
                self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(data_dir)

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # Track file changes for auto-refresh
        self.file_registry = self.cache_dir / "file_registry.json"
        self.index_cache = self.cache_dir / "vector_index"

        # Initialize components using new Settings API
        try:
            # Check for API key first
            import os

            if not os.getenv("ANTHROPIC_API_KEY"):
                logger.warning("⚠️ ANTHROPIC_API_KEY not set - using embeddings only")
                self.llm = None
                self.model_name = "embeddings-only"
            else:
                # Use the model from config if available
                try:
                    from backend.core.config import AppConfig

                    model_name = AppConfig.CLAUDE_MODEL
                except ImportError:
                    model_name = "claude-3-5-sonnet-20240620"

                self.llm = Anthropic(model=model_name)
                self.model_name = model_name
                logger.info(f"🤖 Using Claude model: {model_name}")

            # Use a smaller, faster embedding model to reduce Docker image size
            # all-MiniLM-L6-v2 is only ~90MB vs larger models that can be 1GB+
            self.embed_model = HuggingFaceEmbedding(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                device="cpu",  # Explicitly use CPU to avoid CUDA dependencies
            )
            logger.info("🔤 Using lightweight HuggingFace embeddings (all-MiniLM-L6-v2)")

            # Set global settings
            if self.llm:
                Settings.llm = self.llm
            Settings.embed_model = self.embed_model
            Settings.node_parser = SimpleNodeParser.from_defaults(chunk_size=1024, chunk_overlap=200)

        except Exception as e:
            logger.error(f"Error initializing LLM components: {e}")
            # Fallback without LLM for basic functionality
            self.llm = None
            self.model_name = "embeddings-only"

            # Try to initialize basic embeddings as fallback
            try:
                self.embed_model = HuggingFaceEmbedding(
                    model_name="sentence-transformers/all-MiniLM-L6-v2", device="cpu"
                )
                Settings.embed_model = self.embed_model
                Settings.node_parser = SimpleNodeParser.from_defaults(chunk_size=1024, chunk_overlap=200)
            except Exception as fallback_error:
                logger.error(f"Failed to initialize even fallback embeddings: {fallback_error}")
                raise

        self.index: Optional[VectorStoreIndex] = None
        self._load_or_build_index()

    def _get_file_info(self) -> Dict[str, Dict[str, Any]]:
        """Scan directory and get file metadata for change detection."""
        file_info: Dict[str, Dict[str, Any]] = {}

        if not self.data_dir.exists():
            logger.warning(f"Data directory {self.data_dir} does not exist")
            return file_info

        for file_path in self.data_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                try:
                    stat = file_path.stat()
                    relative_path = str(file_path.relative_to(self.data_dir))

                    file_info[relative_path] = {
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "type": mimetypes.guess_type(file_path)[0] or "unknown",
                    }
                except Exception as e:
                    logger.warning(f"Error reading file {file_path}: {e}")

        return file_info

    def _has_changes(self) -> bool:
        """Check if any files have changed since last indexing."""
        if not self.file_registry.exists():
            return True

        try:
            with open(self.file_registry, "r", encoding="utf-8") as f:
                old_registry = json.load(f)
        except Exception:
            return True

        current_registry = self._get_file_info()
        return bool(old_registry != current_registry)

    def _save_registry(self):
        """Save current file registry for change detection."""
        current_registry = self._get_file_info()
        try:
            with open(self.file_registry, "w", encoding="utf-8") as f:
                json.dump(current_registry, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving file registry: {e}")

    def _load_documents_simple(self) -> List[Document]:
        """Fallback document loader using basic file reading."""
        documents: List[Document] = []

        if not self.data_dir.exists():
            return documents

        for file_path in self.data_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                try:
                    if file_path.suffix.lower() in [".json", ".txt", ".md", ".csv", ".docx"]:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()

                        # Special handling for JSON files
                        if file_path.suffix.lower() == ".json":
                            try:
                                data = json.loads(content)
                                content = json.dumps(data, indent=2)
                            except json.JSONDecodeError:
                                pass  # Use raw content

                        doc = Document(
                            text=content,
                            metadata={
                                "file_path": str(file_path),
                                "file_name": file_path.name,
                                "file_type": file_path.suffix.lower(),
                                "file_size": file_path.stat().st_size,
                            },
                        )
                        documents.append(doc)

                except Exception as e:
                    logger.warning(f"Error reading {file_path}: {e}")

        return documents

    def _build_index(self) -> VectorStoreIndex:
        """Build vector index from all documents in data directory."""
        logger.info("🔍 Auto-discovering documents...")

        documents: List[Document] = []

        try:
            # Try using LlamaIndex's SimpleDirectoryReader first
            documents = SimpleDirectoryReader(
                input_dir=str(self.data_dir),
                recursive=True,
                exclude_hidden=True,
                required_exts=[".json", ".txt", ".md", ".csv", ".docx"],  # Start with basic types
            ).load_data()

            logger.info(f"📄 Discovered {len(documents)} documents using SimpleDirectoryReader")

        except Exception as e:
            logger.warning(f"SimpleDirectoryReader failed: {e}, falling back to basic loader")
            documents = self._load_documents_simple()
            logger.info(f"📄 Discovered {len(documents)} documents using fallback loader")

        if not documents:
            logger.warning("No documents found to index")
            # Create a single empty document to avoid issues with empty index
            documents = [Document(text="No documents found", metadata={"file_name": "empty"})]

        try:
            # Build index - Settings are already configured globally
            index = VectorStoreIndex.from_documents(documents)

            # Try to cache the index using atomic replacement pattern
            try:
                if self.index_cache.exists():
                    # Build in temporary directory first for atomic replacement
                    temp_cache = self.index_cache.parent / f"{self.index_cache.name}_temp"

                    # Clean up any existing temp directory
                    if temp_cache.exists():
                        shutil.rmtree(temp_cache)

                    # Persist to temporary location
                    index.storage_context.persist(persist_dir=str(temp_cache))

                    # Atomic replacement: only if persist succeeded
                    backup_cache = self.index_cache.parent / f"{self.index_cache.name}_backup"
                    if backup_cache.exists():
                        shutil.rmtree(backup_cache)
                    shutil.move(str(self.index_cache), str(backup_cache))

                    shutil.move(str(temp_cache), str(self.index_cache))

                    # Clean up backup after successful replacement
                    if backup_cache.exists():
                        shutil.rmtree(backup_cache)

                    logger.info("💾 Index cached for faster startup")
                else:
                    # First time caching - direct persist is safe
                    index.storage_context.persist(persist_dir=str(self.index_cache))
                    logger.info("💾 Index cached for faster startup")

            except Exception as e:
                logger.warning(f"Could not cache index: {e}")
                # Original cache remains intact if it existed

            return index

        except Exception as e:
            logger.error(f"Error building index: {e}")
            # Return empty index as fallback
            empty_doc = Document(text="Error building index", metadata={"file_name": "error"})
            return VectorStoreIndex.from_documents([empty_doc])

    def _load_or_build_index(self):
        """Load cached index or build new one if needed."""
        # Check if we need to rebuild
        if self._has_changes() or not self.index_cache.exists():
            logger.info("🔄 Changes detected, rebuilding index...")
            self.index = self._build_index()
            self._save_registry()
        else:
            # Try to load from cache
            try:
                storage_context = StorageContext.from_defaults(persist_dir=str(self.index_cache))
                self.index = load_index_from_storage(storage_context)
                logger.info("⚡ Loaded index from cache")
            except Exception as e:
                logger.warning(f"Error loading cached index: {e}, rebuilding...")
                self.index = self._build_index()
                self._save_registry()

    def _load_illustrations(self) -> List[Dict[str, Any]]:
        """Load illustrations from the illustrations.json file."""
        illustrations_path = Path("public/illustrations.json")
        if not illustrations_path.exists():
            logger.warning("illustrations.json not found in public directory")
            return []

        try:
            with open(illustrations_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Type check: ensure we have a list of dictionaries
            if not isinstance(data, list):
                logger.error("illustrations.json should contain a list")
                return []

            # Validate each item is a dictionary
            illustrations: List[Dict[str, Any]] = []
            for item in data:
                if isinstance(item, dict):
                    illustrations.append(item)
                else:
                    logger.warning(f"Skipping non-dictionary item in illustrations.json: {item}")

            logger.info(f"Loaded {len(illustrations)} illustrations from illustrations.json")
            return illustrations

        except Exception as e:
            logger.error(f"Error loading illustrations.json: {e}")
            return []

    def _extract_character_tags(self, illustrations: List[Dict[str, Any]]) -> List[str]:
        """Extract unique character tags from illustrations, excluding generic tags."""
        generic_tags = {
            "illustration",
            "character",
            "art",
            "artwork",
            "animal",
            "object",
            "furniture",
            "bird",
            "technology",
        }
        character_tags = set()

        for illustration in illustrations:
            tags = illustration.get("tags", [])
            for tag in tags:
                tag_lower = tag.lower()
                # Only include specific character/object names, not generic categories
                if tag_lower not in generic_tags:
                    character_tags.add(tag_lower)

        return list(character_tags)

    def _get_relevant_images(self, question: str, response_text: str) -> List[str]:
        """Get relevant image URLs with enhanced matching."""
        illustrations = self._load_illustrations()
        if not illustrations:
            return []

        question_lower = question.lower()

        # Enhanced image keywords - be more specific to avoid false positives
        image_keywords = ["image", "illustration", "picture", "photo", "visual", "graphic", "drawing", "artwork"]

        # More specific image request phrases that clearly indicate wanting to see images
        image_request_phrases = ["show me", "display", "can you show", "let me see", "view", "look at"]

        # Art/design specific terms that should only match when clearly asking for visual content
        art_design_keywords = ["art", "design"]

        # Check if this is an image-related query (but avoid false positives)
        # Skip queries that are clearly not asking for images
        if "not an image" in question_lower or "not image" in question_lower:
            return []

        # Check for explicit image requests
        has_image_keyword = any(keyword in question_lower for keyword in image_keywords)
        has_image_request_phrase = any(phrase in question_lower for phrase in image_request_phrases)

        # For art/design keywords, require them to be combined with explicit visual requests
        has_art_design_with_request = any(keyword in question_lower for keyword in art_design_keywords) and (
            has_image_request_phrase or any(word in question_lower for word in ["portfolio", "gallery", "collection"])
        )

        is_image_query = has_image_keyword or has_art_design_with_request

        if not is_image_query:
            return []

        # Check for specific character/object requests - this takes priority
        specific_characters = self._extract_character_tags(illustrations)
        has_specific_request = any(char in question_lower for char in specific_characters)

        # Special case: if query contains specific characters, treat as specific even if it has general keywords
        # This handles cases like "show me snake illustrations" correctly

        # If it has specific character requests, use strict exact tag matching
        if has_specific_request:
            relevant_images = []

            # Extract the specific character names mentioned in the query
            mentioned_characters = [char for char in specific_characters if char in question_lower]

            for illustration in illustrations:
                tags = [tag.lower() for tag in illustration.get("tags", [])]

                # Only include illustrations that have exact tag matches for the requested characters
                # This ensures we only return illustrations tagged with the specific character
                has_exact_match = any(char in tags for char in mentioned_characters)

                if has_exact_match:
                    image_url = f"/illustrations/{illustration['file']}"
                    relevant_images.append(image_url)

            return relevant_images

        # If it's a general image request (no specific characters mentioned)
        # Return ALL images
        return [f"/illustrations/{ill['file']}" for ill in illustrations]

    def query(self, question: str, **kwargs) -> Tuple[str, List[Any], List[str]]:
        """Query the auto-built knowledge base."""
        if not self.index:
            return "No documents available for querying.", [], []

        if not self.llm:
            return (
                "LLM not available - please set ANTHROPIC_API_KEY environment variable for querying capabilities.",
                [],
                [],
            )

        try:
            query_engine = self.index.as_query_engine(similarity_top_k=kwargs.get("top_k", 5))

            response: RESPONSE_TYPE = query_engine.query(question)

            # Extract source nodes
            source_nodes = response.source_nodes if hasattr(response, "source_nodes") else []

            # Get relevant images based on the query and response
            image_urls = self._get_relevant_images(question, str(response))

            # Post-process response if images are being returned
            response_text = str(response)
            if image_urls:
                # Remove negative statements about showing images
                negative_phrases = [
                    "However, I cannot actually show you the images directly. While these illustrations exist in the portfolio and are referenced in the file system (with .jpg extensions), I don't have access to display the actual image files. You would need to view these through the appropriate platform or website where they are hosted.",
                    "I cannot actually show you the images directly",
                    "I don't have access to display the actual image files",
                    "I cannot display images directly",
                    "I cannot display images",
                    "I can't show you the images",
                    "I don't have the ability to display images",
                    "but I cannot display images directly",
                    "but I cannot actually show you the images directly",
                    "However, I cannot actually show you the images directly",
                    "While these illustrations exist in the portfolio and are referenced in the file system (with .jpg extensions), I don't have access to display the actual image files",
                    "You would need to view these through the appropriate platform or website where they are hosted",
                ]

                for phrase in negative_phrases:
                    response_text = response_text.replace(phrase, "")

                # Clean up sentence fragments and incomplete sentences
                # Remove common sentence starters that are left hanging
                cleanup_patterns = [
                    "However, .",
                    "However,",
                    "But .",
                    "But,",
                    "but .",
                    "but,",
                    "While .",
                    "While,",
                    "Although .",
                    "Although,",
                    ". .",
                    ",,",
                    " ,",
                ]

                for pattern in cleanup_patterns:
                    response_text = response_text.replace(pattern, "")

                # Clean up any double spaces, multiple newlines, and trailing punctuation
                response_text = response_text.replace("  ", " ").replace("\n\n\n", "\n\n").strip()
                response_text = response_text.rstrip(". ,")

                # Add positive statement about images being shown
                if len(image_urls) == 1:
                    response_text += "\n\nI'm showing you the relevant illustration below."
                else:
                    response_text += f"\n\nI'm showing you {len(image_urls)} relevant illustrations below."

            return response_text, source_nodes, image_urls

        except Exception as e:
            logger.error(f"Error querying index: {e}")
            return f"Error processing query: {str(e)}", [], []

    def refresh(self):
        """Force refresh of the index."""
        logger.info("🔄 Forcing index refresh...")
        self.index = self._build_index()
        self._save_registry()

    def get_document_stats(self) -> Dict[str, Any]:
        """Get statistics about discovered documents."""
        file_info = self._get_file_info()

        stats: Dict[str, Any] = {
            "total_files": len(file_info),
            "file_types": {},
            "total_size": 0,
            "last_updated": datetime.now().isoformat(),
        }

        for file_data in file_info.values():
            file_type = file_data.get("type", "unknown")
            file_types_dict = stats["file_types"]
            if file_type in file_types_dict:
                file_types_dict[file_type] += 1
            else:
                file_types_dict[file_type] = 1
            stats["total_size"] += file_data.get("size", 0)

        return stats

    def get_model_name(self) -> str:
        """Get the name of the model being used."""
        return getattr(self, "model_name", "auto-rag")


# Simple factory function
def create_auto_rag() -> AutoRAGSystem:
    """Factory function to create the auto RAG system."""
    return AutoRAGSystem()


# Test function
if __name__ == "__main__":
    import sys

    try:
        rag = AutoRAGSystem()

        print("📊 Document Stats:")
        stats = rag.get_document_stats()
        print(json.dumps(stats, indent=2))

        if stats["total_files"] > 0:
            print("\n🤖 Testing Query:")
            # Fixed: Now properly unpacking all 3 return values
            text_response, nodes, image_urls = rag.query("What can you tell me about this content?")
            print("Response:", text_response)
            if nodes:
                print("\n🔍 Sources:")
                for node in nodes:
                    print(f"  - File: {node.metadata.get('file_name', 'N/A')}, Score: {node.score:.4f}")
            if image_urls:
                print(f"\n🖼️ Images: {len(image_urls)} found")
                for url in image_urls:
                    print(f"  - {url}")
        else:
            print("\n⚠️ No files found in public/ directory")
            print("Add some files to test the system!")

    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("\nInstall with:")
        print("pip install llama-index-core llama-index-llms-anthropic llama-index-embeddings-huggingface")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
