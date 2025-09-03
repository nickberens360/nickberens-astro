# Settings System Migration Plan

## Overview

This document outlines the comprehensive refactoring of the admin dashboard settings system to address critical architectural brittleness and maintainability issues.

## Current Architecture Problems

### 🚨 Critical Issues

#### 1. Massive Central Orchestrator Anti-Pattern
- **SettingsView.vue**: 1,269 lines managing 6 different settings domains
- Single component handling: navigation, data loading, caching, stats, settings, dialogs, bulk operations
- 17+ props passed to router-view creating massive dependency coupling

#### 2. Data Flow Brittleness
```
Current Flow (BRITTLE):
API → Parent loads ALL data → Massive prop drilling → Child renders → Events bubble up → Parent handles API
```

#### 3. Child View Dependency Hell
- **FollowupSettings.vue**: 329 props, 0 autonomous logic, pure presentation layer
- **ResponseSettings.vue**: 68 lines, just emits to parent for saves  
- **FeatureSettings.vue**: 74 lines, no direct API access
- **CacheSettings.vue**: 55 lines, display-only component

#### 4. API Service Over-Centralization
- 733 lines in `api.js` with 80+ methods
- No service separation by domain (auth, settings, queries all mixed)
- No composables for reusable data fetching logic

#### 5. State Management Issues
- No Pinia stores for settings domains
- Parent component becomes accidental state manager
- Cross-child state dependencies managed ad-hoc

#### 6. Routing/Navigation Coupling
- Parent manually maps tabs to routes
- Child components have no route awareness
- Navigation logic tightly coupled to data loading

## Target Architecture

### ✅ Desired State

#### 1. Domain-Driven Architecture
```
New Flow (ROBUST):
Child Component → Domain Store → Domain Service → API → Direct Updates
```

#### 2. Self-Sufficient Components
- Each settings view manages its own data lifecycle
- Direct API access through domain-specific services
- Independent state management via Pinia stores

#### 3. Minimal Parent Container
- Parent becomes pure layout container (~100 lines)
- No data orchestration or prop drilling
- Clean separation of concerns

## Migration Plan

### Phase 1: Service Layer Foundation (Week 1)

#### 1.1 Create Domain-Specific Services

**File: `admin/frontend/src/services/settings/followupSettingsService.js`**
```javascript
import adminAPI from '@/services/api'

export class FollowupSettingsService {
  async getSettings() {
    return await adminAPI.getFollowupSettings()
  }

  async updateSettings(settings) {
    return await adminAPI.updateFollowupSettings(settings)
  }

  async getCategories(includeInactive = true) {
    return await adminAPI.getFollowupCategories(includeInactive)
  }

  async createCategory(categoryData) {
    return await adminAPI.createFollowupCategory(categoryData)
  }

  async updateCategory(categoryId, categoryData) {
    return await adminAPI.updateFollowupCategory(categoryId, categoryData)
  }

  async deleteCategory(deleteRequest) {
    return await adminAPI.deleteFollowupCategoryWithStrategy(deleteRequest)
  }

  async getCategoryStats(categoryId) {
    return await adminAPI.getFollowupCategoryStats(categoryId)
  }

  async bulkUpdateCategories(operations) {
    return await Promise.all(operations.map(op => 
      this.updateCategory(op.id, op.data)
    ))
  }
}

export const followupSettingsService = new FollowupSettingsService()
```

**File: `admin/frontend/src/services/settings/responseSettingsService.js`**
```javascript
import adminAPI from '@/services/api'

export class ResponseSettingsService {
  async getSettings() {
    return await adminAPI.getResponseSettings()
  }

  async updateSettings(settings) {
    return await adminAPI.updateResponseSettings(settings)
  }
}

export const responseSettingsService = new ResponseSettingsService()
```

**File: `admin/frontend/src/services/settings/featureSettingsService.js`**
```javascript
import adminAPI from '@/services/api'

export class FeatureSettingsService {
  async getFeatureFlags() {
    return await adminAPI.getFeatureFlags()
  }

  async updateFeatureFlags(flags) {
    return await adminAPI.updateFeatureFlags(flags)
  }
}

export const featureSettingsService = new FeatureSettingsService()
```

**File: `admin/frontend/src/services/settings/cacheSettingsService.js`**
```javascript
import adminAPI from '@/services/api'

export class CacheSettingsService {
  async getCacheStatus() {
    return await adminAPI.getSettingsCacheStatus()
  }

  async invalidateCache() {
    return await adminAPI.invalidateSettingsCache()
  }
}

export const cacheSettingsService = new CacheSettingsService()
```

#### 1.2 Create Domain-Specific Pinia Stores

**File: `admin/frontend/src/stores/followupSettings.js`**
```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { followupSettingsService } from '@/services/settings/followupSettingsService'

export const useFollowupSettingsStore = defineStore('followupSettings', () => {
  // State
  const settings = ref({
    enabled: true,
    service_type: 'static',
    max_questions: 3,
    include_technical: true,
    include_personal: true,
    include_creative: true
  })
  
  const categories = ref([])
  const categoryStats = ref({})
  const expandedPanels = ref([])
  const selectedCategories = ref([])
  const selectedQuestions = ref({})
  const loading = ref(false)
  const error = ref(null)

  // Computed
  const stats = computed(() => ({
    active_categories: categories.value.filter(c => c.is_active).length,
    inactive_categories: categories.value.filter(c => !c.is_active).length,
    total_questions: Object.values(categoryStats.value)
      .reduce((sum, stat) => sum + (stat.question_count || 0), 0)
  }))

  const availableCategoriesForMove = computed(() => 
    categories.value.filter(c => c.is_active)
  )

  // Actions
  const loadData = async () => {
    try {
      loading.value = true
      error.value = null

      const [settingsData, categoriesData] = await Promise.all([
        followupSettingsService.getSettings(),
        followupSettingsService.getCategories()
      ])

      if (settingsData && typeof settingsData === 'object') {
        Object.assign(settings.value, settingsData)
      }
      categories.value = categoriesData || []

      // Load stats for each category
      const statsPromises = categories.value.map(async (category) => {
        try {
          const stats = await followupSettingsService.getCategoryStats(category.id)
          categoryStats.value[category.id] = stats
        } catch (err) {
          console.warn(`Failed to load stats for category ${category.id}:`, err)
          categoryStats.value[category.id] = { question_count: 0 }
        }
      })

      await Promise.all(statsPromises)
    } catch (err) {
      console.error('Failed to load followup settings data:', err)
      error.value = err.message || 'Failed to load data'
    } finally {
      loading.value = false
    }
  }

  const updateSetting = async (key, value) => {
    try {
      settings.value[key] = value
      await followupSettingsService.updateSettings(settings.value)
    } catch (err) {
      console.error('Failed to update setting:', err)
      error.value = err.message || 'Failed to update setting'
      throw err
    }
  }

  const saveSettings = async () => {
    try {
      loading.value = true
      await followupSettingsService.updateSettings(settings.value)
    } catch (err) {
      console.error('Failed to save settings:', err)
      error.value = err.message || 'Failed to save settings'
      throw err
    } finally {
      loading.value = false
    }
  }

  const createCategory = async (categoryData) => {
    try {
      loading.value = true
      await followupSettingsService.createCategory(categoryData)
      await loadData() // Refresh data
    } catch (err) {
      console.error('Failed to create category:', err)
      error.value = err.message || 'Failed to create category'
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateCategory = async (categoryId, categoryData) => {
    try {
      loading.value = true
      await followupSettingsService.updateCategory(categoryId, categoryData)
      await loadData() // Refresh data
    } catch (err) {
      console.error('Failed to update category:', err)
      error.value = err.message || 'Failed to update category'
      throw err
    } finally {
      loading.value = false
    }
  }

  const deleteCategory = async (deleteRequest) => {
    try {
      loading.value = true
      await followupSettingsService.deleteCategory(deleteRequest)
      await loadData() // Refresh data
    } catch (err) {
      console.error('Failed to delete category:', err)
      error.value = err.message || 'Failed to delete category'
      throw err
    } finally {
      loading.value = false
    }
  }

  const bulkActivateCategories = async (categories) => {
    try {
      loading.value = true
      const operations = categories.map(cat => ({
        id: cat.id,
        data: { is_active: true }
      }))
      await followupSettingsService.bulkUpdateCategories(operations)
      selectedCategories.value = []
      await loadData()
    } catch (err) {
      console.error('Failed to bulk activate categories:', err)
      error.value = err.message || 'Failed to activate categories'
      throw err
    } finally {
      loading.value = false
    }
  }

  const bulkDeactivateCategories = async (categories) => {
    try {
      loading.value = true
      const operations = categories.map(cat => ({
        id: cat.id,
        data: { is_active: false }
      }))
      await followupSettingsService.bulkUpdateCategories(operations)
      selectedCategories.value = []
      await loadData()
    } catch (err) {
      console.error('Failed to bulk deactivate categories:', err)
      error.value = err.message || 'Failed to deactivate categories'
      throw err
    } finally {
      loading.value = false
    }
  }

  const bulkDeleteCategories = async (categories) => {
    try {
      loading.value = true
      const deletePromises = categories.map(cat =>
        followupSettingsService.deleteCategory({
          categoryId: cat.id,
          strategy: 'delete'
        })
      )
      await Promise.all(deletePromises)
      selectedCategories.value = []
      await loadData()
    } catch (err) {
      console.error('Failed to bulk delete categories:', err)
      error.value = err.message || 'Failed to delete categories'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    settings,
    categories,
    categoryStats,
    expandedPanels,
    selectedCategories,
    selectedQuestions,
    loading,
    error,
    
    // Computed
    stats,
    availableCategoriesForMove,
    
    // Actions
    loadData,
    updateSetting,
    saveSettings,
    createCategory,
    updateCategory,
    deleteCategory,
    bulkActivateCategories,
    bulkDeactivateCategories,
    bulkDeleteCategories
  }
})
```

**File: `admin/frontend/src/stores/responseSettings.js`**
```javascript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { responseSettingsService } from '@/services/settings/responseSettingsService'

export const useResponseSettingsStore = defineStore('responseSettings', () => {
  const settings = ref({
    max_context_length: 2000,
    max_context_documents: 3,
    context_fill_ratio: 0.7,
    enable_caching: true,
    cache_ttl_seconds: 3600
  })

  const loading = ref(false)
  const error = ref(null)

  const loadData = async () => {
    try {
      loading.value = true
      error.value = null
      const data = await responseSettingsService.getSettings()
      if (data) {
        Object.assign(settings.value, data)
      }
    } catch (err) {
      console.error('Failed to load response settings:', err)
      error.value = err.message || 'Failed to load settings'
    } finally {
      loading.value = false
    }
  }

  const updateSettings = async (newSettings = null) => {
    try {
      loading.value = true
      const dataToSave = newSettings || settings.value
      await responseSettingsService.updateSettings(dataToSave)
      if (newSettings) {
        Object.assign(settings.value, newSettings)
      }
    } catch (err) {
      console.error('Failed to update response settings:', err)
      error.value = err.message || 'Failed to update settings'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    settings,
    loading,
    error,
    loadData,
    updateSettings
  }
})
```

#### 1.3 Create Reusable Composables

**File: `admin/frontend/src/composables/useSettings.js`**
```javascript
import { ref } from 'vue'

export function useSettings(service, store) {
  const loading = ref(false)
  const error = ref(null)
  const success = ref(false)

  const save = async (data) => {
    try {
      loading.value = true
      error.value = null
      success.value = false
      
      await service.updateSettings(data)
      success.value = true
      
      // Optionally refresh store
      if (store?.loadData) {
        await store.loadData()
      }
    } catch (err) {
      console.error('Failed to save settings:', err)
      error.value = err.message || 'Failed to save settings'
      throw err
    } finally {
      loading.value = false
    }
  }

  const load = async () => {
    try {
      loading.value = true
      error.value = null
      
      if (store?.loadData) {
        await store.loadData()
      }
    } catch (err) {
      console.error('Failed to load settings:', err)
      error.value = err.message || 'Failed to load settings'
      throw err
    } finally {
      loading.value = false
    }
  }

  const reset = () => {
    error.value = null
    success.value = false
  }

  return {
    loading,
    error,
    success,
    save,
    load,
    reset
  }
}
```

**File: `admin/frontend/src/composables/useNotifications.js`**
```javascript
import { ref } from 'vue'

const notifications = ref([])

export function useNotifications() {
  const showSuccess = (message, duration = 4000) => {
    notifications.value.push({
      id: Date.now(),
      type: 'success',
      message,
      duration
    })
  }

  const showError = (message, duration = 6000) => {
    notifications.value.push({
      id: Date.now(),
      type: 'error',
      message,
      duration
    })
  }

  const showInfo = (message, duration = 4000) => {
    notifications.value.push({
      id: Date.now(),
      type: 'info',
      message,
      duration
    })
  }

  const dismiss = (notificationId) => {
    const index = notifications.value.findIndex(n => n.id === notificationId)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }

  return {
    notifications,
    showSuccess,
    showError,
    showInfo,
    dismiss
  }
}
```

### Phase 2: Refactor Child Components (Week 2-3)

#### 2.1 Autonomous FollowupSettings.vue

**File: `admin/frontend/src/views/settings/FollowupSettings.vue`**
```vue
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
                  :items="serviceTypeOptions"
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
            @update-selected-categories="store.selectedCategories = $event"
            @update-expanded-panels="store.expandedPanels = $event"
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

// Constants
const serviceTypeOptions = [
  { title: 'Static (Sequential)', value: 'static' },
  { title: 'Dynamic (Context-aware)', value: 'dynamic' },
  { title: 'Contextual (AI-powered)', value: 'contextual' }
]

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
```

#### 2.2 Autonomous ResponseSettings.vue

**File: `admin/frontend/src/views/settings/ResponseSettings.vue`**
```vue
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
      
      <v-card-text class="pa-6">
        <v-alert v-if="store.error" type="error" variant="tonal" class="mb-4">
          {{ store.error }}
        </v-alert>
        
        <v-row>
          <v-col cols="12" md="6">
            <v-text-field
              v-model.number="store.settings.max_context_length"
              label="Max Context Length"
              type="number"
              variant="outlined"
              :min="100"
              :max="10000"
              hint="Maximum character length for context documents"
              persistent-hint
            />
          </v-col>
          
          <v-col cols="12" md="6">
            <v-text-field
              v-model.number="store.settings.max_context_documents"
              label="Max Context Documents"
              type="number"
              variant="outlined"
              :min="1"
              :max="10"
              hint="Maximum number of documents to include in context"
              persistent-hint
            />
          </v-col>
          
          <v-col cols="12" md="6">
            <v-slider
              v-model="store.settings.context_fill_ratio"
              label="Context Fill Ratio"
              :min="0.1"
              :max="1.0"
              :step="0.1"
              thumb-label="always"
              show-ticks="always"
              color="primary"
              hint="Ratio of context to fill with relevant documents"
              persistent-hint
            />
          </v-col>
          
          <v-col cols="12" md="6">
            <v-switch
              v-model="store.settings.enable_caching"
              label="Enable Response Caching"
              color="primary"
              inset
              hide-details
            />
            <div class="text-caption text-medium-emphasis mt-2">
              Cache responses to improve performance for repeated queries
            </div>
          </v-col>
          
          <v-col cols="12" md="6">
            <v-text-field
              v-model.number="store.settings.cache_ttl_seconds"
              label="Cache TTL (seconds)"
              type="number"
              variant="outlined"
              :min="60"
              :max="86400"
              hint="How long to keep cached responses (60s - 24h)"
              persistent-hint
              :disabled="!store.settings.enable_caching"
            />
          </v-col>
        </v-row>
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
```

#### 2.3 Autonomous FeatureSettings.vue

**File: `admin/frontend/src/views/settings/FeatureSettings.vue`**
```vue
<template>
  <div>
    <v-card elevation="2">
      <v-card-title class="text-h6 font-weight-bold pa-6 d-flex align-center justify-space-between">
        <span>Feature Flags</span>
        <v-btn
          color="primary"
          variant="elevated"
          @click="saveFeatureFlags"
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
        
        <v-row v-if="store.featureFlags && Object.keys(store.featureFlags).length > 0">
          <v-col 
            cols="12" 
            md="6" 
            lg="4" 
            v-for="(value, key) in store.featureFlags" 
            :key="key"
          >
            <v-switch
              v-model="store.featureFlags[key]"
              :label="formatFeatureName(key)"
              color="primary"
              inset
              hide-details
              class="mb-2"
            />
            <div class="text-caption text-medium-emphasis ml-12">
              {{ getFeatureDescription(key) }}
            </div>
          </v-col>
        </v-row>
        
        <v-alert
          v-else
          type="info"
          variant="tonal"
        >
          No feature flags available
        </v-alert>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useFeatureSettingsStore } from '@/stores/featureSettings'
import { useNotifications } from '@/composables/useNotifications'

const store = useFeatureSettingsStore()
const { showSuccess, showError } = useNotifications()

onMounted(() => {
  store.loadData()
})

const formatFeatureName = (key) => {
  return key
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

const getFeatureDescription = (key) => {
  const descriptions = {
    enable_illustrations: 'Show illustration images in responses',
    enable_geolocation: 'Use location-based query processing',
    enable_analytics: 'Collect and analyze usage statistics',
    enable_debug_logging: 'Enable detailed debug logging',
    enable_response_caching: 'Cache responses for better performance',
    enable_query_preprocessing: 'Preprocess queries for better accuracy'
  }
  return descriptions[key] || 'Feature flag setting'
}

const saveFeatureFlags = async () => {
  try {
    await store.updateFeatureFlags()
    showSuccess('Feature flags updated successfully!')
  } catch (err) {
    showError(`Failed to save feature flags: ${err.message}`)
  }
}
</script>
```

### Phase 3: Simplify Parent Container (Week 4)

#### 3.1 Minimal SettingsView.vue

**File: `admin/frontend/src/views/SettingsView.vue`**
```vue
<template>
  <div class="settings-page">
    <div class="settings-layout">
      <!-- Pure Navigation -->
      <SettingsNavigation />
      
      <!-- Content Area -->
      <main class="settings-content">
        <!-- Page Header -->
        <SettingsHeader />
        
        <!-- Just route content, no data orchestration -->
        <router-view />
      </main>
    </div>
    
    <!-- Global Notifications -->
    <SettingsNotifications />
  </div>
</template>

<script setup>
// Minimal parent - only layout and navigation
// No data loading, no prop drilling, no event bubbling
</script>

<style scoped>
.settings-page {
  max-width: 100%;
  margin: 0 auto;
}

.settings-layout {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

.settings-content {
  flex: 1;
  min-width: 0;
}

/* Responsive Design */
@media (max-width: 1024px) {
  .settings-layout {
    flex-direction: column;
    gap: 16px;
  }
}

@media (max-width: 768px) {
  .settings-page {
    padding: 0 16px;
  }
}
</style>
```

#### 3.2 Settings Navigation Component

**File: `admin/frontend/src/components/settings/SettingsNavigation.vue`**
```vue
<template>
  <nav class="settings-nav">
    <v-list class="settings-nav-list" nav density="comfortable" rounded="lg">
      <v-list-item
        v-for="tab in navigationTabs"
        :key="tab.value"
        :value="tab.value"
        :active="currentTab === tab.value"
        @click="navigateToTab(tab.value)"
        class="settings-nav-item"
        :class="{ 'settings-nav-item--active': currentTab === tab.value }"
        rounded="lg"
      >
        <template v-slot:prepend>
          <v-icon :icon="tab.icon" size="20" />
        </template>
        <v-list-item-title class="settings-nav-title">{{ tab.title }}</v-list-item-title>
      </v-list-item>
    </v-list>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const navigationTabs = [
  {
    value: 'followup',
    title: 'Follow-up Questions',
    icon: '$help-circle'
  },
  {
    value: 'welcome',
    title: 'Welcome Questions',
    icon: '$message-text'
  },
  {
    value: 'response',
    title: 'Response Settings',
    icon: '$message-reply'
  },
  {
    value: 'routing',
    title: 'Query Routing',
    icon: '$route'
  },
  {
    value: 'features',
    title: 'Feature Flags',
    icon: '$feature-flag'
  },
  {
    value: 'cache',
    title: 'Cache Status',
    icon: '$cached'
  }
]

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
</script>

<style scoped>
.settings-nav {
  flex-shrink: 0;
  width: 280px;
  position: sticky;
  top: 24px;
}

.settings-nav-list {
  background: transparent;
  padding: 0;
}

.settings-nav-item {
  margin: 8px;
  border-radius: 12px;
  transition: all 0.2s ease;
}

.settings-nav-item:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}

.settings-nav-item--active {
  background: rgba(var(--v-theme-primary), 0.12);
  color: rgb(var(--v-theme-primary));
}

.settings-nav-title {
  font-weight: 500;
  font-size: 0.95rem;
}

/* Mobile responsiveness */
@media (max-width: 1024px) {
  .settings-nav {
    width: 100%;
    position: relative;
    top: auto;
  }
  
  .settings-nav .v-list {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 4px;
    padding: 8px;
  }
  
  .settings-nav-item {
    flex: 1;
    min-width: 140px;
    margin: 0;
  }
  
  .settings-nav-title {
    font-size: 0.85rem;
  }
}

@media (max-width: 768px) {
  .settings-nav .v-list {
    flex-direction: column;
    gap: 0;
  }
  
  .settings-nav-item {
    min-width: auto;
    margin: 4px 8px;
  }
}
</style>
```

#### 3.3 Settings Header Component

**File: `admin/frontend/src/components/settings/SettingsHeader.vue`**
```vue
<template>
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
          :loading="cacheLoading"
          variant="elevated"
          class="mr-3"
        >
          Clear Cache
        </v-btn>
        <v-btn
          color="primary"
          prepend-icon="$refresh"
          @click="refreshAllSettings"
          :loading="refreshLoading"
          variant="elevated"
        >
          Refresh All
        </v-btn>
      </v-btn-group>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useNotifications } from '@/composables/useNotifications'
import { cacheSettingsService } from '@/services/settings/cacheSettingsService'

const { showSuccess, showError } = useNotifications()

const cacheLoading = ref(false)
const refreshLoading = ref(false)

const invalidateCache = async () => {
  try {
    cacheLoading.value = true
    await cacheSettingsService.invalidateCache()
    showSuccess('Settings cache invalidated successfully!')
  } catch (err) {
    showError(`Failed to invalidate cache: ${err.message}`)
  } finally {
    cacheLoading.value = false
  }
}

const refreshAllSettings = async () => {
  try {
    refreshLoading.value = true
    // Trigger refresh across all stores
    // This could be improved with a global event bus
    window.location.reload() // Simple solution for now
  } catch (err) {
    showError(`Failed to refresh settings: ${err.message}`)
  } finally {
    refreshLoading.value = false
  }
}
</script>

<style scoped>
.page-header {
  background: transparent;
  padding: 0 32px 32px 32px;
  margin-bottom: 32px;
}

.page-title {
  color: rgb(var(--v-theme-on-surface));
}

.page-subtitle {
  max-width: 600px;
}

@media (max-width: 768px) {
  .page-header {
    padding: 24px;
  }
  
  .page-header .d-flex {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start !important;
  }
}
</style>
```

#### 3.4 Global Notifications Component

**File: `admin/frontend/src/components/settings/SettingsNotifications.vue`**
```vue
<template>
  <div class="notifications-container">
    <v-snackbar
      v-for="notification in notifications"
      :key="notification.id"
      v-model="notification.show"
      :color="notification.type"
      :timeout="notification.duration"
      location="top right"
      @update:model-value="dismiss(notification.id)"
    >
      {{ notification.message }}
      <template v-slot:actions>
        <v-btn
          variant="text"
          @click="dismiss(notification.id)"
        >
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useNotifications } from '@/composables/useNotifications'

const { notifications, dismiss } = useNotifications()

// Auto-show notifications
onMounted(() => {
  notifications.value.forEach(notification => {
    notification.show = true
  })
})
</script>
```

### Phase 4: Additional Store Implementations

#### 4.1 Feature Settings Store

**File: `admin/frontend/src/stores/featureSettings.js`**
```javascript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { featureSettingsService } from '@/services/settings/featureSettingsService'

export const useFeatureSettingsStore = defineStore('featureSettings', () => {
  const featureFlags = ref({
    enable_illustrations: true,
    enable_geolocation: true,
    enable_analytics: true,
    enable_debug_logging: false,
    enable_response_caching: true,
    enable_query_preprocessing: true
  })

  const loading = ref(false)
  const error = ref(null)

  const loadData = async () => {
    try {
      loading.value = true
      error.value = null
      const data = await featureSettingsService.getFeatureFlags()
      if (data) {
        Object.assign(featureFlags.value, data)
      }
    } catch (err) {
      console.error('Failed to load feature flags:', err)
      error.value = err.message || 'Failed to load feature flags'
    } finally {
      loading.value = false
    }
  }

  const updateFeatureFlags = async (updatedFlags = null) => {
    try {
      loading.value = true
      const dataToSave = updatedFlags || featureFlags.value
      await featureSettingsService.updateFeatureFlags(dataToSave)
      if (updatedFlags) {
        Object.assign(featureFlags.value, updatedFlags)
      }
    } catch (err) {
      console.error('Failed to update feature flags:', err)
      error.value = err.message || 'Failed to update feature flags'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    featureFlags,
    loading,
    error,
    loadData,
    updateFeatureFlags
  }
})
```

#### 4.2 Cache Settings Store

**File: `admin/frontend/src/stores/cacheSettings.js`**
```javascript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { cacheSettingsService } from '@/services/settings/cacheSettingsService'

export const useCacheSettingsStore = defineStore('cacheSettings', () => {
  const cacheStatus = ref({
    cache_size: 0,
    ttl_seconds: 3600,
    cached_settings: {}
  })

  const loading = ref(false)
  const error = ref(null)

  const loadData = async () => {
    try {
      loading.value = true
      error.value = null
      const data = await cacheSettingsService.getCacheStatus()
      if (data) {
        cacheStatus.value = data
      }
    } catch (err) {
      console.error('Failed to load cache status:', err)
      error.value = err.message || 'Failed to load cache status'
    } finally {
      loading.value = false
    }
  }

  const invalidateCache = async () => {
    try {
      loading.value = true
      await cacheSettingsService.invalidateCache()
      // Reload cache status after invalidation
      await loadData()
    } catch (err) {
      console.error('Failed to invalidate cache:', err)
      error.value = err.message || 'Failed to invalidate cache'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    cacheStatus,
    loading,
    error,
    loadData,
    invalidateCache
  }
})
```

### Phase 5: Route-Based Data Loading

#### 5.1 Enhanced Router Configuration

**File: `admin/frontend/src/router/index.js` (Settings Section)**
```javascript
{
  path: 'settings',
  name: 'settings',
  component: () => import('@/views/SettingsView.vue'),
  meta: {
    title: 'Settings',
    icon: 'settings'
  },
  children: [
    {
      path: '',
      name: 'settings-overview',
      redirect: 'followup'
    },
    {
      path: 'followup',
      name: 'settings-followup',
      component: () => import('@/views/settings/FollowupSettings.vue'),
      meta: {
        title: 'Follow-up Questions'
      }
    },
    {
      path: 'welcome',
      name: 'settings-welcome',
      component: () => import('@/views/settings/WelcomeSettings.vue'),
      meta: {
        title: 'Welcome Questions'
      }
    },
    {
      path: 'response',
      name: 'settings-response',
      component: () => import('@/views/settings/ResponseSettings.vue'),
      meta: {
        title: 'Response Settings'
      }
    },
    {
      path: 'routing',
      name: 'settings-routing',
      component: () => import('@/views/settings/RoutingSettings.vue'),
      meta: {
        title: 'Query Routing'
      }
    },
    {
      path: 'features',
      name: 'settings-features',
      component: () => import('@/views/settings/FeatureSettings.vue'),
      meta: {
        title: 'Feature Flags'
      }
    },
    {
      path: 'cache',
      name: 'settings-cache',
      component: () => import('@/views/settings/CacheSettings.vue'),
      meta: {
        title: 'Cache Status'
      }
    }
  ]
}
```

## Testing Strategy

### Phase 1 Testing: Service Layer
1. **Unit tests** for each service class
2. **Integration tests** for API endpoints
3. **Store tests** for Pinia state management

### Phase 2 Testing: Component Isolation
1. **Component tests** for each settings view in isolation
2. **Mock services** to test component behavior
3. **E2E tests** for critical user workflows

### Phase 3 Testing: System Integration
1. **Full navigation tests**
2. **Cross-component communication tests**
3. **Performance tests** for route-based loading

## Rollback Plan

### Safe Migration Approach
1. **Keep original files** as `.backup` during migration
2. **Feature flags** to switch between old/new architecture
3. **Gradual rollout** - migrate one settings view at a time
4. **Comprehensive monitoring** during transition

### Rollback Triggers
- **Performance degradation** > 200ms
- **Error rate increase** > 5%
- **User complaints** about functionality loss
- **Failed automated tests** in CI/CD

## Success Metrics

### Code Quality Improvements
- ✅ **Parent component LOC**: 1,269 → ~100 (92% reduction)
- ✅ **Prop drilling elimination**: 17+ props → 0 props
- ✅ **Component coupling**: High → Low
- ✅ **Code reusability**: Low → High

### Developer Experience Improvements
- ✅ **New settings view creation**: 4+ hours → 30 minutes
- ✅ **Bug isolation time**: Hours → Minutes
- ✅ **Testing complexity**: High → Low
- ✅ **Maintenance overhead**: High → Low

### Performance Improvements
- ✅ **Route-based lazy loading**: Faster initial page load
- ✅ **Domain-specific caching**: Better data freshness
- ✅ **Reduced re-renders**: Better UI responsiveness

## Timeline

### Week 1: Foundation (Service Layer)
- Create domain-specific services
- Build Pinia stores
- Develop composables
- Write unit tests

### Week 2: First Component Migration
- Refactor FollowupSettings.vue
- Test autonomous operation
- Document patterns

### Week 3: Remaining Components
- Migrate ResponseSettings.vue
- Migrate FeatureSettings.vue
- Migrate CacheSettings.vue
- Test all independently

### Week 4: Parent Simplification
- Extract navigation component
- Extract header component  
- Extract notifications component
- Simplify SettingsView.vue
- Test full integration

### Week 5: Polish & Optimization
- Add advanced features (event bus, etc.)
- Performance optimization
- Documentation updates
- Final testing and rollout

## Post-Migration Benefits

### Maintainability
- Individual settings domains can evolve independently
- New settings views require minimal integration effort
- Bug fixes are isolated to specific domains
- Testing becomes component-focused and faster

### Developer Experience  
- Clear separation of concerns
- Predictable data flow patterns
- Reusable service and store patterns
- Better debugging and development tools

### Performance
- Route-based lazy loading
- Domain-specific caching strategies
- Reduced component re-renders
- Smaller JavaScript bundle sizes

### Architecture Quality
- Follows Single Responsibility Principle
- Achieves loose coupling and high cohesion
- Implements proper dependency inversion
- Enables domain-driven development

This migration transforms the brittle, monolithic settings system into a modern, maintainable, and scalable architecture that will serve the project well as it grows and evolves.