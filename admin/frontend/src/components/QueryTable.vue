<template>
  <v-card class="query-table-card">
    <v-card-title class="d-flex align-center justify-space-between">
      <span>{{ title }}</span>

      <div class="d-flex align-center gap-2">
        <v-text-field
          v-model="searchQuery"
          placeholder="Search queries..."
          variant="outlined"
          density="compact"
          hide-details
          prepend-inner-icon="$search"
          clearable
          style="max-width: 300px;"
          @update:model-value="debouncedSearch"
        />

        <v-menu>
          <template #activator="{ props }">
            <v-btn
              icon="$filter"
              size="small"
              variant="outlined"
              v-bind="props"
            >
              <v-icon>$filter</v-icon>
              <v-badge
                v-if="activeFiltersCount > 0"
                :content="activeFiltersCount"
                color="primary"
                offset-x="2"
                offset-y="2"
              />
            </v-btn>
          </template>

          <v-card min-width="320">
            <v-card-title>Filters</v-card-title>

            <v-card-text>
              <div class="mb-4">
                <v-label class="mb-2">Date Range</v-label>
                <div class="d-flex gap-2">
                  <v-text-field
                    v-model="filters.startDate"
                    type="date"
                    variant="outlined"
                    density="compact"
                    hide-details
                    label="Start Date"
                  />
                  <v-text-field
                    v-model="filters.endDate"
                    type="date"
                    variant="outlined"
                    density="compact"
                    hide-details
                    label="End Date"
                  />
                </div>
              </div>

              <v-switch
                v-model="filters.errorOnly"
                label="Show errors only"
                color="primary"
                hide-details
                class="mb-4"
              />

              <div class="mb-4">
                <v-label class="mb-2">Min Relevance Score</v-label>
                <v-slider
                  v-model="filters.minRelevance"
                  :min="0"
                  :max="100"
                  :step="5"
                  show-ticks
                  thumb-label
                  color="primary"
                />
              </div>
            </v-card-text>

            <v-card-actions>
              <v-btn
                text="Reset"
                variant="text"
                @click="resetFilters"
              />
              <v-spacer />
              <v-btn
                text="Apply"
                color="primary"
                @click="applyFilters"
              />
            </v-card-actions>
          </v-card>
        </v-menu>

        <v-menu>
          <template #activator="{ props }">
            <v-btn
              icon="$export"
              size="small"
              variant="outlined"
              v-bind="props"
            />
          </template>

          <v-list>
            <v-list-item @click="exportData('csv')">
              <v-list-item-title>Export as CSV</v-list-item-title>
            </v-list-item>
            <v-list-item @click="exportData('json')">
              <v-list-item-title>Export as JSON</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </div>
    </v-card-title>

    <v-data-table-server
      v-model="selectedQueries"
      :headers="headers"
      :items="queries"
      :items-length="totalQueries"
      :loading="loading"
      :items-per-page="itemsPerPage"
      :page="page"
      show-select
      :search="searchQuery"
      item-value="id"
      @update:options="updateOptions"
      @click:row="handleRowClick"
    >
      <template #item.user_query="{ item }">
        <div class="query-text">
          {{ truncateText(item.user_query, 60) }}
        </div>
      </template>

      <template #item.system_response="{ item }">
        <div class="response-preview">
          {{ truncateText(item.system_response, 80) }}
        </div>
      </template>

      <template #item.status="{ item }">
        <v-chip
          :color="getStatusColor(item.error_occurred ? 'error' : 'success')"
          size="small"
          variant="flat"
        >
          {{ item.error_occurred ? 'Error' : 'Success' }}
        </v-chip>
      </template>

      <template #item.response_time="{ item }">
        <span :class="getResponseTimeColor(item.response_time_ms)">
          {{ formatDuration(item.response_time_ms) }}
        </span>
      </template>

      <template #item.relevance_score="{ item }">
        <div class="d-flex align-center">
          <v-progress-linear
            :model-value="item.vector_search_score * 100"
            :color="getRelevanceColor(item.vector_search_score * 100)"
            height="6"
            class="mr-2"
            style="width: 60px;"
          />
          <span class="text-caption">{{ Math.round(item.vector_search_score * 100) }}%</span>
        </div>
      </template>

      <template #item.location="{ item }">
        <div class="text-no-wrap">
          <div class="text-caption">
            {{ item.location_city || 'Unknown' }}
          </div>
          <div class="text-caption text-medium-emphasis">
            {{ item.location_country || 'Unknown' }}
          </div>
        </div>
      </template>

      <template #item.timestamp="{ item }">
        <span class="text-no-wrap">
          {{ formatDate(item.timestamp) }}
        </span>
      </template>

      <template #item.actions="{ item }">
        <div class="d-flex gap-1">
          <v-btn
            icon="$view"
            size="small"
            variant="text"
            @click.stop="viewDetails(item)"
          >
            <v-icon>$view</v-icon>
            <v-tooltip activator="parent" location="top">
              View Details
            </v-tooltip>
          </v-btn>

          <v-menu>
            <template #activator="{ props }">
              <v-btn
                icon
                size="small"
                variant="text"
                v-bind="props"
                @click.stop
              >
                <v-icon>$thumb-up-outline</v-icon>
              </v-btn>
            </template>

            <v-list>
              <v-list-item @click="updateFeedback(item.id, 'helpful')">
                <v-list-item-title>
                  <v-icon start color="success">$thumb-up</v-icon>
                  Helpful
                </v-list-item-title>
              </v-list-item>
              <v-list-item @click="updateFeedback(item.id, 'not_helpful')">
                <v-list-item-title>
                  <v-icon start color="error">$thumb-down</v-icon>
                  Not Helpful
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </div>
      </template>

      <template #expanded-row="{ item }">
        <v-card flat class="ma-2">
          <v-card-text>
            <div class="mb-4">
              <v-label class="mb-2 font-weight-bold">Query:</v-label>
              <div class="text-body-2">{{ item.user_query }}</div>
            </div>

            <div class="mb-4">
              <v-label class="mb-2 font-weight-bold">Response:</v-label>
              <div class="text-body-2">{{ item.system_response }}</div>
            </div>

            <div v-if="item.sources_used && item.sources_used.length" class="mb-4">
              <v-label class="mb-2 font-weight-bold">Sources:</v-label>
              <div class="d-flex flex-wrap gap-2">
                <v-chip
                  v-for="source in item.sources_used"
                  :key="source"
                  size="small"
                  variant="outlined"
                >
                  {{ source }}
                </v-chip>
              </div>
            </div>

            <div class="d-flex gap-4 text-caption text-medium-emphasis">
              <span>ID: {{ item.id }}</span>
              <span>Session: {{ item.session_id }}</span>
              <span v-if="item.user_agent">{{ item.user_agent }}</span>
            </div>
          </v-card-text>
        </v-card>
      </template>

      <template #bottom>
        <div class="d-flex align-center justify-space-between pa-4">
          <div class="text-caption text-medium-emphasis">
            Showing {{ queries.length }} of {{ totalQueries }} queries
            <span v-if="selectedQueries.length > 0">
              ({{ selectedQueries.length }} selected)
            </span>
          </div>

          <v-pagination
            v-model="page"
            :length="totalPages"
            :total-visible="7"
            @update:model-value="updatePage"
          />
        </div>
      </template>
    </v-data-table-server>

    <!-- Query Details Dialog -->
    <v-dialog
      v-model="showDetailsDialog"
      max-width="800px"
      scrollable
    >
      <v-card v-if="selectedQuery">
        <v-card-title class="d-flex align-center justify-space-between">
          Query Details
          <v-btn
            icon="$close"
            variant="text"
            @click="showDetailsDialog = false"
          />
        </v-card-title>

        <v-divider />

        <v-card-text class="pa-6">
          <!-- Query details content here -->
          <div class="mb-4">
            <v-label class="mb-2 font-weight-bold">Query:</v-label>
            <v-card variant="outlined" class="pa-3">
              <div class="text-body-2">{{ selectedQuery.user_query }}</div>
            </v-card>
          </div>

          <div class="mb-4">
            <v-label class="mb-2 font-weight-bold">Response:</v-label>
            <v-card variant="outlined" class="pa-3">
              <div class="text-body-2">{{ selectedQuery.system_response }}</div>
            </v-card>
          </div>

          <v-row>
            <v-col cols="6">
              <div class="mb-2">
                <v-label class="font-weight-bold">Status:</v-label>
                <v-chip
                  :color="getStatusColor(selectedQuery.error_occurred ? 'error' : 'success')"
                  size="small"
                  variant="flat"
                  class="ml-2"
                >
                  {{ selectedQuery.error_occurred ? 'Error' : 'Success' }}
                </v-chip>
              </div>
            </v-col>
            <v-col cols="6">
              <div class="mb-2">
                <v-label class="font-weight-bold">Response Time:</v-label>
                <span class="ml-2">{{ formatDuration(selectedQuery.response_time_ms) }}</span>
              </div>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useQueriesStore } from '@/stores/queries'
import { formatDate, formatDuration, getStatusColor } from '@/types/admin'

const props = defineProps({
  title: {
    type: String,
    default: 'Query Explorer'
  }
})

const emit = defineEmits(['querySelected'])

const queriesStore = useQueriesStore()

// Local state
const searchQuery = ref('')
const selectedQueries = ref([])
const selectedQuery = ref(null)
const showDetailsDialog = ref(false)
const page = ref(1)
const itemsPerPage = ref(25)

// Filters
const filters = ref({
  startDate: null,
  endDate: null,
  errorOnly: false,
  minRelevance: 0
})

// Computed properties - use storeToRefs to maintain reactivity
const {
  queries,
  totalQueries,
  isLoading: loading,
  error
} = storeToRefs(queriesStore)

const totalPages = computed(() => {
  if (!totalQueries.value || totalQueries.value === 0) {
    return 1
  }
  return Math.ceil(totalQueries.value / itemsPerPage.value) || 1
})

const headers = computed(() => [
  {
    title: 'Query',
    key: 'user_query',
    width: '25%',
    sortable: true
  },
  {
    title: 'Response',
    key: 'system_response',
    width: '20%',
    sortable: false
  },
  {
    title: 'Status',
    key: 'status',
    width: '8%',
    sortable: true
  },
  {
    title: 'Response Time',
    key: 'response_time',
    width: '10%',
    sortable: true
  },
  {
    title: 'Relevance',
    key: 'relevance_score',
    width: '10%',
    sortable: true
  },
  {
    title: 'Location',
    key: 'location',
    width: '10%',
    sortable: false
  },
  {
    title: 'Timestamp',
    key: 'timestamp',
    width: '12%',
    sortable: true
  },
  {
    title: 'Actions',
    key: 'actions',
    width: '5%',
    sortable: false
  }
])

const activeFiltersCount = computed(() => {
  let count = 0
  if (filters.value.startDate) count++
  if (filters.value.endDate) count++
  if (filters.value.errorOnly) count++
  if (filters.value.minRelevance > 0) count++
  return count
})

// Methods
const truncateText = (text, maxLength) => {
  if (!text || text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

const getResponseTimeColor = (responseTime) => {
  if (responseTime < 1000) return 'text-success'
  if (responseTime < 3000) return 'text-warning'
  return 'text-error'
}

const getRelevanceColor = (score) => {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'error'
}

const updateOptions = (options) => {
  page.value = options.page
  itemsPerPage.value = options.itemsPerPage

  const sortBy = options.sortBy?.[0]
  if (sortBy) {
    queriesStore.setFilters({
      sortBy: sortBy.key,
      sortOrder: sortBy.order,
      page: page.value,
      limit: itemsPerPage.value
    })
  }
}

const updatePage = (newPage) => {
  page.value = newPage
  queriesStore.setFilters({ page: newPage })
}

const handleRowClick = (event, { item }) => {
  viewDetails(item)
}

const viewDetails = (query) => {
  selectedQuery.value = query
  showDetailsDialog.value = true
  emit('querySelected', query)
}

const updateFeedback = async (queryId, feedback) => {
  try {
    await queriesStore.updateQueryFeedback(queryId, feedback)
  } catch (error) {
    console.error('Failed to update feedback:', error)
  }
}

const applyFilters = async () => {
  await queriesStore.setFilters({
    ...filters.value,
    page: 1
  })
  page.value = 1
}

const resetFilters = async () => {
  filters.value = {
    startDate: null,
    endDate: null,
    errorOnly: false,
    minRelevance: 0
  }
  await queriesStore.resetFilters()
  page.value = 1
}

const exportData = async (format) => {
  try {
    await queriesStore.exportQueries(format, true)
  } catch (error) {
    console.error('Export failed:', error)
  }
}

// Debounced search
let searchTimeout = null
const debouncedSearch = (value) => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    queriesStore.searchQueries(value)
  }, 300)
}

// Watch for changes
watch(selectedQueries, (newSelection) => {
  // Handle bulk actions if needed
})

// Lifecycle - ensure data is loaded on component mount
onMounted(async () => {
  // Only fetch if we don't have any queries loaded
  if (!queries.value || queries.value.length === 0) {
    await queriesStore.fetchQueries()
  }
})
</script>

<style scoped>
.query-table-card {
  overflow: hidden;
}

.query-text,
.response-preview {
  font-family: 'Roboto Mono', monospace;
  font-size: 0.875rem;
  line-height: 1.4;
}

.query-text {
  color: rgb(var(--v-theme-primary));
}

.response-preview {
  color: rgb(var(--v-theme-on-surface));
  opacity: 0.87;
}

:deep(.v-data-table__wrapper) {
  overflow-x: auto;
}

:deep(.v-data-table-row--clickable:hover) {
  background-color: rgba(var(--v-theme-primary), 0.04);
  cursor: pointer;
}
</style>