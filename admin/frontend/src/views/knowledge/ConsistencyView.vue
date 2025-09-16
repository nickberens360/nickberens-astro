<template>
  <div class="consistency-view">
    <v-card class="mb-4">
      <v-card-title class="text-h6 d-flex align-center">
        <v-icon class="me-2" color="primary">$check-circle</v-icon>
        Knowledge Consistency
        <v-spacer />
        <v-btn size="small" variant="text" :loading="loading" @click="load()">Refresh</v-btn>
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12" sm="6" md="3">
            <v-sheet class="pa-4 rounded-lg" color="blue-lighten-5">
              <div class="text-caption text-medium-emphasis">Filesystem Files</div>
              <div class="text-h6">{{ summary.filesystem_files }}</div>
            </v-sheet>
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-sheet class="pa-4 rounded-lg" color="cyan-lighten-5">
              <div class="text-caption text-medium-emphasis">Vector Docs (chunks)</div>
              <div class="text-h6">{{ summary.vector_docs }}</div>
            </v-sheet>
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-sheet class="pa-4 rounded-lg" color="purple-lighten-5">
              <div class="text-caption text-medium-emphasis">Tracked Files</div>
              <div class="text-h6">{{ summary.tracked_files }}</div>
            </v-sheet>
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-sheet class="pa-4 rounded-lg" color="orange-lighten-5">
              <div class="text-caption text-medium-emphasis">Mismatches</div>
              <div class="text-h6">{{ mismatchTotal }}</div>
            </v-sheet>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <v-card class="mb-4">
      <v-card-title class="text-h6">Reconcile</v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12" sm="6" md="3">
            <v-switch v-model="dryRun" label="Dry Run" color="primary" hide-details />
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-switch v-model="allowDeletes" label="Allow Deletes" color="warning" hide-details />
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-text-field v-model.number="limit" type="number" min="1" label="Limit" hide-details />
          </v-col>
          <v-col cols="12" md="6">
            <v-text-field v-model="pathsText" label="Paths (comma-separated)" hide-details />
          </v-col>
          <v-col cols="12" md="6" class="d-flex align-end">
            <v-btn color="primary" :loading="running" @click="runReconcile">{{ dryRun ? 'Plan' : 'Run' }} Reconcile</v-btn>
          </v-col>
        </v-row>

        <div v-if="planned || executed" class="mt-4">
          <v-alert type="info" v-if="planned">Planned reindex: {{ planned.reindex.length }}, delete orphans: {{ planned.delete_orphans.length }}</v-alert>
          <v-alert type="success" v-if="executed">Reindexed: {{ executed.reindexed.length }}, Deleted: {{ executed.deleted_orphans.length }}, Errors: {{ executed.errors.length }}</v-alert>
        </div>
      </v-card-text>
    </v-card>

    <v-row>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title class="text-h6">Discovered but not indexed</v-card-title>
          <v-card-text>
            <v-data-table
              :items="dni.items"
              :headers="pathActionHeaders"
              :items-per-page="dni.perPage"
              v-model:page="dni.page"
              :items-length="dni.total"
              :loading="dni.loading"
              item-key="path"
              class="elevation-0"
            >
              <template #item.path="{ item }">
                <div class="text-truncate" style="max-width: 520px" :title="item">{{ item }}</div>
              </template>
              <template #item.actions="{ item }">
                <v-btn size="x-small" variant="text" color="primary" @click="reindexOne(item)">
                  Reindex
                </v-btn>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title class="text-h6">Changed files</v-card-title>
          <v-card-text>
            <v-data-table
              :items="chg.items"
              :headers="pathActionHeaders"
              :items-per-page="chg.perPage"
              v-model:page="chg.page"
              :items-length="chg.total"
              :loading="chg.loading"
              item-key="path"
              class="elevation-0"
            >
              <template #item.path="{ item }">
                <div class="text-truncate" style="max-width: 520px" :title="item">{{ item }}</div>
              </template>
              <template #item.actions="{ item }">
                <v-btn size="x-small" variant="text" color="primary" @click="reindexOne(item)">
                  Reindex
                </v-btn>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-4">
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title class="text-h6">Vector orphans</v-card-title>
          <v-card-text>
            <v-data-table
              :items="orph.items"
              :headers="pathDeleteHeaders"
              :items-per-page="orph.perPage"
              v-model:page="orph.page"
              :items-length="orph.total"
              :loading="orph.loading"
              item-key="path"
              class="elevation-0"
            >
              <template #item.path="{ item }">
                <div class="text-truncate" style="max-width: 520px" :title="item">{{ item }}</div>
              </template>
              <template #item.actions="{ item }">
                <v-tooltip text="Delete from index">
                  <template #activator="{ props }">
                    <span v-bind="props">
                      <v-btn size="x-small" variant="text" color="error" @click="deleteFromIndex(item)">
                        Delete
                      </v-btn>
                    </span>
                  </template>
                </v-tooltip>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title class="text-h6">Tracked but missing</v-card-title>
          <v-card-text>
            <v-data-table
              :items="tbm.items"
              :headers="pathOnlyHeaders"
              :items-per-page="tbm.perPage"
              v-model:page="tbm.page"
              :items-length="tbm.total"
              :loading="tbm.loading"
              item-key="path"
              class="elevation-0"
            >
              <template #item.path="{ item }">
                <div class="text-truncate" style="max-width: 520px" :title="item">{{ item }}</div>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { adminAPI } from '@/services/api'
import { useNotifications } from '@/composables/useNotifications'

const loading = ref(false)
const running = ref(false)
const summary = ref({ filesystem_files: 0, vector_docs: 0, tracked_files: 0, discovered_not_indexed: 0, changed_files: 0, vector_orphans: 0, tracked_but_missing: 0 })
const diff = ref({})

const dryRun = ref(true)
const allowDeletes = ref(false)
const limit = ref()
const pathsText = ref('')

const planned = ref(null)
const executed = ref(null)

const { showError, showSuccess } = useNotifications()

const mismatchTotal = computed(() => (summary.value.discovered_not_indexed || 0) + (summary.value.changed_files || 0) + (summary.value.vector_orphans || 0))

// Paginated lists state
const makeListState = () => ({ items: [], total: 0, page: 1, perPage: 10, loading: false })
const dni = ref(makeListState())
const chg = ref(makeListState())
const orph = ref(makeListState())
const tbm = ref(makeListState())

const pathActionHeaders = [
  { title: 'Path', key: 'path' },
  { title: 'Actions', key: 'actions', width: '120px' }
]
const pathDeleteHeaders = [
  { title: 'Path', key: 'path' },
  { title: 'Actions', key: 'actions', width: '120px' }
]
const pathOnlyHeaders = [
  { title: 'Path', key: 'path' }
]

const load = async () => {
  loading.value = true
  planned.value = null
  executed.value = null
  try {
    const res = await adminAPI.getKnowledgeConsistency(100)
    summary.value = res.summary || summary.value
    diff.value = res.diff || {}
  } catch (e) {
    showError('Failed to load consistency')
  } finally {
    loading.value = false
  }
}

const runReconcile = async () => {
  running.value = true
  planned.value = null
  executed.value = null
  try {
    const paths = (pathsText.value || '')
      .split(',')
      .map(s => s.trim())
      .filter(Boolean)
    const res = await adminAPI.reconcileKnowledge({ dryRun: dryRun.value, allowDeletes: allowDeletes.value, limit: limit.value, paths })
    if (dryRun.value) {
      planned.value = res.planned || { reindex: [], delete_orphans: [] }
      showSuccess('Reconcile plan generated')
    } else {
      executed.value = res.actions || { reindexed: [], deleted_orphans: [], errors: [] }
      showSuccess('Reconcile completed')
      // Reload summary after execute
      await load()
    }
  } catch (e) {
    showError('Reconcile failed')
  } finally {
    running.value = false
  }
}

onMounted(load)

// Helpers: fetch paginated lists
const fetchList = async (stateRef, kind) => {
  stateRef.value.loading = true
  try {
    const offset = (stateRef.value.page - 1) * stateRef.value.perPage
    const res = await adminAPI.getKnowledgeConsistencyList(kind, { offset, limit: stateRef.value.perPage })
    stateRef.value.items = (res.items || []).map(p => ({ path: p }))
    stateRef.value.total = res.total || 0
  } catch (e) {
    // ignore per-section errors, keep prior
  } finally {
    stateRef.value.loading = false
  }
}

// Watchers for pagination
watch(() => dni.value.page, () => fetchList(dni, 'discovered_not_indexed'))
watch(() => chg.value.page, () => fetchList(chg, 'changed_files'))
watch(() => orph.value.page, () => fetchList(orph, 'vector_orphans'))
watch(() => tbm.value.page, () => fetchList(tbm, 'tracked_but_missing'))

// Initial load of lists
onMounted(async () => {
  await Promise.all([
    fetchList(dni, 'discovered_not_indexed'),
    fetchList(chg, 'changed_files'),
    fetchList(orph, 'vector_orphans'),
    fetchList(tbm, 'tracked_but_missing'),
  ])
})

// Row actions
const reindexOne = async (itemOrPath) => {
  const path = typeof itemOrPath === 'string' ? itemOrPath : (itemOrPath?.path || '')
  if (!path) return
  try {
    await adminAPI.reindexKnowledgeFile(path)
    showSuccess('Reindex started')
    // Refresh lists and summary
    await Promise.all([
      fetchList(dni, 'discovered_not_indexed'),
      fetchList(chg, 'changed_files'),
    ])
    await load()
  } catch (e) {
    showError('Failed to reindex file')
  }
}

const deleteFromIndex = async (itemOrPath) => {
  const path = typeof itemOrPath === 'string' ? itemOrPath : (itemOrPath?.path || '')
  if (!path) return
  try {
    await adminAPI.deleteKnowledgeSource(path)
    showSuccess('Deleted from index')
    await fetchList(orph, 'vector_orphans')
    await load()
  } catch (e) {
    showError('Failed to delete from index')
  }
}
</script>

<style scoped>
.consistency-view {
  max-width: 1400px;
  margin: 0 auto;
}
</style>
