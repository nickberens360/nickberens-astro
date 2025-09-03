<template>
  <div>
    <v-card elevation="2">
      <v-card-title class="text-h6 font-weight-bold pa-6 d-flex align-center justify-space-between">
        <span>Feature Flags</span>
        <v-btn
          color="primary"
          variant="elevated"
          @click="saveFeatureFlags"
          :loading="store.loading"
          prepend-icon="$check"
        >
          Save Changes
        </v-btn>
      </v-card-title>
      
      <v-card-text class="pa-6">
        <v-alert v-if="store.error" type="error" variant="tonal" class="mb-4">
          {{ store.error }}
        </v-alert>
        
        <v-row v-if="store.featureFlags && Object.keys(store.featureFlags).length > 0">
          <v-col 
            cols="12" 
            md="6" 
            lg="4" 
            v-for="(value, key) in store.featureFlags" 
            :key="key"
          >
            <v-switch
              v-model="store.featureFlags[key]"
              :label="formatFeatureName(key)"
              color="primary"
              inset
              hide-details
              class="mb-2"
            />
            <div class="text-caption text-medium-emphasis ml-12">
              {{ getFeatureDescription(key) }}
            </div>
          </v-col>
        </v-row>
        
        <v-alert
          v-else
          type="info"
          variant="tonal"
        >
          No feature flags available
        </v-alert>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useFeatureSettingsStore } from '@/stores/featureSettings'
import { useNotifications } from '@/composables/useNotifications'

const store = useFeatureSettingsStore()
const { showSuccess, showError } = useNotifications()

onMounted(() => {
  store.loadData()
})

const formatFeatureName = (key) => {
  return key
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

const getFeatureDescription = (key) => {
  const descriptions = {
    enable_illustrations: 'Show illustration images in responses',
    enable_geolocation: 'Use location-based query processing',
    enable_analytics: 'Collect and analyze usage statistics',
    enable_debug_logging: 'Enable detailed debug logging',
    enable_response_caching: 'Cache responses for better performance',
    enable_query_preprocessing: 'Preprocess queries for better accuracy'
  }
  return descriptions[key] || 'Feature flag setting'
}

const saveFeatureFlags = async () => {
  try {
    await store.updateFeatureFlags()
    showSuccess('Feature flags updated successfully!')
  } catch (err) {
    showError(`Failed to save feature flags: ${err.message}`)
  }
}
</script>
