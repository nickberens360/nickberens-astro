import axios from 'axios'

class AdminAPI {
  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${import.meta.env.VITE_ADMIN_TOKEN}`
      }
    })

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        console.log(`Making ${config.method?.toUpperCase()} request to ${config.url}`)
        return config
      },
      (error) => {
        console.error('Request error:', error)
        return Promise.reject(error)
      }
    )

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        return response.data
      },
      (error) => {
        console.error('API Error:', error.response?.data || error.message)
        
        // Handle common error cases
        if (error.response?.status === 401) {
          // Handle unauthorized access
          console.error('Unauthorized access - check admin token')
        } else if (error.response?.status === 404) {
          console.error('API endpoint not found')
        } else if (error.response?.status >= 500) {
          console.error('Server error')
        }
        
        return Promise.reject(error)
      }
    )
  }

  // Stats endpoints
  async getStats(days = 7) {
    return await this.client.get(`/stats/overview?days=${days}`)
  }

  async getSystemHealth() {
    return await this.client.get('/health')
  }

  // Query endpoints
  async getQueries(params = {}) {
    const searchParams = new URLSearchParams()
    
    // Convert page to offset
    if (params.page && params.limit) {
      const offset = (params.page - 1) * params.limit
      searchParams.append('offset', offset)
    }
    if (params.limit) searchParams.append('limit', params.limit)
    if (params.search) searchParams.append('search', params.search)
    if (params.startDate) searchParams.append('start_date', params.startDate)
    if (params.endDate) searchParams.append('end_date', params.endDate)
    if (params.errorOnly) searchParams.append('errors_only', params.errorOnly)
    if (params.minRelevance) searchParams.append('min_relevance', params.minRelevance)
    if (params.sortBy) searchParams.append('sort_by', params.sortBy)
    if (params.sortOrder) searchParams.append('sort_order', params.sortOrder)

    return await this.client.get(`/queries?${searchParams.toString()}`)
  }

  async getQuery(id) {
    return await this.client.get(`/queries/${id}`)
  }

  async updateQueryFeedback(id, feedback) {
    return await this.client.post(`/queries/${id}/feedback`, { feedback })
  }

  async getQueryInsights() {
    return await this.client.get('/queries/insights')
  }

  // Performance endpoints
  async getPerformanceMetrics(timeRange = '24h') {
    return await this.client.get(`/performance/metrics?time_range=${timeRange}`)
  }

  async getPerformanceTimeline(days = 7, interval = 'hour') {
    return await this.client.get(`/performance/timeline?days=${days}&interval=${interval}`)
  }

  async getResponseTimePercentiles(timeRange = '24h') {
    return await this.client.get(`/performance/percentiles?time_range=${timeRange}`)
  }

  // Content endpoints
  async getContentGaps() {
    return await this.client.get('/content/gaps')
  }

  async getPopularTopics(timeRange = '7d') {
    return await this.client.get(`/content/topics?time_range=${timeRange}`)
  }

  async getSourceUsage() {
    return await this.client.get('/content/sources')
  }

  async markGapResolved(gapId) {
    return await this.client.post(`/content/gaps/${gapId}/resolve`)
  }

  // Session endpoints
  async getSessions(params = {}) {
    const searchParams = new URLSearchParams()
    
    if (params.page) searchParams.append('page', params.page)
    if (params.limit) searchParams.append('limit', params.limit)
    if (params.active) searchParams.append('active', params.active)
    if (params.startDate) searchParams.append('start_date', params.startDate)
    if (params.endDate) searchParams.append('end_date', params.endDate)

    return await this.client.get(`/sessions?${searchParams.toString()}`)
  }

  async getSessionDetails(sessionId) {
    return await this.client.get(`/sessions/${sessionId}`)
  }

  async getSessionAnalytics() {
    return await this.client.get('/sessions/analytics')
  }

  // Export endpoints
  async exportQueries(params = {}) {
    const searchParams = new URLSearchParams()
    
    if (params.format) searchParams.append('format', params.format)
    if (params.startDate) searchParams.append('start_date', params.startDate)
    if (params.endDate) searchParams.append('end_date', params.endDate)
    if (params.includeResponses) searchParams.append('include_responses', params.includeResponses)

    const response = await this.client.get(`/export/queries?${searchParams.toString()}`, {
      responseType: 'blob'
    })
    
    return response
  }

  async exportPerformanceReport(timeRange = '7d') {
    const response = await this.client.get(`/export/performance?time_range=${timeRange}`, {
      responseType: 'blob'
    })
    
    return response
  }

  // Knowledge base endpoints
  async uploadKnowledgeFiles(formData) {
    return await this.client.post('/knowledge/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  }

  async getKnowledgeFiles() {
    return await this.client.get('/knowledge/files')
  }

  async deleteKnowledgeFile(filename) {
    return await this.client.delete(`/knowledge/files/${encodeURIComponent(filename)}`)
  }

  async getKnowledgeStats() {
    return await this.client.get('/knowledge/stats')
  }

  async refreshKnowledgeBase(forceReindex = true) {
    return await this.client.post(`/knowledge/refresh?force_reindex=${forceReindex}`)
  }

  async getRefreshStatus() {
    return await this.client.get('/knowledge/refresh/status')
  }

  async waitForRefreshCompletion(timeout = 300) {
    return await this.client.post(`/knowledge/refresh/wait?timeout=${timeout}`)
  }

  async getKnowledgeFileContent(filename) {
    return await this.client.get(`/knowledge/files/${encodeURIComponent(filename)}/content`)
  }

  async updateKnowledgeFileContent(filename, content) {
    return await this.client.put(`/knowledge/files/${encodeURIComponent(filename)}/content`, {
      content: content
    })
  }

  // Utility methods
  async testConnection() {
    try {
      await this.client.get('/health')
      return true
    } catch (error) {
      return false
    }
  }

  formatError(error) {
    if (error.response?.data?.detail) {
      return error.response.data.detail
    } else if (error.response?.data?.message) {
      return error.response.data.message
    } else if (error.message) {
      return error.message
    } else {
      return 'An unknown error occurred'
    }
  }
}

// Create and export singleton instance
export const adminAPI = new AdminAPI()
export default adminAPI