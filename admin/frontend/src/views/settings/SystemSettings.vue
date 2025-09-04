<template>
  <div>
    <v-card elevation="2">
      <v-card-title class="text-h6 font-weight-bold pa-6 d-flex align-center justify-space-between">
        <span>System Configuration</span>
        <v-btn
          color="primary"
          variant="elevated"
          @click="saveSettings"
          :loading="loading"
          prepend-icon="$check"
        >
          Save Changes
        </v-btn>
      </v-card-title>
      
      <v-card-text class="pa-0">
        <v-alert v-if="error" type="error" variant="tonal" class="ma-6 mb-4">
          {{ error }}
        </v-alert>
        
        <v-alert v-if="successMessage" type="success" variant="tonal" class="ma-6 mb-4">
          {{ successMessage }}
        </v-alert>
        
        <!-- Primary LLM Selection Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$brain</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">Primary LLM</div>
                <div class="setting-description text-medium-emphasis">Choose the primary language model for responses</div>
              </div>
            </div>
            <div class="setting-right">
              <v-select
                v-model="settings.primary_llm"
                :items="llmOptions"
                variant="outlined"
                density="compact"
                hide-details
                style="width: 160px;"
              />
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Claude Model Selection Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$robot</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">Claude Model</div>
                <div class="setting-description text-medium-emphasis">Specific Claude model to use for Anthropic queries</div>
              </div>
            </div>
            <div class="setting-right">
              <v-select
                v-model="settings.claude_model"
                :items="claudeModelOptions"
                variant="outlined"
                density="compact"
                hide-details
                style="width: 220px;"
              />
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Gemini Model Selection Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$google</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">Gemini Model</div>
                <div class="setting-description text-medium-emphasis">Specific Gemini model to use for Google queries</div>
              </div>
            </div>
            <div class="setting-right">
              <v-select
                v-model="settings.gemini_model"
                :items="geminiModelOptions"
                variant="outlined"
                density="compact"
                hide-details
                style="width: 180px;"
              />
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Cache TTL Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$cached</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">Cache TTL</div>
                <div class="setting-description text-medium-emphasis">Cache time-to-live in seconds (60-86400)</div>
              </div>
            </div>
            <div class="setting-right">
              <v-text-field
                v-model.number="settings.cache_ttl_seconds"
                type="number"
                variant="outlined"
                density="compact"
                :min="60"
                :max="86400"
                hide-details
                style="width: 120px;"
              />
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Max Cache Size Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$database</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">Max Cache Size</div>
                <div class="setting-description text-medium-emphasis">Maximum number of cache entries (10-10000)</div>
              </div>
            </div>
            <div class="setting-right">
              <v-text-field
                v-model.number="settings.max_cache_size"
                type="number"
                variant="outlined"
                density="compact"
                :min="10"
                :max="10000"
                hide-details
                style="width: 120px;"
              />
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Rate Limit Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$timer</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">Rate Limit</div>
                <div class="setting-description text-medium-emphasis">Request rate limiting (e.g., "100/minute")</div>
              </div>
            </div>
            <div class="setting-right">
              <v-text-field
                v-model="settings.rate_limit"
                variant="outlined"
                density="compact"
                placeholder="100/minute"
                hide-details
                style="width: 140px;"
              />
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Search Similarity Threshold Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$search</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">Search Similarity Threshold</div>
                <div class="setting-description text-medium-emphasis">Minimum similarity for search results (0-100%)</div>
              </div>
            </div>
            <div class="setting-right">
              <div class="setting-slider">
                <v-slider
                  v-model="searchThresholdPercent"
                  :min="0"
                  :max="100"
                  :step="1"
                  thumb-label="always"
                  show-ticks="always"
                  color="primary"
                  track-color="grey-lighten-3"
                  thumb-color="primary"
                  hide-details
                  style="width: 200px;"
                />
                <div class="setting-value text-medium-emphasis">{{ searchThresholdPercent }}%</div>
              </div>
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Max Search Results Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$format-list-bulleted</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">Max Search Results</div>
                <div class="setting-description text-medium-emphasis">Maximum number of search results (1-100)</div>
              </div>
            </div>
            <div class="setting-right">
              <v-text-field
                v-model.number="settings.max_search_results"
                type="number"
                variant="outlined"
                density="compact"
                :min="1"
                :max="100"
                hide-details
                style="width: 120px;"
              />
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Smart Model Selection Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$tune</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">Smart Model Selection</div>
                <div class="setting-description text-medium-emphasis">Automatically choose the best model based on query complexity</div>
              </div>
            </div>
            <div class="setting-right">
              <v-switch
                v-model="settings.enable_smart_model_selection"
                color="primary"
                inset
                hide-details
              />
              <div class="setting-status text-medium-emphasis">
                {{ settings.enable_smart_model_selection ? 'Enabled' : 'Disabled' }}
              </div>
            </div>
          </div>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'
import adminAPI from '@/services/api'

const adminStore = useAdminStore()

// Reactive state
const settings = ref({
  primary_llm: 'claude',
  claude_model: 'claude-3-5-sonnet-20241022',
  gemini_model: 'gemini-1.5-flash',
  embedding_model: 'models/embedding-001',
  cache_ttl_seconds: 3600,
  max_cache_size: 1000,
  rate_limit: '100/minute',
  search_similarity_threshold: 0.55,
  max_search_results: 15,
  retrieval_score_threshold: 0.3,
  enable_smart_model_selection: true,
  default_search_k: 8,
  expanded_search_k: 12
})

const loading = ref(false)
const error = ref('')
const successMessage = ref('')

// Model options
const llmOptions = [
  { title: 'Claude (Anthropic)', value: 'claude' },
  { title: 'Gemini (Google)', value: 'gemini' }
]

const claudeModelOptions = [
  { title: 'Claude 3.5 Sonnet', value: 'claude-3-5-sonnet-20241022' },
  { title: 'Claude 3.5 Haiku', value: 'claude-3-5-haiku-20241022' },
  { title: 'Claude 3 Opus', value: 'claude-3-opus-20240229' }
]

const geminiModelOptions = [
  { title: 'Gemini 1.5 Flash', value: 'gemini-1.5-flash' },
  { title: 'Gemini 1.5 Pro', value: 'gemini-1.5-pro' },
  { title: 'Gemini Pro', value: 'gemini-pro' }
]

// Convert search threshold to percentage for display
const searchThresholdPercent = computed({
  get: () => Math.round(settings.value.search_similarity_threshold * 100),
  set: (value) => {
    settings.value.search_similarity_threshold = value / 100
  }
})

// Load settings on mount
const loadSettings = async () => {
  try {
    loading.value = true
    error.value = ''
    
    const response = await adminAPI.getSystemConfigSettings()
    if (response) {
      settings.value = { ...settings.value, ...response }
    }
  } catch (err) {
    console.error('Failed to load system config settings:', err)
    error.value = 'Failed to load system configuration settings: ' + (err.response?.data?.detail || err.message)
  } finally {
    loading.value = false
  }
}

// Save settings
const saveSettings = async () => {
  try {
    loading.value = true
    error.value = ''
    successMessage.value = ''
    
    const response = await adminAPI.updateSystemConfigSettings(settings.value)
    if (response && response.success) {
      successMessage.value = 'System configuration settings saved successfully!'
      setTimeout(() => {
        successMessage.value = ''
      }, 3000)
    }
  } catch (err) {
    console.error('Failed to save system config settings:', err)
    error.value = 'Failed to save system configuration settings: ' + (err.response?.data?.detail || err.message)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
/* Settings Row Layout */
.setting-row {
  padding: 20px 24px;
}

.setting-row:last-child {
  border-bottom: none;
}

.setting-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 48px;
}

.setting-left {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}

.setting-icon {
  margin-right: 16px;
  flex-shrink: 0;
}

.setting-info {
  flex: 1;
  min-width: 0;
}

.setting-title {
  font-size: 16px;
  font-weight: 500;
  line-height: 1.4;
  margin-bottom: 4px;
}

.setting-description {
  font-size: 14px;
  line-height: 1.4;
}

.setting-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  margin-left: 24px;
}

.setting-slider {
  display: flex;
  align-items: center;
  gap: 16px;
}

.setting-value {
  font-size: 14px;
  font-weight: 500;
  min-width: 50px;
  text-align: center;
}

.setting-status {
  font-size: 14px;
  margin-left: 12px;
  font-weight: 500;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .setting-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .setting-right {
    width: 100%;
    margin-left: 0;
    justify-content: flex-start;
  }

  .setting-slider {
    width: 100%;
  }
}
</style>