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

    <!-- Router View for child components -->
    <router-view v-slot="{ Component }">
      <Transition
        name="fade"
        mode="out-in"
      >
        <component :is="Component" />
      </Transition>
    </router-view>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { adminAPI } from '@/services/api'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
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

const refreshAll = async () => {
  loading.value = true
  try {
    await loadKnowledgeStats()
    await loadContentGaps()
    // Emit refresh event to child components if needed
    // This could be enhanced with an event bus or provide/inject
  } catch (error) {
    console.error('Failed to refresh knowledge data:', error)
  } finally {
    loading.value = false
  }
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