import { defineStore } from 'pinia'
import { ref } from 'vue'
import { cacheSettingsService } from '@/services/settings/cacheSettingsService'

export const useCacheSettingsStore = defineStore('cacheSettings', () => {
  const cacheStatus = ref({
    cache_size: 0,
    ttl_seconds: 3600,
    cached_settings: {}
  })

  const loading = ref(false)
  const error = ref(null)

  const loadData = async () => {
    try {
      loading.value = true
      error.value = null
      const data = await cacheSettingsService.getCacheStatus()
      if (data) {
        cacheStatus.value = data
      }
    } catch (err) {
      console.error('Failed to load cache status:', err)
      error.value = err.message || 'Failed to load cache status'
    } finally {
      loading.value = false
    }
  }

  const invalidateCache = async () => {
    try {
      loading.value = true
      error.value = null
      await cacheSettingsService.invalidateCache()
      // Reload cache status after invalidation
      await loadData()
    } catch (err) {
      console.error('Failed to invalidate cache:', err)
      error.value = err.message || 'Failed to invalidate cache'
      throw err
    } finally {
      loading.value = false
    }
  }

  const clearError = () => {
    error.value = null
  }

  return {
    cacheStatus,
    loading,
    error,
    loadData,
    invalidateCache,
    clearError
  }
})