# Phase 4: Query Routing Settings Integration

## Overview
Implement configurable query routing to enable dynamic control over smart routing logic, confidence thresholds, caching behavior, and fallback strategies for optimal query processing performance.

**Priority:** Medium Impact, Performance Optimization  
**Estimated Effort:** 8-10 hours  
**Risk Level:** Medium - Core query processing changes

---

## Current State

### Database Storage
- Table: `admin_settings`
- Key: `routing_settings`
- Format: JSON with routing configuration

### Available Query Routing Settings
```json
{
  "enable_smart_routing": true,
  "fallback_strategy": "comprehensive_search",
  "confidence_threshold": 0.75,
  "enable_caching": true,
  "cache_ttl_seconds": 300,
  "max_retries": 3,
  "enable_parallel_processing": true
}
```

### Current Issues
- Query router uses hardcoded logic for all routing decisions
- No configurable confidence thresholds
- Caching behavior is hardcoded
- No fallback strategy options
- Retry logic is not configurable

---

## Implementation Plan

### Step 1: Smart Routing Configuration

#### 1.1 Query Router Enhancement
**File:** `backend/core/query_router.py`

**Current State Analysis:**
- Hardcoded routing logic
- No admin settings integration
- Static confidence thresholds

**Changes Required:**
```python
from backend.core.settings_manager import get_settings_manager
from typing import Optional, Dict, Any
import logging

class ConfigurableQueryRouter:
    def __init__(self):
        self.settings_manager = get_settings_manager()
        self.logger = logging.getLogger(__name__)
        self._routing_cache = {}
        
    def route_query(self, query: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
        """Route query with configurable logic"""
        routing_settings = self.settings_manager.get_routing_settings()
        
        if not routing_settings.enable_smart_routing:
            return self._simple_route(query, chat_history)
        
        return self._smart_route(query, chat_history, routing_settings)
    
    def _smart_route(self, query: str, chat_history: List[Dict], settings) -> Dict[str, Any]:
        """Smart routing with configurable parameters"""
        # Analyze query intent with configurable confidence threshold
        intent_analysis = self._analyze_query_intent(query)
        
        if intent_analysis["confidence"] < settings.confidence_threshold:
            self.logger.info(f"Low confidence ({intent_analysis['confidence']:.2f}), using fallback strategy")
            return self._apply_fallback_strategy(query, chat_history, settings.fallback_strategy)
        
        # Apply smart routing logic
        routing_decision = {
            "strategy": "smart",
            "intent": intent_analysis["intent"],
            "confidence": intent_analysis["confidence"],
            "topics": intent_analysis.get("topics", []),
            "enable_caching": settings.enable_caching,
            "cache_ttl": settings.cache_ttl_seconds,
            "parallel_processing": settings.enable_parallel_processing
        }
        
        return routing_decision
    
    def _apply_fallback_strategy(self, query: str, chat_history: List[Dict], strategy: str) -> Dict[str, Any]:
        """Apply configured fallback strategy"""
        fallback_strategies = {
            "comprehensive_search": self._comprehensive_search_fallback,
            "semantic_similarity": self._semantic_similarity_fallback,
            "keyword_matching": self._keyword_matching_fallback,
            "default_response": self._default_response_fallback
        }
        
        fallback_func = fallback_strategies.get(strategy, self._comprehensive_search_fallback)
        return fallback_func(query, chat_history)
    
    def _comprehensive_search_fallback(self, query: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """Comprehensive search across all content types"""
        return {
            "strategy": "comprehensive_search",
            "search_all_types": True,
            "use_semantic_similarity": True,
            "use_keyword_matching": True,
            "confidence": 0.5  # Medium confidence for fallback
        }
    
    def _semantic_similarity_fallback(self, query: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """Focus on semantic similarity matching"""
        return {
            "strategy": "semantic_similarity",
            "search_method": "semantic_only",
            "similarity_threshold": 0.6,
            "confidence": 0.6
        }
    
    def _keyword_matching_fallback(self, query: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """Focus on keyword-based matching"""
        return {
            "strategy": "keyword_matching",
            "search_method": "keyword_only",
            "use_fuzzy_matching": True,
            "confidence": 0.4
        }
```

### Step 2: Caching Configuration

#### 2.1 Retrieval Cache Management
**File:** `backend/core/unified_retriever.py`

**Changes Required:**
```python
def retrieve_with_caching(self, query: str, routing_decision: Dict[str, Any]) -> List[Dict]:
    """Retrieve with configurable caching"""
    routing_settings = self.settings_manager.get_routing_settings()
    
    if not routing_settings.enable_caching:
        return self._retrieve_fresh(query, routing_decision)
    
    # Check cache
    cache_key = self._generate_cache_key(query, routing_decision)
    cached_result = self._get_from_cache(cache_key)
    
    if cached_result and not self._is_cache_expired(cached_result, routing_settings.cache_ttl_seconds):
        self.logger.info(f"Cache hit for query: {query[:50]}...")
        return cached_result["data"]
    
    # Retrieve fresh data
    fresh_result = self._retrieve_fresh(query, routing_decision)
    
    # Cache the result
    self._store_in_cache(cache_key, fresh_result, routing_settings.cache_ttl_seconds)
    
    return fresh_result

def _is_cache_expired(self, cached_result: Dict, ttl_seconds: int) -> bool:
    """Check if cache entry is expired based on configurable TTL"""
    import time
    cache_age = time.time() - cached_result["timestamp"]
    return cache_age > ttl_seconds

def _store_in_cache(self, cache_key: str, data: List[Dict], ttl_seconds: int):
    """Store result in cache with configurable TTL"""
    import time
    cache_entry = {
        "data": data,
        "timestamp": time.time(),
        "ttl": ttl_seconds
    }
    
    self.retrieval_cache[cache_key] = cache_entry
    
    # Log cache statistics
    self.logger.debug(f"Cached result for key {cache_key}, TTL: {ttl_seconds}s")
```

### Step 3: Parallel Processing Configuration

#### 3.1 Concurrent Query Processing
**File:** `backend/core/unified_retriever.py`

**Changes Required:**
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

async def retrieve_with_parallel_processing(self, query: str, routing_decision: Dict[str, Any]) -> List[Dict]:
    """Retrieve using configurable parallel processing"""
    routing_settings = self.settings_manager.get_routing_settings()
    
    if not routing_settings.enable_parallel_processing:
        return await self._retrieve_sequential(query, routing_decision)
    
    return await self._retrieve_parallel(query, routing_decision)

async def _retrieve_parallel(self, query: str, routing_decision: Dict[str, Any]) -> List[Dict]:
    """Parallel retrieval from multiple sources"""
    tasks = []
    
    # Create retrieval tasks based on routing decision
    if routing_decision.get("search_all_types", True):
        tasks.extend([
            self._search_content_type_async("technical", query),
            self._search_content_type_async("experience", query),
            self._search_content_type_async("skills", query),
            self._search_content_type_async("about", query)
        ])
    
    # Execute tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Combine and filter results
    combined_results = []
    for result in results:
        if isinstance(result, Exception):
            self.logger.warning(f"Parallel retrieval task failed: {result}")
            continue
        
        if isinstance(result, list):
            combined_results.extend(result)
    
    return self._deduplicate_and_rank(combined_results)

async def _search_content_type_async(self, content_type: str, query: str) -> List[Dict]:
    """Async search for specific content type"""
    loop = asyncio.get_event_loop()
    
    # Run synchronous search in thread pool
    with ThreadPoolExecutor(max_workers=4) as executor:
        future = executor.submit(self._search_content_type, content_type, query)
        return await loop.run_in_executor(None, lambda: future.result())
```

### Step 4: Retry Logic Configuration

#### 4.1 Configurable Retry Mechanism
**File:** `backend/core/query_router.py`

**Changes Required:**
```python
async def route_query_with_retries(self, query: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
    """Route query with configurable retry logic"""
    routing_settings = self.settings_manager.get_routing_settings()
    max_retries = routing_settings.max_retries
    
    for attempt in range(max_retries + 1):
        try:
            result = await self._attempt_query_routing(query, chat_history)
            
            # Validate result quality
            if self._is_result_acceptable(result):
                return result
            
            if attempt < max_retries:
                self.logger.info(f"Query routing attempt {attempt + 1} produced low-quality result, retrying...")
                await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
                continue
            
            # Final attempt - return what we have
            self.logger.warning(f"All {max_retries + 1} routing attempts completed, returning best available result")
            return result
            
        except Exception as e:
            if attempt < max_retries:
                self.logger.warning(f"Query routing attempt {attempt + 1} failed: {e}, retrying...")
                await asyncio.sleep(1.0 * (attempt + 1))
                continue
            
            # Final attempt failed - use emergency fallback
            self.logger.error(f"All routing attempts failed: {e}")
            return self._emergency_fallback(query, chat_history)

def _is_result_acceptable(self, result: Dict[str, Any]) -> bool:
    """Validate if routing result meets quality standards"""
    routing_settings = self.settings_manager.get_routing_settings()
    
    # Check if confidence meets threshold
    if result.get("confidence", 0) < routing_settings.confidence_threshold:
        return False
    
    # Check if we have sufficient data
    if not result.get("topics") and not result.get("intent"):
        return False
    
    return True

def _emergency_fallback(self, query: str, chat_history: List[Dict]) -> Dict[str, Any]:
    """Emergency fallback when all retries fail"""
    return {
        "strategy": "emergency_fallback",
        "search_all_types": True,
        "use_comprehensive_search": True,
        "confidence": 0.3,
        "retry_attempted": True
    }
```

### Step 5: Query Routing Analytics

#### 5.1 Routing Performance Monitoring
**File:** `backend/core/query_router.py`

**New Feature:**
```python
def log_routing_performance(self, query: str, routing_decision: Dict[str, Any], 
                          processing_time: float, attempt_count: int):
    """Log routing performance metrics"""
    routing_settings = self.settings_manager.get_routing_settings()
    
    performance_data = {
        "query_hash": hashlib.md5(query.encode()).hexdigest()[:8],
        "routing_strategy": routing_decision.get("strategy"),
        "confidence": routing_decision.get("confidence"),
        "processing_time_ms": processing_time * 1000,
        "attempt_count": attempt_count,
        "cache_hit": routing_decision.get("cache_hit", False),
        "parallel_processing_used": routing_settings.enable_parallel_processing,
        "settings_version": self._get_settings_hash(routing_settings),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Log to query analytics
    self.query_logger.log_routing_performance(performance_data)

def _get_settings_hash(self, settings) -> str:
    """Generate hash of current routing settings for analytics"""
    import hashlib
    import json
    
    settings_str = json.dumps(settings.dict(), sort_keys=True)
    return hashlib.md5(settings_str.encode()).hexdigest()[:8]
```

---

## Implementation Details

### Settings Schema Enhancement
**File:** `backend/core/settings_schemas.py`

```python
class QueryRoutingSettings(BaseModel):
    enable_smart_routing: bool = True
    fallback_strategy: Literal[
        "comprehensive_search", 
        "semantic_similarity", 
        "keyword_matching", 
        "default_response"
    ] = "comprehensive_search"
    confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    enable_caching: bool = True
    cache_ttl_seconds: int = Field(default=300, ge=60, le=3600)  # 1min to 1hour
    max_retries: int = Field(default=3, ge=0, le=10)
    enable_parallel_processing: bool = True
```

### Performance Monitoring
```python
class RoutingPerformanceMonitor:
    def __init__(self):
        self.metrics = {
            "total_queries": 0,
            "smart_routing_success_rate": 0.0,
            "average_confidence": 0.0,
            "cache_hit_rate": 0.0,
            "average_processing_time": 0.0,
            "fallback_usage_rate": 0.0
        }
    
    def update_metrics(self, routing_data: Dict[str, Any]):
        """Update performance metrics"""
        # Update running averages and counters
        pass
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report for admin dashboard"""
        return {
            "current_metrics": self.metrics,
            "recommendations": self._generate_recommendations(),
            "optimization_suggestions": self._suggest_optimizations()
        }
```

---

## Testing Strategy

### Unit Tests
**File:** `tests/unit/test_query_routing_settings.py`

```python
def test_smart_routing_disabled():
    # Disable smart routing in settings
    # Verify simple routing is used
    pass

def test_confidence_threshold_impact():
    # Test different confidence thresholds
    # Verify fallback triggers appropriately
    pass

def test_caching_disabled():
    # Disable caching in settings
    # Verify fresh retrieval every time
    pass

def test_parallel_processing_disabled():
    # Disable parallel processing
    # Verify sequential processing is used
    pass

def test_retry_logic_configuration():
    # Test different max retry values
    # Verify retry attempts match configuration
    pass
```

### Performance Tests
**File:** `tests/performance/test_routing_performance.py`

```python
async def test_parallel_vs_sequential_performance():
    # Compare performance with parallel processing on/off
    pass

async def test_caching_performance_impact():
    # Measure performance improvement from caching
    pass

async def test_confidence_threshold_optimization():
    # Find optimal confidence threshold for query types
    pass
```

### Load Tests
```python
async def test_routing_under_load():
    # Test routing performance under concurrent load
    # Verify settings don't cause bottlenecks
    pass
```

---

## Performance Optimization

### Caching Strategy
```python
class IntelligentRoutingCache:
    def __init__(self):
        self.query_pattern_cache = {}  # Cache routing decisions by query pattern
        self.confidence_cache = {}     # Cache confidence calculations
        
    def get_cached_routing_decision(self, query_pattern: str) -> Optional[Dict]:
        """Get cached routing decision for similar query patterns"""
        return self.query_pattern_cache.get(query_pattern)
    
    def cache_routing_decision(self, query_pattern: str, decision: Dict):
        """Cache routing decision for query pattern"""
        self.query_pattern_cache[query_pattern] = decision
```

### Memory Management
```python
def cleanup_expired_cache_entries(self):
    """Clean up expired cache entries to manage memory"""
    current_time = time.time()
    
    # Clean query cache
    expired_keys = [
        key for key, entry in self.retrieval_cache.items()
        if current_time - entry["timestamp"] > entry["ttl"]
    ]
    
    for key in expired_keys:
        del self.retrieval_cache[key]
    
    self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
```

---

## Monitoring and Alerting

### Key Metrics
- Query routing success rate
- Average confidence scores
- Cache hit rates
- Processing times by routing strategy
- Fallback usage frequency
- Retry attempt rates

### Alert Conditions
- Confidence scores consistently below threshold
- High fallback usage (>20% of queries)
- Cache hit rate below 50%
- Processing times exceeding 5 seconds
- High retry rates (>10% of queries)

### Dashboard Integration
```python
@router.get("/api/admin/routing-performance")
async def get_routing_performance():
    """Get routing performance metrics for admin dashboard"""
    monitor = RoutingPerformanceMonitor()
    return monitor.get_performance_report()
```

---

## Files to Modify

### Core Query Processing
- `backend/core/query_router.py` - Add configurable routing logic
- `backend/core/unified_retriever.py` - Add configurable caching and parallel processing
- `backend/routes/query.py` - Integrate routing settings

### Settings Management
- `backend/core/settings_schemas.py` - Add routing settings validation
- `backend/core/settings_manager.py` - Add routing settings methods

### Tests
- `tests/unit/test_query_routing_settings.py` - Routing configuration unit tests
- `tests/performance/test_routing_performance.py` - Performance testing
- `tests/integration/test_routing_integration.py` - End-to-end routing tests

### Monitoring
- `backend/core/query_logger.py` - Add routing performance logging
- `backend/routes/admin.py` - Add routing performance endpoints

---

## Success Criteria

1. **Configuration:** All routing settings can be controlled from admin UI
2. **Performance:** Configurable routing improves or maintains current performance
3. **Reliability:** Fallback strategies handle edge cases gracefully
4. **Scalability:** Parallel processing improves performance under load
5. **Observability:** Routing performance is visible and measurable

---

## Risk Mitigation

### Rollback Strategy
- Keep current routing logic as "simple" fallback
- Settings validation prevents invalid configurations
- Performance monitoring detects regressions quickly
- Circuit breaker pattern for problematic routing strategies

### Gradual Deployment
1. Deploy with current settings as defaults
2. Test individual features in staging
3. Gradually enable new features in production
4. Monitor performance at each step

---

## Next Phase
Upon completion, proceed to **Phase 5: System Configuration Settings Integration** for operational settings completion.