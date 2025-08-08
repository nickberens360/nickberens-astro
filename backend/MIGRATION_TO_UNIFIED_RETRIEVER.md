# Migration Guide: From Manual Retrievers to Unified Retriever System

## Overview
This guide explains how to migrate from the current manual retriever configuration to the new unified, auto-discovery retriever system.

## Benefits of the New System

1. **No Manual Configuration**: Automatically discovers and indexes all content
2. **Intelligent Routing**: Uses semantic analysis to route queries to relevant content
3. **Better Performance**: Single vector store with efficient filtering
4. **Easier Maintenance**: Add new content without updating configuration
5. **Smarter Context Selection**: Post-processing ensures quality responses

## Migration Steps

### 1. Update Imports in main.py

```python
# Old
from .core.app_initializer import initialize_app_state

# New
from .core.app_initializer_v2 import initialize_app_state
```

**Note**: This change has already been made in your codebase!

### 2. Update Query Handling

The new system is backward compatible, but you can optionally update to use the smart query handler:

```python
# In your query endpoint
from .core.smart_query_handler import SmartQueryHandler
from .core.app_initializer_v2 import get_unified_retriever

# Get the unified retriever
unified_retriever = get_unified_retriever(all_retrievers)
smart_handler = SmartQueryHandler(unified_retriever)

# Use it for queries
relevant_docs = smart_handler.get_relevant_context(query)
```

### 3. Remove Manual Configuration

You can remove or archive:
- Manual retriever definitions in `data_sources.yaml`
- Complex routing logic in query handlers
- Multiple vector store management code

### 4. Content Organization

The new system automatically discovers content, but good organization helps:

```
backend/
├── knowledge/           # All knowledge base documents
│   ├── technical/      # Technical documentation
│   ├── about/          # Personal/about content
│   └── projects/       # Project descriptions
├── public/             # JSON data files
└── docs/               # Any other documentation
```

### 5. Testing the Migration

1. **Start Fresh** (Optional but recommended for testing):
   ```bash
   rm -rf backend/.unified_chroma
   rm -rf backend/.chroma
   ```

2. **Run the Backend**:
   ```bash
   npm run backend:dev
   ```

3. **Test Queries**:
   ```bash
   # Test various query types
   curl -X POST http://localhost:8000/query \
     -H "Content-Type: application/json" \
     -d '{"question": "What is Nick's experience with frontend development?"}'
   ```

## Performance Considerations

### Caching
The new system includes built-in caching:
- Query results are cached for repeated questions
- File hashes prevent re-indexing unchanged content
- Cache size is automatically managed

### Indexing Strategy
- Initial indexing happens on startup
- Only changed files are re-indexed
- Use `force_reindex=True` to rebuild everything

### Vector Store Size
- The unified store may be larger but more efficient
- Filtering happens at query time, not store creation time
- Better deduplication reduces redundancy

## Customization Options

### 1. Add Custom Content Types

In `unified_retriever.py`, extend the `_extract_content_metadata` method:

```python
# Add your custom content type detection
if any(term in content for term in ['your', 'custom', 'terms']):
    content_types.append('your_content_type')
```

### 2. Adjust Scoring

Modify the `_post_process_documents` method to adjust relevance scoring:

```python
# Add custom scoring logic
if 'your_criteria' in doc.metadata:
    score *= 1.5  # Boost documents matching your criteria
```

### 3. Configure Search Parameters

```python
# Get retriever with custom parameters
retriever = unified_retriever.get_retriever(
    search_kwargs={"k": 10, "score_threshold": 0.6}
)
```

## Rollback Plan

If you need to rollback:

1. Change import back to original `app_initializer`
2. Restore `data_sources.yaml` configuration
3. Remove new files:
   - `unified_retriever.py`
   - `app_initializer_v2.py`
   - `smart_query_handler.py`

## FAQ

**Q: Will my existing queries still work?**
A: Yes! The new system maintains backward compatibility with the same API.

**Q: How does it handle different file types?**
A: It uses the same loaders and chunkers but applies them automatically.

**Q: Can I still have separate retrievers for different content?**
A: Yes, the system creates virtual retrievers that filter by content type.

**Q: What about performance with large datasets?**
A: The unified approach is actually more efficient due to:
- Single embedding computation
- Better caching
- Smarter filtering

**Q: How do I add new content sources?**
A: Just add files to any indexed directory - no configuration needed!

## Next Steps

1. Test the new system in development
2. Monitor query performance and accuracy
3. Adjust content type detection as needed
4. Consider adding more sophisticated reranking
5. Implement usage analytics to improve routing