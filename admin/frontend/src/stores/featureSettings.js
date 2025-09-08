import { defineStore } from 'pinia'
import { ref } from 'vue'
import { featureSettingsService } from '@/services/settings/featureSettingsService'

export const useFeatureSettingsStore = defineStore('featureSettings', () => {
  const featureFlags = ref({
    // Legacy feature flags
    enable_illustrations: true,
    enable_geolocation: true,
    enable_analytics: true,
    enable_debug_logging: false,
    enable_response_caching: true,
    enable_query_preprocessing: true,
    enable_followup_questions: true,
    enable_smart_routing: true,
    enable_caching: true,
    enable_debug_mode: false,
    enable_maintenance_mode: false,
    enable_rate_limiting: true,
    enable_api_versioning: false,
    
    // RAG Best Practices Settings - Boolean Toggles
    rag_use_mmr: false,
    rag_use_heading_splitter: true,
    rag_enable_delete: false,
    rag_safe_delete: true,
    
    // RAG Best Practices Settings - Numeric Settings
    rag_score_threshold: 0.2,
    rag_mmr_k: 4,
    rag_mmr_fetch_k: 20,
    rag_mmr_lambda_mult: 0.5,
    
    // RAG Best Practices Settings - String/Array Settings
    rag_index_dirs: "backend/knowledge,public"
  })

  const loading = ref(false)
  const error = ref(null)

  const loadData = async () => {
    try {
      loading.value = true
      error.value = null
      const data = await featureSettingsService.getFeatureFlags()
      if (data) {
        Object.assign(featureFlags.value, data)
      }
    } catch (err) {
      console.error('Failed to load feature flags:', err)
      error.value = err.message || 'Failed to load feature flags'
    } finally {
      loading.value = false
    }
  }

  const updateFeatureFlags = async (updatedFlags = null) => {
    try {
      loading.value = true
      error.value = null
      const dataToSave = updatedFlags || featureFlags.value
      await featureSettingsService.updateFeatureFlags(dataToSave)
      if (updatedFlags) {
        Object.assign(featureFlags.value, updatedFlags)
      }
    } catch (err) {
      console.error('Failed to update feature flags:', err)
      error.value = err.message || 'Failed to update feature flags'
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateFeatureFlag = (key, value) => {
    featureFlags.value[key] = value
  }

  const clearError = () => {
    error.value = null
  }

  return {
    featureFlags,
    loading,
    error,
    loadData,
    updateFeatureFlags,
    updateFeatureFlag,
    clearError
  }
})