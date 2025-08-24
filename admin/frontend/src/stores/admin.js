import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import adminAPI from '@/services/api'
import { TimeRanges } from '@/types/admin'

export const useAdminStore = defineStore('admin', () => {
  // State
  const stats = ref({
    totalQueries: 0,
    averageResponseTime: 0,
    successRate: 0,
    cacheHitRate: 0,
    activeSessions: 0,
    errorRate: 0,
    totalSources: 0,
    totalTopics: 0
  })

  const systemHealth = ref({
    status: 'unknown',
    uptime: 0,
    version: '1.0.0',
    lastUpdated: null
  })

  const timeRange = ref(TimeRanges.DAY)
  const isLoading = ref(false)
  const lastUpdate = ref(null)
  const error = ref(null)
  const isConnected = ref(false)

  // Getters
  const formattedStats = computed(() => ({
    ...stats.value,
    averageResponseTime: `${stats.value.averageResponseTime}ms`,
    successRate: `${stats.value.successRate}%`,
    cacheHitRate: `${stats.value.cacheHitRate}%`,
    errorRate: `${stats.value.errorRate}%`
  }))

  const needsRefresh = computed(() => {
    if (!lastUpdate.value) return true
    const now = new Date()
    const lastUpdateTime = new Date(lastUpdate.value)
    const refreshInterval = parseInt(import.meta.env.VITE_REFRESH_INTERVAL) || 30000
    return now - lastUpdateTime > refreshInterval
  })

  const isHealthy = computed(() => {
    return systemHealth.value.status === 'healthy' && stats.value.errorRate < 10
  })

  // Actions
  const initialize = async () => {
    console.log('Initializing admin store...')
    await testConnection()
    if (isConnected.value) {
      await Promise.all([
        fetchStats(),
        fetchSystemHealth()
      ])
      startAutoRefresh()
    }
  }

  const testConnection = async () => {
    try {
      isConnected.value = await adminAPI.testConnection()
      if (isConnected.value) {
        error.value = null
        console.log('Successfully connected to admin API')
      } else {
        error.value = 'Unable to connect to admin API'
        console.error('Failed to connect to admin API')
      }
    } catch (err) {
      isConnected.value = false
      error.value = adminAPI.formatError(err)
      console.error('Connection test failed:', err)
    }
    return isConnected.value
  }

  const fetchStats = async (days = 7) => {
    if (isLoading.value) return

    isLoading.value = true
    error.value = null

    try {
      console.log('Fetching stats with days:', days)
      const data = await adminAPI.getStats(days)
      console.log('Raw API response:', data)
      
      // Update stats with received data - fix field mappings
      stats.value = {
        totalQueries: data.total_queries || 0,
        averageResponseTime: Math.round(data.avg_response_time_ms || 0),
        successRate: Math.round((1 - (data.error_rate || 0)) * 100), // Calculate from error rate
        cacheHitRate: Math.round((data.cache_hit_rate || 0) * 100),
        activeSessions: data.unique_sessions || 0, // Use unique_sessions as active sessions
        errorRate: Math.round((data.error_rate || 0) * 100),
        totalSources: data.total_sources || 0,
        totalTopics: data.total_topics || 0,
        queriesToday: data.queries_today || 0,
        queriesThisWeek: data.queries_this_week || 0,
        helpfulRate: Math.round((data.helpful_rate || 0) * 100)
      }
      
      lastUpdate.value = new Date().toISOString()
      console.log('Stats updated:', stats.value)
      console.log('Stats reactive value:', stats.value)
      console.log('Setting isLoading to false after successful stats fetch')
    } catch (err) {
      error.value = adminAPI.formatError(err)
      console.error('Failed to fetch stats:', err)
    } finally {
      isLoading.value = false
    }
  }

  const fetchSystemHealth = async () => {
    try {
      const data = await adminAPI.getSystemHealth()
      systemHealth.value = {
        status: data.status || 'unknown',
        uptime: data.uptime || 0,
        version: data.version || '1.0.0',
        lastUpdated: new Date().toISOString(),
        ...data
      }
      console.log('System health updated:', systemHealth.value)
    } catch (err) {
      console.error('Failed to fetch system health:', err)
      systemHealth.value.status = 'error'
    }
  }

  const setTimeRange = async (newTimeRange) => {
    if (timeRange.value !== newTimeRange) {
      timeRange.value = newTimeRange
      
      // Convert time range to days for API
      const daysMap = {
        [TimeRanges.HOUR]: 0.04,
        [TimeRanges.SIX_HOURS]: 0.25,
        [TimeRanges.DAY]: 1,
        [TimeRanges.WEEK]: 7,
        [TimeRanges.MONTH]: 30
      }
      
      const days = daysMap[newTimeRange] || 7
      await fetchStats(days)
    }
  }

  const refreshData = async () => {
    console.log('Refreshing admin data...')
    await Promise.all([
      fetchStats(),
      fetchSystemHealth()
    ])
  }

  let refreshInterval = null

  const startAutoRefresh = () => {
    if (refreshInterval) {
      clearInterval(refreshInterval)
    }

    const interval = parseInt(import.meta.env.VITE_REFRESH_INTERVAL) || 30000
    refreshInterval = setInterval(() => {
      if (needsRefresh.value) {
        refreshData()
      }
    }, interval)

    console.log(`Auto-refresh started with ${interval}ms interval`)
  }

  const stopAutoRefresh = () => {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
      console.log('Auto-refresh stopped')
    }
  }

  const resetError = () => {
    error.value = null
  }

  // Cleanup function for when store is no longer used
  const cleanup = () => {
    stopAutoRefresh()
  }

  return {
    // State
    stats,
    systemHealth,
    timeRange,
    isLoading,
    lastUpdate,
    error,
    isConnected,

    // Getters
    formattedStats,
    needsRefresh,
    isHealthy,

    // Actions
    initialize,
    testConnection,
    fetchStats,
    fetchSystemHealth,
    setTimeRange,
    refreshData,
    startAutoRefresh,
    stopAutoRefresh,
    resetError,
    cleanup
  }
})