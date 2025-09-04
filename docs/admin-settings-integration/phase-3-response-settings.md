# Phase 3: Response Settings Integration

## Overview
Implement customizable response generation to allow dynamic control over response length, style, source citations, and formatting based on admin preferences.

**Priority:** Medium Impact, User Experience  
**Estimated Effort:** 6-8 hours  
**Risk Level:** Low - Response formatting changes

---

## Current State

### Database Storage
- Table: `admin_settings`
- Key: `response_settings`
- Format: JSON with response configuration

### Available Response Settings
```json
{
  "preferred_response_length": "medium",
  "response_style": "conversational",
  "include_sources": true,
  "source_format": "numbered",
  "max_sources": 5,
  "enable_markdown": true,
  "enable_code_highlighting": true
}
```

### Current Issues
- Response service ignores all admin settings
- Response length is determined by LLM without guidance
- Source citation format is hardcoded
- Markdown rendering is always enabled

---

## Implementation Plan

### Step 1: Response Length Control

#### 1.1 LLM Chain Enhancement
**File:** `backend/core/llm_chain.py`

**Current State Analysis:**
- Uses static prompts without length guidance
- No admin setting integration

**Changes Required:**
```python
def _build_response_prompt(self, query: str, context: str) -> str:
    """Build prompt with dynamic response length guidance"""
    settings_manager = get_settings_manager()
    response_settings = settings_manager.get_response_settings()
    
    # Length guidance mapping
    length_guidance = {
        "brief": "Provide a concise, brief response in 1-2 sentences.",
        "medium": "Provide a thorough response in 2-3 paragraphs.",
        "detailed": "Provide a comprehensive, detailed response with full explanations.",
        "comprehensive": "Provide an extensive, comprehensive response covering all aspects."
    }
    
    length_instruction = length_guidance.get(
        response_settings.preferred_response_length, 
        length_guidance["medium"]
    )
    
    # Style guidance mapping
    style_guidance = {
        "professional": "Use a professional, formal tone.",
        "conversational": "Use a friendly, conversational tone.",
        "technical": "Use precise, technical language with specific details.",
        "casual": "Use a casual, relaxed tone."
    }
    
    style_instruction = style_guidance.get(
        response_settings.response_style,
        style_guidance["conversational"]
    )
    
    prompt = f"""
    Based on the following context, answer the user's question.
    
    Response Guidelines:
    - Length: {length_instruction}
    - Style: {style_instruction}
    
    Context: {context}
    Question: {query}
    
    Answer:"""
    
    return prompt
```

### Step 2: Source Citation Management

#### 2.1 Response Service Enhancement
**File:** `backend/core/response_service.py`

**Current State Analysis:**
- Hardcoded source formatting
- No limit on source count

**Changes Required:**
```python
def _format_sources(self, sources: List[Dict]) -> str:
    """Format sources based on admin settings"""
    settings_manager = get_settings_manager()
    response_settings = settings_manager.get_response_settings()
    
    if not response_settings.include_sources:
        return ""
    
    # Limit source count
    limited_sources = sources[:response_settings.max_sources]
    
    # Format based on preference
    if response_settings.source_format == "numbered":
        return self._format_numbered_sources(limited_sources)
    elif response_settings.source_format == "bulleted":
        return self._format_bulleted_sources(limited_sources)
    elif response_settings.source_format == "inline":
        return self._format_inline_sources(limited_sources)
    else:
        return self._format_numbered_sources(limited_sources)  # Default

def _format_numbered_sources(self, sources: List[Dict]) -> str:
    """Format sources as numbered list"""
    if not sources:
        return ""
    
    source_lines = ["**Sources:**"]
    for i, source in enumerate(sources, 1):
        title = source.get('title', 'Unknown Source')
        file_path = source.get('file', '')
        source_lines.append(f"{i}. {title} ({file_path})")
    
    return "\n".join(source_lines)

def _format_bulleted_sources(self, sources: List[Dict]) -> str:
    """Format sources as bulleted list"""
    if not sources:
        return ""
    
    source_lines = ["**Sources:**"]
    for source in sources:
        title = source.get('title', 'Unknown Source')
        file_path = source.get('file', '')
        source_lines.append(f"• {title} ({file_path})")
    
    return "\n".join(source_lines)

def _format_inline_sources(self, sources: List[Dict]) -> str:
    """Format sources inline"""
    if not sources:
        return ""
    
    source_names = [s.get('title', 'Unknown') for s in sources]
    return f"\n\n*Sources: {', '.join(source_names)}*"
```

### Step 3: Markdown and Code Highlighting

#### 2.2 Response Service Enhancement (continued)
**File:** `backend/core/response_service.py`

**Changes Required:**
```python
def _process_response_formatting(self, response: str) -> str:
    """Apply formatting based on admin settings"""
    settings_manager = get_settings_manager()
    response_settings = settings_manager.get_response_settings()
    
    # Skip markdown processing if disabled
    if not response_settings.enable_markdown:
        # Strip markdown syntax for plain text
        response = self._strip_markdown(response)
    
    # Handle code highlighting preference
    if not response_settings.enable_code_highlighting:
        # Convert code blocks to plain text blocks
        response = self._strip_code_highlighting(response)
    
    return response

def _strip_markdown(self, text: str) -> str:
    """Remove markdown formatting for plain text output"""
    import re
    
    # Remove headers
    text = re.sub(r'^#{1,6}\s+(.+)$', r'\1', text, flags=re.MULTILINE)
    
    # Remove bold/italic
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    
    # Remove links
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '[Code Block]', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    
    return text

def _strip_code_highlighting(self, text: str) -> str:
    """Remove code highlighting while keeping code blocks"""
    import re
    
    # Convert highlighted code blocks to plain code blocks
    text = re.sub(r'```\w+\n([\s\S]*?)```', r'```\n\1```', text)
    
    return text
```

### Step 4: Response Pipeline Integration

#### 4.1 Main Query Handler
**File:** `backend/routes/query.py`

**Changes Required:**
```python
async def process_query_response(query_data: dict) -> dict:
    """Process query with response settings"""
    # ... existing query processing ...
    
    # Apply response settings during processing
    response_service = ResponseService()
    
    # Generate response with settings
    formatted_response = response_service.process_response(
        raw_response=llm_response,
        sources=retrieved_sources,
        query=query_data["question"]
    )
    
    return {
        "response": formatted_response,
        "sources": response_service.get_formatted_sources(),
        "metadata": {
            "response_settings_applied": True,
            "settings_version": response_service.get_settings_version()
        }
    }
```

### Step 5: Response Validation and Quality Control

#### 5.1 Response Validator
**File:** `backend/core/response_service.py`

**New Feature:**
```python
def validate_response_quality(self, response: str, query: str) -> Dict[str, Any]:
    """Validate response meets quality standards"""
    settings_manager = get_settings_manager()
    response_settings = settings_manager.get_response_settings()
    
    validation_results = {
        "meets_length_requirement": self._check_length_requirement(
            response, response_settings.preferred_response_length
        ),
        "has_appropriate_sources": self._check_source_requirement(
            response, response_settings.include_sources
        ),
        "follows_style_guidelines": self._check_style_adherence(
            response, response_settings.response_style
        ),
        "quality_score": 0.0
    }
    
    # Calculate overall quality score
    validation_results["quality_score"] = sum([
        validation_results["meets_length_requirement"],
        validation_results["has_appropriate_sources"],
        validation_results["follows_style_guidelines"]
    ]) / 3.0
    
    return validation_results

def _check_length_requirement(self, response: str, target_length: str) -> float:
    """Check if response meets length requirement"""
    word_count = len(response.split())
    
    length_targets = {
        "brief": (10, 50),      # 10-50 words
        "medium": (50, 200),    # 50-200 words
        "detailed": (200, 500), # 200-500 words
        "comprehensive": (500, 1000)  # 500+ words
    }
    
    min_words, max_words = length_targets.get(target_length, (50, 200))
    
    if min_words <= word_count <= max_words:
        return 1.0
    elif word_count < min_words:
        return max(0.0, word_count / min_words)
    else:
        return max(0.5, min_words / word_count)
```

---

## Implementation Details

### Settings Schema Enhancement
**File:** `backend/core/settings_schemas.py`

```python
class ResponseSettings(BaseModel):
    preferred_response_length: Literal["brief", "medium", "detailed", "comprehensive"] = "medium"
    response_style: Literal["professional", "conversational", "technical", "casual"] = "conversational"
    include_sources: bool = True
    source_format: Literal["numbered", "bulleted", "inline"] = "numbered"
    max_sources: int = Field(default=5, ge=0, le=20)
    enable_markdown: bool = True
    enable_code_highlighting: bool = True
```

### Caching Integration
```python
def get_response_settings(self) -> ResponseSettings:
    """Get response settings with caching"""
    cache_key = "response_settings"
    cached_settings = self._settings_cache.get(cache_key)
    
    if cached_settings and not self._is_cache_expired(cache_key):
        return ResponseSettings(**cached_settings)
    
    # Fetch from database
    settings_data = self.db_manager.get_admin_setting("response_settings")
    if settings_data:
        response_settings = ResponseSettings(**settings_data)
    else:
        response_settings = ResponseSettings()  # Use defaults
    
    # Cache for 5 minutes
    self._settings_cache[cache_key] = response_settings.dict()
    self._cache_timestamps[cache_key] = time.time()
    
    return response_settings
```

---

## Testing Strategy

### Unit Tests
**File:** `tests/unit/test_response_settings.py`

```python
def test_response_length_brief():
    # Mock settings for brief responses
    # Verify responses are 1-2 sentences
    pass

def test_source_formatting_numbered():
    # Test numbered source formatting
    # Verify sources appear as numbered list
    pass

def test_source_limit_respected():
    # Test max_sources limit
    # Verify only specified number of sources included
    pass

def test_markdown_disabled():
    # Disable markdown in settings
    # Verify response has no markdown formatting
    pass

def test_code_highlighting_disabled():
    # Disable code highlighting
    # Verify code blocks have no language specification
    pass
```

### Integration Tests
**File:** `tests/integration/test_response_formatting.py`

```python
async def test_end_to_end_response_formatting():
    # Update response settings via admin API
    # Send query and verify response follows new settings
    pass

async def test_response_quality_validation():
    # Test various response quality scenarios
    # Verify quality scores are calculated correctly
    pass
```

### A/B Testing Framework
```python
def test_response_settings_impact():
    # Test different settings combinations
    # Measure user satisfaction or response quality
    # Provide recommendations for optimal settings
    pass
```

---

## Performance Considerations

### Response Generation Impact
- Length guidance may increase LLM processing time
- More detailed responses use more tokens
- Source formatting adds minimal overhead

### Caching Strategy
```python
class ResponseSettingsCache:
    def __init__(self):
        self.prompt_cache = {}  # Cache formatted prompts
        self.format_cache = {}  # Cache formatting functions
        
    def get_cached_prompt(self, settings_hash: str) -> Optional[str]:
        return self.prompt_cache.get(settings_hash)
        
    def cache_prompt(self, settings_hash: str, prompt: str):
        self.prompt_cache[settings_hash] = prompt
```

### Token Usage Optimization
- Brief responses save tokens
- Source limiting reduces response size
- Style guidance improves response efficiency

---

## User Experience Improvements

### Response Preview
Add endpoint for previewing response settings:
```python
@router.post("/api/admin/response-settings/preview")
async def preview_response_settings(
    settings: ResponseSettings,
    sample_query: str = "Tell me about Nick's development philosophy"
):
    """Preview how response settings affect output"""
    # Generate sample response with new settings
    # Return formatted preview
    pass
```

### Analytics Integration
Track response setting effectiveness:
```python
def log_response_metrics(self, response_data: dict, settings: ResponseSettings):
    """Log response metrics for analytics"""
    metrics = {
        "word_count": len(response_data["response"].split()),
        "source_count": len(response_data.get("sources", [])),
        "settings_used": settings.dict(),
        "quality_score": response_data.get("quality_score", 0.0),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    self.query_logger.log_response_metrics(metrics)
```

---

## Files to Modify

### Core Response Processing
- `backend/core/llm_chain.py` - Add response length and style guidance
- `backend/core/response_service.py` - Add source formatting and markdown control
- `backend/routes/query.py` - Integrate response settings into query processing

### Settings Management
- `backend/core/settings_schemas.py` - Add response settings validation
- `backend/core/settings_manager.py` - Add response settings methods

### Tests
- `tests/unit/test_response_settings.py` - Response formatting unit tests
- `tests/integration/test_response_formatting.py` - End-to-end response tests
- `tests/quality/test_response_quality.py` - Response quality validation tests

---

## Success Criteria

1. **Customization:** Response length, style, and format can be controlled from admin UI
2. **Quality:** Response quality meets or exceeds current standards across all settings
3. **Performance:** Response processing time increases by < 10% with all features enabled
4. **User Experience:** Changes to settings are reflected in responses within cache TTL
5. **Flexibility:** Settings work well across different types of queries and content

---

## Future Enhancements

### Advanced Features
- Template-based responses for common query types
- A/B testing framework for response optimization
- User feedback integration for response quality
- Dynamic response adaptation based on query complexity

### Machine Learning Integration
- Response quality scoring models
- Automatic setting optimization based on user interactions
- Personalized response preferences

---

## Next Phase
Upon completion, proceed to **Phase 4: Query Routing Settings Integration** for optimized query handling.