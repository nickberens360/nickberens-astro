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
      
      <v-card-text class="pa-0">
        <v-alert v-if="store.error" type="error" variant="tonal" class="ma-6 mb-4">
          {{ store.error }}
        </v-alert>
        
        <div v-if="store.featureFlags && Object.keys(store.featureFlags).length > 0">
          <div 
            v-for="(value, key, index) in store.featureFlags" 
            :key="key"
          >
            <div class="feature-row">
              <div class="feature-content">
                <div class="feature-left">
                  <div class="feature-info">
                    <div class="feature-title text-high-emphasis">{{ formatFeatureName(key) }}</div>
                    <div class="feature-description text-medium-emphasis">{{ getFeatureDescription(key) }}</div>
                  </div>
                </div>
                <div class="feature-right">
                  <v-switch
                    v-model="store.featureFlags[key]"
                    color="primary"
                    inset
                    hide-details
                  />
                  <div class="feature-status text-medium-emphasis">
                    {{ store.featureFlags[key] ? 'Enabled' : 'Disabled' }}
                  </div>
                </div>
              </div>
            </div>
            <v-divider v-if="index < Object.keys(store.featureFlags).length - 1"></v-divider>
          </div>
        </div>
        
        <v-alert
          v-else
          type="info"
          variant="tonal"
          class="ma-6"
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

<style scoped>
/* Feature Flags Row Layout */
.feature-row {
  padding: 20px 24px;
}

.feature-row:last-child {
  border-bottom: none;
}

.feature-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 48px;
}

.feature-left {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}

.feature-info {
  flex: 1;
  min-width: 0;
}

.feature-title {
  font-size: 16px;
  font-weight: 500;
  line-height: 1.4;
  margin-bottom: 4px;
}

.feature-description {
  font-size: 14px;
  line-height: 1.4;
}

.feature-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  margin-left: 24px;
}

.feature-status {
  font-size: 14px;
  margin-left: 12px;
  font-weight: 500;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .feature-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .feature-right {
    width: 100%;
    margin-left: 0;
    justify-content: flex-start;
  }
}
</style>
