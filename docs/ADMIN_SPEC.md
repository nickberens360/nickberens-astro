# RAG Admin Dashboard Feature Specification

## Project Overview
Create an admin dashboard to monitor and analyze the RAG (Retrieval-Augmented Generation) portfolio chatbot system. The dashboard will provide insights into user queries, system performance, content gaps, and overall health metrics.

## Technical Stack
- **Frontend Framework**: Vue 3 with Vuetify 3
- **Backend**: FastAPI (Python)
- **Database**: SQLite3
- **Directory Structure**: `/admin` folder in project root

## Directory Structure
```
/your-project-root
├── /admin
│   ├── /frontend
│   │   ├── /src
│   │   │   ├── /components
│   │   │   ├── /views
│   │   │   ├── /stores
│   │   │   ├── /services
│   │   │   ├── App.vue
│   │   │   └── main.js
│   │   ├── package.json
│   │   └── vite.config.js
│   ├── /backend
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── routes.py
│   │   └── analytics.py
│   ├── rag_monitoring.db (SQLite database)
│   └── README.md
├── /backend (existing RAG system)
└── /frontend (existing portfolio site)
```

## Database Schema

### SQLite Tables

```sql
-- Main query logging table
CREATE TABLE query_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    user_query TEXT NOT NULL,
    system_response TEXT,
    response_time_ms REAL,
    llm_provider TEXT,
    llm_model TEXT,
    vector_search_score REAL,
    sources_used TEXT, -- JSON array
    follow_up_questions TEXT, -- JSON array
    cache_hit BOOLEAN DEFAULT 0,
    error_occurred BOOLEAN DEFAULT 0,
    error_message TEXT,
    user_feedback TEXT, -- 'helpful', 'not_helpful', null
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- User sessions
CREATE TABLE user_sessions (
    id TEXT PRIMARY KEY,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_active_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_queries INTEGER DEFAULT 0,
    user_agent TEXT,
    ip_address TEXT
);

-- Aggregated metrics (calculated every hour)
CREATE TABLE hourly_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hour DATETIME,
    total_queries INTEGER,
    unique_sessions INTEGER,
    avg_response_time_ms REAL,
    p95_response_time_ms REAL,
    cache_hit_rate REAL,
    error_rate REAL,
    helpful_rate REAL
);

-- Content gaps tracking
CREATE TABLE content_gaps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_pattern TEXT,
    occurrence_count INTEGER DEFAULT 1,
    avg_similarity_score REAL,
    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved BOOLEAN DEFAULT 0
);

-- Create indexes
CREATE INDEX idx_query_logs_timestamp ON query_logs(timestamp DESC);
CREATE INDEX idx_query_logs_session ON query_logs(session_id);
CREATE INDEX idx_query_logs_errors ON query_logs(error_occurred);
CREATE INDEX idx_sessions_active ON user_sessions(last_active_at DESC);
```

## Backend API Endpoints

### Base URL: `/admin/api`

#### Authentication
- Use simple token-based auth via query parameter or header
- Token stored in environment variable

#### Endpoints

1. **GET /stats/overview**
    - Query params: `?days=7` (default 7)
    - Returns: Overall statistics including total queries, avg response time, error rate, etc.

2. **GET /queries**
    - Query params: `?limit=50&offset=0&search=&errors_only=false&start_date=&end_date=`
    - Returns: Paginated list of queries with all details

3. **GET /queries/:id**
    - Returns: Detailed information about a specific query

4. **POST /queries/:id/feedback**
    - Body: `{ "feedback": "helpful" | "not_helpful" }`
    - Updates user feedback for a query

5. **GET /performance/metrics**
    - Query params: `?time_range=24h` (options: 1h, 6h, 24h, 7d, 30d)
    - Returns: Performance metrics with percentiles

6. **GET /performance/timeline**
    - Query params: `?days=7&interval=hour` (interval: hour, day)
    - Returns: Time series data for charts

7. **GET /content/gaps**
    - Returns: Queries with low relevance scores or no good matches

8. **GET /content/popular-topics**
    - Returns: Most queried topics/themes

9. **GET /sessions**
    - Query params: `?active_only=false&limit=50`
    - Returns: User session information

10. **GET /export/csv**
    - Query params: `?start_date=&end_date=&type=queries|metrics`
    - Returns: CSV file download

## Frontend Components

### Views (Vuetify 3)

1. **Dashboard Overview** (`/admin`)
    - Key metrics cards (v-card)
    - Real-time query count
    - Performance gauges
    - Recent alerts/errors

2. **Query Explorer** (`/admin/queries`)
    - Searchable data table (v-data-table-server)
    - Filters: date range, errors only, search text
    - Expandable rows for full response
    - Quick feedback buttons
    - Color coding for errors/slow queries

3. **Performance Analytics** (`/admin/performance`)
    - Response time chart (line chart)
    - Query volume timeline
    - Cache hit rate visualization
    - LLM provider comparison

4. **Content Insights** (`/admin/content`)
    - Popular topics word cloud or bar chart
    - Low-confidence queries list
    - Content gap analysis
    - Suggested improvements

5. **Sessions View** (`/admin/sessions`)
    - Active sessions counter
    - Session duration histogram
    - Geographic distribution (if tracking)

### Key Components

```javascript
// Component structure
/components
  ├── MetricCard.vue        // Reusable metric display card
  ├── QueryTable.vue        // Main query data table
  ├── PerformanceChart.vue  // Chart.js wrapper for metrics
  ├── TimeRangeSelector.vue // Date/time range picker
  ├── ExportDialog.vue      // CSV export options
  └── FeedbackButton.vue    // Quick feedback widget
```

## Features to Implement

### Phase 1: Core Monitoring
1. **Query Logging Integration**
    - Modify existing chat endpoint to log all queries
    - Track performance metrics
    - Store in SQLite database

2. **Basic Dashboard**
    - Overview stats page
    - Query browser with search
    - Simple performance metrics

3. **Error Tracking**
    - Flag and display failed queries
    - Show error messages and stack traces
    - Alert on high error rates

### Phase 2: Analytics
1. **Performance Analysis**
    - Response time percentiles
    - Cache effectiveness
    - LLM provider performance comparison

2. **Content Insights**
    - Identify frequently asked topics
    - Find queries with poor results
    - Track which sources are most used

3. **User Behavior**
    - Session analysis
    - Query patterns
    - Follow-up question effectiveness

### Phase 3: Advanced Features
1. **Real-time Updates**
    - WebSocket for live query monitoring
    - Real-time metric updates
    - Active user count

2. **Alerts & Notifications**
    - Performance degradation alerts
    - Error rate threshold alerts
    - Daily/weekly summary emails

3. **Export & Reporting**
    - Scheduled reports
    - Custom date range exports
    - Integration with analytics tools

## Implementation Details

### Backend Integration Points

```python
# In existing chat endpoint, add logging:
async def log_query(
    session_id: str,
    query: str,
    response: str,
    response_time: float,
    metadata: dict
):
    # Insert into SQLite database
    pass

# Add middleware to track sessions
@app.middleware("http")
async def track_session(request: Request, call_next):
    # Extract or create session ID
    # Update last_active_at
    pass
```

### Frontend State Management (Pinia)

```javascript
// stores/admin.js
export const useAdminStore = defineStore('admin', {
  state: () => ({
    stats: {},
    queries: [],
    isLoading: false,
    timeRange: '24h'
  }),
  actions: {
    async fetchStats() {},
    async fetchQueries() {},
    async updateFeedback() {}
  }
})
```

### Vuetify 3 Theme Configuration

```javascript
// vuetify configuration
const vuetify = createVuetify({
  theme: {
    themes: {
      light: {
        colors: {
          primary: '#1976D2',
          secondary: '#424242',
          accent: '#82B1FF',
          error: '#FF5252',
          info: '#2196F3',
          success: '#4CAF50',
          warning: '#FFC107'
        }
      }
    }
  }
})
```

## Security Considerations

1. **Authentication**
    - Admin token in environment variable
    - Middleware to check auth on all admin routes
    - No sensitive data in frontend

2. **Data Privacy**
    - Option to anonymize user queries
    - Configurable data retention period
    - No PII in logs

3. **Rate Limiting**
    - Limit export endpoints
    - Throttle expensive analytics queries

## Performance Requirements

1. Dashboard should load in < 2 seconds
2. Query search should return results in < 500ms
3. Charts should update smoothly with animations
4. Support up to 10,000 queries in the data table
5. Export should handle up to 100,000 records

## Development Setup

```bash
# Admin backend setup
cd admin/backend
pip install fastapi uvicorn sqlite3 pandas

# Admin frontend setup  
cd admin/frontend
npm create vue@latest .
npm install vuetify@next @mdi/font chart.js pinia axios
```

## Testing Requirements

1. Unit tests for analytics calculations
2. API endpoint tests
3. Frontend component tests
4. E2E tests for critical paths
5. Load testing for performance

## Deployment

1. Admin runs as separate service on different port (e.g., 8001)
2. SQLite database file with proper backups
3. Environment variables for configuration
4. For production, configure your hosting service to route /admin/* to the admin service

## Success Metrics

1. Admin can identify poorly performing queries within 5 clicks
2. Loading any view takes less than 2 seconds
3. Can export 30 days of data in under 10 seconds
4. Clear visibility into system health at a glance

## Additional Notes

- Use Vuetify's built-in dark mode support
- Implement responsive design for mobile access
- Add keyboard shortcuts for common actions
- Include tooltips for all metrics
- Provide contextual help/documentation