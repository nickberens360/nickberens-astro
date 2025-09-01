<template>
  <div>
    <v-card elevation="2">
      <v-card-title class="text-h6 font-weight-bold pa-6">Settings Cache Status</v-card-title>
      <v-card-text class="pa-6">
        <v-row v-if="cacheStatus">
          <v-col cols="12" md="3">
            <v-card>
              <v-card-text class="text-center">
                <div class="text-h4 font-weight-bold text-primary">{{ cacheStatus.cache_size }}</div>
                <div class="text-body-2 text-medium-emphasis">Cache Items</div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" md="3">
            <v-card>
              <v-card-text class="text-center">
                <div class="text-h4 font-weight-bold text-info">{{ cacheStatus.ttl_seconds }}s</div>
                <div class="text-body-2 text-medium-emphasis">Cache TTL</div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" md="6">
            <v-card>
              <v-card-title class="text-subtitle-1">Cached Settings</v-card-title>
              <v-card-text>
                <v-chip
                  v-for="(cached, key) in cacheStatus.cached_settings"
                  :key="key"
                  :color="cached ? 'success' : 'warning'"
                  size="small"
                  class="mr-2 mb-2"
                >
                  {{ key }} {{ cached ? '✓' : '✗' }}
                </v-chip>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
        <div v-else class="text-center text-medium-emphasis">
          Loading cache status...
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script>
export default {
  name: 'CacheSettings',
  props: {
    cacheStatus: Object
  }
}
</script>