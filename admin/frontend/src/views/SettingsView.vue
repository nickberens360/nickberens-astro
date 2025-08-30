<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-6">
          <v-icon left>$settings</v-icon>
          Follow-up Question Management
        </h1>
      </v-col>
    </v-row>

    <!-- Quick Stats Dashboard -->
    <v-row class="mb-6">
      <v-col cols="3">
        <MetricCard 
          title="Active Categories" 
          :value="stats.active_categories"
          icon="$folder"
          color="success"
        />
      </v-col>
      <v-col cols="3">
        <MetricCard 
          title="Total Questions" 
          :value="stats.total_questions"
          icon="$help-circle"
          color="primary"
        />
      </v-col>
      <v-col cols="3">
        <MetricCard 
          title="Inactive Categories" 
          :value="stats.inactive_categories"
          icon="$alert"
          color="warning"
        />
      </v-col>
      <v-col cols="3">
        <MetricCard 
          title="Generation Method" 
          :value="settings.service_type || 'static'"
          icon="$brain"
          color="info"
        />
      </v-col>
    </v-row>

    <!-- System Settings Card -->
    <v-card class="mb-6">
      <v-card-title>
        <v-icon left>$brain</v-icon>
        System Settings
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12" md="6">
            <v-switch
              v-model="settings.enabled"
              label="Enable follow-up questions"
              color="primary"
              hide-details
              @change="saveSettings"
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-select
              v-model="settings.service_type"
              :items="serviceTypeOptions"
              label="Generation Method"
              variant="outlined"
              density="comfortable"
              @update:model-value="saveSettings"
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-slider
              v-model="settings.max_questions"
              :min="1"
              :max="5"
              :step="1"
              label="Maximum Questions"
              thumb-label="always"
              show-ticks="always"
              @end="saveSettings"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Bulk Actions Toolbar -->
    <v-card class="mb-4" v-if="selectedCategories.length > 0">
      <v-card-text>
        <v-row align="center">
          <v-col>
            <v-chip color="primary" variant="flat">
              {{ selectedCategories.length }} categories selected
            </v-chip>
          </v-col>
          <v-col cols="auto">
            <v-btn-group>
              <v-btn
                variant="outlined"
                prepend-icon="$eye"
                @click="bulkActivateCategories"
                :disabled="loading"
              >
                Activate
              </v-btn>
              <v-btn
                variant="outlined"
                prepend-icon="$eye-off"
                @click="bulkDeactivateCategories"
                :disabled="loading"
              >
                Deactivate
              </v-btn>
              <v-btn
                variant="outlined"
                color="error"
                prepend-icon="$delete"
                @click="bulkDeleteCategories"
                :disabled="loading"
              >
                Delete
              </v-btn>
            </v-btn-group>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Categories Management -->
    <v-card>
      <v-card-title>
        <v-row align="center">
          <v-col>
            <v-icon left>$format-list-group</v-icon>
            Categories & Questions
          </v-col>
          <v-col cols="auto">
            <v-btn
              color="primary"
              prepend-icon="$plus"
              @click="handleCreateCategoryDialog"
              :disabled="loading"
            >
              Add Category
            </v-btn>
          </v-col>
        </v-row>
      </v-card-title>
      
      <v-card-text>
        <!-- Categories with Expansion Panels -->
        <v-expansion-panels v-model="expandedPanels" multiple>
          <v-expansion-panel
            v-for="category in categories"
            :key="category.id"
            :value="category.id"
            class="category-panel"
            :class="{ 'category-panel--inactive': !category.is_active }"
          >
            <v-expansion-panel-title>
              <div class="d-flex align-center w-100">
                <!-- Selection Checkbox -->
                <v-checkbox
                  v-model="selectedCategories"
                  :value="category"
                  hide-details
                  density="compact"
                  class="mr-3"
                  @click.stop
                />
                
                <!-- Category Info -->
                <div class="flex-grow-1 d-flex align-center">
                  <v-icon class="mr-3" :color="category.is_active ? 'primary' : 'grey'">
                    ${{ category.icon || 'help-circle' }}
                  </v-icon>
                  <div>
                    <div class="text-subtitle-1 font-weight-medium">
                      {{ category.display_name }}
                      <v-chip
                        v-if="!category.is_active"
                        size="small"
                        color="warning"
                        variant="flat"
                        class="ml-2"
                      >
                        Inactive
                      </v-chip>
                    </div>
                    <div class="text-caption text-medium-emphasis">
                      {{ categoryStats[category.id]?.question_count || 0 }} questions
                      • Sort order: {{ category.sort_order }}
                    </div>
                  </div>
                </div>
                
                <!-- Quick Actions -->
                <div class="d-flex" @click.stop>
                  <v-btn
                    icon="$edit"
                    size="small"
                    variant="text"
                    @click="editCategory(category)"
                    :disabled="loading"
                  />
                  <v-btn
                    icon="$delete"
                    size="small"
                    variant="text"
                    color="error"
                    @click="showDeleteCategoryDialog(category)"
                    :disabled="loading"
                  />
                </div>
              </div>
            </v-expansion-panel-title>
            
            <v-expansion-panel-text>
              <!-- Question Manager Component -->
              <QuestionManager
                :category="category"
                :selected-questions="selectedQuestions[category.id] || []"
                @questions-updated="loadData"
                @selection-changed="(questions) => updateQuestionSelection(category.id, questions)"
              />
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>

        <!-- Empty State -->
        <div v-if="categories.length === 0" class="text-center py-12">
          <v-icon size="64" color="grey-lighten-1">$format-list-group</v-icon>
          <h3 class="text-h6 mt-4 mb-2">No categories yet</h3>
          <p class="text-body-2 text-medium-emphasis mb-6">
            Create your first category to start managing follow-up questions
          </p>
          <v-btn
            color="primary"
            prepend-icon="$plus"
            @click="handleCreateCategoryDialog"
          >
            Create First Category
          </v-btn>
        </div>
      </v-card-text>
    </v-card>

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
  </v-container>
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
    const editingCategory = ref(null)
    const deletingCategory = ref(null)

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

    const bulkDeleteCategories = async () => {
      if (!confirm(`Are you sure you want to delete ${selectedCategories.value.length} categories?`)) {
        return
      }

      try {
        loading.value = true
        await Promise.all(
          selectedCategories.value.map(category =>
            api.deleteFollowupCategoryWithStrategyNormalized({
              categoryId: category.id,
              strategy: 'delete_all'
            })
          )
        )
        showSuccessMessage(`${selectedCategories.value.length} categories deleted!`)
        selectedCategories.value = []
        await loadData()
      } catch (err) {
        showErrorMessage('Failed to delete categories')
      } finally {
        loading.value = false
      }
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
      editingCategory,
      deletingCategory,
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
      updateQuestionSelection,
      handleCreateCategoryDialog
    }
  }
}
</script>

<style scoped>
.category-panel {
  margin-bottom: 8px;
  border: 1px solid rgba(var(--v-theme-outline), 0.2);
}

.category-panel--inactive {
  opacity: 0.7;
  border-style: dashed;
}

.category-panel--inactive .v-expansion-panel-title {
  background: rgba(var(--v-theme-warning), 0.05);
}
</style>