<template>
  <div class="performance-view">
    <h1 class="text-h4 font-weight-bold mb-6">Performance Analytics</h1>
    
    <v-row class="mb-6">
      <v-col
        v-for="metric in performanceMetrics"
        :key="metric.key"
        cols="12"
        sm="6"
        lg="3"
      >
        <MetricCard
          :title="metric.title"
          :value="metric.value"
          :icon="metric.icon"
          :color="metric.color"
          :change="metric.change"
          :loading="isLoading"
        />
      </v-col>
    </v-row>
    
    <v-row>
      <v-col cols="12" lg="8">
        <PerformanceChart
          title="Response Time Timeline"
          :data="responseTimeData"
          :loading="isLoading"
          type="line"
        />
      </v-col>
      
      <v-col cols="12" lg="4">
        <PerformanceChart
          title="Throughput"
          :data="throughputData"
          :loading="isLoading"
          type="bar"
          :height="400"
        />
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { computed, onMounted, onActivated, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import { usePerformanceStore } from '@/stores/performance'
import MetricCard from '@/components/MetricCard.vue'
import PerformanceChart from '@/components/PerformanceChart.vue'

const performanceStore = usePerformanceStore()

// Use storeToRefs for proper reactivity like the dashboard does
const { metrics, chartData, isLoading } = storeToRefs(performanceStore)

const performanceMetrics = computed(() => {
  if (!metrics.value) {
    return []
  }
  
  return [
    {
      key: 'responseTime',
      title: 'Avg Response Time',
      value: `${metrics.value?.responseTime?.current || 0}ms`,
      icon: '$clock',
      color: 'primary',
      change: metrics.value?.responseTime?.change || 0
    },
    {
      key: 'throughput',
      title: 'Throughput',
      value: `${metrics.value?.throughput?.current || 0}/hr`,
      icon: '$trendUp',
      color: 'success',
      change: metrics.value?.throughput?.change || 0
    },
    {
      key: 'errorRate',
      title: 'Error Rate',
      value: `${metrics.value?.errorRate?.current || 0}%`,
      icon: '$alert',
      color: 'error',
      change: metrics.value?.errorRate?.change || 0,
      inverse: true
    },
    {
      key: 'cacheHitRate',
      title: 'Cache Hit Rate',
      value: `${metrics.value?.cacheHitRate?.current || 0}%`,
      icon: '$check',
      color: 'info',
      change: metrics.value?.cacheHitRate?.change || 0
    }
  ]
})

// Chart data computed properties with fallbacks like dashboard
const responseTimeData = computed(() => {
  return chartData.value?.responseTime || { 
    labels: [], 
    datasets: [] 
  }
})

const throughputData = computed(() => {
  return chartData.value?.throughput || { 
    labels: [], 
    datasets: [] 
  }
})

onMounted(async () => {
  // Simple direct API call like the dashboard does
  await performanceStore.refreshData()
})
</script>

<style scoped>
.performance-view {
  max-width: 1400px;
  margin: 0 auto;
}
</style>