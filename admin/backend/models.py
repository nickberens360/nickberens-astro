"""
Database models for the RAG admin dashboard.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class QueryLog(BaseModel):
    """Query log entry model."""

    id: Optional[int] = None
    session_id: Optional[str] = None
    user_query: str
    system_response: Optional[str] = None
    response_time_ms: Optional[float] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    vector_search_score: Optional[float] = None
    sources_used: Optional[List[str]] = None
    follow_up_questions: Optional[List[str]] = None
    cache_hit: bool = False
    error_occurred: bool = False
    error_message: Optional[str] = None
    user_feedback: Optional[str] = None  # 'helpful', 'not_helpful', null
    timestamp: Optional[datetime] = None
    # Location fields
    client_ip: Optional[str] = None
    location_city: Optional[str] = None
    location_region: Optional[str] = None
    location_country: Optional[str] = None
    location_country_code: Optional[str] = None


class UserSession(BaseModel):
    """User session model."""

    id: str
    started_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None
    total_queries: int = 0
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class HourlyMetrics(BaseModel):
    """Hourly aggregated metrics model."""

    id: Optional[int] = None
    hour: datetime
    total_queries: int
    unique_sessions: int
    avg_response_time_ms: float
    p95_response_time_ms: float
    cache_hit_rate: float
    error_rate: float
    helpful_rate: float


class ContentGap(BaseModel):
    """Content gap tracking model."""

    id: Optional[int] = None
    query_pattern: str
    occurrence_count: int = 1
    avg_similarity_score: float
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    resolved: bool = False


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
    """User feedback update model."""

    feedback: str  # 'helpful' or 'not_helpful'


class FileContentUpdate(BaseModel):
    """File content update model."""

    content: str


class AdminUser(BaseModel):
    """Admin user model."""

    id: Optional[int] = None
    username: str
    email: Optional[str] = None
    password_hash: Optional[str] = None
    role: str = "viewer"
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


class AdminSession(BaseModel):
    """Admin session model."""

    id: str
    user_id: int
    started_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool = True


class LoginRequest(BaseModel):
    """Login request model."""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model."""

    success: bool
    message: str
    user: Optional[AdminUser] = None
    session_id: Optional[str] = None


class CreateUserRequest(BaseModel):
    """Create user request model."""

    username: str
    email: Optional[str] = None
    password: str
    role: str = "viewer"


class ChangePasswordRequest(BaseModel):
    """Change password request model."""

    current_password: str
    new_password: str
