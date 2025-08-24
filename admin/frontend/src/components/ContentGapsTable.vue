<template>
  <div class="content-gaps-table">
    <!-- Header with filters -->
    <div class="d-flex justify-space-between align-center mb-4">
      <div class="d-flex align-center gap-4">
        <h2 class="text-h6 font-weight-bold">Content Gaps</h2>
        <v-chip 
          :color="showResolved ? 'success' : 'warning'"
          variant="tonal"
          size="small"
        >
          {{ gaps.length }} {{ showResolved ? 'Total' : 'Unresolved' }} Gaps
        </v-chip>
      </div>
      
      <div class="d-flex align-center gap-2">
        <v-switch
          v-model="showResolved"
          :label="showResolved ? 'Show All' : 'Unresolved Only'"
          color="primary"
          hide-details
          inset
          @update:model-value="fetchGaps"
        />
        
        <v-btn
          color="primary"
          variant="outlined"
          prepend-icon="mdi-refresh"
          @click="fetchGaps"
          :loading="loading"
        >
          Refresh
        </v-btn>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && gaps.length === 0" class="text-center py-8">
      <v-progress-circular indeterminate color="primary" />
      <p class="text-body-2 mt-2 text-medium-emphasis">Loading content gaps...</p>
    </div>

    <!-- Empty State -->
    <v-card v-else-if="!loading && gaps.length === 0" variant="outlined">
      <v-card-text class="text-center py-8">
        <v-icon size="64" color="success" class="mb-4">mdi-check-circle</v-icon>
        <h3 class="text-h6 mb-2">No Content Gaps Found</h3>
        <p class="text-body-2 text-medium-emphasis">
          {{ showResolved ? 'No content gaps have been detected.' : 'All content gaps have been resolved!' }}
        </p>
      </v-card-text>
    </v-card>

    <!-- Gaps Table -->
    <v-card v-else variant="outlined">
      <v-table hover>
        <thead>
          <tr>
            <th class="text-left font-weight-bold">Pattern</th>
            <th class="text-center font-weight-bold">Count</th>
            <th class="text-center font-weight-bold">Avg Score</th>
            <th class="text-center font-weight-bold">First Seen</th>
            <th class="text-center font-weight-bold">Last Seen</th>
            <th class="text-center font-weight-bold">Status</th>
            <th class="text-center font-weight-bold">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="gap in gaps" :key="gap.id">
            <!-- Pattern -->
            <td class="py-4">
              <div class="d-flex flex-column">
                <span class="font-weight-medium">{{ gap.pattern }}</span>
                <span 
                  v-if="gap.sample_query" 
                  class="text-caption text-medium-emphasis mt-1"
                  style="max-width: 300px;"
                >
                  Sample: "{{ truncateText(gap.sample_query, 60) }}"
                </span>
              </div>
            </td>

            <!-- Count -->
            <td class="text-center">
              <v-chip 
                :color="getCountColor(gap.count)"
                variant="tonal"
                size="small"
              >
                {{ gap.count }}
              </v-chip>
            </td>

            <!-- Average Score -->
            <td class="text-center">
              <div class="d-flex flex-column align-center">
                <span class="font-weight-medium">{{ gap.avg_score.toFixed(2) }}</span>
                <v-progress-linear
                  :model-value="gap.avg_score * 100"
                  :color="getScoreColor(gap.avg_score)"
                  height="4"
                  class="mt-1"
                  style="width: 60px;"
                />
              </div>
            </td>

            <!-- First Seen -->
            <td class="text-center text-caption">
              {{ formatDate(gap.first_seen) }}
            </td>

            <!-- Last Seen -->
            <td class="text-center text-caption">
              {{ formatDate(gap.last_seen) }}
            </td>

            <!-- Status -->
            <td class="text-center">
              <v-chip
                :color="gap.resolved ? 'success' : 'warning'"
                :variant="gap.resolved ? 'flat' : 'tonal'"
                size="small"
              >
                {{ gap.resolved ? 'Resolved' : 'Open' }}
              </v-chip>
            </td>

            <!-- Actions -->
            <td class="text-center">
              <div class="d-flex justify-center gap-1">
                <v-btn
                  v-if="!gap.resolved"
                  color="success"
                  variant="text"
                  size="small"
                  icon="mdi-check"
                  @click="markResolved(gap)"
                  :loading="resolvingIds.has(gap.id)"
                >
                  <v-icon>mdi-check</v-icon>
                  <v-tooltip activator="parent">Mark as Resolved</v-tooltip>
                </v-btn>
                
                <v-btn
                  v-else
                  color="warning"
                  variant="text"
                  size="small"
                  icon="mdi-undo"
                  @click="markUnresolved(gap)"
                  :loading="resolvingIds.has(gap.id)"
                >
                  <v-icon>mdi-undo</v-icon>
                  <v-tooltip activator="parent">Mark as Unresolved</v-tooltip>
                </v-btn>

                <v-btn
                  color="primary"
                  variant="text"
                  size="small"
                  icon="mdi-note-edit"
                  @click="openNotesDialog(gap)"
                >
                  <v-icon>mdi-note-edit</v-icon>
                  <v-tooltip activator="parent">Edit Notes</v-tooltip>
                </v-btn>
              </div>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>

    <!-- Notes Dialog -->
    <v-dialog v-model="notesDialog.show" max-width="600px">
      <v-card>
        <v-card-title class="d-flex align-center gap-2">
          <v-icon>mdi-note-edit</v-icon>
          Edit Notes
        </v-card-title>
        
        <v-card-text>
          <div class="mb-4">
            <strong>Pattern:</strong> {{ notesDialog.gap?.pattern }}
          </div>
          
          <v-textarea
            v-model="notesDialog.notes"
            label="Notes"
            placeholder="Add notes about this content gap..."
            rows="4"
            variant="outlined"
            counter
            :rules="[v => !v || v.length <= 500 || 'Notes must be less than 500 characters']"
          />
        </v-card-text>
        
        <v-card-actions>
          <v-spacer />
          <v-btn @click="closeNotesDialog" color="grey">Cancel</v-btn>
          <v-btn 
            @click="saveNotes" 
            color="primary"
            :loading="notesDialog.saving"
          >
            Save Notes
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Loading overlay for actions -->
    <v-overlay v-model="loading && gaps.length > 0" contained>
      <v-progress-circular indeterminate />
    </v-overlay>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useToast } from 'vue-toastification'
import api from '@/services/api'

const toast = useToast()

// Define emits
const emit = defineEmits(['stats-updated'])

// Reactive state
const gaps = ref([])
const loading = ref(false)
const showResolved = ref(false)
const resolvingIds = ref(new Set())

const notesDialog = ref({
  show: false,
  gap: null,
  notes: '',
  saving: false
})

// Methods
const fetchGaps = async () => {
  try {
    loading.value = true
    const response = await api.getContentGaps({ 
      resolved: showResolved.value, 
      limit: 100 
    })
    gaps.value = response.data.gaps || []
  } catch (error) {
    console.error('Failed to fetch content gaps:', error)
    toast.error('Failed to fetch content gaps')
  } finally {
    loading.value = false
  }
}

const markResolved = async (gap) => {
  try {
    resolvingIds.value.add(gap.id)
    await api.updateContentGap(gap.id, { resolved: true })
    gap.resolved = true
    toast.success(`Content gap "${truncateText(gap.pattern, 30)}" marked as resolved`)
  } catch (error) {
    console.error('Failed to mark gap as resolved:', error)
    toast.error('Failed to mark gap as resolved')
  } finally {
    resolvingIds.value.delete(gap.id)
  }
}

const markUnresolved = async (gap) => {
  try {
    resolvingIds.value.add(gap.id)
    await api.updateContentGap(gap.id, { resolved: false })
    gap.resolved = false
    toast.success(`Content gap "${truncateText(gap.pattern, 30)}" marked as unresolved`)
  } catch (error) {
    console.error('Failed to mark gap as unresolved:', error)
    toast.error('Failed to mark gap as unresolved')
  } finally {
    resolvingIds.value.delete(gap.id)
  }
}

const openNotesDialog = (gap) => {
  notesDialog.value = {
    show: true,
    gap: gap,
    notes: gap.notes || '',
    saving: false
  }
}

const closeNotesDialog = () => {
  notesDialog.value.show = false
}

const saveNotes = async () => {
  try {
    notesDialog.value.saving = true
    const gap = notesDialog.value.gap
    await api.updateContentGap(gap.id, { notes: notesDialog.value.notes })
    gap.notes = notesDialog.value.notes
    closeNotesDialog()
    toast.success('Notes saved successfully')
  } catch (error) {
    console.error('Failed to save notes:', error)
    toast.error('Failed to save notes')
  } finally {
    notesDialog.value.saving = false
  }
}

// Utility functions
const truncateText = (text, maxLength) => {
  if (!text) return ''
  return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getCountColor = (count) => {
  if (count >= 10) return 'error'
  if (count >= 5) return 'warning'
  return 'info'
}

const getScoreColor = (score) => {
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'warning'
  return 'error'
}

// Computed stats
const stats = computed(() => {
  const total = gaps.value.length
  const resolved = gaps.value.filter(g => g.resolved).length
  const unresolved = total - resolved
  const avgScore = total > 0 
    ? (gaps.value.reduce((sum, g) => sum + g.avg_score, 0) / total).toFixed(2)
    : '0.00'

  return {
    total,
    resolved,
    unresolved,
    avgScore
  }
})

// Watch for stats changes and emit
watch(stats, (newStats) => {
  emit('stats-updated', newStats)
}, { immediate: true })

// Lifecycle
onMounted(() => {
  fetchGaps()
})
</script>

<style scoped>
.content-gaps-table {
  width: 100%;
}

.v-table th {
  background-color: rgb(var(--v-theme-surface-variant));
  font-weight: 600;
}

.v-table tbody tr:hover {
  background-color: rgba(var(--v-theme-primary), 0.04);
}
</style>