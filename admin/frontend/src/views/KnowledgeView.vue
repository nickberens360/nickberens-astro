<template>
  <div class="knowledge-view">
    <div class="knowledge-layout">
      <!-- Vertical Navigation -->
      <KnowledgeNavigation />

      <!-- Content Area -->
      <main class="knowledge-content">
        <KnowledgeHeader
          :refresh-loading="refreshLoading"
          :reindex-loading="reindexLoading"
          @refresh="refreshData"
          @reindex="confirmReindex"
        />

        <!-- Legacy metric cards removed in favor of vertical nav -->

        <!-- Action Buttons Row removed (buttons moved to header) -->

        <!-- Routed content -->
        <router-view v-slot="{ Component }">
          <Transition name="fade" mode="out-in">
            <component :is="Component" :refresh-trigger="refreshTrigger" @refresh-complete="onRefreshComplete" />
          </Transition>
        </router-view>
      </main>
    </div>
    

    <!-- Re-Index Confirmation Dialog -->
    <v-dialog
      v-model="showReindexDialog"
      max-width="500"
      persistent
    >
      <v-card>
        <v-card-title class="text-h6">
          {{ reindexLoading ? 'Re-Indexing Knowledge Base' : 'Confirm Knowledge Base Re-Index' }}
        </v-card-title>
        <v-card-text>
          <div v-if="!reindexLoading">
            <v-alert
              type="warning"
              class="mb-4"
            >
              <strong>This operation will:</strong>
              <ul class="mt-2">
                <li>Force rebuild all content indices</li>
                <li>Re-classify all documents with AI</li>
                <li>Take several minutes to complete</li>
                <li>Use additional API credits</li>
              </ul>
            </v-alert>
            Are you sure you want to re-index the entire knowledge base?
          </div>

          <!-- Progress Section -->
          <div v-else>
            <v-alert
              type="info"
              class="mb-4"
            >
              <v-icon class="me-2">$info</v-icon>
              Re-index process has been initiated. The system will process this request on the next server restart.
            </v-alert>

            <div class="mb-4">
              <div class="text-body-2 mb-2">Setting up re-index operation...</div>
              <v-progress-linear
                indeterminate
                color="primary"
                height="8"
                rounded
              />
            </div>

            <div class="text-caption text-medium-emphasis">
              <v-icon size="16" class="me-1">$clock</v-icon>
              This may take a few moments to complete. Please wait...
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            v-if="!reindexLoading"
            variant="text"
            @click="showReindexDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            v-if="!reindexLoading"
            color="warning"
            variant="elevated"
            :loading="reindexLoading"
            @click="executeReindex"
          >
            Re-Index Now
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { adminAPI } from '@/services/api'
import { useNotifications } from '@/composables/useNotifications'
import KnowledgeNavigation from '@/components/knowledge/KnowledgeNavigation.vue'
import KnowledgeHeader from '@/components/knowledge/KnowledgeHeader.vue'

const router = useRouter()
const { showSuccess, showError, showInfo } = useNotifications()

const loading = ref(false)
const refreshLoading = ref(false)
const reindexLoading = ref(false)
const showReindexDialog = ref(false)
const refreshTrigger = ref(0)

const embeddingModel = ref('text-embedding-3-small')

const refreshData = async () => {
  refreshLoading.value = true
  try {
    // Trigger child components to refresh
    refreshTrigger.value++
  } catch (error) {
    console.error('Failed to refresh knowledge data:', error)
    showError('Failed to refresh data')
  } finally {
    refreshLoading.value = false
  }
}

const confirmReindex = () => {
  showReindexDialog.value = true
}

const executeReindex = async () => {
  reindexLoading.value = true
  try {
    // Step 1: Set the reindex flag
    showInfo('Setting re-index flag...')
    const result = await adminAPI.refreshKnowledgeBase(true)

    // Step 2: Show progress simulation with meaningful steps
    showInfo('Re-index flag set successfully! The system will process this on next restart.')

    // Step 3: Provide polling to check flag status
    let flagProcessed = false
    let pollAttempts = 0
    const maxPolls = 30 // Poll for up to 1 minute

    const pollInterval = setInterval(async () => {
      try {
        pollAttempts++
        const status = await adminAPI.getRefreshStatus()

        if (!status.refresh_pending) {
          // Flag has been processed
          clearInterval(pollInterval)
          flagProcessed = true
          showSuccess('Re-index completed successfully! Knowledge base has been refreshed.')
          await refreshData()
          // Close dialog after successful completion
          showReindexDialog.value = false
        } else if (pollAttempts >= maxPolls) {
          // Timeout - flag still pending
          clearInterval(pollInterval)
          showInfo('Re-index flag is set and waiting for server restart. Changes will take effect when the server restarts.')
          // Close dialog after timeout
          showReindexDialog.value = false
        }
      } catch (error) {
        console.error('Error polling refresh status:', error)
      }
    }, 2000) // Poll every 2 seconds

    // If flag wasn't processed within polling period, show helpful message
    setTimeout(() => {
      if (!flagProcessed && pollAttempts < maxPolls) {
        clearInterval(pollInterval)
        showInfo('Re-index scheduled successfully. Changes will take effect on next server restart.')
        showReindexDialog.value = false
      }
    }, 60000) // 1 minute timeout

  } catch (error) {
    console.error('Failed to set re-index flag:', error)
    showError('Failed to set re-index flag: ' + (error.response?.data?.detail || error.message || 'Unknown error'))
  } finally {
    reindexLoading.value = false
    showReindexDialog.value = false
  }
}

const onRefreshComplete = () => {
  // Called when child components finish their refresh operations
  // Can be used for additional coordination if needed
}


onMounted(() => {})
</script>

<style scoped>
.knowledge-view {
  margin: 0 auto;
}

.cursor-pointer {
  cursor: pointer;
  transition: all 0.3s ease;
}

.cursor-pointer:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* New layout mirroring Settings layout */
.knowledge-layout { display: flex; gap: 24px; align-items: flex-start; }
.knowledge-content { flex: 1; min-width: 0; }
.page-header { padding: 0 8px 8px 8px; }
.gap-2 { gap: 8px; }

@media (max-width: 1024px) {
  .knowledge-layout { flex-direction: column; gap: 16px; }
}
</style>
