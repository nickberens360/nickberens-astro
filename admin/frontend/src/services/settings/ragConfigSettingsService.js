import adminAPI from '@/services/api'

export class RagConfigSettingsService {
  /**
   * Get RAG configuration settings
   * @returns {Promise<Object>} RAG configuration data
   */
  async getRagConfig() {
    try {
      const response = await adminAPI.client.get('/settings/rag-config')
      return response
    } catch (error) {
      console.error('Error fetching RAG configuration:', error)
      
      // Handle specific error cases
      if (error.response?.status === 401) {
        throw new Error('Authentication required')
      } else if (error.response?.status === 403) {
        throw new Error('Access denied')
      } else if (error.response?.status === 404) {
        throw new Error('RAG configuration not found')
      } else if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail)
      } else if (error.message) {
        throw new Error(error.message)
      } else {
        throw new Error('Failed to fetch RAG configuration')
      }
    }
  }

  /**
   * Update RAG configuration settings
   * @param {Object} configData - RAG configuration object
   * @returns {Promise<Object>} Updated configuration data
   */
  async updateRagConfig(configData) {
    try {
      // Validate required fields
      if (!configData || typeof configData !== 'object') {
        throw new Error('Invalid configuration data')
      }

      const response = await adminAPI.client.put('/settings/rag-config', configData)
      return response
    } catch (error) {
      console.error('Error updating RAG configuration:', error)
      
      // Handle specific error cases
      if (error.response?.status === 400) {
        const detail = error.response.data?.detail || 'Invalid configuration data'
        throw new Error(`Validation error: ${detail}`)
      } else if (error.response?.status === 401) {
        throw new Error('Authentication required')
      } else if (error.response?.status === 403) {
        throw new Error('Access denied')
      } else if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail)
      } else if (error.message) {
        throw new Error(error.message)
      } else {
        throw new Error('Failed to update RAG configuration')
      }
    }
  }

  /**
   * Reset RAG configuration to defaults
   * @returns {Promise<Object>} Default configuration data
   */
  async resetRagConfigToDefaults() {
    try {
      // Reset by updating with default values
      const defaultConfig = {
        rag_use_mmr: false,
        rag_use_heading_splitter: false,
        rag_enable_delete: false,
        rag_safe_delete: true,
        rag_score_threshold: 0.2,
        rag_mmr_k: 4,
        rag_mmr_fetch_k: 20,
        rag_mmr_lambda_mult: 0.5,
        rag_index_dirs: 'backend/knowledge,public'
      }

      return await this.updateRagConfig(defaultConfig)
    } catch (error) {
      console.error('Error resetting RAG configuration:', error)
      throw new Error('Failed to reset RAG configuration')
    }
  }

  /**
   * Validate RAG configuration
   * @param {Object} configData - Configuration to validate
   * @returns {Promise<Object>} Validation results
   */
  async validateRagConfig(configData) {
    try {
      // Client-side validation that matches backend validation
      const errors = []
      
      if (configData.rag_score_threshold < 0.0 || configData.rag_score_threshold > 1.0) {
        errors.push('Score threshold must be between 0.0 and 1.0')
      }
      
      if (configData.rag_mmr_k < 1 || configData.rag_mmr_k > 20) {
        errors.push('MMR K must be between 1 and 20')
      }
      
      if (configData.rag_mmr_fetch_k < 10 || configData.rag_mmr_fetch_k > 100) {
        errors.push('MMR Fetch K must be between 10 and 100')
      }
      
      if (configData.rag_mmr_lambda_mult < 0.0 || configData.rag_mmr_lambda_mult > 1.0) {
        errors.push('MMR Lambda multiplier must be between 0.0 and 1.0')
      }
      
      if (!configData.rag_index_dirs || configData.rag_index_dirs.trim() === '') {
        errors.push('Index directories cannot be empty')
      }

      if (configData.rag_mmr_k > configData.rag_mmr_fetch_k) {
        errors.push('MMR K cannot be greater than MMR Fetch K')
      }

      return {
        valid: errors.length === 0,
        errors: errors
      }
    } catch (error) {
      console.error('Error validating RAG configuration:', error)
      return {
        valid: false,
        errors: ['Failed to validate configuration']
      }
    }
  }
}

const ragConfigService = new RagConfigSettingsService()

export default ragConfigService