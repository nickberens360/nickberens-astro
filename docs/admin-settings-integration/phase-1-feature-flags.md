# Phase 1: Feature Flags Integration

## Overview
Implement dynamic feature toggles throughout the backend services to enable/disable functionality based on admin settings without requiring code changes or server restarts.

**Priority:** High Impact, Quick Win  
**Estimated Effort:** 4-6 hours  
**Risk Level:** Low - Additive changes only

---

## Current State

### Database Storage
- Table: `admin_settings`
- Key: `feature_flags`
- Format: JSON with boolean values

### Available Feature Flags
```json
{
  "enable_followup_questions": true,
  "enable_smart_routing": true,
  "enable_caching": true,
  "enable_analytics": true,
  "enable_debug_mode": false,
  "enable_maintenance_mode": false,
  "enable_rate_limiting": true,
  "enable_api_versioning": false
}
```

### Current Issues
- All features are hardcoded as enabled/disabled
- No dynamic control from admin dashboard
- Settings exist in database but are unused

---

## Implementation Plan

### Step 1: Add Feature Flag Checks to Core Services

#### 1.1 Follow-up Questions Service
**File:** `backend/core/followup_service.py`

**Changes:**
```python
# Add at top of generate_followup_questions method
settings_manager = get_settings_manager()
if not settings_manager.is_feature_enabled("enable_followup_questions"):
    return []  # Return empty list when disabled
```

**Integration Points:**
- Line ~85: `generate_followup_questions()` method
- Add graceful fallback when disabled

#### 1.2 Query Router Service
**File:** `backend/core/query_router.py`

**Changes:**
```python
# Add to __init__ method
self.settings_manager = get_settings_manager()

# Add to route_query method
if not self.settings_manager.is_feature_enabled("enable_smart_routing"):
    # Fall back to simple routing
    return self._simple_route(query)
```

**Integration Points:**
- Smart routing logic
- Fallback to basic query processing

#### 1.3 Response Service
**File:** `backend/core/response_service.py`

**Changes:**
```python
# Add caching check
if self.settings_manager.is_feature_enabled("enable_caching"):
    # Use cached responses
    cached_response = self._get_cached_response(query_hash)
    if cached_response:
        return cached_response
```

**Integration Points:**
- Response caching mechanism
- Cache storage and retrieval

#### 1.4 Security Middleware
**File:** `backend/core/security_middleware.py`

**Changes:**
```python
# Add rate limiting check
settings_manager = get_settings_manager()
if settings_manager.is_feature_enabled("enable_rate_limiting"):
    # Apply rate limiting
    await self._apply_rate_limit(request)
```

**Integration Points:**
- Rate limiting middleware
- Request throttling logic

### Step 2: Add Analytics Toggle

#### 2.1 Query Logger
**File:** `backend/core/sqlite_query_logger.py`

**Changes:**
```python
def log_query(self, query_data):
    settings_manager = get_settings_manager()
    if not settings_manager.is_feature_enabled("enable_analytics"):
        return  # Skip logging when analytics disabled
    
    # Continue with normal logging
    self._store_query(query_data)
```

### Step 3: Add Debug Mode Support

#### 3.1 Logging Configuration
**File:** `backend/core/config.py`

**Changes:**
```python
def get_log_level():
    settings_manager = get_settings_manager()
    if settings_manager.is_feature_enabled("enable_debug_mode"):
        return "DEBUG"
    return os.getenv("LOG_LEVEL", "INFO")
```

### Step 4: Add Maintenance Mode

#### 4.1 Main Application
**File:** `backend/main.py`

**Changes:**
```python
@app.middleware("http")
async def maintenance_mode_middleware(request: Request, call_next):
    settings_manager = get_settings_manager()
    if settings_manager.is_feature_enabled("enable_maintenance_mode"):
        return JSONResponse(
            status_code=503,
            content={"detail": "System is under maintenance"}
        )
    return await call_next(request)
```

---

## Implementation Details

### Required Imports
Add to affected files:
```python
from backend.core.settings_manager import get_settings_manager
```

### Error Handling
```python
def check_feature_enabled(feature_name: str) -> bool:
    try:
        settings_manager = get_settings_manager()
        return settings_manager.is_feature_enabled(feature_name)
    except Exception as e:
        logger.warning(f"Failed to check feature flag {feature_name}: {e}")
        return True  # Default to enabled on error
```

### Caching Considerations
- Feature flag checks are already cached by `settings_manager` (5-minute TTL)
- No additional caching needed at service level
- Settings changes take effect within 5 minutes

---

## Testing Strategy

### Unit Tests
Create `tests/unit/test_feature_flags.py`:
```python
def test_followup_questions_disabled():
    # Mock settings manager to return False for enable_followup_questions
    # Verify followup service returns empty list
    pass

def test_smart_routing_disabled():
    # Mock settings manager to return False for enable_smart_routing
    # Verify query router uses simple routing
    pass

def test_caching_disabled():
    # Mock settings manager to return False for enable_caching
    # Verify response service skips cache
    pass
```

### Integration Tests
Create `tests/integration/test_feature_flags_integration.py`:
```python
def test_feature_flag_changes_from_admin():
    # Update feature flag via admin API
    # Verify backend behavior changes within cache TTL
    pass
```

### Manual Testing Checklist
- [ ] Disable followup questions → No followup questions generated
- [ ] Disable smart routing → Queries use basic routing
- [ ] Disable caching → Fresh responses every time
- [ ] Disable analytics → No query logs stored
- [ ] Enable debug mode → Debug logs appear
- [ ] Enable maintenance mode → 503 responses returned

---

## Rollback Plan

### If Issues Arise
1. **Database Rollback:** Update feature flags to previous values via admin UI
2. **Code Rollback:** All changes are additive with fallbacks to current behavior
3. **Emergency Disable:** Set all flags to `true` to maintain current functionality

### Monitoring
- Watch for error logs indicating feature flag failures
- Monitor response times for performance impact
- Check that disabled features actually stop working

---

## Files to Modify

### Core Services
- `backend/core/followup_service.py` - Add followup questions toggle
- `backend/core/query_router.py` - Add smart routing toggle  
- `backend/core/response_service.py` - Add caching toggle
- `backend/core/sqlite_query_logger.py` - Add analytics toggle
- `backend/core/security_middleware.py` - Add rate limiting toggle

### Configuration
- `backend/core/config.py` - Add debug mode support
- `backend/main.py` - Add maintenance mode middleware

### Tests
- `tests/unit/test_feature_flags.py` - New unit tests
- `tests/integration/test_feature_flags_integration.py` - New integration tests

---

## Success Criteria

1. **Functional:** All feature flags can be toggled from admin UI and affect backend behavior
2. **Performance:** Feature flag checks add < 1ms overhead per request
3. **Reliability:** Fallback behavior works when settings are unavailable
4. **Testability:** All feature combinations are covered by tests
5. **Documentation:** Admin users understand what each flag controls

---

## Next Phase
Upon completion, proceed to **Phase 2: Security Settings Integration** for dynamic security configuration.