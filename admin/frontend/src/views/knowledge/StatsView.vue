<template>
  <div class="stats-view">
    <div class="d-flex justify-space-between align-center mb-6">
      <h2 class="text-h5">Knowledge Analytics</h2>
      <v-btn
        color="primary"
        prepend-icon="$refresh"
        @click="loadStats"
        :loading="loading"
        variant="outlined"
      >
        Refresh
      </v-btn>
    </div>

    <!-- Key Metrics Row -->
    <v-row class="mb-6">
      <v-col cols="12" md="3">
        <v-card elevation="2">
          <v-card-text class="text-center">
            <div class="text-h3 font-weight-bold" :class="getHealthColor()">
              {{ contentHealthScore }}%
            </div>
            <div class="text-subtitle-1">Content Health Score</div>
            <v-progress-linear
              :model-value="contentHealthScore"
              :color="getHealthColor()"
              height="4"
              rounded
              class="mt-2"
            />
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card elevation="2">
          <v-card-text class="text-center">
            <div class="text-h3 font-weight-bold text-blue">
              {{ stats.total_documents || 0 }}
            </div>
            <div class="text-subtitle-1">Total Documents</div>
            <div class="text-caption text-medium-emphasis">
              {{ averageChunksPerSource }} chunks/source
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card elevation="2">
          <v-card-text class="text-center">
            <div class="text-h3 font-weight-bold text-purple">
              {{ dominantContentType }}
            </div>
            <div class="text-subtitle-1">Dominant Type</div>
            <div class="text-caption text-medium-emphasis">
              {{ dominantPercentage }}% of content
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="3">
        <v-card elevation="2">
          <v-card-text class="text-center">
            <div class="text-h3 font-weight-bold text-orange">
              {{ contentDiversity }}
            </div>
            <div class="text-subtitle-1">Content Diversity</div>
            <div class="text-caption text-medium-emphasis">
              {{ Object.keys(stats.content_types || {}).length }} unique types
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Charts Row -->
    <v-row class="mb-6">
      <v-col cols="12" md="6">
        <v-card elevation="2">
          <v-card-title class="text-h6">
            <v-icon class="me-2">$chart</v-icon>
            Content Distribution
          </v-card-title>
          <v-card-text>
            <canvas ref="pieChart" style="max-height: 300px;"></canvas>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card elevation="2">
          <v-card-title class="text-h6">
            <v-icon class="me-2">$bar_chart</v-icon>
            Top Content Types
          </v-card-title>
          <v-card-text>
            <canvas ref="barChart" style="max-height: 300px;"></canvas>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Insights and Recommendations -->
    <v-row class="mb-6">
      <v-col cols="12" md="6">
        <v-card elevation="2">
          <v-card-title class="text-h6">
            <v-icon class="me-2">$lightbulb</v-icon>
            Content Insights
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item v-for="insight in contentInsights" :key="insight.title">
                <template v-slot:prepend>
                  <v-icon :color="insight.color" size="small">{{ insight.icon }}</v-icon>
                </template>
                <v-list-item-title>{{ insight.title }}</v-list-item-title>
                <v-list-item-subtitle>{{ insight.description }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card elevation="2">
          <v-card-title class="text-h6">
            <v-icon class="me-2">$recommend</v-icon>
            Recommendations
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item v-for="rec in recommendations" :key="rec.title">
                <template v-slot:prepend>
                  <v-chip :color="rec.priority" size="x-small" class="me-2">
                    {{ rec.priority }}
                  </v-chip>
                </template>
                <v-list-item-title>{{ rec.title }}</v-list-item-title>
                <v-list-item-subtitle>{{ rec.action }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Detailed Content Type Table -->
    <v-card elevation="2">
      <v-card-title class="text-h6 d-flex align-center">
        <v-icon class="me-2">$table</v-icon>
        Detailed Content Analysis
        <v-spacer />
        <v-text-field
          v-model="typeSearch"
          density="compact"
          variant="outlined"
          placeholder="Search types..."
          hide-details
          style="max-width: 300px"
        />
      </v-card-title>
      <v-card-text class="pa-0">
        <v-data-table
          :headers="contentHeaders"
          :items="contentTableItems"
          :search="typeSearch"
          density="compact"
        >
          <template v-slot:item.type="{ item }">
            <v-chip
              :color="getContentTypeColor(item.type)"
              size="small"
            >
              {{ item.type }}
            </v-chip>
          </template>
          <template v-slot:item.percentage="{ item }">
            <div class="d-flex align-center">
              <v-progress-linear
                :model-value="item.percentage"
                :color="getContentTypeColor(item.type)"
                height="20"
                rounded
                class="me-2"
                style="min-width: 100px"
              >
                <template v-slot:default>
                  <span class="text-caption">{{ item.percentage.toFixed(1) }}%</span>
                </template>
              </v-progress-linear>
            </div>
          </template>
          <template v-slot:item.status="{ item }">
            <v-chip
              :color="getStatusColor(item.status)"
              size="x-small"
              variant="outlined"
            >
              {{ item.status }}
            </v-chip>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { adminAPI } from '@/services/api'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const loading = ref(false)
const typeSearch = ref('')
const pieChart = ref(null)
const barChart = ref(null)
let pieChartInstance = null
let barChartInstance = null

const stats = ref({
  total_documents: 0,
  total_chunks: 0,
  unique_sources: 0,
  content_types: {}
})

const contentHeaders = [
  { title: 'Content Type', key: 'type', sortable: true },
  { title: 'Documents', key: 'count', sortable: true },
  { title: 'Distribution', key: 'percentage', sortable: true },
  { title: 'Status', key: 'status', sortable: true }
]

// Computed properties for metrics
const contentHealthScore = computed(() => {
  const types = Object.keys(stats.value.content_types || {})
  const totalTypes = types.length
  const totalDocs = stats.value.total_documents || 1
  const avgDocsPerType = totalDocs / Math.max(totalTypes, 1)

  // Calculate balance score
  const values = Object.values(stats.value.content_types || {})
  const maxCount = Math.max(...values, 1)
  const minCount = Math.min(...values, 0)
  const balance = minCount / maxCount * 100

  // Diversity score
  const diversityScore = Math.min(totalTypes / 8 * 100, 100)

  // Combined health score
  return Math.round((balance * 0.4 + diversityScore * 0.6))
})

const averageChunksPerSource = computed(() => {
  if (!stats.value.unique_sources) return '0'
  return (stats.value.total_chunks / stats.value.unique_sources).toFixed(1)
})

const dominantContentType = computed(() => {
  const types = stats.value.content_types || {}
  if (Object.keys(types).length === 0) return 'None'

  const sorted = Object.entries(types).sort((a, b) => b[1] - a[1])
  return sorted[0][0]
})

const dominantPercentage = computed(() => {
  const types = stats.value.content_types || {}
  const total = Object.values(types).reduce((a, b) => a + b, 0)
  if (total === 0) return 0

  const sorted = Object.entries(types).sort((a, b) => b[1] - a[1])
  return ((sorted[0]?.[1] || 0) / total * 100).toFixed(1)
})

const contentDiversity = computed(() => {
  const types = Object.values(stats.value.content_types || {})
  if (types.length === 0) return 'Low'

  const total = types.reduce((a, b) => a + b, 0)
  const avg = total / types.length
  const variance = types.reduce((sum, val) => sum + Math.pow(val - avg, 2), 0) / types.length
  const stdDev = Math.sqrt(variance)
  const cv = stdDev / avg

  if (cv < 0.3) return 'High'
  if (cv < 0.6) return 'Medium'
  return 'Low'
})

const contentTableItems = computed(() => {
  const types = stats.value.content_types || {}
  const total = Object.values(types).reduce((a, b) => a + b, 0) || 1

  return Object.entries(types)
    .map(([type, count]) => {
      const percentage = (count / total) * 100
      let status = 'Balanced'
      if (percentage > 30) status = 'Dominant'
      else if (percentage < 5) status = 'Underrepresented'

      return {
        type,
        count,
        percentage,
        status
      }
    })
    .sort((a, b) => b.count - a.count)
})

const contentInsights = computed(() => {
  const insights = []
  const types = stats.value.content_types || {}
  const total = Object.values(types).reduce((a, b) => a + b, 0) || 1

  // Find underrepresented types
  const underrepresented = Object.entries(types)
    .filter(([_, count]) => (count / total) * 100 < 5)
    .map(([type]) => type)

  if (underrepresented.length > 0) {
    insights.push({
      icon: '$warning',
      color: 'warning',
      title: 'Coverage Gaps Detected',
      description: `${underrepresented.join(', ')} content types are underrepresented`
    })
  }

  // Check for imbalance
  const values = Object.values(types)
  if (values.length > 0) {
    const maxCount = Math.max(...values)
    const minCount = Math.min(...values)
    if (maxCount / minCount > 10) {
      insights.push({
        icon: '$info',
        color: 'info',
        title: 'Content Imbalance',
        description: 'Significant variation in content type distribution'
      })
    }
  }

  // Positive insights
  if (Object.keys(types).length >= 6) {
    insights.push({
      icon: '$check_circle',
      color: 'success',
      title: 'Good Content Diversity',
      description: 'Knowledge base covers multiple content areas'
    })
  }

  return insights
})

const recommendations = computed(() => {
  const recs = []
  const types = stats.value.content_types || {}
  const total = Object.values(types).reduce((a, b) => a + b, 0) || 1

  // Find gaps
  const commonTypes = ['technical', 'experience', 'skills', 'about', 'project', 'creative']
  const missingTypes = commonTypes.filter(type => !types[type] || types[type] < 5)

  if (missingTypes.length > 0) {
    recs.push({
      priority: 'high',
      title: 'Add Missing Content',
      action: `Consider adding ${missingTypes.slice(0, 3).join(', ')} content`
    })
  }

  // Check for dominant types
  const dominant = Object.entries(types)
    .filter(([_, count]) => (count / total) * 100 > 30)
    .map(([type]) => type)

  if (dominant.length > 0) {
    recs.push({
      priority: 'medium',
      title: 'Balance Content',
      action: `${dominant[0]} is dominant, diversify other areas`
    })
  }

  // Chunk optimization
  if (stats.value.total_chunks / stats.value.unique_sources > 20) {
    recs.push({
      priority: 'low',
      title: 'Optimize Chunking',
      action: 'Consider adjusting chunk size for better retrieval'
    })
  }

  return recs
})

// Helper functions
const getContentTypeColor = (type) => {
  const colorMap = {
    'technical': 'blue',
    'experience': 'green',
    'skills': 'orange',
    'about': 'purple',
    'creative': 'pink',
    'project': 'teal',
    'code': 'indigo',
    'documentation': 'cyan'
  }
  return colorMap[type?.toLowerCase()] || 'grey'
}

const getHealthColor = () => {
  if (contentHealthScore.value >= 70) return 'text-success'
  if (contentHealthScore.value >= 40) return 'text-warning'
  return 'text-error'
}

const getStatusColor = (status) => {
  if (status === 'Balanced') return 'success'
  if (status === 'Dominant') return 'warning'
  return 'error'
}

const updateCharts = () => {
  if (!stats.value.content_types) return

  const types = Object.entries(stats.value.content_types || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8) // Top 8 for visibility

  const labels = types.map(([type]) => type)
  const data = types.map(([_, count]) => count)
  const colors = types.map(([type]) => {
    const color = getContentTypeColor(type)
    const colorMap = {
      'blue': '#2196F3',
      'green': '#4CAF50',
      'orange': '#FF9800',
      'purple': '#9C27B0',
      'pink': '#E91E63',
      'teal': '#009688',
      'indigo': '#3F51B5',
      'cyan': '#00BCD4',
      'grey': '#9E9E9E'
    }
    return colorMap[color] || '#9E9E9E'
  })

  // Update pie chart
  if (pieChart.value) {
    if (pieChartInstance) {
      pieChartInstance.destroy()
    }

    const ctx = pieChart.value.getContext('2d')
    pieChartInstance = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data,
          backgroundColor: colors,
          borderWidth: 2,
          borderColor: '#fff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            position: 'right',
            labels: {
              padding: 10,
              font: {
                size: 11
              }
            }
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                const total = context.dataset.data.reduce((a, b) => a + b, 0)
                const percentage = ((context.parsed / total) * 100).toFixed(1)
                return `${context.label}: ${context.parsed} (${percentage}%)`
              }
            }
          }
        }
      }
    })
  }

  // Update bar chart
  if (barChart.value) {
    if (barChartInstance) {
      barChartInstance.destroy()
    }

    const ctx = barChart.value.getContext('2d')
    barChartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Document Count',
          data,
          backgroundColor: colors.map(c => c + '80'), // Add transparency
          borderColor: colors,
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              precision: 0
            }
          }
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                return `${context.parsed.y} documents`
              }
            }
          }
        }
      }
    })
  }
}

const loadStats = async () => {
  loading.value = true
  try {
    const response = await adminAPI.getKnowledgeStats()
    stats.value = response
    await nextTick()
    updateCharts()
  } catch (error) {
    console.error('Failed to load knowledge stats:', error)
  } finally {
    loading.value = false
  }
}

watch(stats, () => {
  updateCharts()
}, { deep: true })

onMounted(() => {
  loadStats()
})
</script>

<style scoped>

.v-card {
  margin-bottom: 16px;
}
</style>