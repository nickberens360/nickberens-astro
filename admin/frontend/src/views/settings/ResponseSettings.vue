<template>
  <div>
    <v-card elevation="2">
      <v-card-title class="text-h6 font-weight-bold pa-6 d-flex align-center justify-space-between">
        <span>Response Generation Settings</span>
        <v-btn
          color="primary"
          variant="elevated"
          @click="saveSettings"
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
        
        <v-row>
          <v-col cols="12" md="6">
            <v-text-field
              v-model.number="store.settings.max_context_length"
              label="Max Context Length"
              type="number"
              variant="outlined"
              :min="100"
              :max="10000"
              hint="Maximum character length for context documents"
              persistent-hint
            />
          </v-col>
          
          <v-col cols="12" md="6">
            <v-text-field
              v-model.number="store.settings.max_context_documents"
              label="Max Context Documents"
              type="number"
              variant="outlined"
              :min="1"
              :max="10"
              hint="Maximum number of documents to include in context"
              persistent-hint
            />
          </v-col>
          
          <v-col cols="12" md="6">
            <v-slider
              v-model="store.settings.context_fill_ratio"
              label="Context Fill Ratio"
              :min="0.1"
              :max="1.0"
              :step="0.1"
              thumb-label="always"
              show-ticks="always"
              color="primary"
              hint="Ratio of context to fill with relevant documents"
              persistent-hint
            />
          </v-col>
          
          <v-col cols="12" md="6">
            <v-switch
              v-model="store.settings.enable_caching"
              label="Enable Response Caching"
              color="primary"
              inset
              hide-details
            />
            <div class="text-caption text-medium-emphasis mt-2">
              Cache responses to improve performance for repeated queries
            </div>
          </v-col>
          
          <v-col cols="12" md="6">
            <v-text-field
              v-model.number="store.settings.cache_ttl_seconds"
              label="Cache TTL (seconds)"
              type="number"
              variant="outlined"
              :min="60"
              :max="86400"
              hint="How long to keep cached responses (60s - 24h)"
              persistent-hint
              :disabled="!store.settings.enable_caching"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useResponseSettingsStore } from '@/stores/responseSettings'
import { useNotifications } from '@/composables/useNotifications'

const store = useResponseSettingsStore()
const { showSuccess, showError } = useNotifications()

onMounted(() => {
  store.loadData()
})

const saveSettings = async () => {
  try {
    await store.updateSettings()
    showSuccess('Response settings saved successfully!')
  } catch (err) {
    showError(`Failed to save settings: ${err.message}`)
  }
}
</script>