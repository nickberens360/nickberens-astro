# backend/core/auto_rag.py

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import mimetypes
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from llama_index.core import VectorStoreIndex, Document, SimpleDirectoryReader, Settings
    from llama_index.core.node_parser import SimpleNodeParser
    from llama_index.llms.anthropic import Anthropic
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    LLAMA_INDEX_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LlamaIndex not installed: {e}")
    logger.warning("Install with: pip install llama-index llama-index-llms-anthropic llama-index-embeddings-huggingface")
    LLAMA_INDEX_AVAILABLE = False


class AutoRAGSystem:
    """
    Zero-configuration RAG system that automatically discovers,
    processes, and indexes any document type in the public directory.
    """

    def __init__(self, data_dir: str = "public", cache_dir: str = ".rag_cache"):
        if not LLAMA_INDEX_AVAILABLE:
            raise ImportError(
                "LlamaIndex is required. Install with: "
                "pip install llama-index llama-index-llms-anthropic llama-index-embeddings-huggingface"
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
                    model_name = "claude-3-5-sonnet-20241022"

                self.llm = Anthropic(model=model_name)
                self.model_name = model_name
                logger.info(f"🤖 Using Claude model: {model_name}")

            self.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")

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
            self.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
            Settings.embed_model = self.embed_model
            Settings.node_parser = SimpleNodeParser.from_defaults(chunk_size=1024, chunk_overlap=200)

        self.index: Optional[VectorStoreIndex] = None
        self._load_or_build_index()

    def _get_file_info(self) -> Dict[str, Dict[str, Any]]:
        """Scan directory and get file metadata for change detection."""
        file_info: Dict[str, Dict[str, Any]] = {}

        if not self.data_dir.exists():
            logger.warning(f"Data directory {self.data_dir} does not exist")
            return file_info

        for file_path in self.data_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith('.'):
                try:
                    stat = file_path.stat()
                    relative_path = str(file_path.relative_to(self.data_dir))

                    file_info[relative_path] = {
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "type": mimetypes.guess_type(file_path)[0] or "unknown"
                    }
                except Exception as e:
                    logger.warning(f"Error reading file {file_path}: {e}")

        return file_info

    def _has_changes(self) -> bool:
        """Check if any files have changed since last indexing."""
        if not self.file_registry.exists():
            return True

        try:
            with open(self.file_registry, 'r') as f:
                old_registry = json.load(f)
        except Exception:
            return True

        current_registry = self._get_file_info()
        return bool(old_registry != current_registry)

    def _save_registry(self):
        """Save current file registry for change detection."""
        current_registry = self._get_file_info()
        try:
            with open(self.file_registry, 'w') as f:
                json.dump(current_registry, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving file registry: {e}")

    def _load_documents_simple(self) -> List[Document]:
        """Fallback document loader using basic file reading."""
        documents: List[Document] = []

        if not self.data_dir.exists():
            return documents

        for file_path in self.data_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith('.'):
                try:
                    if file_path.suffix.lower() in ['.json', '.txt', '.md']:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Special handling for JSON files
                        if file_path.suffix.lower() == '.json':
                            try:
                                data = json.loads(content)
                                content = json.dumps(data, indent=2)
                            except json.JSONDecodeError:
                                pass  # Use raw content

                        doc = Document(
                            text=content,
                            metadata={
                                'file_path': str(file_path),
                                'file_name': file_path.name,
                                'file_type': file_path.suffix.lower(),
                                'file_size': file_path.stat().st_size
                            }
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
                required_exts=['.json', '.txt', '.md', '.csv']  # Start with basic types
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

            # Try to cache the index
            try:
                if self.index_cache.exists():
                    import shutil
                    shutil.rmtree(self.index_cache)

                index.storage_context.persist(persist_dir=str(self.index_cache))
                logger.info("💾 Index cached for faster startup")
            except Exception as e:
                logger.warning(f"Could not cache index: {e}")

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
                from llama_index.core import load_index_from_storage, StorageContext
                storage_context = StorageContext.from_defaults(persist_dir=str(self.index_cache))
                self.index = load_index_from_storage(storage_context)
                logger.info("⚡ Loaded index from cache")
            except Exception as e:
                logger.warning(f"Error loading cached index: {e}, rebuilding...")
                self.index = self._build_index()
                self._save_registry()

    def query(self, question: str, **kwargs) -> str:
        """Query the auto-built knowledge base."""
        if not self.index:
            return "No documents available for querying."

        if not self.llm:
            return "LLM not available - please set ANTHROPIC_API_KEY environment variable for querying capabilities."

        try:
            query_engine = self.index.as_query_engine(similarity_top_k=kwargs.get('top_k', 5))

            response = query_engine.query(question)
            return str(response)

        except Exception as e:
            logger.error(f"Error querying index: {e}")
            return f"Error processing query: {str(e)}"

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
            "last_updated": datetime.now().isoformat()
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
        return getattr(self, 'model_name', 'auto-rag')


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
            response = rag.query("What can you tell me about this content?")
            print(response)
        else:
            print("\n⚠️ No files found in public/ directory")
            print("Add some files to test the system!")

    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("\nInstall with:")
        print("pip install llama-index llama-index-llms-anthropic llama-index-embeddings-huggingface")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
