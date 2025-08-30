<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-6">
          <v-icon left>$settings</v-icon>
          System Settings
        </h1>
      </v-col>
    </v-row>
    
    <v-row>
      <v-col cols="12" md="8">
        <!-- Follow-up Questions Settings Card -->
        <v-card class="mb-6">
          <v-card-title>
            <v-icon left>$help-circle</v-icon>
            Follow-up Questions
          </v-card-title>
          
          <v-card-subtitle>
            Configure how follow-up questions are generated and displayed
          </v-card-subtitle>
          
          <v-card-text>
            <v-form ref="followupForm">
              <!-- Enable/Disable Toggle -->
              <v-switch
                v-model="followupSettings.enabled"
                label="Enable follow-up questions"
                color="primary"
                hide-details
                class="mb-4"
              ></v-switch>
              
              <div v-show="followupSettings.enabled" class="settings-section">
                <!-- Service Type Selection -->
                <v-select
                  v-model="followupSettings.service_type"
                  :items="serviceTypeOptions"
                  label="Generation Method"
                  prepend-icon="$brain"
                  hint="How follow-up questions are selected"
                  persistent-hint
                  class="mb-4"
                ></v-select>
                
                <!-- Maximum Questions -->
                <v-slider
                  v-model="followupSettings.max_questions"
                  :min="1"
                  :max="5"
                  :step="1"
                  label="Maximum Questions"
                  prepend-icon="$numeric"
                  thumb-label="always"
                  show-ticks="always"
                  tick-size="4"
                  class="mb-4"
                >
                  <template v-slot:append>
                    <v-text-field
                      v-model="followupSettings.max_questions"
                      type="number"
                      style="width: 60px"
                      density="compact"
                      hide-details
                      variant="outlined"
                    ></v-text-field>
                  </template>
                </v-slider>
                
                <!-- Question Categories -->
                <div class="mb-4">
                  <v-subheader class="pl-0">Question Categories</v-subheader>
                  <v-row>
                    <v-col cols="12" sm="4">
                      <v-checkbox
                        v-model="followupSettings.include_technical"
                        label="Technical"
                        color="primary"
                        hide-details
                      ></v-checkbox>
                    </v-col>
                    <v-col cols="12" sm="4">
                      <v-checkbox
                        v-model="followupSettings.include_personal"
                        label="Personal"
                        color="primary"
                        hide-details
                      ></v-checkbox>
                    </v-col>
                    <v-col cols="12" sm="4">
                      <v-checkbox
                        v-model="followupSettings.include_creative"
                        label="Creative"
                        color="primary"
                        hide-details
                      ></v-checkbox>
                    </v-col>
                  </v-row>
                </div>
                
                <!-- Question Style -->
                <v-select
                  v-model="followupSettings.question_style"
                  :items="questionStyleOptions"
                  label="Question Style"
                  prepend-icon="$format-text"
                  hint="The tone and style of generated questions"
                  persistent-hint
                  class="mb-4"
                ></v-select>
                
                <!-- Advanced Settings (collapsed by default) -->
                <v-expansion-panels v-model="advancedPanel" variant="accordion">
                  <v-expansion-panel>
                    <v-expansion-panel-title>
                      <v-icon left>$tune</v-icon>
                      Advanced Settings
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <v-slider
                        v-model="followupSettings.relevance_threshold"
                        :min="0.1"
                        :max="1.0"
                        :step="0.1"
                        label="Relevance Threshold"
                        prepend-icon="$target"
                        thumb-label="always"
                        show-ticks="always"
                        tick-size="2"
                        hint="Higher values make questions more contextually relevant"
                        persistent-hint
                        class="mb-4"
                      >
                        <template v-slot:append>
                          <v-text-field
                            v-model="followupSettings.relevance_threshold"
                            type="number"
                            :step="0.1"
                            :min="0.1"
                            :max="1.0"
                            style="width: 80px"
                            density="compact"
                            hide-details
                            variant="outlined"
                          ></v-text-field>
                        </template>
                      </v-slider>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>
              </div>
            </v-form>
            
            <!-- Status Messages -->
            <v-alert
              v-if="error"
              type="error"
              dismissible
              @click="error = ''"
              class="mt-4"
            >
              {{ error }}
            </v-alert>
            
            <v-alert
              v-if="success"
              type="success"
              dismissible
              @click="success = ''"
              class="mt-4"
            >
              {{ success }}
            </v-alert>
          </v-card-text>
          
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn
              color="grey"
              variant="text"
              @click="resetToDefaults"
              :disabled="loading"
            >
              Reset to Defaults
            </v-btn>
            <v-btn
              color="primary"
              :disabled="loading"
              :loading="loading"
              @click="saveSettings"
            >
              Save Settings
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      
      <!-- Settings Info Sidebar -->
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>
            <v-icon left>$info</v-icon>
            Settings Information
          </v-card-title>
          
          <v-card-text>
            <div class="mb-4">
              <h4 class="text-subtitle-1 mb-2">Generation Methods</h4>
              <v-list density="compact">
                <v-list-item>
                  <v-list-item-title>Static</v-list-item-title>
                  <v-list-item-subtitle>Sequential rotation through predefined questions</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Dynamic</v-list-item-title>
                  <v-list-item-subtitle>Context-aware question selection</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Contextual</v-list-item-title>
                  <v-list-item-subtitle>AI-powered conversation analysis</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </div>
            
            <div class="mb-4">
              <h4 class="text-subtitle-1 mb-2">Question Categories</h4>
              <v-list density="compact">
                <v-list-item>
                  <v-list-item-title>Technical</v-list-item-title>
                  <v-list-item-subtitle>Development, technologies, coding</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Personal</v-list-item-title>
                  <v-list-item-subtitle>Experience, background, contact</v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title>Creative</v-list-item-title>
                  <v-list-item-subtitle>Illustrations, art, design work</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </div>
            
            <v-alert
              type="info"
              variant="tonal"
              density="compact"
            >
              Changes take effect immediately for new queries. Existing cached responses are not affected.
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import api from '@/services/api'

export default {
  name: 'SettingsView',
  setup() {
    const followupForm = ref(null)
    const loading = ref(false)
    const error = ref('')
    const success = ref('')
    const advancedPanel = ref([])
    
    const followupSettings = reactive({
      enabled: true,
      service_type: 'static',
      max_questions: 1,
      relevance_threshold: 0.7,
      include_technical: true,
      include_personal: true,
      include_creative: true,
      question_style: 'conversational'
    })
    
    const serviceTypeOptions = [
      { title: 'Static (Sequential)', value: 'static' },
      { title: 'Dynamic (Context-aware)', value: 'dynamic' },
      { title: 'Contextual (AI-powered)', value: 'contextual' }
    ]
    
    const questionStyleOptions = [
      { title: 'Conversational', value: 'conversational' },
      { title: 'Formal', value: 'formal' },
      { title: 'Exploratory', value: 'exploratory' }
    ]
    
    const loadSettings = async () => {
      try {
        loading.value = true
        error.value = ''
        
        const response = await api.getFollowupSettings()
        Object.assign(followupSettings, response)
        
        console.log('Loaded follow-up settings:', response)
      } catch (err) {
        console.error('Failed to load settings:', err)
        error.value = err.response?.data?.detail || 'Failed to load settings'
      } finally {
        loading.value = false
      }
    }
    
    const saveSettings = async () => {
      try {
        loading.value = true
        error.value = ''
        success.value = ''
        
        const response = await api.updateFollowupSettings(followupSettings)
        
        if (response.success) {
          success.value = response.message || 'Settings saved successfully!'
          console.log('Settings saved:', response.settings)
        }
      } catch (err) {
        console.error('Failed to save settings:', err)
        error.value = err.response?.data?.detail || 'Failed to save settings'
      } finally {
        loading.value = false
      }
    }
    
    const resetToDefaults = async () => {
      try {
        loading.value = true
        error.value = ''
        success.value = ''
        
        const response = await api.resetFollowupSettings()
        
        if (response.success) {
          Object.assign(followupSettings, response.settings)
          success.value = 'Settings reset to defaults!'
          console.log('Settings reset:', response.settings)
        }
      } catch (err) {
        console.error('Failed to reset settings:', err)
        error.value = err.response?.data?.detail || 'Failed to reset settings'
      } finally {
        loading.value = false
      }
    }
    
    onMounted(() => {
      loadSettings()
    })
    
    return {
      followupForm,
      loading,
      error,
      success,
      advancedPanel,
      followupSettings,
      serviceTypeOptions,
      questionStyleOptions,
      loadSettings,
      saveSettings,
      resetToDefaults
    }
  }
}
</script>

<style scoped>
.settings-section {
  padding-left: 16px;
  border-left: 2px solid rgba(var(--v-theme-primary), 0.3);
  margin-left: 8px;
}

.v-subheader {
  font-weight: 500;
  color: rgba(var(--v-theme-on-surface), 0.87);
}
</style>