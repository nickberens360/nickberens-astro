<template>
  <div class="dashboard">
    <!-- Health Status -->
    <HealthStatusCard />
    <!-- Diagnostics Status -->
    <DiagnosticsCard />
    <!-- Metric Cards Grid -->
    <v-row class="ds-mb-6">
      <v-col
        v-for="metric in metrics"
        :key="metric.key"
        cols="12"
        sm="6"
        lg="3"
      >
        <MetricCard
          :title="metric.title"
          :value="metric.value"
          :unit="metric.unit"
          :icon="metric.icon"
          :color="metric.color"
          :loading="cardsLoading"
          clickable
          @click="handleMetricClick(metric)"
        />
      </v-col>
    </v-row>
    
    <!-- Charts Row -->
    <v-row class="ds-mb-6">
      <!-- Left Side: Response Time Chart -->
      <v-col
        cols="12"
        lg="8"
      >
        <PerformanceChart
          title="Response Time Timeline"
          :data="responseTimeChartData"
          :loading="isLoading || performanceLoading"
          type="line"
        />
      </v-col>
      
      <!-- Right Side: Donut Chart -->
      <v-col
        cols="12"
        lg="4"
      >
        <PerformanceChart
          title="Query Status Distribution"
          :data="statusChartData"
          :loading="isLoading"
          type="doughnut"
          :height="400"
        />
      </v-col>
    </v-row>
    
    <!-- Full Width Queries Table -->
    <v-row>
      <v-col cols="12">
        <QueryTable
          title="All Queries"
          @query-selected="handleQuerySelected"
        />
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useAdminStore } from '@/stores/admin'
import { useQueriesStore } from '@/stores/queries'
import { usePerformanceStore } from '@/stores/performance'
import MetricCard from '@/components/MetricCard.vue'
import HealthStatusCard from '@/components/HealthStatusCard.vue'
import DiagnosticsCard from '@/components/DiagnosticsCard.vue'
import PerformanceChart from '@/components/PerformanceChart.vue'
import QueryTable from '@/components/QueryTable.vue'

const router = useRouter()
const adminStore = useAdminStore()
const queriesStore = useQueriesStore()
const performanceStore = usePerformanceStore()

// Computed properties - use storeToRefs for reactivity
const { stats, isLoading } = storeToRefs(adminStore)
const { chartData: performanceChartData, isLoading: performanceLoading } = storeToRefs(performanceStore)

// Computed property for loading state to ensure reactivity
const cardsLoading = computed(() => {
  // Force loading to false if we have stats data
  if (stats.value && stats.value.totalQueries !== undefined) {
    return false
  }
  return isLoading.value
})

const metrics = computed(() => {
  // Debug logging to see what data we're getting
  // Debug stats data (development only)
  // Stats validation and processing...
  
  return [
    {
      key: 'totalQueries',
      title: 'Total Queries',
      value: stats.value?.totalQueries || 0,
      icon: '$search',
      color: 'primary',
      change: stats.value?.totalQueriesChange ?? 0
    },
    {
      key: 'avgResponseTime',
      title: 'Avg Response Time',
      value: stats.value?.averageResponseTime || 0,
      unit: 'ms',
      icon: '$clock',
      color: 'info',
      change: stats.value?.averageResponseTimeChange ?? 0,
      inverse: true
    },
    {
      key: 'successRate',
      title: 'Success Rate',
      value: stats.value?.successRate || 0,
      unit: '%',
      icon: '$check',
      color: 'success',
      change: stats.value?.errorRateChange != null ? -stats.value.errorRateChange : 0,
      inverse: true
    },
    {
      key: 'activeSessions',
      title: 'Active Sessions',
      value: stats.value?.activeSessions || 0,
      icon: '$users',
      color: 'warning',
      change: stats.value?.uniqueSessionsChange ?? 0
    }
  ]
})

// Real-time response time chart data from performance store
const responseTimeChartData = computed(() => {
  return performanceChartData.value?.responseTime || {
    labels: [],
    datasets: [{
      label: 'Response Time (ms)',
      data: [],
      borderColor: '#1976D2',
      backgroundColor: 'rgba(25, 118, 210, 0.1)',
      tension: 0.4
    }]
  }
})

const statusChartData = computed(() => {
  // Use real data from stats if available
  const errorRate = stats.value?.errorRate || 0
  const successRate = 100 - errorRate
  
  return {
    labels: ['Success', 'Error'],
    datasets: [{
      data: [successRate, errorRate],
      backgroundColor: ['#4CAF50', '#FF5252'],
      borderWidth: 0,
      hoverBorderWidth: 3,
      hoverBorderColor: '#fff'
    }]
  }
})

// Methods
const handleMetricClick = (metric) => {
  // Navigate to relevant page based on metric
  switch (metric.key) {
    case 'totalQueries':
      router.push('/admin/queries')
      break
    case 'avgResponseTime':
    case 'successRate':
      router.push('/admin/performance')
      break
    case 'activeSessions':
      router.push('/admin/sessions')
      break
  }
}

const handleQuerySelected = (query) => {
  // Handle query selection
  // Could navigate to query details or show modal
}

// Lifecycle
onMounted(async () => {
  // Initialize data - the stores will handle API calls
  await Promise.all([
    adminStore.fetchStats(),
    queriesStore.fetchQueries({ limit: 10 }),
    performanceStore.refreshData()
  ])
})

onUnmounted(() => {
  // Cleanup if needed
})
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}
</style>
