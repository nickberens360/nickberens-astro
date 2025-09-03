<template>
  <div>
    <v-card elevation="2">
      <v-card-title class="text-h6 font-weight-bold pa-6 d-flex align-center justify-space-between">
        <span>Settings Cache Status</span>
        <v-btn-group variant="outlined" density="comfortable">
          <v-btn
            color="warning"
            prepend-icon="$refresh"
            @click="invalidateCache"
            :loading="store.loading"
            variant="elevated"
            class="mr-3"
          >
            Clear Cache
          </v-btn>
          <v-btn
            color="primary"
            prepend-icon="$refresh"
            @click="refreshStatus"
            :loading="store.loading"
            variant="elevated"
          >
            Refresh
          </v-btn>
        </v-btn-group>
      </v-card-title>
      
      <v-card-text class="pa-6">
        <v-alert v-if="store.error" type="error" variant="tonal" class="mb-4">
          {{ store.error }}
        </v-alert>
        
        <v-row v-if="store.cacheStatus">
          <v-col cols="12" md="3">
            <v-card variant="tonal">
              <v-card-text class="text-center">
                <div class="text-h4 font-weight-bold text-primary">{{ store.cacheStatus.cache_size || 0 }}</div>
                <div class="text-body-2 text-medium-emphasis">Cache Items</div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" md="3">
            <v-card variant="tonal">
              <v-card-text class="text-center">
                <div class="text-h4 font-weight-bold text-info">{{ store.cacheStatus.ttl_seconds || 0 }}s</div>
                <div class="text-body-2 text-medium-emphasis">Cache TTL</div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" md="6">
            <v-card variant="tonal">
              <v-card-title class="text-subtitle-1">Cached Settings</v-card-title>
              <v-card-text>
                <div v-if="store.cacheStatus.cached_settings && Object.keys(store.cacheStatus.cached_settings).length > 0">
                  <v-chip
                    v-for="(cached, key) in store.cacheStatus.cached_settings"
                    :key="key"
                    :color="cached ? 'success' : 'warning'"
                    size="small"
                    class="mr-2 mb-2"
                  >
                    {{ key }} {{ cached ? '✓' : '✗' }}
                  </v-chip>
                </div>
                <div v-else class="text-body-2 text-medium-emphasis">
                  No cached settings data
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
        
        <div v-else-if="store.loading" class="text-center py-8">
          <v-progress-circular indeterminate color="primary" size="48" />
          <div class="text-body-1 text-medium-emphasis mt-4">
            Loading cache status...
          </div>
        </div>
        
        <v-alert v-else type="info" variant="tonal">
          No cache status data available
        </v-alert>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useCacheSettingsStore } from '@/stores/cacheSettings'
import { useNotifications } from '@/composables/useNotifications'

const store = useCacheSettingsStore()
const { showSuccess, showError } = useNotifications()

onMounted(() => {
  store.loadData()
})

const invalidateCache = async () => {
  try {
    await store.invalidateCache()
    showSuccess('Settings cache invalidated successfully!')
  } catch (err) {
    showError(`Failed to invalidate cache: ${err.message}`)
  }
}

const refreshStatus = async () => {
  try {
    await store.loadData()
    showSuccess('Cache status refreshed!')
  } catch (err) {
    showError(`Failed to refresh status: ${err.message}`)
  }
}
</script>