import axios from 'axios'

class AdminAPI {
  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL,
      timeout: 10000,
      headers: { 'Content-Type': 'application/json' },
      withCredentials: true  // Enable cookies for session management
    })

    // Runtime token container
    this.authToken = null

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Optional: minimal dev-only logging
        if (import.meta.env.DEV) {
          console.log(`Making ${config.method?.toUpperCase()} request to ${config.url}`)
        }
        // Session-based authentication - cookies are automatically sent with withCredentials: true
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
          console.error('Unauthorized access - authentication required')
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
  async getContentGaps(params = {}) {
    const { resolved = false, limit = 50 } = params
    return await this.client.get(`/content/gaps?resolved=${resolved}&limit=${limit}`)
  }

  async updateContentGap(gapId, data) {
    const params = new URLSearchParams()
    if (data.resolved !== undefined) params.append('resolved', data.resolved)
    if (data.notes !== undefined) params.append('notes', data.notes)
    return await this.client.patch(`/content/gaps/${gapId}?${params}`)
  }

  async getPopularTopics(timeRange = '7d') {
    return await this.client.get(`/content/popular-topics?time_range=${timeRange}`)
  }

  async getSourceUsage() {
    return await this.client.get('/content/sources')
  }

  // Legacy method for backward compatibility
  async markGapResolved(gapId) {
    return this.updateContentGap(gapId, { resolved: true })
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

  async getKnowledgeDocuments(limit = 100, offset = 0) {
    return await this.client.get(`/knowledge/documents?limit=${limit}&offset=${offset}`)
  }

  async getKnowledgeSources() {
    return await this.client.get('/knowledge/sources')
  }

  async getDocumentContent(documentId) {
    return await this.client.get(`/knowledge/documents/${documentId}`)
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
    }, {
      timeout: 30000  // 30 second timeout for file saves with re-indexing
    })
  }

  async updateKnowledgeSource(sourcePath, updateData) {
    return await this.client.put(`/knowledge/sources/${encodeURIComponent(sourcePath)}`, updateData)
  }

  async deleteKnowledgeSource(sourcePath) {
    return await this.client.delete(`/knowledge/sources/${encodeURIComponent(sourcePath)}`)
  }

  // Authentication endpoints
  async login(username, password) {
    try {
      const response = await this.client.post('/auth/login', {
        username,
        password
      })
      
      if (response.success && response.session_id) {
        this.setAuthToken(response.session_id)
      }
      
      return response
    } catch (error) {
      console.error('Login failed:', error)
      throw error
    }
  }

  async logout() {
    try {
      const response = await this.client.post('/auth/logout')
      this.clearAuthToken()
      return response
    } catch (error) {
      console.error('Logout failed:', error)
      this.clearAuthToken() // Clear token even if logout fails
      throw error
    }
  }

  async getCurrentUser() {
    try {
      return await this.client.get('/auth/me')
    } catch (error) {
      console.error('Failed to get current user:', error)
      throw error
    }
  }

  async createUser(userData) {
    try {
      return await this.client.post('/auth/create-user', userData)
    } catch (error) {
      console.error('Failed to create user:', error)
      throw error
    }
  }

  async changePassword(currentPassword, newPassword) {
    try {
      return await this.client.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      })
    } catch (error) {
      console.error('Failed to change password:', error)
      throw error
    }
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

  setAuthToken(token) {
    this.authToken = token
    if (typeof localStorage !== 'undefined') localStorage.setItem('admin_token', token)
  }

  clearAuthToken() {
    this.authToken = null
    if (typeof localStorage !== 'undefined') localStorage.removeItem('admin_token')
  }
}

// Create and export singleton instance
export const adminAPI = new AdminAPI()
export default adminAPI