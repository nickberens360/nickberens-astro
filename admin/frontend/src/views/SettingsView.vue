<template>
  <div class="settings-page">
    <!-- Page Header -->
    <div class="page-header mb-8">
      <div class="d-flex align-center justify-space-between">
        <div>
          <h1 class="page-title text-h4 font-weight-bold mb-2">Settings</h1>
          <p class="page-subtitle text-body-1 text-medium-emphasis">
            Manage system configuration, follow-up questions, and feature settings
          </p>
        </div>
        <v-btn-group variant="outlined" density="comfortable">
          <v-btn
            color="warning"
            prepend-icon="$refresh"
            @click="invalidateCache"
            :loading="cacheInvalidating"
            variant="elevated"
            class="mr-3"
          >
            Clear Cache
          </v-btn>
          <v-btn
            color="primary"
            prepend-icon="$refresh"
            @click="loadData"
            :loading="loading"
            variant="elevated"
          >
            Refresh
          </v-btn>
        </v-btn-group>
      </div>
    </div>

    <!-- Settings Tabs -->
    <v-tabs :model-value="currentTab" @update:model-value="navigateToTab" class="mb-6" color="primary">
      <v-tab value="followup">
        <v-icon class="mr-2">$help-circle</v-icon>
        Follow-up Questions
      </v-tab>
      <v-tab value="welcome">
        <v-icon class="mr-2">$message-text</v-icon>
        Welcome Questions
      </v-tab>
      <v-tab value="response">
        <v-icon class="mr-2">$message-reply</v-icon>
        Response Settings
      </v-tab>
      <v-tab value="routing">
        <v-icon class="mr-2">$route</v-icon>
        Query Routing
      </v-tab>
      <v-tab value="features">
        <v-icon class="mr-2">$feature-flag</v-icon>
        Feature Flags
      </v-tab>
      <v-tab value="cache">
        <v-icon class="mr-2">$cached</v-icon>
        Cache Status
      </v-tab>
    </v-tabs>

    <!-- Router View for Child Components -->
    <router-view
      ref="routerViewRef"
      :loading="loading"
      :categories="categories"
      :category-stats="categoryStats"
      :expanded-panels="expandedPanels"
      :settings="settings"
      :service-type-options="serviceTypeOptions"
      :selected-categories="selectedCategories"
      :selected-questions="selectedQuestions"
      :stats="stats"
      :response-settings="responseSettings"
      :routing-settings="routingSettings"
      :feature-flags="featureFlags"
      :cache-status="cacheStatus"
      @save-settings="saveSettings"
      @update-setting="updateSetting"
      @create-category="handleCreateCategoryDialog"
      @edit-category="editCategory"
      @delete-category="showDeleteCategoryDialog"
      @bulk-activate="bulkActivateCategories"
      @bulk-deactivate="bulkDeactivateCategories"
      @bulk-delete="bulkDeleteCategories"
      @update-question-selection="updateQuestionSelection"
      @update-selected-categories="updateSelectedCategories"
      @update-expanded-panels="updateExpandedPanels"
      @load-data="loadData"
      @save-response-settings="saveResponseSettings"
      @save-routing-settings="saveRoutingSettings"
      @save-feature-flags="saveFeatureFlags"
    />

    <!-- Status Messages -->
    <v-snackbar
      v-model="showSuccess"
      color="success"
      timeout="4000"
    >
      {{ successMessage }}
    </v-snackbar>

    <v-snackbar
      v-model="showError"
      color="error"
      timeout="6000"
    >
      {{ errorMessage }}
    </v-snackbar>

    <!-- Category Dialog -->
    <CategoryDialog
      v-model="showCategoryDialog"
      :category="editingCategory"
      :loading="loading"
      @save="saveCategory"
      @cancel="cancelCategoryEdit"
    />

    <!-- Category Delete Dialog -->
    <CategoryDeleteDialog
      v-model="showDeleteDialog"
      :category="deletingCategory"
      :category-stats="deletingCategory ? categoryStats[deletingCategory.id] : null"
      :available-categories="availableCategoriesForMove"
      :loading="loading"
      @confirm="confirmDeleteCategory"
      @cancel="cancelDeleteCategory"
    />

    <!-- Bulk Delete Confirmation Dialog -->
    <v-dialog v-model="showBulkDeleteDialog" max-width="580px" persistent>
      <v-card class="bulk-delete-dialog" elevation="12" rounded="xl">
        <v-card-title class="dialog-header pa-6">
          <div class="d-flex align-center">
            <v-avatar
              size="48"
              color="error"
              variant="tonal"
              class="mr-4"
            >
              <v-icon size="24">$alert-triangle</v-icon>
            </v-avatar>
            <div class="flex-grow-1">
              <h2 class="text-h5 font-weight-bold mb-1">Bulk Delete Categories</h2>
              <p class="text-body-2 text-medium-emphasis ma-0">
                {{ selectedCategories.length }} categories selected for deletion
              </p>
            </div>
            <v-chip
              color="error"
              variant="tonal"
              size="small"
            >
              High Risk
            </v-chip>
          </div>
        </v-card-title>

        <v-divider class="border-opacity-12"></v-divider>

        <v-card-text class="pa-6">
          <div class="bulk-delete-content">
            <!-- Warning Alert -->
            <v-card
              color="error"
              variant="tonal"
              elevation="0"
              rounded="lg"
              class="mb-6"
            >
              <v-card-text class="pa-4">
                <div class="d-flex align-center mb-3">
                  <v-icon color="error" size="20" class="mr-2">$alert</v-icon>
                  <span class="font-weight-bold text-body-1">Destructive Action</span>
                </div>
                <p class="text-body-2 ma-0">
                  You are about to delete <strong>{{ selectedCategories.length }} categories</strong>
                  and <strong>all their questions permanently</strong>.
                </p>
              </v-card-text>
            </v-card>

            <!-- Categories List -->
            <div class="categories-list-section mb-6">
              <div class="section-title text-subtitle-1 font-weight-bold mb-4 d-flex align-center">
                <v-icon size="18" class="mr-2">$list</v-icon>
                Categories to be deleted
              </div>

              <div class="categories-to-delete">
                <v-card
                  v-for="category in selectedCategories"
                  :key="category.id"
                  class="category-item mb-2"
                  elevation="0"
                  variant="outlined"
                  rounded="lg"
                >
                  <v-card-text class="pa-3">
                    <div class="d-flex align-center">
                      <v-avatar size="32" color="error" variant="tonal" class="mr-3">
                        <v-icon size="16">$folder</v-icon>
                      </v-avatar>
                      <div class="flex-grow-1">
                        <div class="font-weight-medium text-body-1">{{ category.display_name }}</div>
                        <div v-if="categoryStats[category.id]" class="text-caption text-medium-emphasis">
                          {{ categoryStats[category.id].question_count }} questions will be deleted
                        </div>
                      </div>
                      <v-chip
                        color="error"
                        variant="tonal"
                        size="small"
                      >
                        <v-icon start size="12">$delete</v-icon>
                        Delete
                      </v-chip>
                    </div>
                  </v-card-text>
                </v-card>
              </div>
            </div>

            <!-- Final Warning -->
            <v-card
              color="error"
              variant="tonal"
              elevation="1"
              rounded="lg"
              class="mb-6"
            >
              <v-card-text class="pa-4">
                <div class="d-flex align-center mb-3">
                  <v-icon color="error" size="20" class="mr-2">$warning</v-icon>
                  <span class="font-weight-bold text-error">Final Warning</span>
                </div>
                <p class="text-body-2 text-error ma-0">
                  This action cannot be undone. All questions in these categories will be permanently deleted.
                </p>
              </v-card-text>
            </v-card>

            <!-- Confirmation Checkbox -->
            <v-card
              color="error"
              variant="tonal"
              elevation="0"
              rounded="lg"
            >
              <v-card-text class="pa-4">
                <v-checkbox
                  v-model="confirmBulkDelete"
                  color="error"
                  class="confirmation-checkbox"
                >
                  <template v-slot:label>
                    <span class="text-error font-weight-medium">
                      I understand this will permanently delete all selected categories and their questions
                    </span>
                  </template>
                </v-checkbox>
              </v-card-text>
            </v-card>
          </div>
        </v-card-text>

        <v-divider class="border-opacity-12"></v-divider>

        <v-card-actions class="dialog-actions pa-6">
          <v-spacer></v-spacer>
          <v-btn
            variant="outlined"
            size="large"
            @click="cancelBulkDelete"
            :disabled="loading"
            class="mr-3"
          >
            Cancel
          </v-btn>
          <v-btn
            color="error"
            variant="elevated"
            size="large"
            :loading="loading"
            :disabled="!confirmBulkDelete"
            @click="confirmBulkDeleteCategories"
            prepend-icon="$delete"
          >
            Delete {{ selectedCategories.length }} Categories
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/services/api'
import MetricCard from '@/components/MetricCard.vue'
import QuestionManager from '@/components/QuestionManager.vue'
import CategoryDialog from '@/components/CategoryDialog.vue'
import CategoryDeleteDialog from '@/components/CategoryDeleteDialog.vue'

export default {
  name: 'SettingsView',
  components: {
    MetricCard,
    QuestionManager,
    CategoryDialog,
    CategoryDeleteDialog
  },
  setup() {
    const route = useRoute()
    const router = useRouter()

    // Reactive state
    const loading = ref(false)
    const categories = ref([])
    const categoryStats = ref({})
    const expandedPanels = ref([])
    const cacheInvalidating = ref(false)
    const cacheStatus = ref(null)
    const routerViewRef = ref(null)

    // Settings
    const settings = reactive({
      enabled: true,
      service_type: 'static',
      max_questions: 3,
      include_technical: true,
      include_personal: true,
      include_creative: true
    })

    // New settings for additional tabs
    const responseSettings = reactive({
      max_context_length: 2000,
      max_context_documents: 3,
      context_fill_ratio: 0.7,
      enable_caching: true,
      cache_ttl_seconds: 3600
    })

    const routingSettings = reactive({
      enable_smart_routing: true,
      similarity_threshold: 0.3,
      max_search_results: 15,
      enable_fuzzy_matching: true,
      fuzzy_threshold: 0.7
    })

    const featureFlags = reactive({
      enable_illustrations: true,
      enable_geolocation: true,
      enable_analytics: true,
      enable_debug_logging: false,
      enable_response_caching: true,
      enable_query_preprocessing: true
    })

    const serviceTypeOptions = [
      { title: 'Static (Sequential)', value: 'static' },
      { title: 'Dynamic (Context-aware)', value: 'dynamic' },
      { title: 'Contextual (AI-powered)', value: 'contextual' }
    ]

    // Selection state
    const selectedCategories = ref([])
    const selectedQuestions = reactive({})

    // Dialog state
    const showCreateCategoryDialog = ref(false)
    const showCategoryDialog = ref(false)
    const showDeleteDialog = ref(false)
    const showBulkDeleteDialog = ref(false)
    const editingCategory = ref(null)
    const deletingCategory = ref(null)
    const confirmBulkDelete = ref(false)

    // Messages
    const showSuccess = ref(false)
    const showError = ref(false)
    const successMessage = ref('')
    const errorMessage = ref('')

    // Computed properties
    const stats = computed(() => ({
      active_categories: categories.value.filter(c => c.is_active).length,
      inactive_categories: categories.value.filter(c => !c.is_active).length,
      total_questions: Object.values(categoryStats.value).reduce((sum, stat) => sum + (stat.question_count || 0), 0)
    }))

    const availableCategoriesForMove = computed(() =>
      categories.value.filter(c => c.id !== deletingCategory.value?.id && c.is_active)
    )

    // Get current tab from route
    const currentTab = computed(() => {
      const routeName = route.name
      if (routeName === 'settings-followup') return 'followup'
      if (routeName === 'settings-welcome') return 'welcome'
      if (routeName === 'settings-response') return 'response'
      if (routeName === 'settings-routing') return 'routing'
      if (routeName === 'settings-features') return 'features'
      if (routeName === 'settings-cache') return 'cache'
      return 'followup' // default
    })

    // Navigate to tab
    const navigateToTab = (tabValue) => {
      const routeMap = {
        'followup': 'settings-followup',
        'welcome': 'settings-welcome',
        'response': 'settings-response',
        'routing': 'settings-routing',
        'features': 'settings-features',
        'cache': 'settings-cache'
      }

      const routeName = routeMap[tabValue]
      if (routeName && route.name !== routeName) {
        router.push({ name: routeName })
      }
    }

    // Methods
    const lightweightRefresh = async () => {
      try {
        // Only refresh categories and settings without expensive dev logging
        const [settingsResponse, categoriesResponse] = await Promise.all([
          api.getFollowupSettings(),
          api.getFollowupCategories()
        ])

        // Safely assign settings with fallback
        if (settingsResponse && typeof settingsResponse === 'object') {
          Object.assign(settings, settingsResponse)
        }
        categories.value = categoriesResponse || []

        // Update category stats without dev logging
        const statsPromises = categories.value.map(async (category) => {
          try {
            const stats = await api.getFollowupCategoryStatsNormalized(category.id)
            categoryStats.value[category.id] = stats
          } catch (err) {
            console.warn(`Failed to load stats for category ${category.id}:`, err)
            categoryStats.value[category.id] = { question_count: 0 }
          }
        })

        await Promise.all(statsPromises)
      } catch (err) {
        console.error('Failed to refresh data:', err)
      }
    }

    const loadData = async () => {
      try {
        loading.value = true

        // Load all settings and categories in parallel - always load all for consistency
        const promises = [
          api.getFollowupSettings(),
          api.getFollowupCategories(),
          api.getResponseSettings().catch((err) => {
            console.error('Failed to load response settings:', err)
            return {}
          }),
          api.getRoutingSettings().catch((err) => {
            console.error('Failed to load routing settings:', err)
            return {}
          }),
          api.getFeatureFlags().catch((err) => {
            console.error('Failed to load feature flags:', err)
            return {}
          }),
          api.getSettingsCacheStatus().catch((err) => {
            console.error('Failed to load cache status:', err)
            return null
          })
        ]

        const [
          settingsResponse,
          categoriesResponse,
          responseSettingsResponse,
          routingSettingsResponse,
          featureFlagsResponse,
          cacheStatusResponse
        ] = await Promise.all(promises)


        // Safely assign settings with fallback
        if (settingsResponse && typeof settingsResponse === 'object') {
          Object.assign(settings, settingsResponse)
        }
        categories.value = categoriesResponse || []

        // Update additional settings if received
        if (responseSettingsResponse) Object.assign(responseSettings, responseSettingsResponse)
        if (routingSettingsResponse) Object.assign(routingSettings, routingSettingsResponse)
        if (featureFlagsResponse) {
          Object.assign(featureFlags, featureFlagsResponse)
        }
        if (cacheStatusResponse) cacheStatus.value = cacheStatusResponse

        // Only reset expanded panels on initial load (when categories change)
        // This preserves the user's accordion state during refresh operations
        const categoryIds = categories.value.map(c => c.id)
        const currentPanelIds = expandedPanels.value || []

        // Remove panels for categories that no longer exist
        expandedPanels.value = currentPanelIds.filter(id => categoryIds.includes(id))

        // Open all accordions by default on initial load
        if ((expandedPanels.value?.length || 0) === 0 && categoryIds.length > 0) {
          expandedPanels.value = [...categoryIds]
        }

        // Load stats for each category
        const statsPromises = categories.value.map(async (category) => {
          try {
            const stats = await api.getFollowupCategoryStatsNormalized(category.id)
            categoryStats.value[category.id] = stats
          } catch (err) {
            console.warn(`Failed to load stats for category ${category.id}:`, err)
            categoryStats.value[category.id] = { question_count: 0 }
          }
        })

        await Promise.all(statsPromises)

        // Dev-only: log follow-up questions for each category (debounced to prevent loops)
        if (import.meta.env.DEV && !loadData._devLoggingInProgress) {
          loadData._devLoggingInProgress = true
          setTimeout(async () => {
            try {
              console.log('Loading dev follow-up questions data...')
              // Reduced logging - just count questions instead of fetching all
              categories.value.forEach((category) => {
                const stats = categoryStats.value[category.id]
                console.group(
                  `Follow-up questions for category ${category.id} (${category.display_name})`
                )
                console.log(`Question count: ${stats?.question_count || 0}`)
                console.groupEnd()
              })
            } catch (e) {
              console.warn('Dev logging of follow-up questions failed:', e)
            } finally {
              loadData._devLoggingInProgress = false
            }
          }, 100)
        }

      } catch (err) {
        console.error('Failed to load data:', err)
        showErrorMessage('Failed to load settings and categories')
      } finally {
        loading.value = false
      }
    }

    const updateSetting = async (key, value) => {
      // Ensure settings object exists
      if (!settings || typeof settings !== 'object') {
        console.warn('Settings object not initialized yet')
        return
      }
      // Update the settings object (reactive objects don't use .value)
      settings[key] = value
      // Automatically save the settings
      await saveSettings()
    }

    const saveSettings = async () => {
      try {
        if (!settings || typeof settings !== 'object') {
          console.error('Settings object is not properly initialized')
          showErrorMessage('Settings not initialized properly')
          return
        }
        await api.updateFollowupSettings(settings)
        showSuccessMessage('Followup settings saved successfully!')
      } catch (err) {
        console.error('Failed to save settings:', err)
        showErrorMessage('Failed to save followup settings')
      }
    }

    // New save methods for additional settings
    const saveResponseSettings = async () => {
      try {
        await api.updateResponseSettings(responseSettings)
        showSuccessMessage('Response settings saved successfully!')
      } catch (err) {
        console.error('Failed to save response settings:', err)
        showErrorMessage('Failed to save response settings')
      }
    }

    const saveRoutingSettings = async () => {
      try {
        await api.updateRoutingSettings(routingSettings)
        showSuccessMessage('Routing settings saved successfully!')
      } catch (err) {
        console.error('Failed to save routing settings:', err)
        showErrorMessage('Failed to save routing settings')
      }
    }

    const saveFeatureFlags = async (updatedFlags) => {
      try {
        // If updatedFlags are provided, update the reactive object
        if (updatedFlags) {
          Object.assign(featureFlags, updatedFlags)
        }
        await api.updateFeatureFlags(featureFlags)
        showSuccessMessage('Feature flags updated successfully!')
      } catch (err) {
        console.error('Failed to save feature flags:', err)
        showErrorMessage('Failed to save feature flags')
      }
    }

    const invalidateCache = async () => {
      try {
        cacheInvalidating.value = true
        await api.invalidateSettingsCache()
        showSuccessMessage('Settings cache invalidated successfully!')
        // Reload cache status
        const cacheStatusResponse = await api.getSettingsCacheStatus()
        cacheStatus.value = cacheStatusResponse
      } catch (err) {
        console.error('Failed to invalidate cache:', err)
        showErrorMessage('Failed to invalidate settings cache')
      } finally {
        cacheInvalidating.value = false
      }
    }

    const editCategory = (category) => {
      editingCategory.value = category
      showCategoryDialog.value = true
    }

    const saveCategory = async (categoryData) => {
      try {
        loading.value = true

        if (editingCategory.value) {
          // Update existing category
          await api.updateFollowupCategory(editingCategory.value.id, categoryData)
          showSuccessMessage('Category updated successfully!')
        } else {
          // Create new category
          await api.createFollowupCategory(categoryData)
          showSuccessMessage('Category created successfully!')
        }

        showCategoryDialog.value = false
        editingCategory.value = null
        await loadData()

      } catch (err) {
        console.error('Failed to save category:', err)
        showErrorMessage('Failed to save category')
      } finally {
        loading.value = false
      }
    }

    const cancelCategoryEdit = () => {
      showCategoryDialog.value = false
      editingCategory.value = null
    }

    const showDeleteCategoryDialog = (category) => {
      deletingCategory.value = category
      showDeleteDialog.value = true
    }

    const confirmDeleteCategory = async (deleteRequest) => {
      try {
        loading.value = true

        await api.deleteFollowupCategoryWithStrategyNormalized(deleteRequest)

        if (deleteRequest.strategy === 'deactivate') {
          showSuccessMessage('Category deactivated successfully!')
        } else {
          showSuccessMessage('Category deleted successfully!')
        }

        showDeleteDialog.value = false
        deletingCategory.value = null
        await loadData()

      } catch (err) {
        console.error('Failed to delete category:', err)
        showErrorMessage('Failed to delete category')
      } finally {
        loading.value = false
      }
    }

    const cancelDeleteCategory = () => {
      showDeleteDialog.value = false
      deletingCategory.value = null
    }

    // Bulk operations
    const bulkActivateCategories = async () => {
      try {
        loading.value = true
        await Promise.all(
          selectedCategories.value.map(category =>
            api.updateFollowupCategory(category.id, { is_active: true })
          )
        )
        showSuccessMessage(`${selectedCategories.value.length} categories activated!`)
        selectedCategories.value = []
        // Use lightweight refresh instead of full loadData()
        await lightweightRefresh()
      } catch (err) {
        showErrorMessage('Failed to activate categories')
      } finally {
        loading.value = false
      }
    }

    const bulkDeactivateCategories = async () => {
      try {
        loading.value = true
        await Promise.all(
          selectedCategories.value.map(category =>
            api.updateFollowupCategory(category.id, { is_active: false })
          )
        )
        showSuccessMessage(`${selectedCategories.value.length} categories deactivated!`)
        selectedCategories.value = []
        // Use lightweight refresh instead of full loadData()
        await lightweightRefresh()
      } catch (err) {
        showErrorMessage('Failed to deactivate categories')
      } finally {
        loading.value = false
      }
    }

    const bulkDeleteCategories = () => {
      // Reset confirmation state and show dialog
      confirmBulkDelete.value = false
      showBulkDeleteDialog.value = true
    }

    const confirmBulkDeleteCategories = async () => {
      try {
        loading.value = true
        await Promise.all(
          selectedCategories.value.map(category =>
            api.deleteFollowupCategoryWithStrategyNormalized({
              categoryId: category.id,
              strategy: 'delete'
            })
          )
        )
        showSuccessMessage(`${selectedCategories.value.length} categories deleted!`)
        selectedCategories.value = []
        showBulkDeleteDialog.value = false
        confirmBulkDelete.value = false
        await loadData()
      } catch (err) {
        showErrorMessage('Failed to delete categories')
      } finally {
        loading.value = false
      }
    }

    const cancelBulkDelete = () => {
      showBulkDeleteDialog.value = false
      confirmBulkDelete.value = false
    }

    // Question selection management
    const updateQuestionSelection = (categoryId, questions) => {
      selectedQuestions[categoryId] = questions
    }

    // Category selection management
    const updateSelectedCategories = (newValue) => {
      selectedCategories.value = newValue
    }

    // Expanded panels management
    const updateExpandedPanels = (newValue) => {
      expandedPanels.value = newValue
    }

    // Message helpers
    const showSuccessMessage = (message) => {
      successMessage.value = message
      showSuccess.value = true
    }

    const showErrorMessage = (message) => {
      errorMessage.value = message
      showError.value = true
    }

    // Handle create category dialog
    const handleCreateCategoryDialog = () => {
      console.log('SettingsView: handleCreateCategoryDialog called!')
      console.log('Before: showCategoryDialog.value =', showCategoryDialog.value)
      editingCategory.value = null
      showCategoryDialog.value = true
      console.log('After: showCategoryDialog.value =', showCategoryDialog.value)
    }


    // Initialize
    onMounted(() => {
      loadData()
    })

    return {
      loading,
      categories,
      categoryStats,
      expandedPanels,
      settings,
      serviceTypeOptions,
      selectedCategories,
      selectedQuestions,
      showCreateCategoryDialog,
      showCategoryDialog,
      showDeleteDialog,
      showBulkDeleteDialog,
      editingCategory,
      deletingCategory,
      confirmBulkDelete,
      showSuccess,
      showError,
      successMessage,
      errorMessage,
      stats,
      availableCategoriesForMove,
      // New reactive data
      currentTab,
      cacheInvalidating,
      cacheStatus,
      responseSettings,
      routingSettings,
      featureFlags,
      // Methods
      navigateToTab,
      loadData,
      updateSetting,
      saveSettings,
      saveResponseSettings,
      saveRoutingSettings,
      saveFeatureFlags,
      invalidateCache,
      editCategory,
      saveCategory,
      cancelCategoryEdit,
      showDeleteCategoryDialog,
      confirmDeleteCategory,
      cancelDeleteCategory,
      bulkActivateCategories,
      bulkDeactivateCategories,
      bulkDeleteCategories,
      confirmBulkDeleteCategories,
      cancelBulkDelete,
      updateQuestionSelection,
      updateSelectedCategories,
      updateExpandedPanels,
      handleCreateCategoryDialog
    }
  }
}
</script>

<style scoped>
.settings-page {
  max-width: 100%;
  margin: 0 auto;
}

.page-header {
  background: rgb(var(--v-theme-surface));
  border-radius: 16px;
  padding: 32px;
  margin-bottom: 32px;
  border: 1px solid rgba(var(--v-theme-outline), 0.08);
}

.page-title {
  color: rgb(var(--v-theme-on-surface));
}

.page-subtitle {
  max-width: 600px;
}

/* Metric Cards */
.metric-card {
  border-radius: 16px;
  border: 1px solid rgba(var(--v-theme-outline), 0.12);
  transition: all 0.2s ease;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.metric-label {
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: rgb(var(--v-theme-on-surface-variant));
}

.metric-value {
  color: rgb(var(--v-theme-on-surface));
  line-height: 1.2;
}

.metric-trend {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* Settings Sections */
.settings-section, .categories-section {
  margin-bottom: 32px;
}

.section-header {
  margin-bottom: 24px;
}

.section-title {
  color: rgb(var(--v-theme-on-surface));
  margin-bottom: 8px;
}

.section-subtitle {
  color: rgb(var(--v-theme-on-surface-variant));
  max-width: 600px;
}

.settings-card, .categories-card {
  border-radius: 16px;
  border: 1px solid rgba(var(--v-theme-outline), 0.12);
}

/* Setting Groups */
.setting-group {
  padding: 20px;
  border-radius: 12px;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-theme-outline), 0.08);
}

.setting-label {
  display: flex;
  align-items: center;
  color: rgb(var(--v-theme-on-surface));
  margin-bottom: 12px;
}

.setting-helper {
  color: rgb(var(--v-theme-on-surface-variant));
  line-height: 1.4;
}

/* Bulk Actions */
.bulk-actions-card {
  border-radius: 12px;
  border: 1px solid rgba(var(--v-theme-primary), 0.2);
}

/* Category Panels */
.category-panel {
  border: 1px solid rgba(var(--v-theme-outline), 0.12);
  border-radius: 12px;
  overflow: hidden;
  background: rgb(var(--v-theme-surface));
  transition: all 0.2s ease;
}

.category-panel:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.category-panel--inactive {
  opacity: 0.7;
  border: 1px dashed rgba(var(--v-theme-warning), 0.4);
}

.category-panel--inactive .category-panel-header {
  background: rgba(var(--v-theme-warning), 0.05);
}

.category-panel-header {
  padding: 16px 20px;
  background: rgb(var(--v-theme-surface));
  border-bottom: 1px solid rgba(var(--v-theme-outline), 0.08);
}

.category-panel-content {
  background: rgb(var(--v-theme-surface));
}

.category-info {
  min-width: 0;
  flex: 1;
}

/* Empty State */
.empty-state {
  padding: 48px 24px;
  background: rgb(var(--v-theme-surface));
  border-radius: 12px;
  border: 2px dashed rgba(var(--v-theme-outline), 0.2);
}

/* Responsive Design */
@media (max-width: 768px) {
  .page-header {
    padding: 24px;
  }

  .settings-page {
    padding: 0 16px;
  }

  .section-header .d-flex {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start !important;
  }

  .category-panel-header {
    padding: 12px 16px;
  }

  .category-panel-header .d-flex {
    flex-wrap: wrap;
    gap: 8px;
  }

  .setting-group {
    margin-bottom: 16px;
  }
}


/* Bulk Delete Dialog Styling */
.bulk-delete-dialog {
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-theme-outline), 0.08);
}

.bulk-delete-dialog .dialog-header {
  background: linear-gradient(135deg, rgb(var(--v-theme-surface)) 0%, rgba(var(--v-theme-error), 0.02) 100%);
  border-bottom: 1px solid rgba(var(--v-theme-outline), 0.08);
}

.bulk-delete-content {
  padding: 0;
}

.categories-list-section {
  padding: 20px;
  background: rgba(var(--v-theme-surface-variant), 0.02);
  border-radius: 12px;
  border: 1px solid rgba(var(--v-theme-outline), 0.06);
}

.categories-list-section .section-title {
  color: rgb(var(--v-theme-primary));
}

.categories-to-delete {
  max-height: 200px;
  overflow-y: auto;
  padding: 0 2px;
}

.category-item {
  transition: all 0.2s ease;
  border: 1px solid rgba(var(--v-theme-error), 0.12);
}

.category-item:hover {
  border-color: rgba(var(--v-theme-error), 0.3);
  box-shadow: 0 2px 8px rgba(var(--v-theme-error), 0.1);
}

.bulk-delete-dialog .confirmation-checkbox :deep(.v-selection-control__wrapper) {
  margin-right: 12px;
}

.bulk-delete-dialog .dialog-actions {
  background: rgba(var(--v-theme-surface-variant), 0.02);
  border-top: 1px solid rgba(var(--v-theme-outline), 0.08);
}

/* Bulk Delete Dialog Animation */
.bulk-delete-dialog {
  animation: dialogSlideIn 0.3s ease-out;
}

/* Mobile responsiveness for bulk delete dialog */
@media (max-width: 600px) {
  .categories-list-section {
    padding: 16px;
    margin: 0 -6px 16px -6px;
  }

  .categories-to-delete {
    max-height: 150px;
  }

  .bulk-delete-dialog .dialog-header {
    padding: 20px !important;
  }

  .bulk-delete-dialog .dialog-actions {
    padding: 20px !important;
  }

  .category-item {
    margin-bottom: 8px;
  }
}

</style>
