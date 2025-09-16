<template>
  <div class="knowledge-view">
    <!-- Navigation Metric Cards - Always Visible -->
    <v-row class="mb-6">
      <v-col
        cols="12"
        sm="6"
        md="3"
      >
        <v-card
          elevation="1"
          class="cursor-pointer"
          :class="{'v-card--active': currentRoute === 'knowledge-sources'}"
          @click="navigateTo('knowledge-sources')"
        >
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon
                color="green"
                size="large"
                class="me-3"
              >
                $folder
              </v-icon>
              <div>
                <div class="text-h6">
                  {{ knowledgeStats.unique_sources || 0 }}
                </div>
                <div class="text-body-2 text-medium-emphasis">
                  Source Files
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col
        cols="12"
        sm="6"
        md="3"
      >
        <v-card
          elevation="1"
          class="cursor-pointer"
          :class="{'v-card--active': currentRoute === 'knowledge-documents'}"
          @click="navigateTo('knowledge-documents')"
        >
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon
                color="blue"
                size="large"
                class="me-3"
              >
                $description
              </v-icon>
              <div>
                <div class="text-h6">
                  {{ knowledgeStats.total_documents || 0 }}
                </div>
                <div class="text-body-2 text-medium-emphasis">
                  Indexed Documents
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col
        cols="12"
        sm="6"
        md="3"
      >
        <v-card
          elevation="1"
          class="cursor-pointer"
          :class="{'v-card--active': currentRoute === 'knowledge-gaps'}"
          @click="navigateTo('knowledge-gaps')"
        >
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon
                color="warning"
                size="large"
                class="me-3"
              >
                $warning
              </v-icon>
              <div>
                <div class="text-h6">
                  {{ contentGaps || 0 }}
                </div>
                <div class="text-body-2 text-medium-emphasis">
                  Content Gaps
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col
        cols="12"
        sm="6"
        md="3"
      >
        <v-card
          elevation="1"
          class="cursor-pointer"
          :class="{'v-card--active': currentRoute === 'knowledge-stats'}"
          @click="navigateTo('knowledge-stats')"
        >
          <v-card-text>
            <div class="d-flex align-center">
              <v-icon
                color="purple"
                size="large"
                class="me-3"
              >
                $chart
              </v-icon>
              <div>
                <div class="text-h6">
                  Analytics
                </div>
                <div class="text-body-2 text-medium-emphasis">
                  Knowledge Stats
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Action Buttons Row -->
    <v-row class="mb-4">
      <v-col class="d-flex justify-end">
        <div class="d-flex gap-2">
          <v-btn
            color="primary"
            prepend-icon="$refresh"
            :loading="refreshLoading"
            variant="outlined"
            @click="refreshData"
          >
            Refresh
          </v-btn>
          <v-btn
            color="warning"
            prepend-icon="$refresh"
            :loading="reindexLoading"
            variant="outlined"
            class="ml-3"
            @click="confirmReindex"
          >
            Re-Index
          </v-btn>
        </div>
      </v-col>
    </v-row>

    <!-- Router View for child components -->
    <router-view v-slot="{ Component }">
      <Transition
        name="fade"
        mode="out-in"
      >
        <component 
          :is="Component" 
          :refresh-trigger="refreshTrigger"
          @refresh-complete="onRefreshComplete" 
        />
      </Transition>
    </router-view>

    <!-- Re-Index Confirmation Dialog -->
    <v-dialog
      v-model="showReindexDialog"
      max-width="500"
    >
      <v-card>
        <v-card-title class="text-h6">
          Confirm Knowledge Base Re-Index
        </v-card-title>
        <v-card-text>
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
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showReindexDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
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
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { adminAPI } from '@/services/api'
import { useNotifications } from '@/composables/useNotifications'

const router = useRouter()
const route = useRoute()
const { showSuccess, showError } = useNotifications()

const loading = ref(false)
const refreshLoading = ref(false)
const reindexLoading = ref(false)
const showReindexDialog = ref(false)
const refreshTrigger = ref(0)

const knowledgeStats = ref({
  total_documents: 0,
  total_chunks: 0,
  unique_sources: 0,
  content_types: {}
})
const contentGaps = ref(0)
const embeddingModel = ref('text-embedding-3-small')

const currentRoute = computed(() => route.name)

const navigateTo = (routeName) => {
  router.push({ name: routeName })
}

const refreshData = async () => {
  refreshLoading.value = true
  try {
    // Refresh parent stats
    await loadKnowledgeStats()
    await loadContentGaps()
    
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
    await adminAPI.refreshKnowledgeBase(true)
    
    // Wait a moment for the reindex to start
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    // Refresh all data after reindex
    await refreshData()
    
    showSuccess('Knowledge base re-indexing completed successfully!')
  } catch (error) {
    console.error('Failed to re-index knowledge base:', error)
    showError('Failed to re-index knowledge base: ' + (error.message || 'Unknown error'))
  } finally {
    reindexLoading.value = false
    showReindexDialog.value = false
  }
}

const onRefreshComplete = () => {
  // Called when child components finish their refresh operations
  // Can be used for additional coordination if needed
}


const loadKnowledgeStats = async () => {
  try {
    knowledgeStats.value = await adminAPI.getKnowledgeStats()
  } catch (error) {
    console.error('Failed to load knowledge stats:', error)
  }
}

const loadContentGaps = async () => {
  try {
    const response = await adminAPI.getContentGaps({ resolved: false, limit: 100 })
    contentGaps.value = response.total_count || 0
  } catch (error) {
    console.error('Failed to load content gaps:', error)
  }
}

onMounted(() => {
  loadKnowledgeStats()
  loadContentGaps()
})
</script>

<style scoped>
.knowledge-view {
  max-width: 1400px;
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

.v-card--active {
  border: 2px solid rgb(var(--v-theme-primary));
  background-color: rgba(var(--v-theme-primary), 0.04);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>