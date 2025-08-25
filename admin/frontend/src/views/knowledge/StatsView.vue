<template>
  <div class="stats-view">
    <div class="d-flex justify-space-between align-center mb-6">
      <h2 class="text-h5">Knowledge Base Statistics</h2>
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

    <!-- Content Type Distribution -->
    <v-card elevation="2" class="mb-6">
      <v-card-title class="text-h6">
        <v-icon class="me-2">$chart</v-icon>
        Content Type Distribution
      </v-card-title>
      <v-card-text>
        <div v-if="Object.keys(stats.content_types || {}).length > 0" class="pa-4">
          <v-row>
            <v-col
              v-for="(count, type) in stats.content_types"
              :key="type"
              cols="12"
              sm="6"
              md="4"
            >
              <div class="d-flex align-center justify-space-between pa-2">
                <div class="d-flex align-center">
                  <v-chip
                    :color="getContentTypeColor(type)"
                    size="small"
                    class="me-2"
                  >
                    {{ type }}
                  </v-chip>
                </div>
                <div class="text-h6">{{ count }}</div>
              </div>
              <v-progress-linear
                :model-value="getPercentage(count)"
                :color="getContentTypeColor(type)"
                height="8"
                rounded
              />
            </v-col>
          </v-row>
        </div>
        <div v-else class="pa-4 text-center text-medium-emphasis">
          No content type data available
        </div>
      </v-card-text>
    </v-card>

    <!-- Additional Information -->
    <v-card elevation="2">
      <v-card-title class="text-h6">
        <v-icon class="me-2">$info</v-icon>
        Additional Information
      </v-card-title>
      <v-card-text class="pa-4">
        <v-row>
          <v-col cols="12" md="6">
            <div class="mb-3">
              <div class="text-subtitle-2 text-medium-emphasis mb-1">Embedding Model</div>
              <div class="text-body-1">{{ embeddingModel }}</div>
            </div>
            <div class="mb-3">
              <div class="text-subtitle-2 text-medium-emphasis mb-1">Collection Name</div>
              <div class="text-body-1">unified_knowledge</div>
            </div>
          </v-col>
          <v-col cols="12" md="6">
            <div class="mb-3">
              <div class="text-subtitle-2 text-medium-emphasis mb-1">Average Chunks per Document</div>
              <div class="text-body-1">{{ averageChunksPerDocument }}</div>
            </div>
            <div class="mb-3">
              <div class="text-subtitle-2 text-medium-emphasis mb-1">Last Updated</div>
              <div class="text-body-1">{{ formatDate(new Date()) }}</div>
            </div>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { adminAPI } from '@/services/api'

const loading = ref(false)
const stats = ref({
  total_documents: 0,
  total_chunks: 0,
  unique_sources: 0,
  content_types: {}
})
const embeddingModel = ref('text-embedding-3-small')

const averageChunksPerDocument = computed(() => {
  if (!stats.value.total_documents || !stats.value.total_chunks) return '0'
  return (stats.value.total_chunks / stats.value.total_documents).toFixed(1)
})

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

const getPercentage = (count) => {
  const total = Object.values(stats.value.content_types || {}).reduce((a, b) => a + b, 0)
  return total > 0 ? (count / total) * 100 : 0
}

const formatDate = (date) => {
  return new Date(date).toLocaleString()
}

const loadStats = async () => {
  loading.value = true
  try {
    const response = await adminAPI.getKnowledgeStats()
    stats.value = response
  } catch (error) {
    console.error('Failed to load knowledge stats:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadStats()
})
</script>

<style scoped>
.stats-view {
  padding: 24px;
}
</style>