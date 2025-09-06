<template>
  <div>
    <v-card elevation="2">
      <v-card-title class="text-h6 font-weight-bold pa-6 d-flex align-center justify-space-between">
        <span>Security & Privacy Settings</span>
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
        
        <!-- IP Anonymization Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$shield-check</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">IP Anonymization</div>
                <div class="setting-description text-medium-emphasis">Anonymize IP addresses in logs for privacy compliance</div>
              </div>
            </div>
            <div class="setting-right">
              <v-switch
                v-model="settings.anonymize_ips"
                color="primary"
                inset
                hide-details
              />
              <div class="setting-status text-medium-emphasis">
                {{ settings.anonymize_ips ? 'Enabled' : 'Disabled' }}
              </div>
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Query Logging Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$clipboard-list</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">Query Logging</div>
                <div class="setting-description text-medium-emphasis">Enable logging of user queries for analytics</div>
              </div>
            </div>
            <div class="setting-right">
              <v-switch
                v-model="settings.enable_query_logging"
                color="primary"
                inset
                hide-details
              />
              <div class="setting-status text-medium-emphasis">
                {{ settings.enable_query_logging ? 'Enabled' : 'Disabled' }}
              </div>
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Query Log Retention Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$clock-outline</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">Log Retention Period</div>
                <div class="setting-description text-medium-emphasis">Number of days to retain query logs (1-365)</div>
              </div>
            </div>
            <div class="setting-right">
              <v-text-field
                v-model.number="settings.query_log_retention_days"
                type="number"
                variant="outlined"
                density="compact"
                :min="1"
                :max="365"
                suffix="days"
                hide-details
                style="width: 140px;"
              />
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Session Timeout Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$timer</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">Session Timeout</div>
                <div class="setting-description text-medium-emphasis">Admin session timeout in minutes (30-1440)</div>
              </div>
            </div>
            <div class="setting-right">
              <v-text-field
                v-model.number="settings.session_timeout_minutes"
                type="number"
                variant="outlined"
                density="compact"
                :min="30"
                :max="1440"
                suffix="min"
                hide-details
                style="width: 140px;"
              />
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Session Fingerprinting Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$fingerprint</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">Session Fingerprinting</div>
                <div class="setting-description text-medium-emphasis">Enable session fingerprinting for enhanced security</div>
              </div>
            </div>
            <div class="setting-right">
              <v-switch
                v-model="settings.enable_session_fingerprinting"
                color="primary"
                inset
                hide-details
              />
              <div class="setting-status text-medium-emphasis">
                {{ settings.enable_session_fingerprinting ? 'Enabled' : 'Disabled' }}
              </div>
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Audit Logging Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$book-open</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">Audit Logging</div>
                <div class="setting-description text-medium-emphasis">Log all admin actions for security auditing</div>
              </div>
            </div>
            <div class="setting-right">
              <v-switch
                v-model="settings.enable_audit_logging"
                color="primary"
                inset
                hide-details
              />
              <div class="setting-status text-medium-emphasis">
                {{ settings.enable_audit_logging ? 'Enabled' : 'Disabled' }}
              </div>
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Rate Limiting Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$speedometer</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">Rate Limiting</div>
                <div class="setting-description text-medium-emphasis">Enable request rate limiting protection</div>
              </div>
            </div>
            <div class="setting-right">
              <v-switch
                v-model="settings.enable_rate_limiting"
                color="primary"
                inset
                hide-details
              />
              <div class="setting-status text-medium-emphasis">
                {{ settings.enable_rate_limiting ? 'Enabled' : 'Disabled' }}
              </div>
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Max Requests Per Minute Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$gauge</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">Request Limit</div>
                <div class="setting-description text-medium-emphasis">Maximum requests per minute per IP (1-1000)</div>
              </div>
            </div>
            <div class="setting-right">
              <v-text-field
                v-model.number="settings.max_requests_per_minute"
                type="number"
                variant="outlined"
                density="compact"
                :min="1"
                :max="1000"
                suffix="req/min"
                hide-details
                style="width: 160px;"
                :disabled="!settings.enable_rate_limiting"
              />
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Input Validation Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$check-circle</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">Input Validation</div>
                <div class="setting-description text-medium-emphasis">Enable strict input validation and sanitization</div>
              </div>
            </div>
            <div class="setting-right">
              <v-switch
                v-model="settings.enable_input_validation"
                color="primary"
                inset
                hide-details
              />
              <div class="setting-status text-medium-emphasis">
                {{ settings.enable_input_validation ? 'Enabled' : 'Disabled' }}
              </div>
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Low Similarity Threshold Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$alert-circle</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">Low Similarity Threshold</div>
                <div class="setting-description text-medium-emphasis">Flag queries with similarity below this threshold</div>
              </div>
            </div>
            <div class="setting-right">
              <div class="setting-slider">
                <v-slider
                  v-model="similarityThresholdPercent"
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
                <div class="setting-value text-medium-emphasis">{{ similarityThresholdPercent }}%</div>
              </div>
            </div>
          </div>
        </div>

        <v-divider></v-divider>

        <!-- Excluded IPs Row -->
        <div class="setting-row">
          <div class="setting-content">
            <div class="setting-left">
              <v-icon color="primary" class="setting-icon">$ip-network</v-icon>
              <div class="setting-info">
                <div class="setting-title text-high-emphasis">Excluded IP Addresses</div>
                <div class="setting-description text-medium-emphasis">IP addresses to exclude from logging (one per line)</div>
              </div>
            </div>
            <div class="setting-right">
              <v-textarea
                v-model="excludedIpsText"
                variant="outlined"
                density="compact"
                placeholder="192.168.1.1&#10;10.0.0.1"
                rows="3"
                hide-details
                style="width: 200px;"
              />
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
  excluded_ips: [],
  anonymize_ips: true,
  enable_query_logging: true,
  low_similarity_threshold: 0.7,
  query_log_retention_days: 30,
  session_timeout_minutes: 480,
  enable_session_fingerprinting: true,
  enable_audit_logging: true,
  enable_rate_limiting: true,
  max_requests_per_minute: 100,
  enable_input_validation: true
})

const loading = ref(false)
const error = ref('')
const successMessage = ref('')

// Convert arrays to text for display
const excludedIpsText = computed({
  get: () => settings.value.excluded_ips.join('\n'),
  set: (value) => {
    settings.value.excluded_ips = value ? value.split('\n').map(ip => ip.trim()).filter(ip => ip) : []
  }
})


// Convert similarity threshold to percentage for display
const similarityThresholdPercent = computed({
  get: () => Math.round(settings.value.low_similarity_threshold * 100),
  set: (value) => {
    settings.value.low_similarity_threshold = value / 100
  }
})

// Load settings on mount
const loadSettings = async () => {
  try {
    loading.value = true
    error.value = ''
    
    const response = await adminAPI.getSecuritySettings()
    if (response) {
      settings.value = { ...settings.value, ...response }
    }
  } catch (err) {
    console.error('Failed to load security settings:', err)
    error.value = 'Failed to load security settings: ' + (err.response?.data?.detail || err.message)
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
    
    const response = await adminAPI.updateSecuritySettings(settings.value)
    if (response && response.success) {
      successMessage.value = 'Security settings saved successfully!'
      setTimeout(() => {
        successMessage.value = ''
      }, 3000)
    }
  } catch (err) {
    console.error('Failed to save security settings:', err)
    error.value = 'Failed to save security settings: ' + (err.response?.data?.detail || err.message)
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