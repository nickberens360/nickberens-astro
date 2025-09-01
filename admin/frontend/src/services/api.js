import axios from 'axios'

class AdminAPI {
  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL,
      timeout: 10000,
      headers: { 'Content-Type': 'application/json' },
      withCredentials: true  // Enable cookies for session management
    })

    // Authentication is now handled via HTTPOnly cookies
    // No longer storing tokens in localStorage for security

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Optional: minimal dev-only logging
        if (import.meta.env.DEV && import.meta.env.VITE_DEBUG_API) {
          console.debug(`API ${config.method?.toUpperCase()}: ${config.url}`)
        }
        
        // Session-based authentication - HTTPOnly cookies are automatically sent with withCredentials: true
        // No manual Authorization header needed
        return config
      },
      (error) => {
        if (import.meta.env.DEV) {
          console.error('Request error:', error)
        }
        return Promise.reject(error)
      }
    )

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        return response.data
      },
      (error) => {
        if (import.meta.env.DEV) {
          console.error('API Error:', error.response?.data || error.message)
        }
        
        // Handle common error cases
        if (error.response?.status === 401) {
          // SECURITY FIX: Better authentication state management
          if (import.meta.env.DEV) {
            console.debug('Unauthorized access - authentication required')
          }
          
          // Trigger logout and redirect for authentication errors
          this.handleAuthenticationError()
        } else if (error.response?.status === 404) {
          if (import.meta.env.DEV) {
            console.error('API endpoint not found')
          }
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

  // Knowledge base endpoints (available on both public and admin APIs)
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

  async getKnowledgeFileContent(filename) {
    return await this.client.get(`/knowledge/files/${encodeURIComponent(filename)}/content`)
  }

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

  async refreshKnowledgeBase(forceReindex = true) {
    return await this.client.post(`/knowledge/refresh?force_reindex=${forceReindex}`)
  }

  async getRefreshStatus() {
    return await this.client.get('/knowledge/refresh/status')
  }

  async waitForRefreshCompletion(timeout = 300) {
    return await this.client.post(`/knowledge/refresh/wait?timeout=${timeout}`)
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
      
      // Session is now managed via HTTPOnly cookies
      // No need to store session_id manually
      
      return response
    } catch (error) {
      console.error('Login failed:', error)
      throw error
    }
  }

  async logout() {
    try {
      const response = await this.client.post('/auth/logout')
      // HTTPOnly cookie will be cleared by the server
      return response
    } catch (error) {
      console.error('Logout failed:', error)
      // Cookie should still be cleared by server even if logout fails
      throw error
    }
  }

  // SECURITY FIX: Handle authentication errors properly
  handleAuthenticationError() {
    if (import.meta.env.DEV) {
      console.debug('Handling authentication error - redirecting to login')
    }
    
    // In a real Vue app, you'd use router here
    // For now, trigger a page reload to the login page
    if (typeof window !== 'undefined' && window.location) {
      // Only redirect if we're not already on login page
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/admin/'
      }
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

  // Settings API methods
  async getFollowupSettings() {
    try {
      const response = await this.client.get('/settings/followup')
      return response
    } catch (error) {
      console.error('Failed to get follow-up settings:', error)
      throw error
    }
  }

  async updateFollowupSettings(settings) {
    try {
      const response = await this.client.put('/settings/followup', settings)
      return response
    } catch (error) {
      console.error('Failed to update follow-up settings:', error)
      throw error
    }
  }

  async resetFollowupSettings() {
    try {
      const response = await this.client.post('/settings/followup/reset')
      return response
    } catch (error) {
      console.error('Failed to reset follow-up settings:', error)
      throw error
    }
  }

  // New settings API methods for the hybrid configuration system
  async getResponseSettings() {
    try {
      const response = await this.client.get('/settings/response')
      return response
    } catch (error) {
      console.error('Failed to get response settings:', error)
      throw error
    }
  }

  async updateResponseSettings(settings) {
    try {
      const response = await this.client.put('/settings/response', settings)
      return response
    } catch (error) {
      console.error('Failed to update response settings:', error)
      throw error
    }
  }

  async getRoutingSettings() {
    try {
      const response = await this.client.get('/settings/routing')
      return response
    } catch (error) {
      console.error('Failed to get routing settings:', error)
      throw error
    }
  }

  async updateRoutingSettings(settings) {
    try {
      const response = await this.client.put('/settings/routing', settings)
      return response
    } catch (error) {
      console.error('Failed to update routing settings:', error)
      throw error
    }
  }

  async getFeatureFlags() {
    try {
      const response = await this.client.get('/settings/features')
      return response
    } catch (error) {
      console.error('Failed to get feature flags:', error)
      throw error
    }
  }

  async updateFeatureFlags(settings) {
    try {
      const response = await this.client.put('/settings/features', settings)
      return response
    } catch (error) {
      console.error('Failed to update feature flags:', error)
      throw error
    }
  }

  async getSettingsCacheStatus() {
    try {
      const response = await this.client.get('/settings/cache/status')
      return response
    } catch (error) {
      console.error('Failed to get settings cache status:', error)
      throw error
    }
  }

  async invalidateSettingsCache() {
    try {
      const response = await this.client.post('/settings/cache/invalidate')
      return response
    } catch (error) {
      console.error('Failed to invalidate settings cache:', error)
      throw error
    }
  }


  async resetFollowupQuestions() {
    try {
      const response = await this.client.post('/settings/followup/questions/reset')
      return response
    } catch (error) {
      console.error('Failed to reset follow-up questions:', error)
      throw error
    }
  }


  async reorderFollowupCategories(categories) {
    try {
      const response = await this.client.post('/settings/followup/categories/reorder', { categories })
      return response
    } catch (error) {
      console.error('Failed to reorder follow-up categories:', error)
      throw error
    }
  }

  // Enhanced category management with stats
  async getCategoriesWithStats(includeInactive = false) {
    try {
      const response = await this.client.get(`/settings/followup/categories/with-stats?include_inactive=${includeInactive}`)
      return response
    } catch (error) {
      console.error('Failed to get categories with stats:', error)
      throw error
    }
  }

  async validateCategoryDeletion(categoryId) {
    try {
      const response = await this.client.get(`/settings/followup/categories/${categoryId}/validate-deletion`)
      return response
    } catch (error) {
      console.error('Failed to validate category deletion:', error)
      throw error
    }
  }

  async deleteCategoryWithStrategy(categoryId, strategy, targetCategoryId = null) {
    try {
      const response = await this.client.post(`/settings/followup/categories/${categoryId}/delete`, {
        strategy,
        target_category_id: targetCategoryId
      })
      return response
    } catch (error) {
      console.error('Failed to delete category with strategy:', error)
      throw error
    }
  }

  // New normalized question management
  async getFollowupQuestions(params = {}) {
    try {
      const searchParams = new URLSearchParams()
      if (params.category_id) searchParams.append('category_id', params.category_id)
      if (params.active_only !== undefined) searchParams.append('active_only', params.active_only)
      if (params.search) searchParams.append('search', params.search)
      if (params.limit) searchParams.append('limit', params.limit)
      if (params.offset) searchParams.append('offset', params.offset)

      const response = await this.client.get(`/settings/followup/questions?${searchParams}`)
      return response
    } catch (error) {
      console.error('Failed to get followup questions:', error)
      throw error
    }
  }

  async getFollowupQuestion(questionId) {
    try {
      const response = await this.client.get(`/settings/followup/questions/${questionId}`)
      return response
    } catch (error) {
      console.error('Failed to get followup question:', error)
      throw error
    }
  }

  async createFollowupQuestion(questionData) {
    try {
      const response = await this.client.post('/settings/followup/questions', questionData)
      return response
    } catch (error) {
      console.error('Failed to create followup question:', error)
      throw error
    }
  }

  async updateFollowupQuestion(questionId, questionData) {
    try {
      const response = await this.client.put(`/settings/followup/questions/${questionId}`, questionData)
      return response
    } catch (error) {
      console.error('Failed to update followup question:', error)
      throw error
    }
  }

  async deleteFollowupQuestion(questionId) {
    try {
      const response = await this.client.delete(`/settings/followup/questions/${questionId}`)
      return response
    } catch (error) {
      console.error('Failed to delete followup question:', error)
      throw error
    }
  }

  async bulkUpdateQuestions(operations) {
    try {
      const response = await this.client.post('/settings/followup/questions/bulk', { operations })
      return response
    } catch (error) {
      console.error('Failed to bulk update questions:', error)
      throw error
    }
  }

  async searchFollowupQuestions(query, categoryId = null, limit = 20) {
    try {
      const searchParams = new URLSearchParams()
      searchParams.append('query', query)
      if (categoryId) searchParams.append('category_id', categoryId)
      searchParams.append('limit', limit)

      const response = await this.client.get(`/settings/followup/questions/search?${searchParams}`)
      return response
    } catch (error) {
      console.error('Failed to search followup questions:', error)
      throw error
    }
  }

  // Additional normalized API methods for the unified interface
  async getFollowupCategories(includeInactive = true) {
    try {
      const response = await this.client.get(`/settings/followup/categories?include_inactive=${includeInactive}`)
      return response
    } catch (error) {
      console.error('Failed to get followup categories normalized:', error)
      throw error
    }
  }

  async createFollowupCategory(categoryData) {
    try {
      const response = await this.client.post('/settings/followup/categories', categoryData)
      return response
    } catch (error) {
      console.error('Failed to create followup category normalized:', error)
      throw error
    }
  }

  async updateFollowupCategory(categoryId, categoryData) {
    try {
      const response = await this.client.put(`/settings/followup/categories/${categoryId}`, categoryData)
      return response
    } catch (error) {
      console.error('Failed to update followup category normalized:', error)
      throw error
    }
  }

  async deleteFollowupCategoryWithStrategy(deleteRequest) {
    try {
      const response = await this.client.post(`/settings/followup/categories/${deleteRequest.categoryId}/delete`, {
        strategy: deleteRequest.strategy,
        target_category_id: deleteRequest.targetCategoryId
      })
      return response
    } catch (error) {
      console.error('Failed to delete followup category with strategy:', error)
      throw error
    }
  }

  async getFollowupCategoryStats(categoryId) {
    try {
      const response = await this.client.get(`/settings/followup/categories/${categoryId}/stats`)
      return response
    } catch (error) {
      console.error('Failed to get followup category stats:', error)
      // Return default stats instead of throwing to prevent UI breaking
      return { question_count: 0, active_questions: 0 }
    }
  }

  async getFollowupCategoryStatsNormalized(categoryId) {
    try {
      const response = await this.client.get(`/settings/followup/categories/${categoryId}/stats`)
      return response
    } catch (error) {
      console.error('Failed to get followup category stats normalized:', error)
      // Return default stats instead of throwing to prevent UI breaking
      return { question_count: 0, active_questions: 0 }
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

  // Authentication token methods removed - now using HTTPOnly cookies exclusively
  // These methods are kept for backward compatibility but do nothing
  setAuthToken(token) {
    console.warn('setAuthToken deprecated - using HTTPOnly cookies')
  }

  clearAuthToken() {
    console.warn('clearAuthToken deprecated - using HTTPOnly cookies')
  }
}

// Create and export singleton instance
export const adminAPI = new AdminAPI()
export default adminAPI