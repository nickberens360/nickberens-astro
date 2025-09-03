<template>
  <div>
    <!-- Overview Cards -->
    <v-row class="ds-mb-8">
      <v-col cols="12" sm="6" md="3">
        <v-card class="ds-card metric-card h-100">
          <v-card-text class="ds-p-6">
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="metric-label text-caption text-medium-emphasis font-weight-medium">
                  ACTIVE CATEGORIES
                </div>
                <div class="metric-value text-h4 font-weight-bold mt-1">
                  {{ store.stats.active_categories }}
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
        <v-card class="ds-card metric-card h-100">
          <v-card-text class="ds-p-6">
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="metric-label text-caption text-medium-emphasis font-weight-medium">
                  TOTAL QUESTIONS
                </div>
                <div class="metric-value text-h4 font-weight-bold mt-1">
                  {{ store.stats.total_questions }}
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
        <v-card class="ds-card metric-card h-100">
          <v-card-text class="ds-p-6">
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="metric-label text-caption text-medium-emphasis font-weight-medium">
                  INACTIVE CATEGORIES
                </div>
                <div class="metric-value text-h4 font-weight-bold mt-1">
                  {{ store.stats.inactive_categories }}
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
        <v-card class="ds-card metric-card h-100">
          <v-card-text class="ds-p-6">
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="metric-label text-caption text-medium-emphasis font-weight-medium">
                  SERVICE MODE
                </div>
                <div class="metric-value text-h6 font-weight-bold mt-1 text-capitalize">
                  {{ store.settings.service_type || 'Static' }}
                </div>
                <div class="metric-trend text-caption mt-1">
                  <span class="text-info">
                    <v-icon size="12">$brain</v-icon>
                    {{ store.settings.enabled ? 'Active' : 'Inactive' }}
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
    <div class="ds-section-spacing">
      <div class="ds-content-spacing">
        <h2 class="ds-text-2xl ds-font-bold ds-mb-2">System Configuration</h2>
        <p class="ds-text-sm text-medium-emphasis">
          Configure follow-up question generation behavior and limits
        </p>
      </div>

      <v-card class="ds-card settings-card">
        <v-card-text class="ds-p-6">
          <v-row>
            <!-- Enable/Disable Toggle -->
            <v-col cols="12" md="4">
              <div class="ds-item-spacing">
                <div class="ds-text-base ds-font-medium ds-mb-3 d-flex align-center">
                  <v-icon class="mr-2" size="20">$toggle-switch</v-icon>
                  Service Status
                </div>
                <v-switch
                  v-model="store.settings.enabled"
                  :label="store.settings.enabled ? 'Enabled' : 'Disabled'"
                  color="primary"
                  inset
                  hide-details
                  @update:model-value="updateSetting('enabled', $event)"
                />
                <div class="ds-text-xs text-medium-emphasis ds-mt-2">
                  Toggle the follow-up question system on or off
                </div>
              </div>
            </v-col>

            <!-- Generation Method -->
            <v-col cols="12" md="4">
              <div class="ds-item-spacing">
                <div class="ds-text-base ds-font-medium ds-mb-3 d-flex align-center">
                  <v-icon class="mr-2" size="20">$brain</v-icon>
                  Generation Method
                </div>
                <v-select
                  v-model="store.settings.service_type"
                  :items="store.serviceTypeOptions"
                  variant="outlined"
                  density="comfortable"
                  hide-details
                  @update:model-value="updateSetting('service_type', $event)"
                />
                <div class="ds-text-xs text-medium-emphasis ds-mt-2">
                  Choose how questions are generated and selected
                </div>
              </div>
            </v-col>

            <!-- Maximum Questions -->
            <v-col cols="12" md="4">
              <div class="ds-item-spacing">
                <div class="ds-text-base ds-font-medium ds-mb-3 d-flex align-center">
                  <v-icon class="mr-2" size="20">$numeric</v-icon>
                  Question Limit
                </div>
                <v-slider
                  v-model="store.settings.max_questions"
                  :min="1"
                  :max="5"
                  :step="1"
                  thumb-label="always"
                  show-ticks="always"
                  color="primary"
                  track-color="grey-lighten-3"
                  thumb-color="primary"
                  hide-details
                  @update:model-value="updateSetting('max_questions', $event)"
                />
                <div class="ds-text-xs text-medium-emphasis ds-mt-2">
                  Maximum number of follow-up questions to display
                </div>
              </div>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </div>

    <!-- Categories Management Section -->
    <div class="ds-section-spacing">
      <div class="ds-content-spacing">
        <div class="d-flex align-center justify-space-between">
          <div>
            <h2 class="ds-text-2xl ds-font-bold ds-mb-2">Category Management</h2>
            <p class="ds-text-sm text-medium-emphasis">
              Manage question categories and their associated follow-up questions
            </p>
          </div>
        </div>
      </div>

      <!-- Bulk Actions Banner -->
      <v-card
        v-if="store.selectedCategories.length > 0"
        class="ds-card bulk-actions-card ds-mb-6"
        color="primary"
        variant="tonal"
      >
        <v-card-text class="ds-p-4">
          <div class="d-flex align-center justify-space-between">
            <div class="d-flex align-center">
              <v-icon class="mr-2">$checkbox-marked</v-icon>
              <span class="font-weight-medium">
                {{ store.selectedCategories.length }} {{ store.selectedCategories.length === 1 ? 'category' : 'categories' }} selected
              </span>
            </div>
            <v-btn-group variant="outlined" density="compact">
              <v-btn
                prepend-icon="$eye"
                @click="bulkActivate"
                :loading="store.loading"
                class="mr-3"
              >
                Activate
              </v-btn>
              <v-btn
                prepend-icon="$eye-off"
                @click="bulkDeactivate"
                :loading="store.loading"
                class="mr-3"
              >
                Deactivate
              </v-btn>
              <v-btn
                color="error"
                prepend-icon="$delete"
                @click="bulkDelete"
                :loading="store.loading"
              >
                Delete
              </v-btn>
            </v-btn-group>
          </div>
        </v-card-text>
      </v-card>

      <!-- Categories List -->
      <v-card class="ds-card categories-card">
        <v-card-title class="ds-p-6 pb-6">
          <div class="d-flex align-center justify-space-between categories-header">
            <div class="d-flex align-center">
              <span class="ds-text-xl ds-font-semibold">Question Categories</span>
              <v-chip
                :text="`${store.categories.length}`"
                variant="tonal"
                size="small"
                class="ml-3"
              />
            </div>
            <v-btn 
              color="primary" 
              @click="showCreateDialog = true" 
              prepend-icon="$plus"
              variant="elevated"
            >
              Add Category
            </v-btn>
          </div>
        </v-card-title>

        <v-divider class="mx-6 mb-4"></v-divider>

        <v-card-text class="ds-p-6 pt-0">
          <FollowupAccordion
            v-if="store.categories.length > 0"
            :categories="store.categories"
            :category-stats="store.categoryStats"
            :expanded-panels="store.expandedPanels"
            :selected-categories="store.selectedCategories"
            :loading="store.loading"
            @update-selected-categories="store.updateSelectedCategories"
            @update-expanded-panels="store.updateExpandedPanels"
            @update-question-selection="store.updateQuestionSelection"
            @edit-category="editCategory"
            @delete-category="deleteCategory"
          />

          <!-- Empty State -->
          <div v-else class="empty-state text-center py-12">
            <v-avatar size="80" color="grey-lighten-3" class="ds-mb-4">
              <v-icon size="40" color="grey-lighten-1">$format-list-group</v-icon>
            </v-avatar>

            <h3 class="text-h6 ds-font-semibold ds-mb-2">No Categories Yet</h3>
            <p class="text-body-2 text-medium-emphasis ds-mb-6 mx-auto" style="max-width: 320px;">
              Create your first category to organize follow-up questions
            </p>

            <v-btn
              color="primary"
              prepend-icon="$plus"
              @click="showCreateDialog = true"
              variant="elevated"
            >
              Create First Category
            </v-btn>
          </div>
        </v-card-text>
      </v-card>
    </div>

    <!-- Category Dialog -->
    <CategoryDialog
      v-model="showCategoryDialog"
      :category="editingCategory"
      :loading="store.loading"
      @save="saveCategory"
    />

    <!-- Delete Dialog -->
    <CategoryDeleteDialog
      v-model="showDeleteDialog"
      :category="deletingCategory"
      :category-stats="deletingCategory ? store.categoryStats[deletingCategory.id] : null"
      :available-categories="store.availableCategoriesForMove"
      :loading="store.loading"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useFollowupSettingsStore } from '@/stores/followupSettings'
import { useNotifications } from '@/composables/useNotifications'
import FollowupAccordion from '@/components/FollowupAccordion.vue'
import CategoryDialog from '@/components/CategoryDialog.vue'
import CategoryDeleteDialog from '@/components/CategoryDeleteDialog.vue'

// Store and composables
const store = useFollowupSettingsStore()
const { showSuccess, showError } = useNotifications()

// Local state
const showCreateDialog = ref(false)
const showCategoryDialog = ref(false)
const showDeleteDialog = ref(false)
const editingCategory = ref(null)
const deletingCategory = ref(null)

// Lifecycle
onMounted(() => {
  store.loadData()
})

// Methods
const updateSetting = async (key, value) => {
  try {
    await store.updateSetting(key, value)
    showSuccess(`Setting "${key}" updated successfully!`)
  } catch (err) {
    showError(`Failed to update setting: ${err.message}`)
  }
}

const editCategory = (category) => {
  editingCategory.value = category
  showCategoryDialog.value = true
}

const saveCategory = async (categoryData) => {
  try {
    if (editingCategory.value) {
      await store.updateCategory(editingCategory.value.id, categoryData)
      showSuccess('Category updated successfully!')
    } else {
      await store.createCategory(categoryData)
      showSuccess('Category created successfully!')
    }
    showCategoryDialog.value = false
    editingCategory.value = null
  } catch (err) {
    showError(`Failed to save category: ${err.message}`)
  }
}

const deleteCategory = (category) => {
  deletingCategory.value = category
  showDeleteDialog.value = true
}

const confirmDelete = async (deleteRequest) => {
  try {
    await store.deleteCategory(deleteRequest)
    showSuccess('Category deleted successfully!')
    showDeleteDialog.value = false
    deletingCategory.value = null
  } catch (err) {
    showError(`Failed to delete category: ${err.message}`)
  }
}

const bulkActivate = async () => {
  try {
    await store.bulkActivateCategories(store.selectedCategories)
    showSuccess(`${store.selectedCategories.length} categories activated!`)
  } catch (err) {
    showError(`Failed to activate categories: ${err.message}`)
  }
}

const bulkDeactivate = async () => {
  try {
    await store.bulkDeactivateCategories(store.selectedCategories)
    showSuccess(`${store.selectedCategories.length} categories deactivated!`)
  } catch (err) {
    showError(`Failed to deactivate categories: ${err.message}`)
  }
}

const bulkDelete = async () => {
  try {
    await store.bulkDeleteCategories(store.selectedCategories)
    showSuccess(`${store.selectedCategories.length} categories deleted!`)
  } catch (err) {
    showError(`Failed to delete categories: ${err.message}`)
  }
}
</script>

<style scoped>
.categories-header {
  padding-bottom: 16px;
}
</style>
