<template>
  <div class="content-view">
    <!-- Header -->
    <div class="d-flex justify-space-between align-center mb-6">
      <div>
        <h2 class="text-h5">Content Gaps</h2>
        <p class="text-body-1 text-medium-emphasis mt-1">
          Monitor and manage content gaps in your knowledge base
        </p>
      </div>
      
      <v-btn
        color="primary"
        variant="outlined"
        prepend-icon="$chart"
        @click="showAnalytics = !showAnalytics"
      >
        {{ showAnalytics ? 'Hide' : 'Show' }} Analytics
      </v-btn>
    </div>

    <!-- Analytics Cards (Optional) -->
    <div v-show="showAnalytics" class="mb-6">
      <v-row>
        <v-col cols="12" md="3">
          <v-card variant="outlined">
            <v-card-text class="text-center">
              <div class="text-h4 font-weight-bold text-warning">{{ stats.total || 0 }}</div>
              <div class="text-body-2 text-medium-emphasis">Total Gaps</div>
            </v-card-text>
          </v-card>
        </v-col>
        
        <v-col cols="12" md="3">
          <v-card variant="outlined">
            <v-card-text class="text-center">
              <div class="text-h4 font-weight-bold text-error">{{ stats.unresolved || 0 }}</div>
              <div class="text-body-2 text-medium-emphasis">Unresolved</div>
            </v-card-text>
          </v-card>
        </v-col>
        
        <v-col cols="12" md="3">
          <v-card variant="outlined">
            <v-card-text class="text-center">
              <div class="text-h4 font-weight-bold text-success">{{ stats.resolved || 0 }}</div>
              <div class="text-body-2 text-medium-emphasis">Resolved</div>
            </v-card-text>
          </v-card>
        </v-col>
        
        <v-col cols="12" md="3">
          <v-card variant="outlined">
            <v-card-text class="text-center">
              <div class="text-h4 font-weight-bold text-info">{{ stats.avgScore || '0.00' }}</div>
              <div class="text-body-2 text-medium-emphasis">Avg Score</div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </div>

    <!-- Content Gaps Table -->
    <ContentGapsTable @stats-updated="updateStats" />

    <!-- Help Section -->
    <v-card class="mt-6" variant="tonal" color="info">
      <v-card-text>
        <div class="d-flex align-start gap-3">
          <v-icon color="info">$info</v-icon>
          <div>
            <h3 class="text-body-1 font-weight-bold mb-2">About Content Gaps</h3>
            <p class="text-body-2 mb-2">
              Content gaps are automatically detected when queries have low similarity scores (< 0.7) 
              or result in errors. These indicate areas where your knowledge base might need improvement.
            </p>
            <ul class="text-body-2">
              <li><strong>Pattern:</strong> Normalized query pattern to group similar issues</li>
              <li><strong>Count:</strong> Number of times this pattern has occurred</li>
              <li><strong>Avg Score:</strong> Average similarity score for queries matching this pattern</li>
              <li><strong>Sample Query:</strong> Example of an actual query that triggered this gap</li>
            </ul>
          </div>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import ContentGapsTable from '@/components/ContentGapsTable.vue'

// Reactive state
const showAnalytics = ref(true)
const stats = ref({
  total: 0,
  unresolved: 0,
  resolved: 0,
  avgScore: '0.00'
})

// Methods
const updateStats = (newStats) => {
  stats.value = newStats
}
</script>

<style scoped>
.content-view {
  max-width: 1400px;
  margin: 0 auto;
}
</style>