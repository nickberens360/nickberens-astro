# Phase 2: Security Settings Integration

## Overview
Implement dynamic security configuration to enable real-time adjustment of rate limiting, CORS policies, session management, and authentication parameters without server restarts.

**Priority:** Critical for Production  
**Estimated Effort:** 6-8 hours  
**Risk Level:** Medium - Security-critical changes

---

## Current State

### Database Storage
- Table: `admin_settings`
- Key: `security_settings`
- Format: JSON with security configuration

### Available Security Settings
```json
{
  "enable_rate_limiting": true,
  "rate_limit_requests": 100,
  "rate_limit_window": 60,
  "enable_cors": true,
  "allowed_origins": ["http://localhost:3000", "https://nickberens.com"],
  "enable_api_keys": false,
  "require_https": true,
  "session_timeout": 86400,
  "max_login_attempts": 5,
  "lockout_duration": 300
}
```

### Current Issues
- Rate limiting uses hardcoded values in middleware
- CORS origins are hardcoded in main.py
- Session timeouts are hardcoded as 24 hours
- Login attempt limits are hardcoded as 5 attempts

---

## Implementation Plan

### Step 1: Dynamic Rate Limiting

#### 1.1 Security Middleware Enhancement
**File:** `backend/core/security_middleware.py`

**Current State Analysis:**
- Uses slowapi with hardcoded limits
- No database integration

**Changes Required:**
```python
from backend.core.settings_manager import get_settings_manager
from slowapi import Limiter
import asyncio

class DynamicSecurityMiddleware:
    def __init__(self):
        self.settings_manager = get_settings_manager()
        self._limiter_cache = {}
        self._last_update = 0
        
    async def get_rate_limiter(self):
        """Get rate limiter with current settings"""
        current_time = asyncio.get_event_loop().time()
        
        # Check cache every 60 seconds
        if current_time - self._last_update > 60:
            security_settings = self.settings_manager.get_security_settings()
            
            if security_settings.enable_rate_limiting:
                limit = f"{security_settings.rate_limit_requests}/{security_settings.rate_limit_window}second"
                self._current_limiter = Limiter(
                    key_func=self._get_client_ip,
                    default_limits=[limit]
                )
            else:
                self._current_limiter = None
                
            self._last_update = current_time
            
        return self._current_limiter
```

**Integration Points:**
- Replace hardcoded SlowAPI limits with dynamic configuration
- Add rate limit bypass for admin endpoints
- Implement IP-based tracking

### Step 2: Dynamic CORS Configuration

#### 2.1 Main Application CORS
**File:** `backend/main.py`

**Current State:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Hardcoded
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

**Changes Required:**
```python
from backend.core.settings_manager import get_settings_manager

def configure_cors_middleware(app: FastAPI):
    """Configure CORS with dynamic origins from settings"""
    settings_manager = get_settings_manager()
    security_settings = settings_manager.get_security_settings()
    
    if security_settings.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=security_settings.allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["*"],
        )
```

**Implementation:**
- Call `configure_cors_middleware(app)` during app initialization
- Add periodic CORS reconfiguration (requires app restart for now)

### Step 3: Dynamic Session Management

#### 3.1 Admin Authentication
**File:** `backend/core/admin_auth.py`

**Current State Analysis:**
- Hardcoded 24-hour session timeout
- Hardcoded 5 max login attempts

**Changes Required:**
```python
def create_session(self, user_id: str) -> str:
    """Create session with dynamic timeout"""
    settings_manager = get_settings_manager()
    security_settings = settings_manager.get_security_settings()
    
    session_data = {
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (
            datetime.utcnow() + 
            timedelta(seconds=security_settings.session_timeout)
        ).isoformat()
    }
    
    session_token = self._generate_session_token()
    self.db_manager.store_session(session_token, session_data)
    return session_token

def check_login_attempts(self, username: str) -> bool:
    """Check if user is locked out based on dynamic settings"""
    settings_manager = get_settings_manager()
    security_settings = settings_manager.get_security_settings()
    
    attempts = self.db_manager.get_failed_attempts(username)
    
    if len(attempts) >= security_settings.max_login_attempts:
        last_attempt = max(attempts, key=lambda x: x['timestamp'])
        lockout_end = datetime.fromisoformat(last_attempt['timestamp']) + \
                     timedelta(seconds=security_settings.lockout_duration)
        
        if datetime.utcnow() < lockout_end:
            return False  # Still locked out
    
    return True
```

### Step 4: HTTPS Enforcement

#### 4.1 Security Middleware Addition
**File:** `backend/core/security_middleware.py`

**New Feature:**
```python
async def https_redirect_middleware(request: Request, call_next):
    """Redirect HTTP to HTTPS if required by settings"""
    settings_manager = get_settings_manager()
    security_settings = settings_manager.get_security_settings()
    
    if security_settings.require_https and request.url.scheme == "http":
        # Skip redirect for localhost/development
        if request.client.host not in ["127.0.0.1", "localhost"]:
            https_url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(https_url), status_code=301)
    
    return await call_next(request)
```

### Step 5: API Key Authentication (Future Proofing)

#### 5.1 API Key Middleware
**File:** `backend/core/security_middleware.py`

**New Feature:**
```python
async def api_key_middleware(request: Request, call_next):
    """Check API keys if enabled in settings"""
    settings_manager = get_settings_manager()
    security_settings = settings_manager.get_security_settings()
    
    if security_settings.enable_api_keys:
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "API key required"}
            )
        
        # Validate API key (implement key validation logic)
        if not self._validate_api_key(api_key):
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid API key"}
            )
    
    return await call_next(request)
```

---

## Implementation Details

### Settings Schema Validation
**File:** `backend/core/settings_schemas.py`

Add validation for security settings:
```python
class SecuritySettings(BaseModel):
    enable_rate_limiting: bool = True
    rate_limit_requests: int = Field(default=100, ge=1, le=10000)
    rate_limit_window: int = Field(default=60, ge=1, le=3600)
    enable_cors: bool = True
    allowed_origins: List[str] = ["http://localhost:3000"]
    enable_api_keys: bool = False
    require_https: bool = True
    session_timeout: int = Field(default=86400, ge=300, le=604800)  # 5min to 7 days
    max_login_attempts: int = Field(default=5, ge=1, le=100)
    lockout_duration: int = Field(default=300, ge=60, le=86400)  # 1min to 1day
```

### Database Schema Updates
**File:** `backend/core/admin_database.py`

Add tables for security tracking:
```sql
CREATE TABLE IF NOT EXISTS failed_login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_agent TEXT
);

CREATE TABLE IF NOT EXISTS rate_limit_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    request_count INTEGER DEFAULT 1,
    window_start DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ip_address, endpoint, window_start)
);
```

---

## Testing Strategy

### Unit Tests
**File:** `tests/unit/test_security_settings.py`

```python
def test_rate_limit_disabled():
    # Mock settings to disable rate limiting
    # Verify requests are not rate limited
    pass

def test_dynamic_session_timeout():
    # Update session timeout in settings
    # Verify new sessions use new timeout
    pass

def test_cors_origins_update():
    # Update allowed origins
    # Verify CORS allows new origins (requires app restart test)
    pass

def test_login_attempt_limits():
    # Update max login attempts
    # Verify lockout triggers at new limit
    pass
```

### Security Tests
**File:** `tests/security/test_dynamic_security.py`

```python
async def test_rate_limiting_enforcement():
    # Test rate limiting works with dynamic values
    pass

async def test_session_timeout_enforcement():
    # Test sessions expire at configured time
    pass

async def test_https_redirect():
    # Test HTTPS redirect when required
    pass

async def test_lockout_duration():
    # Test user lockout lasts configured duration
    pass
```

### Load Testing
Use locust or similar to test:
- Rate limiting under load
- Session handling capacity
- Security middleware performance impact

---

## Security Considerations

### Validation Rules
- Rate limits: 1-10,000 requests per 1-3600 seconds
- Session timeout: 5 minutes to 7 days
- Max login attempts: 1-100
- Lockout duration: 1 minute to 1 day
- Origins: Must be valid URLs

### Audit Logging
All security setting changes must be logged:
```python
def update_security_settings(self, new_settings: SecuritySettings, admin_user: str):
    """Update security settings with audit logging"""
    old_settings = self.get_security_settings()
    
    # Update settings
    self._update_settings("security_settings", new_settings.dict())
    
    # Log the change
    self.audit_logger.log_security_change(
        admin_user=admin_user,
        old_settings=old_settings,
        new_settings=new_settings,
        timestamp=datetime.utcnow()
    )
```

### Fallback Behavior
- If settings unavailable: Use secure defaults
- If rate limiter fails: Allow request but log error  
- If session check fails: Require re-authentication
- If CORS fails: Deny request

---

## Files to Modify

### Security Core
- `backend/core/security_middleware.py` - Add dynamic rate limiting and HTTPS redirect
- `backend/core/admin_auth.py` - Add dynamic session and login attempt management
- `backend/main.py` - Add dynamic CORS configuration

### Database
- `backend/core/admin_database.py` - Add security tracking tables
- `backend/core/settings_schemas.py` - Add security settings validation

### Tests
- `tests/unit/test_security_settings.py` - Unit tests for security settings
- `tests/security/test_dynamic_security.py` - Security-specific integration tests
- `tests/load/test_security_performance.py` - Performance tests

---

## Monitoring & Alerts

### Metrics to Track
- Rate limit hits per endpoint
- Failed login attempts per IP
- Session timeout rates
- HTTPS redirect frequency
- Security setting change frequency

### Alert Conditions
- Sudden spike in rate limit hits
- Multiple failed logins from same IP
- Frequent security setting changes
- High number of session timeouts

---

## Rollback Plan

### Emergency Procedures
1. **Settings Rollback:** Admin UI can quickly revert to previous values
2. **Database Fallback:** Script to restore default security values
3. **Code Fallback:** All changes maintain backward compatibility
4. **Service Restart:** May be required for CORS changes

### Rollback Script
```python
# emergency_security_restore.py
def restore_default_security():
    settings_manager = get_settings_manager()
    default_security = SecuritySettings()  # Uses defaults
    settings_manager.update_security_settings(default_security, "emergency_restore")
```

---

## Success Criteria

1. **Functional:** All security settings can be changed from admin UI and take effect
2. **Performance:** Security checks add < 2ms overhead per request
3. **Security:** No security regressions introduced
4. **Auditability:** All security changes are logged and trackable
5. **Resilience:** System remains secure even if settings are unavailable

---

## Next Phase
Upon completion, proceed to **Phase 3: Response Settings Integration** for customizable response generation.