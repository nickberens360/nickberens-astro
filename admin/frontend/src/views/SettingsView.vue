<template>
  <div class="settings-page">
    <!-- Page Header -->
    <div class="page-header mb-8">
      <div class="d-flex align-center justify-space-between">
        <div>
<!--          <h1 class="page-title text-h4 font-weight-bold mb-2">Settings</h1>-->
          <p class="page-subtitle text-body-1 text-medium-emphasis">
            Manage follow-up question system configuration and categories
          </p>
        </div>
        <v-btn
          color="primary"
          prepend-icon="$refresh"
          @click="loadData"
          :loading="loading"
          variant="elevated"
        >
          Refresh
        </v-btn>
      </div>
    </div>

    <!-- Overview Cards -->
    <v-row class="mb-8">
      <v-col cols="12" sm="6" md="3">
        <v-card class="metric-card h-100" elevation="2">
          <v-card-text class="pa-6">
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="metric-label text-caption text-medium-emphasis font-weight-medium">
                  ACTIVE CATEGORIES
                </div>
                <div class="metric-value text-h4 font-weight-bold mt-1">
                  {{ stats.active_categories }}
                </div>
                <div class="metric-trend text-caption mt-1">
                  <span class="text-success">
                    <v-icon size="12">$trending-up</v-icon>
                    Ready for use
                  </span>
                </div>
              </div>
              <v-avatar size="48" color="success" variant="tonal">
                <v-icon size="24">$folder</v-icon>
              </v-avatar>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card class="metric-card h-100" elevation="2">
          <v-card-text class="pa-6">
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="metric-label text-caption text-medium-emphasis font-weight-medium">
                  TOTAL QUESTIONS
                </div>
                <div class="metric-value text-h4 font-weight-bold mt-1">
                  {{ stats.total_questions }}
                </div>
                <div class="metric-trend text-caption mt-1">
                  <span class="text-primary">
                    <v-icon size="12">$help-circle</v-icon>
                    Available
                  </span>
                </div>
              </div>
              <v-avatar size="48" color="primary" variant="tonal">
                <v-icon size="24">$help-circle</v-icon>
              </v-avatar>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card class="metric-card h-100" elevation="2">
          <v-card-text class="pa-6">
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="metric-label text-caption text-medium-emphasis font-weight-medium">
                  INACTIVE CATEGORIES
                </div>
                <div class="metric-value text-h4 font-weight-bold mt-1">
                  {{ stats.inactive_categories }}
                </div>
                <div class="metric-trend text-caption mt-1">
                  <span class="text-warning">
                    <v-icon size="12">$alert</v-icon>
                    Need attention
                  </span>
                </div>
              </div>
              <v-avatar size="48" color="warning" variant="tonal">
                <v-icon size="24">$alert</v-icon>
              </v-avatar>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card class="metric-card h-100" elevation="2">
          <v-card-text class="pa-6">
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="metric-label text-caption text-medium-emphasis font-weight-medium">
                  SERVICE MODE
                </div>
                <div class="metric-value text-h6 font-weight-bold mt-1 text-capitalize">
                  {{ settings.service_type || 'Static' }}
                </div>
                <div class="metric-trend text-caption mt-1">
                  <span class="text-info">
                    <v-icon size="12">$brain</v-icon>
                    {{ settings.enabled ? 'Active' : 'Inactive' }}
                  </span>
                </div>
              </div>
              <v-avatar size="48" color="info" variant="tonal">
                <v-icon size="24">$brain</v-icon>
              </v-avatar>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- System Settings Section -->
    <div class="settings-section mb-8">
      <div class="section-header mb-6">
        <h2 class="section-title text-h5 font-weight-bold">System Configuration</h2>
        <p class="section-subtitle text-body-2 text-medium-emphasis">
          Configure follow-up question generation behavior and limits
        </p>
      </div>

      <v-card class="settings-card" elevation="2">
        <v-card-text class="pa-6">
          <v-row>
            <!-- Enable/Disable Toggle -->
            <v-col cols="12" md="4">
              <div class="setting-group">
                <div class="setting-label text-subtitle-1 font-weight-medium mb-3">
                  <v-icon class="mr-2" size="20">$toggle-switch</v-icon>
                  Service Status
                </div>
                <v-switch
                  v-model="settings.enabled"
                  :label="settings.enabled ? 'Enabled' : 'Disabled'"
                  color="primary"
                  inset
                  hide-details
                  @change="saveSettings"
                />
                <div class="setting-helper text-caption text-medium-emphasis mt-2">
                  Toggle the follow-up question system on or off
                </div>
              </div>
            </v-col>

            <!-- Generation Method -->
            <v-col cols="12" md="4">
              <div class="setting-group">
                <div class="setting-label text-subtitle-1 font-weight-medium mb-3">
                  <v-icon class="mr-2" size="20">$brain</v-icon>
                  Generation Method
                </div>
                <v-select
                  v-model="settings.service_type"
                  :items="serviceTypeOptions"
                  variant="outlined"
                  density="comfortable"
                  hide-details
                  @update:model-value="saveSettings"
                />
                <div class="setting-helper text-caption text-medium-emphasis mt-2">
                  Choose how questions are generated and selected
                </div>
              </div>
            </v-col>

            <!-- Maximum Questions -->
            <v-col cols="12" md="4">
              <div class="setting-group">
                <div class="setting-label text-subtitle-1 font-weight-medium mb-3">
                  <v-icon class="mr-2" size="20">$numeric</v-icon>
                  Question Limit
                </div>
                <v-slider
                  v-model="settings.max_questions"
                  :min="1"
                  :max="5"
                  :step="1"
                  thumb-label="always"
                  show-ticks="always"
                  color="primary"
                  track-color="grey-lighten-3"
                  thumb-color="primary"
                  hide-details
                  @end="saveSettings"
                />
                <div class="setting-helper text-caption text-medium-emphasis mt-2">
                  Maximum number of follow-up questions to display
                </div>
              </div>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </div>

    <!-- Categories Management Section -->
    <div class="categories-section">
      <div class="section-header mb-6">
        <div class="d-flex align-center justify-space-between">
          <div>
            <h2 class="section-title text-h5 font-weight-bold">Category Management</h2>
            <p class="section-subtitle text-body-2 text-medium-emphasis">
              Manage question categories and their associated follow-up questions
            </p>
          </div>
          <v-btn
            color="primary"
            prepend-icon="$plus"
            @click="handleCreateCategoryDialog"
            :disabled="loading"
            variant="elevated"
          >
            Add Category
          </v-btn>
        </div>
      </div>

      <!-- Bulk Actions Banner -->
      <v-card
        v-if="selectedCategories.length > 0"
        class="bulk-actions-card mb-6"
        elevation="1"
        color="primary"
        variant="tonal"
      >
        <v-card-text class="pa-4">
          <div class="d-flex align-center justify-space-between">
            <div class="d-flex align-center">
              <v-icon class="mr-2">$checkbox-marked</v-icon>
              <span class="font-weight-medium">
                {{ selectedCategories.length }} {{ selectedCategories.length === 1 ? 'category' : 'categories' }} selected
              </span>
            </div>
            <v-btn-group variant="outlined" density="compact">
              <v-btn
                prepend-icon="$eye"
                @click="bulkActivateCategories"
                :loading="loading"
              >
                Activate
              </v-btn>
              <v-btn
                prepend-icon="$eye-off"
                @click="bulkDeactivateCategories"
                :loading="loading"
              >
                Deactivate
              </v-btn>
              <v-btn
                color="error"
                prepend-icon="$delete"
                @click="bulkDeleteCategories"
                :loading="loading"
              >
                Delete
              </v-btn>
            </v-btn-group>
          </div>
        </v-card-text>
      </v-card>

      <!-- Categories List -->
      <v-card class="categories-card" elevation="2">
        <v-card-title class="pa-6 pb-0">
          <div class="d-flex align-center">
            <v-icon class="mr-3">$format-list-group</v-icon>
            <span class="text-h6 font-weight-bold">Question Categories</span>
            <v-spacer/>
            <v-chip
              :text="`${categories.length} total`"
              variant="tonal"
              size="small"
            />
          </div>
        </v-card-title>

        <v-card-text class="pa-6">
          <!-- Categories with Expansion Panels -->
          <v-expansion-panels v-if="categories.length > 0" v-model="expandedPanels" multiple variant="accordion">
            <v-expansion-panel
              v-for="category in categories"
              :key="category.id"
              :value="category.id"
              class="category-panel mb-4"
              :class="{ 'category-panel--inactive': !category.is_active }"
              elevation="0"
              rounded="lg"
            >
              <v-expansion-panel-title class="category-panel-header">
                <div class="d-flex align-center w-100">
                  <!-- Selection Checkbox -->
                  <v-checkbox
                    v-model="selectedCategories"
                    :value="category"
                    hide-details
                    density="compact"
                    class="mr-4 flex-shrink-0"
                    @click.stop
                  />

                  <!-- Category Info -->
                  <div class="flex-grow-1 d-flex align-center">
                    <v-avatar
                      size="40"
                      :color="category.is_active ? 'primary' : 'grey-lighten-1'"
                      variant="tonal"
                      class="mr-4"
                    >
                      <v-icon size="20">
                        ${{ category.icon || 'help-circle' }}
                      </v-icon>
                    </v-avatar>

                    <div class="category-info">
                      <div class="d-flex align-center mb-1">
                        <span class="text-subtitle-1 font-weight-bold">
                          {{ category.display_name }}
                        </span>
                        <v-chip
                          v-if="!category.is_active"
                          size="small"
                          color="warning"
                          variant="tonal"
                          class="ml-3"
                        >
                          <v-icon start size="12">$alert</v-icon>
                          Inactive
                        </v-chip>
                      </div>
                      <div class="text-caption text-medium-emphasis">
                        <v-icon size="12" class="mr-1">$help-circle</v-icon>
                        {{ categoryStats[category.id]?.question_count || 0 }} questions
                        <span class="mx-2">•</span>
                        <v-icon size="12" class="mr-1">$sort</v-icon>
                        Order: {{ category.sort_order }}
                      </div>
                    </div>
                  </div>

                  <!-- Quick Actions -->
                  <div class="d-flex align-center" @click.stop>
                    <v-tooltip text="Edit Category" location="top">
                      <template #activator="{ props }">
                        <v-btn
                          v-bind="props"
                          icon="$edit"
                          size="small"
                          variant="text"
                          @click="editCategory(category)"
                          :disabled="loading"
                          class="mr-1"
                        />
                      </template>
                    </v-tooltip>

                    <v-tooltip text="Delete Category" location="top">
                      <template #activator="{ props }">
                        <v-btn
                          v-bind="props"
                          icon="$delete"
                          size="small"
                          variant="text"
                          color="error"
                          @click="showDeleteCategoryDialog(category)"
                          :disabled="loading"
                        />
                      </template>
                    </v-tooltip>
                  </div>
                </div>
              </v-expansion-panel-title>

              <v-expansion-panel-text class="category-panel-content">
                <div class="pt-4">
                  <QuestionManager
                    :category="category"
                    :selected-questions="selectedQuestions[category.id] || []"
                    @questions-updated="loadData"
                    @selection-changed="(questions) => updateQuestionSelection(category.id, questions)"
                  />
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <!-- Empty State -->
          <div v-else class="empty-state text-center py-16">
            <v-avatar size="120" color="grey-lighten-3" class="mb-6">
              <v-icon size="60" color="grey-lighten-1">$format-list-group</v-icon>
            </v-avatar>

            <h3 class="text-h5 font-weight-bold mb-3">No Categories Yet</h3>
            <p class="text-body-1 text-medium-emphasis mb-8 mx-auto" style="max-width: 400px;">
              Create your first category to start organizing and managing follow-up questions for your system.
            </p>

            <v-btn
              color="primary"
              size="large"
              prepend-icon="$plus"
              @click="handleCreateCategoryDialog"
              variant="elevated"
            >
              Create First Category
            </v-btn>
          </div>
        </v-card-text>
      </v-card>
    </div>

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
import { ref, reactive, computed, onMounted } from 'vue'
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
    // Reactive state
    const loading = ref(false)
    const categories = ref([])
    const categoryStats = ref({})
    const expandedPanels = ref([])

    // Settings
    const settings = reactive({
      enabled: true,
      service_type: 'static',
      max_questions: 3,
      include_technical: true,
      include_personal: true,
      include_creative: true
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

    // Methods
    const loadData = async () => {
      try {
        loading.value = true

        // Load settings, categories, and stats in parallel
        const [settingsResponse, categoriesResponse] = await Promise.all([
          api.getFollowupSettings(),
          api.getFollowupCategoriesNormalized()
        ])

        Object.assign(settings, settingsResponse)
        categories.value = categoriesResponse || []

        // Keep expansion panels closed by default
        // QuestionManager components will load when panels are opened by user
        expandedPanels.value = []

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

      } catch (err) {
        console.error('Failed to load data:', err)
        showErrorMessage('Failed to load settings and categories')
      } finally {
        loading.value = false
      }
    }

    const saveSettings = async () => {
      try {
        await api.updateFollowupSettings(settings)
        showSuccessMessage('Settings saved successfully!')
      } catch (err) {
        console.error('Failed to save settings:', err)
        showErrorMessage('Failed to save settings')
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
          await api.updateFollowupCategoryNormalized(editingCategory.value.id, categoryData)
          showSuccessMessage('Category updated successfully!')
        } else {
          // Create new category
          await api.createFollowupCategoryNormalized(categoryData)
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
            api.updateFollowupCategoryNormalized(category.id, { is_active: true })
          )
        )
        showSuccessMessage(`${selectedCategories.value.length} categories activated!`)
        selectedCategories.value = []
        await loadData()
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
            api.updateFollowupCategoryNormalized(category.id, { is_active: false })
          )
        )
        showSuccessMessage(`${selectedCategories.value.length} categories deactivated!`)
        selectedCategories.value = []
        await loadData()
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
      editingCategory.value = null
      showCategoryDialog.value = true
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
      loadData,
      saveSettings,
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

/* Animation */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.settings-page > * {
  animation: fadeIn 0.3s ease-out;
}

.settings-page > *:nth-child(2) {
  animation-delay: 0.1s;
}

.settings-page > *:nth-child(3) {
  animation-delay: 0.2s;
}

.settings-page > *:nth-child(4) {
  animation-delay: 0.3s;
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

/* Remove focus outline from all input elements globally in dialogs */
:deep(.v-field__input),
:deep(.v-field__field),
:deep(.v-input__control),
:deep(.v-text-field input),
:deep(.v-textarea textarea),
:deep(.v-select input),
:deep(.v-btn:focus-visible),
:deep(.v-text-field:focus-within),
:deep(.v-select:focus-within) {
  outline: none !important;
  outline-offset: 0 !important;
}

:deep(.v-field__input:focus),
:deep(.v-field__field:focus),
:deep(.v-input__control:focus),
:deep(.v-text-field input:focus),
:deep(.v-textarea textarea:focus),
:deep(.v-select input:focus),
:deep(.v-btn:focus),
:deep(.v-btn:focus-visible),
:deep(.v-text-field:focus-within),
:deep(.v-select:focus-within) {
  outline: none !important;
  outline-offset: 0 !important;
  box-shadow: none !important;
}
</style>