<template>
  <div>
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
          <v-expansion-panels
            v-if="categories.length > 0"
            :modelValue="expandedPanels"
            @update:modelValue="updateExpandedPanels"
            multiple
            variant="accordion"
          >
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
                <div class="d-flex align-center w-100" @click.stop>
                  <!-- Selection Checkbox -->
                  <v-checkbox
                    :model-value="selectedCategories"
                    :value="category"
                    hide-details
                    density="compact"
                    class="mr-4 flex-shrink-0"
                    @click.stop
                    @update:model-value="updateSelectedCategories"
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
                          @click="$emit('edit-category', category)"
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
  </div>
</template>

<script>
import QuestionManager from '@/components/QuestionManager.vue'

export default {
  name: 'FollowupSettings',
  components: {
    QuestionManager
  },
  props: {
    loading: Boolean,
    categories: Array,
    categoryStats: Object,
    expandedPanels: Array,
    settings: Object,
    serviceTypeOptions: Array,
    selectedCategories: Array,
    selectedQuestions: Object,
    stats: Object
  },
  emits: [
    'save-settings',
    'create-category',
    'edit-category',
    'delete-category',
    'bulk-activate',
    'bulk-deactivate',
    'bulk-delete',
    'update-question-selection',
    'update-selected-categories',
    'update-expanded-panels',
    'load-data'
  ],
  computed: {
    // Other computed properties could go here
  },
  methods: {
    saveSettings() {
      this.$emit('save-settings')
    },
    handleCreateCategoryDialog() {
      this.$emit('create-category')
    },
    // Note: edit action handled inline in template via $emit
    showDeleteCategoryDialog(category) {
      this.$emit('delete-category', category)
    },
    bulkActivateCategories() {
      this.$emit('bulk-activate')
    },
    bulkDeactivateCategories() {
      this.$emit('bulk-deactivate')
    },
    bulkDeleteCategories() {
      this.$emit('bulk-delete')
    },
    updateQuestionSelection(categoryId, questions) {
      this.$emit('update-question-selection', categoryId, questions)
    },
    updateSelectedCategories(newValue) {
      this.$emit('update-selected-categories', newValue)
    },
    updateExpandedPanels(newValue) {
      this.$emit('update-expanded-panels', newValue)
    },
    loadData() {
      this.$emit('load-data')
    }
  }
}
</script>
