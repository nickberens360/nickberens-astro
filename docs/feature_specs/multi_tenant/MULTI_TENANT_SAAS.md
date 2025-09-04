# Multi-Tenant SaaS Transformation Plan

## Project Overview

Transform the current personal website with RAG-powered AI assistant into a multi-tenant SaaS product. The core product will be a ChatBot service where tenants can upload their own knowledge bases and provide AI-powered chat experiences to their users.

## Current State → Target State

**Current:** Personal website (Astro) + AI assistant + admin dashboard  
**Target:** Multi-tenant SaaS with ChatBot as the core product

### Key Changes
- Remove Astro-based personal website content
- Keep only ChatBot and related components
- Each tenant gets their own ChatBot instance with isolated knowledge base
- Transform admin system for multi-tenant management
- Add billing, authentication, and tenant management

## Architecture Overview

### Tenant Isolation Strategy
Each tenant will have:
- **Separate vector store** (ChromaDB collection per tenant)
- **Isolated knowledge base** storage
- **Tenant-scoped authentication**
- **Usage tracking and billing**

### Three-Tier System Architecture

#### 1. Marketing Site (New - Next.js/React)
- Landing pages and pricing
- Documentation and demos
- Sign-up flows
- Public-facing content

#### 2. Tenant Dashboard (New - Vue.js + Vuetify)
- ChatBot interface (core product)
- Knowledge base management
- Analytics dashboard
- Team management
- Settings and customization

#### 3. Super Admin Panel (Enhanced current admin)
- Tenant management
- System monitoring
- Billing oversight
- Support tools

## Database Architecture

### Multi-Tenant Tables
```sql
-- Core tenant management
tenants (
  id, name, slug, plan_type, status, created_at, updated_at, settings_json
)

-- Tenant user management
tenant_users (
  id, tenant_id, email, role, api_key_hash, created_at, last_login
)

-- Subscription management
tenant_subscriptions (
  id, tenant_id, plan_id, status, billing_cycle, next_billing_date, stripe_subscription_id
)

-- Usage tracking
tenant_usage_metrics (
  id, tenant_id, queries_count, storage_mb, month_year, overage_charges
)

-- Enhanced query logging with tenant isolation
query_logs (
  id, tenant_id, query, response, response_time_ms, created_at, user_ip, metadata_json
)
```

### Vector Store Structure
```
/vector_stores/
├── tenant_001/           # ChromaDB collection per tenant
│   ├── chroma.sqlite3
│   └── embeddings/
├── tenant_002/
│   ├── chroma.sqlite3  
│   └── embeddings/
└── shared_system/        # System-level collections
    └── admin_docs/
```

### Knowledge Base Storage
```
/knowledge_bases/
├── tenant_001/
│   ├── documents/        # Tenant's uploaded files
│   ├── processed/        # Processed and indexed content
│   └── metadata.json    # Indexing status and statistics
├── tenant_002/
└── system/              # System documentation and templates
```

## Authentication & API Keys

### Three-Tier Authentication System
```
1. Public API Keys (tenant-scoped, read-only)
   - Chat interface access
   - Rate limited per tenant plan
   - Format: pk_live_tenant001_abc123...

2. Private API Keys (full tenant access)
   - Knowledge base management
   - Analytics access
   - Team management
   - Format: sk_live_tenant001_def456...

3. Admin Keys (super admin only)
   - Cross-tenant operations
   - System management
   - Format: ak_system_jkl012...
```

### Test vs Production Keys
- Test keys: `pk_test_`, `sk_test_`
- Live keys: `pk_live_`, `sk_live_`
- Separate environments and rate limits

## API Architecture

### Current vs New Endpoints
```
Current: /query, /health, /admin/*
New v1:  /api/v1/tenants/{tenant_id}/*, /api/v1/chat
```

### Tenant-Scoped API Structure
```
/api/v1/tenants/{tenant_id}/
├── chat/                 # Main chat interface
├── knowledge/           # Content management
│   ├── upload           # File upload endpoint
│   ├── documents        # Document management
│   └── reindex          # Force reindexing
├── analytics/           # Usage statistics
├── settings/           # Tenant configuration
└── users/              # Team management

/api/v1/auth/           # Authentication endpoints
├── login               # Tenant user login
├── register            # New tenant signup
└── api-keys           # API key management

/api/v1/admin/          # Super admin endpoints
├── tenants            # Tenant management
├── system             # System monitoring
└── billing            # Billing oversight
```

## Current System Adaptation

### Service Mapping
Your existing services adapt perfectly to multi-tenant architecture:

#### `unified_retriever.py` → `tenant_retriever.py`
- Initialize per-tenant ChromaDB collection
- Tenant-scoped document indexing
- Isolated vector search

#### `smart_query_handler.py` (Enhanced)
- Route queries to tenant-specific vector store
- Tenant-specific response customization
- Maintain existing smart routing logic

#### `sqlite_query_logger.py` (Enhanced)
- Add tenant_id field to all query logs
- Per-tenant analytics and reporting
- Maintain existing logging functionality

#### `admin_database.py` (Expanded)
- Multi-tenant database operations
- Tenant provisioning and management
- Enhanced with billing and usage tracking

## Pricing & Billing Strategy

### Pricing Tiers
```
Free Tier:
- 100 queries/month
- 10MB knowledge base storage
- Basic chat interface
- Community support

Starter ($29/month):
- 1,000 queries/month
- 100MB knowledge base storage
- Custom branding
- Email support

Pro ($99/month):
- 10,000 queries/month
- 1GB knowledge base storage
- Advanced analytics
- Priority support
- Team management (up to 5 users)

Enterprise (Custom pricing):
- Unlimited queries
- Unlimited storage
- Dedicated resources
- SLA guarantees
- Custom integrations
```

### Billing Integration
- **Payment processor:** Stripe
- **Billing model:** Subscription + metered usage
- **Overage handling:** Automatic charges for excess usage
- **Usage tracking:** Enhanced query logger with tenant scoping

## Tenant Onboarding Flow

### Step-by-Step Process
1. **Sign Up** → Create tenant record and admin user
2. **Choose Plan** → Set up Stripe subscription
3. **Upload Knowledge Base** → File upload and processing
4. **Test ChatBot** → Verify functionality with sample queries
5. **Customize Appearance** → Branding, colors, messaging
6. **Get API Keys** → Generate public/private keys
7. **Integration** → Embed chat widget or use API
8. **Go Live!** → Monitor usage and performance

### Knowledge Base Upload Options
- **File Upload:** PDF, Word, Markdown, text files
- **URL Crawling:** Website content scraping (future)
- **API Integration:** Sync from CMS/documentation platforms (future)
- **Bulk Import:** CSV/JSON structured data

## Implementation Phases

### Phase 1A: Core Multi-Tenant Foundation (Weeks 1-3)
**Goal:** Solid multi-tenant infrastructure (FREE TIER ONLY)

**Deliverables:**
- Multi-tenant database schema implementation (no billing tables)
- Tenant-scoped vector store isolation
- Basic API key authentication system
- Simple tenant CRUD operations
- Enhanced admin panel for tenant management
- Generous free tier limits for validation

**Key Files to Modify:**
- `backend/core/config.py` - Multi-tenant configuration
- `backend/core/admin_database.py` - Tenant management
- `backend/core/unified_retriever.py` - Tenant-scoped retrieval
- `backend/routes/admin.py` - Multi-tenant admin APIs

### Phase 1B: Basic Tenant Dashboard (Week 4)
**Goal:** Simple self-service tenant interface

**Deliverables:**
- Basic Vue.js tenant dashboard (no billing UI)
- Knowledge base file upload interface
- ChatBot testing interface
- API key display and management
- Simple onboarding flow (no payments)
- Basic usage statistics display

**New Components:**
- Tenant dashboard frontend
- File upload service
- Simple onboarding wizard

### Phase 2: Billing & Monetization (Weeks 5-8)
**Goal:** Add revenue generation to proven foundation

**Deliverables:**
- Stripe subscription management
- Usage tracking and automated billing
- Plan upgrade/downgrade in existing dashboard
- Usage limit enforcement
- Email notification system
- Enhanced admin panel for billing oversight

**New Components:**
- Billing service integration
- Payment processing
- Usage monitoring and enforcement
- Marketing landing page

### Phase 3: Enhanced Features (Weeks 9-12)
**Goal:** Competitive SaaS features

**Deliverables:**
- Advanced analytics dashboard
- Team management within tenants
- ChatBot customization options
- API documentation and developer portal
- Knowledge base management UI

### Phase 4: Scale & Polish (Weeks 13-16)
**Goal:** Production-ready SaaS platform

**Deliverables:**
- Performance optimization
- Advanced security features
- Marketing website
- Customer support tools
- Monitoring and alerting

## Technical Migration Strategy

### Backward Compatibility
- Maintain current `/query` endpoint during transition
- Gradual deprecation with clear timeline
- Version headers for API routing
- Migration tools for existing users

### Data Migration Plan
1. **Current system → Tenant #1:** Convert existing data to first tenant
2. **Admin users → Super admin:** Upgrade current admin accounts  
3. **Query logs → Tenant-scoped:** Add tenant_id to existing logs
4. **Vector store → Tenant collection:** Migrate existing ChromaDB data

### Testing Strategy
- **Unit tests:** Enhanced with tenant isolation testing
- **Integration tests:** Multi-tenant API endpoint testing
- **Load testing:** Performance with multiple tenants
- **Security testing:** Tenant data isolation verification

## Infrastructure Scaling Plan

### Stage 1: Single Server (0-100 tenants)
- Multiple containers on single server
- Shared database with tenant isolation
- Basic monitoring

### Stage 2: Load Balanced (100-1000 tenants)  
- Load balancer + multiple app servers
- Managed database service
- Enhanced monitoring and alerting

### Stage 3: Microservices (1000+ tenants)
- Separate services: auth, chat, admin, billing
- Container orchestration (Kubernetes)
- Distributed caching and queuing

### Stage 4: Enterprise Scale
- Auto-scaling groups
- Multiple regions/availability zones
- Advanced security and compliance features

## Success Metrics

### Technical Metrics
- **Query response time:** < 2 seconds average
- **System uptime:** 99.9% availability
- **Tenant isolation:** Zero cross-tenant data leaks
- **Scalability:** Support 1000+ concurrent tenants

### Business Metrics
- **Customer acquisition:** Track sign-ups and conversions
- **Revenue growth:** Monthly recurring revenue (MRR)
- **Churn rate:** < 5% monthly churn
- **Usage growth:** Queries per tenant growth

## Risk Mitigation

### Technical Risks
- **Data isolation failures:** Comprehensive testing and monitoring
- **Performance degradation:** Load testing and optimization
- **Security vulnerabilities:** Regular security audits
- **Scalability bottlenecks:** Gradual scaling with monitoring

### Business Risks
- **Competition:** Focus on superior AI quality and ease of use
- **Customer churn:** Excellent onboarding and support
- **Pricing pressure:** Value-based pricing with clear ROI
- **Technical debt:** Maintain code quality during rapid development

## Next Steps

1. **Review and approve** this plan
2. **Set up project tracking** (GitHub project, milestones)
3. **Create detailed technical specifications** for Phase 1
4. **Begin database schema design** and implementation
5. **Start with tenant isolation** proof of concept

---

*This document will be updated as the project progresses and requirements evolve.*