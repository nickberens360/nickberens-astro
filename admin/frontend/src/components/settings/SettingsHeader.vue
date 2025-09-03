<template>
  <div class="page-header mb-8">
    <div class="d-flex align-center justify-space-between">
      <div>
        <h1 class="page-title text-h4 font-weight-bold mb-2">Settings</h1>
        <p class="page-subtitle text-body-1 text-medium-emphasis">
          Manage system configuration, follow-up questions, and feature settings
        </p>
      </div>
      <div class="d-flex gap-3">
        <v-btn
          color="warning"
          prepend-icon="$refresh"
          @click="invalidateCache"
          :loading="cacheLoading"
          variant="elevated"
          size="default"
        >
          Clear Cache
        </v-btn>
        <v-btn
          color="primary"
          prepend-icon="$refresh"
          @click="refreshAllSettings"
          :loading="refreshLoading"
          variant="elevated"
          size="default"
        >
          Refresh All
        </v-btn>
      </div>
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
    // Simple solution: reload the page to refresh all stores
    window.location.reload()
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

.gap-3 {
  gap: 12px;
}

/* Ensure buttons maintain proper spacing and don't cause overflow */
.page-header .d-flex {
  flex-wrap: nowrap;
  overflow: visible;
}

@media (max-width: 768px) {
  .page-header {
    padding: 24px;
  }
  
  .page-header > .d-flex {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start !important;
  }
  
  .gap-3 {
    flex-direction: column;
    width: 100%;
  }
  
  .gap-3 .v-btn {
    width: 100%;
  }
}

/* Ensure no horizontal overflow */
@media (max-width: 1024px) {
  .page-header > .d-flex {
    flex-wrap: wrap;
    gap: 16px;
  }
  
  .gap-3 {
    flex-shrink: 0;
  }
}
</style>