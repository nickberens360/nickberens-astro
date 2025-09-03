<template>
  <div>
    <v-card elevation="2">
      <v-card-title class="text-h6 font-weight-bold pa-6 d-flex align-center justify-space-between">
        <span>Query Routing Settings</span>
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
            <v-switch
              v-model="store.settings.enable_smart_routing"
              label="Enable Smart Routing"
              color="primary"
              inset
              hide-details
            />
            <div class="text-caption text-medium-emphasis mt-2">
              Use intelligent routing algorithms for query processing
            </div>
          </v-col>
          
          <v-col cols="12" md="6">
            <v-switch
              v-model="store.settings.enable_fuzzy_matching"
              label="Enable Fuzzy Matching"
              color="primary"
              inset
              hide-details
            />
            <div class="text-caption text-medium-emphasis mt-2">
              Allow approximate string matching for better results
            </div>
          </v-col>
          
          <v-col cols="12" md="6">
            <v-slider
              v-model="store.settings.similarity_threshold"
              label="Similarity Threshold"
              :min="0.0"
              :max="1.0"
              :step="0.1"
              thumb-label="always"
              show-ticks="always"
              color="primary"
              hint="Minimum similarity score for matching results"
              persistent-hint
            />
          </v-col>
          
          <v-col cols="12" md="6">
            <v-text-field
              v-model.number="store.settings.max_search_results"
              label="Max Search Results"
              type="number"
              variant="outlined"
              :min="1"
              :max="100"
              hint="Maximum number of search results to return"
              persistent-hint
            />
          </v-col>
          
          <v-col cols="12" md="6">
            <v-slider
              v-model="store.settings.fuzzy_threshold"
              label="Fuzzy Threshold"
              :min="0.0"
              :max="1.0"
              :step="0.1"
              thumb-label="always"
              show-ticks="always"
              color="primary"
              :disabled="!store.settings.enable_fuzzy_matching"
              hint="Threshold for fuzzy string matching accuracy"
              persistent-hint
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoutingSettingsStore } from '@/stores/routingSettings'
import { useNotifications } from '@/composables/useNotifications'

const store = useRoutingSettingsStore()
const { showSuccess, showError } = useNotifications()

onMounted(() => {
  store.loadData()
})

const saveSettings = async () => {
  try {
    await store.updateSettings()
    showSuccess('Routing settings saved successfully!')
  } catch (err) {
    showError(`Failed to save settings: ${err.message}`)
  }
}
</script>