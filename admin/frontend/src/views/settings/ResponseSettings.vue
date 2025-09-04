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
      
      <v-card-text class="pa-0">
        <v-alert v-if="store.error" type="error" variant="tonal" class="ma-6 mb-4">
          {{ store.error }}
        </v-alert>
        
        <!-- Max Context Length Row -->
        <div class="response-row">
          <div class="response-content">
            <div class="response-left">
              <v-icon color="primary" class="response-icon">$text</v-icon>
              <div class="response-info">
                <div class="response-title text-high-emphasis">Max Context Length</div>
                <div class="response-description text-medium-emphasis">Maximum character length for context documents</div>
              </div>
            </div>
            <div class="response-right">
              <v-text-field
                v-model.number="store.settings.max_context_length"
                type="number"
                variant="outlined"
                density="compact"
                :min="100"
                :max="10000"
                hide-details
                style="width: 140px;"
              />
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Max Context Documents Row -->
        <div class="response-row">
          <div class="response-content">
            <div class="response-left">
              <v-icon color="primary" class="response-icon">$document</v-icon>
              <div class="response-info">
                <div class="response-title text-high-emphasis">Max Context Documents</div>
                <div class="response-description text-medium-emphasis">Maximum number of documents to include in context</div>
              </div>
            </div>
            <div class="response-right">
              <v-text-field
                v-model.number="store.settings.max_context_documents"
                type="number"
                variant="outlined"
                density="compact"
                :min="1"
                :max="10"
                hide-details
                style="width: 120px;"
              />
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Context Fill Ratio Row -->
        <div class="response-row">
          <div class="response-content">
            <div class="response-left">
              <v-icon color="primary" class="response-icon">$tune</v-icon>
              <div class="response-info">
                <div class="response-title text-high-emphasis">Context Fill Ratio</div>
                <div class="response-description text-medium-emphasis">Ratio of context to fill with relevant documents</div>
              </div>
            </div>
            <div class="response-right">
              <div class="response-slider">
                <v-slider
                  v-model="store.settings.context_fill_ratio"
                  :min="0.1"
                  :max="1.0"
                  :step="0.1"
                  thumb-label="always"
                  show-ticks="always"
                  color="primary"
                  track-color="grey-lighten-3"
                  thumb-color="primary"
                  hide-details
                  style="width: 200px;"
                />
                <div class="response-status text-medium-emphasis">{{ store.settings.context_fill_ratio.toFixed(1) }}</div>
              </div>
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Enable Response Caching Row -->
        <div class="response-row">
          <div class="response-content">
            <div class="response-left">
              <v-icon color="primary" class="response-icon">$cached</v-icon>
              <div class="response-info">
                <div class="response-title text-high-emphasis">Enable Response Caching</div>
                <div class="response-description text-medium-emphasis">Cache responses to improve performance for repeated queries</div>
              </div>
            </div>
            <div class="response-right">
              <v-switch
                v-model="store.settings.enable_caching"
                color="primary"
                inset
                hide-details
              />
              <div class="response-status text-medium-emphasis">
                {{ store.settings.enable_caching ? 'Enabled' : 'Disabled' }}
              </div>
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Cache TTL Row -->
        <div class="response-row">
          <div class="response-content">
            <div class="response-left">
              <v-icon color="primary" class="response-icon">$clock</v-icon>
              <div class="response-info">
                <div class="response-title text-high-emphasis">Cache TTL (seconds)</div>
                <div class="response-description text-medium-emphasis">How long to keep cached responses (60s - 24h)</div>
              </div>
            </div>
            <div class="response-right">
              <v-text-field
                v-model.number="store.settings.cache_ttl_seconds"
                type="number"
                variant="outlined"
                density="compact"
                :min="60"
                :max="86400"
                :disabled="!store.settings.enable_caching"
                hide-details
                style="width: 140px;"
              />
            </div>
          </div>
        </div>
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

<style scoped>
/* Response Settings Row Layout */
.response-row {
  padding: 20px 24px;
}

.response-row:last-child {
  border-bottom: none;
}

.response-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 48px;
}

.response-left {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}

.response-icon {
  margin-right: 16px;
  flex-shrink: 0;
}

.response-info {
  flex: 1;
  min-width: 0;
}

.response-title {
  font-size: 16px;
  font-weight: 500;
  line-height: 1.4;
  margin-bottom: 4px;
}

.response-description {
  font-size: 14px;
  line-height: 1.4;
}

.response-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  margin-left: 24px;
}

.response-status {
  font-size: 14px;
  margin-left: 12px;
  font-weight: 500;
}

.response-slider {
  display: flex;
  align-items: center;
}

.response-slider .response-status {
  margin-left: 16px;
  min-width: 50px;
  text-align: right;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .response-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .response-right {
    width: 100%;
    margin-left: 0;
    justify-content: flex-start;
  }

  .response-slider {
    width: 100%;
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .response-slider .response-status {
    margin-left: 0;
    text-align: left;
    min-width: auto;
  }
}
</style>