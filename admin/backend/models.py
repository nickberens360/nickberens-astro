"""
Database models for the RAG admin dashboard.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class QueryLog(BaseModel):
    """Query log entry model with validation."""

    id: Optional[int] = Field(None, description="Unique query log ID")
    session_id: Optional[str] = Field(None, max_length=255, description="User session identifier")
    user_query: str = Field(..., min_length=1, max_length=10000, description="User's query text")
    system_response: Optional[str] = Field(None, max_length=50000, description="System response text")
    response_time_ms: Optional[float] = Field(None, ge=0, description="Response time in milliseconds")
    llm_provider: Optional[str] = Field(None, max_length=50, description="LLM provider name")
    llm_model: Optional[str] = Field(None, max_length=100, description="LLM model name")
    vector_search_score: Optional[float] = Field(None, ge=0, le=1, description="Vector search similarity score")
    sources_used: Optional[List[str]] = Field(default_factory=list, description="List of sources used")
    follow_up_questions: Optional[List[str]] = Field(default_factory=list, description="Generated follow-up questions")
    cache_hit: bool = Field(False, description="Whether response was served from cache")
    error_occurred: bool = Field(False, description="Whether an error occurred during processing")
    error_message: Optional[str] = Field(None, max_length=2000, description="Error message if any")
    user_feedback: Optional[str] = Field(None, description="User feedback: 'helpful' or 'not_helpful'")
    timestamp: Optional[datetime] = Field(None, description="Query timestamp")
    # Location fields
    client_ip: Optional[str] = Field(None, max_length=45, description="Client IP address")
    location_city: Optional[str] = Field(None, max_length=100, description="Client city")
    location_region: Optional[str] = Field(None, max_length=100, description="Client region/state")
    location_country: Optional[str] = Field(None, max_length=100, description="Client country")
    location_country_code: Optional[str] = Field(None, max_length=2, description="Client country code")

    @validator("user_feedback")
    def validate_feedback(cls, v):
        """Validate user feedback values."""
        if v is not None and v not in ["helpful", "not_helpful"]:
            raise ValueError('Feedback must be "helpful" or "not_helpful"')
        return v

    @validator("sources_used", "follow_up_questions")
    def validate_lists(cls, v):
        """Ensure lists are not None."""
        return v or []


class UserSession(BaseModel):
    """User session model with validation."""

    id: str = Field(..., min_length=1, max_length=255, description="Session identifier")
    started_at: Optional[datetime] = Field(None, description="Session start time")
    last_active_at: Optional[datetime] = Field(None, description="Last activity time")
    total_queries: int = Field(0, ge=0, description="Total queries in session")
    user_agent: Optional[str] = Field(None, max_length=500, description="User agent string")
    ip_address: Optional[str] = Field(None, max_length=45, description="IP address")


class HourlyMetrics(BaseModel):
    """Hourly aggregated metrics model with validation."""

    id: Optional[int] = Field(None, description="Metric record ID")
    hour: datetime = Field(..., description="Hour timestamp")
    total_queries: int = Field(..., ge=0, description="Total queries in hour")
    unique_sessions: int = Field(..., ge=0, description="Unique sessions in hour")
    avg_response_time_ms: float = Field(..., ge=0, description="Average response time")
    p95_response_time_ms: float = Field(..., ge=0, description="95th percentile response time")
    cache_hit_rate: float = Field(..., ge=0, le=1, description="Cache hit rate (0-1)")
    error_rate: float = Field(..., ge=0, le=1, description="Error rate (0-1)")
    helpful_rate: float = Field(..., ge=0, le=1, description="Helpful rate (0-1)")


class ContentGap(BaseModel):
    """Content gap tracking model with validation."""

    id: Optional[int] = Field(None, description="Content gap ID")
    query_pattern: str = Field(..., min_length=1, max_length=500, description="Query pattern or theme")
    occurrence_count: int = Field(1, ge=1, description="Number of occurrences")
    avg_similarity_score: float = Field(..., ge=0, le=1, description="Average similarity score")
    first_seen: Optional[datetime] = Field(None, description="First occurrence timestamp")
    last_seen: Optional[datetime] = Field(None, description="Last occurrence timestamp")
    resolved: bool = Field(False, description="Whether gap has been resolved")


class OverviewStats(BaseModel):
    """Overview statistics response model."""

    total_queries: int
    unique_sessions: int
    avg_response_time_ms: float
    error_rate: float
    cache_hit_rate: float
    helpful_rate: float
    queries_today: int
    queries_this_week: int


class QueryResponse(BaseModel):
    """Query list response model."""

    queries: List[QueryLog]
    total: int
    page: int
    per_page: int


class PerformanceMetrics(BaseModel):
    """Performance metrics response model."""

    avg_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    total_queries: int
    error_count: int
    cache_hits: int
    cache_hit_rate: float


class TimelinePoint(BaseModel):
    """Timeline data point model."""

    timestamp: datetime
    query_count: int
    avg_response_time: float
    error_count: int
    cache_hit_rate: float


class FeedbackUpdate(BaseModel):
    """User feedback update model with validation."""

    feedback: str = Field(..., description="Feedback value")

    @validator("feedback")
    def validate_feedback(cls, v):
        """Validate feedback values."""
        if v not in ["helpful", "not_helpful"]:
            raise ValueError('Feedback must be "helpful" or "not_helpful"')
        return v


class FileContentUpdate(BaseModel):
    """File content update model with validation."""

    content: str = Field(..., max_length=1_000_000, description="File content (max 1MB)")


class AdminUser(BaseModel):
    """Admin user model with validation."""

    id: Optional[int] = Field(None, description="User ID")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: Optional[str] = Field(None, max_length=255, description="Email address")
    password_hash: Optional[str] = Field(None, description="Password hash (internal use only)")
    role: str = Field("viewer", description="User role")
    is_active: bool = Field(True, description="Whether user is active")
    created_at: Optional[datetime] = Field(None, description="Account creation time")
    last_login_at: Optional[datetime] = Field(None, description="Last login time")

    @validator("role")
    def validate_role(cls, v):
        """Validate user role."""
        valid_roles = ["viewer", "admin", "owner"]
        if v not in valid_roles:
            raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
        return v

    @validator("email")
    def validate_email(cls, v):
        """Basic email validation."""
        if v is not None and "@" not in v:
            raise ValueError("Invalid email format")
        return v


class AdminSession(BaseModel):
    """Admin session model with validation."""

    id: str = Field(..., min_length=1, max_length=255, description="Session ID")
    user_id: int = Field(..., gt=0, description="Associated user ID")
    started_at: Optional[datetime] = Field(None, description="Session start time")
    last_active_at: Optional[datetime] = Field(None, description="Last activity time")
    ip_address: Optional[str] = Field(None, max_length=45, description="IP address")
    user_agent: Optional[str] = Field(None, max_length=500, description="User agent string")
    is_active: bool = Field(True, description="Whether session is active")


class LoginRequest(BaseModel):
    """Login request model with validation."""

    username: str = Field(..., min_length=1, max_length=50, strip_whitespace=True, description="Username")
    password: str = Field(..., min_length=1, max_length=200, description="Password")


class LoginResponse(BaseModel):
    """Login response model."""

    success: bool
    message: str
    user: Optional[AdminUser] = None
    session_id: Optional[str] = None


class CreateUserRequest(BaseModel):
    """Create user request model with validation."""

    username: str = Field(..., min_length=3, max_length=50, strip_whitespace=True, description="Username")
    email: Optional[str] = Field(None, max_length=255, description="Email address")
    password: str = Field(..., min_length=8, max_length=200, description="Password (min 8 chars)")
    role: str = Field("viewer", description="User role")

    @validator("email")
    def validate_email(cls, v):
        """Basic email validation."""
        if v is not None and v.strip() and "@" not in v:
            raise ValueError("Invalid email format")
        return v.strip() if v else None

    @validator("role")
    def validate_role(cls, v):
        """Validate user role."""
        valid_roles = ["viewer", "admin", "owner"]
        if v not in valid_roles:
            raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
        return v


class ChangePasswordRequest(BaseModel):
    """Change password request model with validation."""

    current_password: str = Field(..., min_length=1, max_length=200, description="Current password")
    new_password: str = Field(..., min_length=8, max_length=200, description="New password (min 8 chars)")

    @validator("new_password")
    def validate_new_password(cls, v, values):
        """Ensure new password is different from current."""
        if "current_password" in values and v == values["current_password"]:
            raise ValueError("New password must be different from current password")
        return v
