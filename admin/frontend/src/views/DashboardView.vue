<template>
  <div class="dashboard">
    <h1 class="text-h4 font-weight-bold mb-6">Dashboard Overview</h1>
    
    <!-- Metric Cards Grid -->
    <v-row class="mb-6">
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
          :change="metric.change"
          :loading="cardsLoading"
          clickable
          @click="handleMetricClick(metric)"
        />
      </v-col>
    </v-row>
    
    <!-- Charts Row -->
    <v-row>
      <v-col cols="12" md="8">
        <PerformanceChart
          title="Response Time Trend"
          :data="responseTimeChartData"
          :loading="isLoading"
          type="line"
        />
      </v-col>
      
      <v-col cols="12" md="4">
        <PerformanceChart
          title="Query Status Distribution"
          :data="statusChartData"
          :loading="isLoading"
          type="doughnut"
          :height="350"
        />
      </v-col>
    </v-row>
    
    <!-- Recent Queries Table -->
    <v-row class="mt-6">
      <v-col cols="12">
        <QueryTable
          title="Recent Queries"
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
import MetricCard from '@/components/MetricCard.vue'
import PerformanceChart from '@/components/PerformanceChart.vue'
import QueryTable from '@/components/QueryTable.vue'

const router = useRouter()
const adminStore = useAdminStore()
const queriesStore = useQueriesStore()

// Computed properties - use storeToRefs for reactivity
const { stats, isLoading } = storeToRefs(adminStore)

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
  if (import.meta.env.DEV && stats.value) {
    console.log('Stats data:', stats.value)
    console.log('totalQueriesChange:', stats.value?.totalQueriesChange)
    console.log('averageResponseTimeChange:', stats.value?.averageResponseTimeChange) 
    console.log('uniqueSessionsChange:', stats.value?.uniqueSessionsChange)
    console.log('errorRateChange:', stats.value?.errorRateChange)
  }
  
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

// Mock chart data - in real app, this would come from stores
const responseTimeChartData = computed(() => ({
  labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
  datasets: [{
    label: 'Response Time (ms)',
    data: [450, 520, 380, 420, 360, 400],
    borderColor: '#1976D2',
    backgroundColor: 'rgba(25, 118, 210, 0.1)',
    tension: 0.4
  }]
}))

const statusChartData = computed(() => {
  // Use real data from stats if available
  const errorRate = stats.value?.errorRate || 0
  const successRate = 100 - errorRate
  
  return {
    labels: ['Success', 'Error'],
    datasets: [{
      data: [successRate, errorRate],
      backgroundColor: ['#4CAF50', '#FF5252']
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
  console.log('Selected query:', query)
  // Could navigate to query details or show modal
}

// Lifecycle
onMounted(async () => {
  // Initialize data - the stores will handle API calls
  await Promise.all([
    adminStore.fetchStats(),
    queriesStore.fetchQueries({ limit: 10 })
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