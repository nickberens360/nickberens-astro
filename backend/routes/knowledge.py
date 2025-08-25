"""
Knowledge base management API routes.

Provides endpoints for:
- Viewing indexed documents
- Managing knowledge base content
- Document statistics and analytics
"""

import logging
import os
import shutil
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class IndexedDocument(BaseModel):
    """Model for indexed document data."""

    id: str
    source: str
    content_preview: str
    content_type: str
    metadata: dict
    word_count: int


class IndexedDocumentsResponse(BaseModel):
    """Response model for indexed documents listing."""

    documents: List[IndexedDocument]
    total_count: int
    collection_name: str
    embedding_model: str


class KnowledgeStats(BaseModel):
    """Model for knowledge base statistics."""

    total_documents: int
    total_chunks: int
    unique_sources: int
    content_types: dict
    last_updated: Optional[str] = None


class SourceUpdateRequest(BaseModel):
    """Model for updating a source."""

    content_type: Optional[str] = None


@router.get("/api/knowledge/documents", response_model=IndexedDocumentsResponse)
async def get_indexed_documents(
    request: Request,
    limit: int = Query(50, ge=1, le=500, description="Maximum number of documents to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    source_filter: Optional[str] = Query(None, description="Filter by source path"),
):
    """
    Get indexed documents from the knowledge base.

    Args:
        limit: Maximum number of documents to return
        offset: Offset for pagination
        content_type: Optional filter by content type
        source_filter: Optional filter by source path
    """
    try:
        # Get the unified retriever from the app state
        if not hasattr(request.app.state, "unified_retriever"):
            raise HTTPException(status_code=503, detail="Knowledge base not initialized")

        retriever = request.app.state.unified_retriever

        # Access the vector store through the semantic_searcher component
        if not hasattr(retriever, "semantic_searcher") or not retriever.semantic_searcher:
            raise HTTPException(status_code=503, detail="Semantic searcher not available")

        if not retriever.semantic_searcher.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")

        # Get the collection from the vector store
        try:
            collection = retriever.semantic_searcher.vector_store._collection
        except Exception as e:
            logger.error(f"Failed to get collection: {e}")
            raise HTTPException(status_code=503, detail="Collection not available")

        # Build query filter
        where_clause = {}
        if content_type:
            where_clause["content_type"] = content_type
        if source_filter:
            where_clause["source"] = {"$contains": source_filter}

        # Get documents with pagination
        if where_clause:
            results = collection.get(where=where_clause, limit=limit, offset=offset, include=["metadatas", "documents"])
        else:
            results = collection.get(limit=limit, offset=offset, include=["metadatas", "documents"])

        # Format documents for response
        documents = []
        if results and results.get("ids"):
            for i, doc_id in enumerate(results["ids"]):
                content = results["documents"][i] if results.get("documents") else ""
                metadata = results["metadatas"][i] if results.get("metadatas") else {}

                # Create content preview (first 200 characters)
                preview = content[:200] + "..." if len(content) > 200 else content

                documents.append(
                    IndexedDocument(
                        id=doc_id,
                        source=metadata.get("source", "unknown"),
                        content_preview=preview,
                        content_type=metadata.get("content_type", "unknown"),
                        metadata=metadata,
                        word_count=len(content.split()) if content else 0,
                    )
                )

        # Get total count
        all_docs = collection.get(include=["metadatas"])
        total_count = len(all_docs["ids"]) if all_docs and all_docs.get("ids") else 0

        # Get collection info
        collection_name = "unified_knowledge"  # This is hardcoded in SemanticSearcher
        embedding_model = "text-embedding-3-small"  # Default embedding model from config

        return IndexedDocumentsResponse(
            documents=documents,
            total_count=total_count,
            collection_name=collection_name,
            embedding_model=embedding_model,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_indexed_documents: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/api/knowledge/stats", response_model=KnowledgeStats)
async def get_knowledge_stats(request: Request):
    """
    Get statistics about the knowledge base.
    """
    try:
        # Get the unified retriever from the app state
        if not hasattr(request.app.state, "unified_retriever"):
            raise HTTPException(status_code=503, detail="Knowledge base not initialized")

        retriever = request.app.state.unified_retriever

        # Access the vector store through the semantic_searcher component
        if not hasattr(retriever, "semantic_searcher") or not retriever.semantic_searcher:
            raise HTTPException(status_code=503, detail="Semantic searcher not available")

        if not retriever.semantic_searcher.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")

        # Get the collection from the vector store
        try:
            collection = retriever.semantic_searcher.vector_store._collection
        except Exception as e:
            logger.error(f"Failed to get collection: {e}")
            raise HTTPException(status_code=503, detail="Collection not available")

        # Get all documents metadata
        all_docs = collection.get(include=["metadatas"])

        if not all_docs or not all_docs.get("ids"):
            return KnowledgeStats(total_documents=0, total_chunks=0, unique_sources=0, content_types={})

        # Calculate statistics
        total_chunks = len(all_docs["ids"])

        # Count unique sources and content types
        sources = set()
        content_types = {}

        for metadata in all_docs["metadatas"]:
            if metadata:
                source = metadata.get("source", "unknown")
                sources.add(source)

                ct = metadata.get("content_type", "unknown")
                content_types[ct] = content_types.get(ct, 0) + 1

        return KnowledgeStats(
            total_documents=len(sources),
            total_chunks=total_chunks,
            unique_sources=len(sources),
            content_types=content_types,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_knowledge_stats: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/api/knowledge/sources")
async def get_knowledge_sources(request: Request):
    """
    Get list of all unique sources in the knowledge base.
    """
    try:
        # Get the unified retriever from the app state
        if not hasattr(request.app.state, "unified_retriever"):
            raise HTTPException(status_code=503, detail="Knowledge base not initialized")

        retriever = request.app.state.unified_retriever

        # Access the vector store through the semantic_searcher component
        if not hasattr(retriever, "semantic_searcher") or not retriever.semantic_searcher:
            raise HTTPException(status_code=503, detail="Semantic searcher not available")

        if not retriever.semantic_searcher.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")

        # Get the collection from the vector store
        try:
            collection = retriever.semantic_searcher.vector_store._collection
        except Exception as e:
            logger.error(f"Failed to get collection: {e}")
            raise HTTPException(status_code=503, detail="Collection not available")

        # Get all documents metadata
        all_docs = collection.get(include=["metadatas"])

        if not all_docs or not all_docs.get("ids"):
            return {"sources": [], "total": 0}

        # Collect unique sources with counts
        source_counts = {}

        for metadata in all_docs["metadatas"]:
            if metadata:
                source = metadata.get("source", "unknown")
                content_type = metadata.get("content_type", "unknown")

                if source not in source_counts:
                    source_counts[source] = {"path": source, "content_type": content_type, "chunk_count": 0}
                source_counts[source]["chunk_count"] += 1

        # Convert to list and sort by path
        sources = list(source_counts.values())
        sources.sort(key=lambda x: x["path"])

        return {"sources": sources, "total": len(sources)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_knowledge_sources: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/api/knowledge/documents/{document_id}")
async def get_document_content(request: Request, document_id: str):
    """
    Get full content of a specific document by ID.

    Args:
        document_id: The ID of the document to retrieve

    Returns:
        Document with full content and metadata
    """
    try:
        # Get the unified retriever from the app state
        if not hasattr(request.app.state, "unified_retriever"):
            raise HTTPException(status_code=503, detail="Knowledge base not initialized")

        retriever = request.app.state.unified_retriever

        # Access the vector store through the semantic_searcher component
        if not hasattr(retriever, "semantic_searcher") or not retriever.semantic_searcher:
            raise HTTPException(status_code=503, detail="Semantic searcher not available")

        if not retriever.semantic_searcher.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")

        # Get the collection from the vector store
        try:
            collection = retriever.semantic_searcher.vector_store._collection
        except Exception as e:
            logger.error(f"Failed to get collection: {e}")
            raise HTTPException(status_code=503, detail="Collection not available")

        # Get the specific document by ID
        result = collection.get(ids=[document_id], include=["metadatas", "documents"])

        if not result or not result.get("ids") or document_id not in result["ids"]:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

        # Find the index of our document
        doc_index = result["ids"].index(document_id)

        # Extract document data
        metadata = result["metadatas"][doc_index] if result.get("metadatas") else {}
        content = result["documents"][doc_index] if result.get("documents") else ""

        # Count words
        word_count = len(content.split()) if content else 0

        return {
            "id": document_id,
            "source": metadata.get("source", "Unknown"),
            "content": content,
            "content_type": metadata.get("content_type", "unknown"),
            "metadata": metadata,
            "word_count": word_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get document content: {str(e)}")


@router.put("/api/knowledge/sources/{source_path:path}")
async def update_knowledge_source(request: Request, source_path: str, update_data: SourceUpdateRequest):
    """
    Update metadata for a knowledge source.

    Args:
        source_path: The path of the source to update
        update_data: The data to update

    Returns:
        Success message and updated source info
    """
    try:
        # Get the unified retriever from the app state
        if not hasattr(request.app.state, "unified_retriever"):
            raise HTTPException(status_code=503, detail="Knowledge base not initialized")

        retriever = request.app.state.unified_retriever

        # Access the vector store through the semantic_searcher component
        if not hasattr(retriever, "semantic_searcher") or not retriever.semantic_searcher:
            raise HTTPException(status_code=503, detail="Semantic searcher not available")

        if not retriever.semantic_searcher.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")

        # Get the collection from the vector store
        try:
            collection = retriever.semantic_searcher.vector_store._collection
        except Exception as e:
            logger.error(f"Failed to get collection: {e}")
            raise HTTPException(status_code=503, detail="Collection not available")

        # Find all documents from this source
        results = collection.get(where={"source": source_path}, include=["metadatas"])

        if not results or not results.get("ids"):
            raise HTTPException(status_code=404, detail=f"Source '{source_path}' not found")

        # Update metadata for all chunks from this source
        updated_metadatas = []
        for i, doc_id in enumerate(results["ids"]):
            metadata = results["metadatas"][i] if results.get("metadatas") else {}

            # Update the content_type if provided
            if update_data.content_type is not None:
                metadata["content_type"] = update_data.content_type

            updated_metadatas.append(metadata)

        # Update in ChromaDB
        collection.update(ids=results["ids"], metadatas=updated_metadatas)

        logger.info(f"Updated {len(results['ids'])} documents from source: {source_path}")

        return {
            "success": True,
            "message": f"Updated {len(results['ids'])} documents from source '{source_path}'",
            "updated_chunks": len(results["ids"]),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update knowledge source: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update knowledge source: {str(e)}")


@router.delete("/api/knowledge/sources/{source_path:path}")
async def delete_knowledge_source(request: Request, source_path: str):
    """
    Delete a knowledge source and all its associated chunks.

    Args:
        source_path: The path of the source to delete

    Returns:
        Success message with deletion info
    """
    try:
        # Get the unified retriever from the app state
        if not hasattr(request.app.state, "unified_retriever"):
            raise HTTPException(status_code=503, detail="Knowledge base not initialized")

        retriever = request.app.state.unified_retriever

        # Access the vector store through the semantic_searcher component
        if not hasattr(retriever, "semantic_searcher") or not retriever.semantic_searcher:
            raise HTTPException(status_code=503, detail="Semantic searcher not available")

        if not retriever.semantic_searcher.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")

        # Get the collection from the vector store
        try:
            collection = retriever.semantic_searcher.vector_store._collection
        except Exception as e:
            logger.error(f"Failed to get collection: {e}")
            raise HTTPException(status_code=503, detail="Collection not available")

        # Find all documents from this source
        results = collection.get(where={"source": source_path}, include=["metadatas"])

        if not results or not results.get("ids"):
            raise HTTPException(status_code=404, detail=f"Source '{source_path}' not found")

        chunk_count = len(results["ids"])

        # Delete all chunks from this source
        collection.delete(where={"source": source_path})

        # Also try to delete the physical file if it exists in the knowledge directory
        try:
            # Construct the full file path
            knowledge_base_path = os.path.join("backend", "knowledge")
            full_path = os.path.join(knowledge_base_path, source_path)

            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"Deleted physical file: {full_path}")
                file_deleted = True
            else:
                logger.info(f"Physical file not found or not in knowledge directory: {full_path}")
                file_deleted = False
        except Exception as e:
            logger.warning(f"Could not delete physical file {source_path}: {e}")
            file_deleted = False

        logger.info(f"Deleted {chunk_count} chunks from source: {source_path}")

        return {
            "success": True,
            "message": f"Deleted source '{source_path}' with {chunk_count} chunks",
            "deleted_chunks": chunk_count,
            "file_deleted": file_deleted,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete knowledge source: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete knowledge source: {str(e)}")


@router.get("/api/knowledge/files/{file_path:path}/content")
async def get_knowledge_file_content(file_path: str):
    """
    Get the content of a specific knowledge file.

    Args:
        file_path: The path of the file to read

    Returns:
        File content and metadata
    """
    try:
        # Construct the full file path
        knowledge_base_path = os.path.join("backend", "knowledge")
        full_path = os.path.join(knowledge_base_path, file_path)

        # Security check: ensure the file is within the knowledge directory
        if not os.path.abspath(full_path).startswith(os.path.abspath(knowledge_base_path)):
            raise HTTPException(status_code=400, detail="Invalid file path")

        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail=f"File '{file_path}' not found")

        # Read file content
        try:
            with open(full_path, "r", encoding="utf-8") as file:
                content = file.read()
        except UnicodeDecodeError:
            # Try reading as binary and decode with errors
            with open(full_path, "rb") as file:
                raw_content = file.read()
                content = raw_content.decode("utf-8", errors="replace")

        # Get file stats
        file_stats = os.stat(full_path)

        return {
            "content": content,
            "path": file_path,
            "size": file_stats.st_size,
            "modified": file_stats.st_mtime,
            "readable": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to read file content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to read file content: {str(e)}")


@router.put("/api/knowledge/files/{file_path:path}/content")
async def update_knowledge_file_content(file_path: str, request: Request):
    """
    Update the content of a specific knowledge file.

    Args:
        file_path: The path of the file to update
        request: Request containing the new content

    Returns:
        Success message
    """
    try:
        # Parse request body
        body = await request.json()
        new_content = body.get("content", "")

        # Construct the full file path
        knowledge_base_path = os.path.join("backend", "knowledge")
        full_path = os.path.join(knowledge_base_path, file_path)

        # Security check: ensure the file is within the knowledge directory
        if not os.path.abspath(full_path).startswith(os.path.abspath(knowledge_base_path)):
            raise HTTPException(status_code=400, detail="Invalid file path")

        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail=f"File '{file_path}' not found")

        # Create backup of original file
        backup_path = full_path + ".backup"
        if os.path.exists(full_path):
            shutil.copy2(full_path, backup_path)

        # Write new content
        try:
            with open(full_path, "w", encoding="utf-8") as file:
                file.write(new_content)
        except Exception as write_error:
            # Restore backup if write failed
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, full_path)
            raise write_error
        finally:
            # Remove backup file
            if os.path.exists(backup_path):
                os.remove(backup_path)

        logger.info(f"Updated file content: {file_path}")

        # Trigger re-indexing of the updated file
        try:
            if hasattr(request.app.state, "unified_retriever"):
                retriever = request.app.state.unified_retriever

                # Re-index the updated file using the new reindex_file method
                full_file_path = os.path.join("backend", "knowledge", file_path)
                if os.path.exists(full_file_path):
                    logger.info(f"Re-indexing updated file: {full_file_path}")
                    success = retriever.reindex_file(full_file_path)
                    if success:
                        logger.info(f"Successfully re-indexed: {full_file_path}")
                    else:
                        logger.error(f"Failed to re-index: {full_file_path}")
                else:
                    logger.warning(f"File not found for re-indexing: {full_file_path}")
            else:
                logger.warning("Unified retriever not available for re-indexing")
        except Exception as reindex_error:
            logger.error(f"Failed to re-index file {file_path}: {reindex_error}")
            # Don't fail the save operation if re-indexing fails

        return {
            "success": True,
            "message": f"File '{file_path}' updated successfully",
            "path": file_path,
            "size": len(new_content.encode("utf-8")),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update file content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update file content: {str(e)}")
