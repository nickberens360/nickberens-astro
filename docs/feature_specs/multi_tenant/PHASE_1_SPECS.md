# Phase 1A: Core Multi-Tenant Foundation

## Overview

**Duration:** Weeks 1-3  
**Goal:** Solid multi-tenant infrastructure with tenant isolation and authentication (NO BILLING)  
**Success Criteria:** Multiple tenants can use isolated ChatBot instances with secure authentication on free tier

## Deliverables

1. Multi-tenant database schema implementation (without billing tables)
2. Tenant-scoped vector store isolation
3. Basic API key authentication system
4. Simple tenant CRUD operations
5. Enhanced admin panel for tenant management
6. Free tier tenant functionality validation

## Database Schema Design

### New Tables

#### `tenants` Table
```sql
CREATE TABLE tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    plan_type VARCHAR(50) DEFAULT 'free',
    status VARCHAR(50) DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    settings_json TEXT DEFAULT '{}',
    vector_collection_name VARCHAR(255) UNIQUE NOT NULL,
    knowledge_base_path VARCHAR(500) NOT NULL,
    
    -- Basic usage tracking (free tier only for now)
    monthly_query_limit INTEGER DEFAULT 1000,  -- Generous free tier
    storage_limit_mb INTEGER DEFAULT 100,      -- Generous free tier
    
    -- Current usage (for basic tracking)
    current_queries INTEGER DEFAULT 0,
    current_storage_mb REAL DEFAULT 0.0,
    usage_reset_date DATE DEFAULT (date('now', 'start of month', '+1 month')),
    
    -- Metadata
    api_key_public VARCHAR(255),
    api_key_private_hash VARCHAR(255),
    last_activity_at DATETIME,
    
    CONSTRAINT chk_plan_type CHECK (plan_type IN ('free')),  -- Only free tier for Phase 1A
    CONSTRAINT chk_status CHECK (status IN ('active', 'suspended', 'cancelled'))
);

-- Indexes for performance
CREATE INDEX idx_tenants_slug ON tenants(slug);
CREATE INDEX idx_tenants_status ON tenants(status);
CREATE INDEX idx_tenants_plan_type ON tenants(plan_type);
CREATE INDEX idx_tenants_api_key_public ON tenants(api_key_public);
```

#### `tenant_users` Table
```sql
CREATE TABLE tenant_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'admin',
    status VARCHAR(50) DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login_at DATETIME,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT chk_role CHECK (role IN ('admin', 'user')),
    CONSTRAINT chk_user_status CHECK (status IN ('active', 'inactive')),
    UNIQUE(tenant_id, email)
);

-- Indexes
CREATE INDEX idx_tenant_users_tenant_id ON tenant_users(tenant_id);
CREATE INDEX idx_tenant_users_email ON tenant_users(email);
```

#### Enhanced `query_logs` Table
```sql
-- Add tenant_id column to existing query_logs table
ALTER TABLE query_logs ADD COLUMN tenant_id INTEGER;
ALTER TABLE query_logs ADD CONSTRAINT fk_query_logs_tenant_id 
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;

-- Add index for tenant-scoped queries
CREATE INDEX idx_query_logs_tenant_id ON query_logs(tenant_id);
CREATE INDEX idx_query_logs_tenant_created ON query_logs(tenant_id, created_at);
```

### Database Migration Strategy

#### Migration Scripts Structure
```
backend/migrations/
├── 001_create_tenants_table.sql
├── 002_create_tenant_users_table.sql  
├── 003_add_tenant_id_to_query_logs.sql
└── migration_runner.py
```

#### Migration Runner (`backend/migrations/migration_runner.py`)
```python
import sqlite3
import os
from pathlib import Path
from typing import List

class DatabaseMigrator:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.migrations_dir = Path(__file__).parent
        
    def get_applied_migrations(self) -> List[str]:
        """Get list of already applied migrations"""
        conn = sqlite3.connect(self.db_path)
        
        # Create migrations table if it doesn't exist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY version")
        applied = [row[0] for row in cursor.fetchall()]
        conn.close()
        return applied
    
    def run_migrations(self):
        """Run all pending migrations"""
        applied_migrations = self.get_applied_migrations()
        migration_files = sorted([f for f in os.listdir(self.migrations_dir) if f.endswith('.sql')])
        
        conn = sqlite3.connect(self.db_path)
        
        for migration_file in migration_files:
            if migration_file not in applied_migrations:
                print(f"Running migration: {migration_file}")
                
                with open(self.migrations_dir / migration_file, 'r') as f:
                    migration_sql = f.read()
                
                # Execute migration
                conn.executescript(migration_sql)
                
                # Record migration as applied
                conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES (?)",
                    (migration_file,)
                )
                conn.commit()
        
        conn.close()
        print("All migrations completed successfully")

# Usage
if __name__ == "__main__":
    migrator = DatabaseMigrator("backend/logs/admin_monitoring.db")
    migrator.run_migrations()
```

## Tenant Management Service

### Core Service (`backend/core/tenant_service.py`)
```python
import secrets
import hashlib
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, date
import sqlite3
import os

@dataclass
class Tenant:
    id: Optional[int]
    name: str
    slug: str
    email: str
    plan_type: str = 'free'
    status: str = 'active'
    settings: Dict[str, Any] = None
    vector_collection_name: Optional[str] = None
    knowledge_base_path: Optional[str] = None
    monthly_query_limit: int = 100
    storage_limit_mb: int = 10
    current_queries: int = 0
    current_storage_mb: float = 0.0
    api_key_public: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass 
class TenantUser:
    id: Optional[int]
    tenant_id: int
    email: str
    role: str = 'admin'
    status: str = 'active'
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

class TenantService:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Ensure database and tables exist"""
        if not os.path.exists(self.db_path):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Run migrations
        from backend.migrations.migration_runner import DatabaseMigrator
        migrator = DatabaseMigrator(self.db_path)
        migrator.run_migrations()
    
    def create_tenant(self, name: str, slug: str, email: str, plan_type: str = 'free') -> Tenant:
        """Create a new tenant with all required setup"""
        
        # Generate unique identifiers
        vector_collection_name = f"tenant_{slug}_{secrets.token_hex(8)}"
        knowledge_base_path = f"knowledge_bases/{slug}_{secrets.token_hex(8)}"
        api_key_public = self._generate_api_key('pk', slug)
        api_key_private = self._generate_api_key('sk', slug)
        api_key_private_hash = self._hash_api_key(api_key_private)
        
        # Plan-based limits (Phase 1A: Free tier only)
        plan_limits = {
            'free': {'queries': 1000, 'storage': 100}  # Generous limits for validation
        }
        limits = plan_limits['free']  # Only free tier for now
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            INSERT INTO tenants (
                name, slug, email, plan_type, status, settings_json,
                vector_collection_name, knowledge_base_path,
                monthly_query_limit, storage_limit_mb,
                api_key_public, api_key_private_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, slug, email, plan_type, 'active', '{}',
            vector_collection_name, knowledge_base_path,
            limits['queries'], limits['storage'],
            api_key_public, api_key_private_hash
        ))
        
        tenant_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Create knowledge base directory
        kb_full_path = f"backend/{knowledge_base_path}"
        os.makedirs(kb_full_path, exist_ok=True)
        
        # Create initial tenant user (admin)
        self.create_tenant_user(tenant_id, email, 'admin')
        
        # Initialize vector store
        self._initialize_vector_store(vector_collection_name)
        
        # Return tenant with private API key (only shown once)
        tenant = self.get_tenant_by_id(tenant_id)
        tenant.api_key_private = api_key_private  # Include for initial setup
        
        return tenant
    
    def get_tenant_by_id(self, tenant_id: int) -> Optional[Tenant]:
        """Get tenant by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("""
            SELECT * FROM tenants WHERE id = ?
        """, (tenant_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        return self._row_to_tenant(row)
    
    def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get tenant by slug"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("""
            SELECT * FROM tenants WHERE slug = ?
        """, (slug,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        return self._row_to_tenant(row)
    
    def get_tenant_by_api_key(self, api_key: str) -> Optional[Tenant]:
        """Get tenant by public API key"""
        if not api_key.startswith(('pk_', 'sk_')):
            return None
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        if api_key.startswith('pk_'):
            # Public key - direct lookup
            cursor = conn.execute("""
                SELECT * FROM tenants WHERE api_key_public = ? AND status = 'active'
            """, (api_key,))
        else:
            # Private key - hash and compare
            api_key_hash = self._hash_api_key(api_key)
            cursor = conn.execute("""
                SELECT * FROM tenants WHERE api_key_private_hash = ? AND status = 'active'
            """, (api_key_hash,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        return self._row_to_tenant(row)
    
    def list_tenants(self, status: str = None, plan_type: str = None, limit: int = 100, offset: int = 0) -> List[Tenant]:
        """List tenants with optional filtering"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        where_conditions = []
        params = []
        
        if status:
            where_conditions.append("status = ?")
            params.append(status)
            
        if plan_type:
            where_conditions.append("plan_type = ?")
            params.append(plan_type)
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        cursor = conn.execute(f"""
            SELECT * FROM tenants {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, params + [limit, offset])
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_tenant(row) for row in rows]
    
    def update_tenant_usage(self, tenant_id: int, queries_increment: int = 0, storage_mb: float = None):
        """Update tenant usage metrics"""
        conn = sqlite3.connect(self.db_path)
        
        updates = ["last_activity_at = CURRENT_TIMESTAMP"]
        params = []
        
        if queries_increment > 0:
            updates.append("current_queries = current_queries + ?")
            params.append(queries_increment)
        
        if storage_mb is not None:
            updates.append("current_storage_mb = ?")
            params.append(storage_mb)
        
        params.append(tenant_id)
        
        conn.execute(f"""
            UPDATE tenants 
            SET {', '.join(updates)}
            WHERE id = ?
        """, params)
        
        conn.commit()
        conn.close()
    
    def check_usage_limits(self, tenant_id: int) -> Dict[str, Any]:
        """Check if tenant is within usage limits"""
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            return {'allowed': False, 'reason': 'Tenant not found'}
        
        # Check query limit
        if tenant.monthly_query_limit > 0 and tenant.current_queries >= tenant.monthly_query_limit:
            return {'allowed': False, 'reason': 'Monthly query limit exceeded'}
        
        # Check storage limit
        if tenant.storage_limit_mb > 0 and tenant.current_storage_mb >= tenant.storage_limit_mb:
            return {'allowed': False, 'reason': 'Storage limit exceeded'}
        
        return {'allowed': True, 'queries_remaining': tenant.monthly_query_limit - tenant.current_queries if tenant.monthly_query_limit > 0 else -1}
    
    def create_tenant_user(self, tenant_id: int, email: str, role: str = 'admin', password: str = None) -> TenantUser:
        """Create a new user for a tenant"""
        if not password:
            password = secrets.token_urlsafe(16)  # Generate temporary password
        
        password_hash = self._hash_password(password)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            INSERT INTO tenant_users (tenant_id, email, password_hash, role, status)
            VALUES (?, ?, ?, ?, 'active')
        """, (tenant_id, email, password_hash, role))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        user = TenantUser(
            id=user_id,
            tenant_id=tenant_id,
            email=email,
            role=role,
            status='active'
        )
        
        return user
    
    def _generate_api_key(self, prefix: str, slug: str) -> str:
        """Generate API key with format: prefix_env_slug_randompart"""
        env = 'test'  # Will be 'live' in production
        random_part = secrets.token_hex(16)
        return f"{prefix}_{env}_{slug}_{random_part}"
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def _hash_password(self, password: str) -> str:
        """Hash password for secure storage"""
        import bcrypt
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _initialize_vector_store(self, collection_name: str):
        """Initialize ChromaDB collection for tenant"""
        # This will be implemented when we modify the unified_retriever
        pass
    
    def _row_to_tenant(self, row) -> Tenant:
        """Convert database row to Tenant object"""
        import json
        
        return Tenant(
            id=row['id'],
            name=row['name'],
            slug=row['slug'],
            email=row['email'],
            plan_type=row['plan_type'],
            status=row['status'],
            settings=json.loads(row['settings_json']) if row['settings_json'] else {},
            vector_collection_name=row['vector_collection_name'],
            knowledge_base_path=row['knowledge_base_path'],
            monthly_query_limit=row['monthly_query_limit'],
            storage_limit_mb=row['storage_limit_mb'],
            current_queries=row['current_queries'],
            current_storage_mb=row['current_storage_mb'],
            api_key_public=row['api_key_public'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )
```

## Vector Store Isolation

### Enhanced Unified Retriever (`backend/core/tenant_retriever.py`)
```python
import os
from typing import Optional, List, Dict, Any
from pathlib import Path
import chromadb
from chromadb.config import Settings

from backend.core.unified_retriever import UnifiedRetriever  # Base class
from backend.core.tenant_service import TenantService

class TenantRetriever(UnifiedRetriever):
    """Enhanced retriever with tenant isolation"""
    
    def __init__(self, tenant_id: int, config_override: Dict[str, Any] = None):
        self.tenant_id = tenant_id
        self.tenant_service = TenantService("backend/logs/admin_monitoring.db")
        self.tenant = self.tenant_service.get_tenant_by_id(tenant_id)
        
        if not self.tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Initialize with tenant-specific paths
        self.knowledge_base_path = f"backend/{self.tenant.knowledge_base_path}"
        self.vector_collection_name = self.tenant.vector_collection_name
        
        # Initialize parent with tenant-specific config
        tenant_config = self._get_tenant_config(config_override)
        super().__init__(config_override=tenant_config)
    
    def _get_tenant_config(self, config_override: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get tenant-specific configuration"""
        base_config = {
            'knowledge_directories': [self.knowledge_base_path],
            'vector_store_path': f"vector_stores/{self.tenant.slug}",
            'collection_name': self.vector_collection_name
        }
        
        if config_override:
            base_config.update(config_override)
        
        return base_config
    
    def initialize_chroma_client(self):
        """Initialize ChromaDB client with tenant-specific collection"""
        vector_store_path = f"vector_stores/{self.tenant.slug}"
        os.makedirs(vector_store_path, exist_ok=True)
        
        self.chroma_client = chromadb.PersistentClient(
            path=vector_store_path,
            settings=Settings(allow_reset=True)
        )
        
        # Create or get tenant-specific collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.vector_collection_name,
            metadata={"tenant_id": str(self.tenant_id)}
        )
        
        print(f"Initialized vector store for tenant {self.tenant.slug}")
    
    def get_relevant_contexts(self, query: str, max_contexts: int = 5) -> List[Dict[str, Any]]:
        """Get relevant contexts with tenant isolation verification"""
        contexts = super().get_relevant_contexts(query, max_contexts)
        
        # Verify all contexts belong to this tenant (safety check)
        for context in contexts:
            if 'tenant_id' in context and context['tenant_id'] != str(self.tenant_id):
                raise ValueError(f"Cross-tenant data leak detected! Context from tenant {context['tenant_id']} returned for tenant {self.tenant_id}")
        
        return contexts
    
    def add_documents_to_collection(self, documents: List[Dict[str, Any]]):
        """Add documents with tenant metadata"""
        if not documents:
            return
        
        # Add tenant metadata to all documents
        for doc in documents:
            doc['metadata']['tenant_id'] = str(self.tenant_id)
        
        super().add_documents_to_collection(documents)
        
        # Update tenant storage usage
        total_size = sum(len(doc['content'].encode('utf-8')) for doc in documents)
        storage_mb = total_size / (1024 * 1024)
        
        current_storage = self._calculate_current_storage()
        self.tenant_service.update_tenant_usage(
            self.tenant_id, 
            storage_mb=current_storage + storage_mb
        )
    
    def _calculate_current_storage(self) -> float:
        """Calculate current storage usage for tenant"""
        try:
            # Get all documents in collection and calculate size
            results = self.collection.get()
            if not results['documents']:
                return 0.0
            
            total_bytes = sum(len(doc.encode('utf-8')) for doc in results['documents'])
            return total_bytes / (1024 * 1024)  # Convert to MB
        except Exception as e:
            print(f"Error calculating storage for tenant {self.tenant_id}: {e}")
            return 0.0

# Factory function for creating tenant retrievers
def create_tenant_retriever(tenant_id: int) -> TenantRetriever:
    """Factory function to create tenant-specific retriever"""
    return TenantRetriever(tenant_id)

# Global cache for tenant retrievers (optional optimization)
_tenant_retrievers = {}

def get_tenant_retriever(tenant_id: int) -> TenantRetriever:
    """Get cached or create new tenant retriever"""
    if tenant_id not in _tenant_retrievers:
        _tenant_retrievers[tenant_id] = create_tenant_retriever(tenant_id)
    return _tenant_retrievers[tenant_id]
```

## API Authentication Middleware

### Authentication Service (`backend/core/tenant_auth.py`)
```python
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.core.tenant_service import TenantService, Tenant

security = HTTPBearer()

class TenantAuth:
    def __init__(self):
        self.tenant_service = TenantService("backend/logs/admin_monitoring.db")
    
    async def get_tenant_from_api_key(self, credentials: HTTPAuthorizationCredentials = Security(security)) -> Tenant:
        """Authenticate and return tenant from API key"""
        if not credentials or not credentials.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required"
            )
        
        api_key = credentials.credentials
        tenant = self.tenant_service.get_tenant_by_api_key(api_key)
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        if tenant.status != 'active':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tenant account is {tenant.status}"
            )
        
        return tenant
    
    async def get_tenant_with_usage_check(self, credentials: HTTPAuthorizationCredentials = Security(security)) -> Tenant:
        """Authenticate tenant and check usage limits"""
        tenant = await self.get_tenant_from_api_key(credentials)
        
        # Check usage limits
        usage_check = self.tenant_service.check_usage_limits(tenant.id)
        if not usage_check['allowed']:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Usage limit exceeded: {usage_check['reason']}"
            )
        
        return tenant
    
    def require_private_key(self, api_key: str) -> bool:
        """Check if API key is a private key (for admin operations)"""
        return api_key.startswith('sk_')
    
    async def get_tenant_admin(self, credentials: HTTPAuthorizationCredentials = Security(security)) -> Tenant:
        """Authenticate tenant with admin privileges (private key required)"""
        tenant = await self.get_tenant_from_api_key(credentials)
        
        if not self.require_private_key(credentials.credentials):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access requires private API key"
            )
        
        return tenant

# Global auth instance
tenant_auth = TenantAuth()
```

## Enhanced API Routes

### Multi-Tenant Query Route (`backend/routes/tenant_query.py`)
```python
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.core.tenant_auth import tenant_auth, Tenant
from backend.core.tenant_retriever import get_tenant_retriever
from backend.core.smart_query_handler import SmartQueryHandler
from backend.core.sqlite_query_logger import SQLiteQueryLogger

router = APIRouter(prefix="/api/v1", tags=["tenant-query"])

class QueryRequest(BaseModel):
    question: str
    chat_history: List[Dict[str, str]] = []
    metadata: Dict[str, Any] = {}

class QueryResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]] = []
    tenant_id: int
    query_id: Optional[str] = None
    usage: Dict[str, Any] = {}

@router.post("/chat", response_model=QueryResponse)
async def tenant_chat(
    request: QueryRequest,
    tenant: Tenant = Depends(tenant_auth.get_tenant_with_usage_check)
):
    """Main chat endpoint with tenant isolation"""
    try:
        # Get tenant-specific retriever
        retriever = get_tenant_retriever(tenant.id)
        
        # Initialize query handler with tenant retriever
        query_handler = SmartQueryHandler(retriever=retriever)
        
        # Process query
        result = await query_handler.process_query(
            question=request.question,
            chat_history=request.chat_history,
            metadata=request.metadata
        )
        
        # Log query with tenant context
        query_logger = SQLiteQueryLogger()
        query_id = await query_logger.log_query(
            query=request.question,
            response=result['response'],
            response_time_ms=result.get('response_time_ms', 0),
            sources=result.get('sources', []),
            chat_history=request.chat_history,
            tenant_id=tenant.id,
            metadata=request.metadata
        )
        
        # Update tenant usage
        tenant_auth.tenant_service.update_tenant_usage(tenant.id, queries_increment=1)
        
        # Get updated usage info
        usage_check = tenant_auth.tenant_service.check_usage_limits(tenant.id)
        
        return QueryResponse(
            response=result['response'],
            sources=result.get('sources', []),
            tenant_id=tenant.id,
            query_id=query_id,
            usage={
                'queries_remaining': usage_check.get('queries_remaining', -1),
                'plan_type': tenant.plan_type
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}"
        )

@router.get("/tenants/{tenant_id}/status")
async def tenant_status(
    tenant_id: int,
    tenant: Tenant = Depends(tenant_auth.get_tenant_from_api_key)
):
    """Get tenant status and usage information"""
    # Verify tenant can only access their own data
    if tenant.id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    usage_check = tenant_auth.tenant_service.check_usage_limits(tenant.id)
    
    return {
        'tenant_id': tenant.id,
        'name': tenant.name,
        'plan_type': tenant.plan_type,
        'status': tenant.status,
        'usage': {
            'current_queries': tenant.current_queries,
            'monthly_query_limit': tenant.monthly_query_limit,
            'current_storage_mb': tenant.current_storage_mb,
            'storage_limit_mb': tenant.storage_limit_mb,
            'queries_remaining': usage_check.get('queries_remaining', -1)
        },
        'created_at': tenant.created_at.isoformat() if tenant.created_at else None
    }
```

### Admin Routes for Tenant Management (`backend/routes/admin_tenants.py`)
```python
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Any, Optional

from backend.core.tenant_service import TenantService, Tenant
from backend.core.admin_auth import require_admin_session  # Existing admin auth

router = APIRouter(prefix="/api/admin", tags=["admin-tenants"])

class CreateTenantRequest(BaseModel):
    name: str
    slug: str
    email: EmailStr
    plan_type: str = 'free'

class TenantResponse(BaseModel):
    id: int
    name: str
    slug: str
    email: str
    plan_type: str
    status: str
    current_queries: int
    monthly_query_limit: int
    current_storage_mb: float
    storage_limit_mb: int
    created_at: Optional[str]
    api_key_public: str

class CreateTenantResponse(TenantResponse):
    api_key_private: str  # Only shown once during creation

@router.post("/tenants", response_model=CreateTenantResponse)
async def create_tenant(
    request: CreateTenantRequest,
    admin_session = Depends(require_admin_session)
):
    """Create a new tenant (admin only)"""
    tenant_service = TenantService("backend/logs/admin_monitoring.db")
    
    try:
        # Check if slug already exists
        existing = tenant_service.get_tenant_by_slug(request.slug)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tenant slug already exists"
            )
        
        # Create tenant
        tenant = tenant_service.create_tenant(
            name=request.name,
            slug=request.slug,
            email=request.email,
            plan_type=request.plan_type
        )
        
        return CreateTenantResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            email=tenant.email,
            plan_type=tenant.plan_type,
            status=tenant.status,
            current_queries=tenant.current_queries,
            monthly_query_limit=tenant.monthly_query_limit,
            current_storage_mb=tenant.current_storage_mb,
            storage_limit_mb=tenant.storage_limit_mb,
            created_at=tenant.created_at.isoformat() if tenant.created_at else None,
            api_key_public=tenant.api_key_public,
            api_key_private=tenant.api_key_private  # Only shown during creation
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/tenants", response_model=List[TenantResponse])
async def list_tenants(
    status: Optional[str] = None,
    plan_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin_session = Depends(require_admin_session)
):
    """List tenants with optional filtering (admin only)"""
    tenant_service = TenantService("backend/logs/admin_monitoring.db")
    
    tenants = tenant_service.list_tenants(
        status=status,
        plan_type=plan_type,
        limit=limit,
        offset=offset
    )
    
    return [
        TenantResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            email=tenant.email,
            plan_type=tenant.plan_type,
            status=tenant.status,
            current_queries=tenant.current_queries,
            monthly_query_limit=tenant.monthly_query_limit,
            current_storage_mb=tenant.current_storage_mb,
            storage_limit_mb=tenant.storage_limit_mb,
            created_at=tenant.created_at.isoformat() if tenant.created_at else None,
            api_key_public=tenant.api_key_public
        )
        for tenant in tenants
    ]

@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: int,
    admin_session = Depends(require_admin_session)
):
    """Get specific tenant details (admin only)"""
    tenant_service = TenantService("backend/logs/admin_monitoring.db")
    tenant = tenant_service.get_tenant_by_id(tenant_id)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        email=tenant.email,
        plan_type=tenant.plan_type,
        status=tenant.status,
        current_queries=tenant.current_queries,
        monthly_query_limit=tenant.monthly_query_limit,
        current_storage_mb=tenant.current_storage_mb,
        storage_limit_mb=tenant.storage_limit_mb,
        created_at=tenant.created_at.isoformat() if tenant.created_at else None,
        api_key_public=tenant.api_key_public
    )
```

## Configuration Updates

### Enhanced Config (`backend/core/config.py`)
```python
# Add multi-tenant configuration options

class Config:
    # ... existing config ...
    
    # Multi-tenant settings
    MULTI_TENANT_MODE: bool = True
    DEFAULT_TENANT_PLAN: str = 'free'
    TENANT_VECTOR_STORE_BASE_PATH: str = 'vector_stores'
    TENANT_KNOWLEDGE_BASE_PATH: str = 'knowledge_bases'
    
    # Plan limits (Phase 1A: Free tier only with generous limits)
    PLAN_LIMITS = {
        'free': {
            'monthly_queries': 1000,    # Generous for validation
            'storage_mb': 100,          # Generous for validation
            'features': ['basic_chat', 'knowledge_upload', 'api_access']
        }
    }
    
    # Security settings
    API_KEY_LENGTH: int = 32
    TENANT_ISOLATION_STRICT: bool = True
    
    @classmethod
    def get_plan_limits(cls, plan_type: str) -> Dict[str, Any]:
        """Get limits for specific plan type (free only in Phase 1A)"""
        return cls.PLAN_LIMITS['free']  # Always return free tier for Phase 1A
```

## Testing Strategy

### Unit Tests (`tests/unit/test_tenant_service.py`)
```python
import pytest
import tempfile
import os
from backend.core.tenant_service import TenantService

class TestTenantService:
    @pytest.fixture
    def tenant_service(self):
        # Use temporary database for testing
        temp_db = tempfile.mktemp(suffix='.db')
        service = TenantService(temp_db)
        yield service
        # Cleanup
        if os.path.exists(temp_db):
            os.unlink(temp_db)
    
    def test_create_tenant(self, tenant_service):
        """Test tenant creation"""
        tenant = tenant_service.create_tenant(
            name="Test Company",
            slug="test-company",
            email="admin@test.com",
            plan_type="free"
        )
        
        assert tenant.id is not None
        assert tenant.name == "Test Company"
        assert tenant.slug == "test-company"
        assert tenant.plan_type == "free"
        assert tenant.api_key_public.startswith("pk_test_")
        assert tenant.api_key_private.startswith("sk_test_")
    
    def test_tenant_isolation(self, tenant_service):
        """Test that tenants are properly isolated"""
        tenant1 = tenant_service.create_tenant("Company 1", "company1", "admin1@test.com")
        tenant2 = tenant_service.create_tenant("Company 2", "company2", "admin2@test.com")
        
        # Verify different vector collections
        assert tenant1.vector_collection_name != tenant2.vector_collection_name
        
        # Verify different knowledge base paths
        assert tenant1.knowledge_base_path != tenant2.knowledge_base_path
        
        # Verify different API keys
        assert tenant1.api_key_public != tenant2.api_key_public
    
    def test_usage_limits(self, tenant_service):
        """Test usage limit checking"""
        tenant = tenant_service.create_tenant("Test Company", "test", "admin@test.com", "free")
        
        # Initially should be allowed
        check = tenant_service.check_usage_limits(tenant.id)
        assert check['allowed'] is True
        
        # Simulate reaching query limit
        tenant_service.update_tenant_usage(tenant.id, queries_increment=100)
        
        check = tenant_service.check_usage_limits(tenant.id)
        assert check['allowed'] is False
        assert 'query limit' in check['reason'].lower()
```

### Integration Tests (`tests/integration/test_tenant_api.py`)
```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

class TestTenantAPI:
    @pytest.fixture
    def test_tenant(self):
        """Create a test tenant"""
        # This would use the admin API to create a tenant for testing
        response = client.post("/api/admin/tenants", 
            json={
                "name": "Test Company",
                "slug": "test-company",
                "email": "admin@test.com",
                "plan_type": "free"
            },
            headers={"Authorization": "Bearer admin_test_token"}
        )
        return response.json()
    
    def test_tenant_chat_with_valid_key(self, test_tenant):
        """Test chat with valid API key"""
        response = client.post("/api/v1/chat",
            json={
                "question": "Hello, what can you help me with?",
                "chat_history": []
            },
            headers={"Authorization": f"Bearer {test_tenant['api_key_public']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['tenant_id'] == test_tenant['id']
        assert 'response' in data
    
    def test_tenant_isolation(self, test_tenant):
        """Test that tenants can't access each other's data"""
        # Create second tenant
        tenant2_response = client.post("/api/admin/tenants",
            json={
                "name": "Company 2",
                "slug": "company2",
                "email": "admin2@test.com"
            },
            headers={"Authorization": "Bearer admin_test_token"}
        )
        tenant2 = tenant2_response.json()
        
        # Try to access tenant1's status with tenant2's key
        response = client.get(f"/api/v1/tenants/{test_tenant['id']}/status",
            headers={"Authorization": f"Bearer {tenant2['api_key_public']}"}
        )
        
        assert response.status_code == 403  # Forbidden
```

## Deployment Checklist for Phase 1A

### Pre-deployment
- [ ] Run database migrations (basic tenant tables only)
- [ ] Update environment variables for multi-tenant mode
- [ ] Create initial super admin account
- [ ] Test tenant creation and isolation
- [ ] Verify API key authentication
- [ ] Run full test suite (free tier focus)

### Post-deployment
- [ ] Create multiple test tenants (all free tier)
- [ ] Verify tenant isolation in production
- [ ] Monitor database performance
- [ ] Check vector store creation per tenant
- [ ] Verify query logging with tenant context
- [ ] Test basic usage tracking (no enforcement yet)

## Success Metrics for Phase 1A

1. **Functional Requirements**
   - [ ] Multiple tenants can be created successfully (free tier only)
   - [ ] Each tenant has isolated vector store
   - [ ] API key authentication works correctly
   - [ ] Basic usage tracking works (no enforcement yet)
   - [ ] Admin panel shows multi-tenant data

2. **Performance Requirements**
   - [ ] Query response time < 3 seconds with multiple tenants
   - [ ] Database operations complete < 1 second
   - [ ] Vector store isolation doesn't impact performance

3. **Security Requirements**
   - [ ] No cross-tenant data leakage
   - [ ] API keys properly validate tenant access
   - [ ] Tenant isolation is bulletproof
   - [ ] Admin operations require proper authentication

## Risk Mitigation

### Technical Risks
- **Data isolation failure**: Comprehensive testing and strict validation
- **Performance impact**: Monitor and optimize database queries  
- **API key security**: Secure generation and storage
- **Complexity creep**: Resist adding billing features too early

### Implementation Risks  
- **Complex migration**: Phased approach with rollback plan
- **Testing coverage**: Automated tests for all tenant operations
- **Configuration errors**: Environment-specific validation
- **Scope expansion**: Stay focused on core multi-tenancy only

---

# Phase 1B: Basic Tenant Dashboard

## Overview

**Duration:** Week 4  
**Goal:** Simple tenant dashboard for knowledge management and ChatBot testing  
**Success Criteria:** Tenants can upload documents, test ChatBot, and view API keys

## Deliverables

1. Basic Vue.js tenant dashboard (no billing UI)
2. Knowledge base file upload interface
3. ChatBot testing interface  
4. API key display and management
5. Simple tenant onboarding flow (no payments)
6. Basic usage statistics display

## Dashboard Components

### Core Features
- **Knowledge Manager**: Upload/delete documents, view indexing status
- **ChatBot Tester**: Test interface to validate ChatBot responses
- **API Keys**: Display public/private keys, regeneration capability
- **Usage Stats**: Show current usage vs limits (basic tracking)
- **Settings**: Basic tenant settings and preferences

### Simple Onboarding Flow
1. **Welcome**: Show tenant info and API keys
2. **Upload Knowledge**: File upload interface with progress
3. **Test ChatBot**: Interactive testing with sample queries
4. **Integration**: Show API documentation and examples
5. **Complete**: Dashboard overview and next steps

### Dashboard Structure
```
tenant-dashboard/
├── src/
│   ├── components/
│   │   ├── knowledge/
│   │   │   ├── FileUpload.vue
│   │   │   ├── DocumentsList.vue
│   │   │   └── IndexingStatus.vue
│   │   ├── chatbot/
│   │   │   ├── ChatTester.vue
│   │   │   └── ResponseViewer.vue
│   │   ├── api/
│   │   │   ├── ApiKeyDisplay.vue
│   │   │   └── ApiDocumentation.vue
│   │   └── onboarding/
│   │       ├── SimpleOnboarding.vue
│   │       └── OnboardingSteps.vue
│   └── views/
│       ├── DashboardView.vue
│       ├── KnowledgeView.vue
│       ├── ChatBotView.vue
│       ├── ApiKeysView.vue
│       └── OnboardingView.vue
```

## API Routes for Dashboard

### Basic Dashboard API (`backend/routes/tenant_dashboard.py`)
```python
@router.get("/dashboard/stats")
async def get_dashboard_stats(tenant: Tenant = Depends(tenant_auth.get_tenant_from_api_key)):
    """Get basic dashboard statistics"""
    return {
        'tenant_info': {
            'name': tenant.name,
            'plan': tenant.plan_type,
            'created_at': tenant.created_at
        },
        'usage': {
            'queries_used': tenant.current_queries,
            'queries_limit': tenant.monthly_query_limit,
            'storage_used_mb': tenant.current_storage_mb,
            'storage_limit_mb': tenant.storage_limit_mb
        },
        'knowledge_base': {
            'documents_count': 0,  # To be implemented
            'indexing_status': 'ready'
        }
    }

@router.post("/knowledge/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    tenant: Tenant = Depends(tenant_auth.get_tenant_from_api_key)
):
    """Upload knowledge base documents"""
    # Implementation for file upload and indexing
    pass

@router.post("/chatbot/test")  
async def test_chatbot(
    request: dict,
    tenant: Tenant = Depends(tenant_auth.get_tenant_from_api_key)
):
    """Test ChatBot with user query"""
    # Use existing tenant chat endpoint
    pass
```

## Success Metrics for Phase 1B

1. **User Experience**
   - [ ] Intuitive file upload with progress indication
   - [ ] Real-time ChatBot testing works smoothly  
   - [ ] API keys clearly displayed with copy functionality
   - [ ] Simple onboarding flow completion under 5 minutes

2. **Functional Requirements**
   - [ ] File upload and indexing pipeline works
   - [ ] ChatBot responses are tenant-specific
   - [ ] Usage statistics display correctly
   - [ ] Dashboard is responsive on mobile/desktop

## Combined Phase 1A + 1B Timeline

**Weeks 1-2**: Core multi-tenant backend (database, services, API)
**Week 3**: Enhanced admin panel and tenant isolation testing  
**Week 4**: Basic tenant dashboard frontend and simple onboarding

This approach validates the multi-tenant architecture thoroughly before adding billing complexity, while still providing a complete user experience for free-tier tenants.