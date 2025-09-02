<template>
  <div class="pa-6">
    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">{{ error }}</v-alert>
    <div class="mb-3 d-flex align-center">
      <v-btn class="mr-2" @click="openAll" :disabled="!categories.length" prepend-icon="$chevron-down">Open All</v-btn>
      <v-btn class="mr-4" @click="closeAll" :disabled="!categories.length" prepend-icon="$chevron-up">Close All</v-btn>
      <v-chip v-if="categories.length" size="small" variant="tonal">{{ categories.length }} categories</v-chip>
      <v-spacer />
      
      <v-progress-circular v-if="loading" indeterminate color="primary" size="20" />
    </div>

    <v-expansion-panels v-model="model" multiple variant="accordion">
      <v-expansion-panel
        v-for="cat in categories"
        :key="cat.id"
        :value="cat.id"
      >
        <v-expansion-panel-title>
          <div class="d-flex align-center w-100">
            <v-checkbox
              v-model="selectedCategories"
              :value="cat.id"
              hide-details
              density="compact"
              class="mr-3"
              @click.stop
              @update:model-value="emitSelectedCategories"
            />
            <span class="font-weight-medium">{{ cat.display_name }}</span>
            <v-chip class="ml-2" size="x-small" variant="tonal">
              {{ (questionsByCat[cat.id] || []).length }} questions
            </v-chip>
            <v-spacer />
            <v-chip v-if="!cat.is_active" size="x-small" color="warning" variant="tonal">Inactive</v-chip>
          </div>
          <template #actions="{ expanded }">
            <div class="actions-icons d-flex align-center">
              <v-tooltip text="Edit Category" location="top">
                <template #activator="{ props }">
                  <v-btn
                    v-bind="props"
                    icon="$edit"
                    size="small"
                    variant="text"
                    color="primary"
                    :disabled="saving || loading"
                    @click.stop="openEditCategoryDialog(cat)"
                  />
                </template>
              </v-tooltip>
              <v-icon :icon="expanded ? '$chevron-up' : '$chevron-down'" />
            </div>
          </template>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <div v-if="(questionsByCat[cat.id] || []).length === 0" class="text-medium-emphasis">
            No questions
          </div>
          <v-list v-else density="compact">
            <v-list-item v-for="(q, idx) in questionsByCat[cat.id]" :key="q.id" class="py-1">
              <template #prepend>
                <v-checkbox
                  v-model="selectedQuestionsIdsByCat[cat.id]"
                  :value="q.id"
                  hide-details
                  density="compact"
                  class="mr-3"
                  @click.stop
                  @update:model-value="() => emitSelectedQuestions(cat.id)"
                />
              </template>
              <v-list-item-title>{{ q.question_text }}</v-list-item-title>
              <v-list-item-subtitle>Order: {{ q.sort_order }} • Active: {{ q.is_active ? 'Yes' : 'No' }}</v-list-item-subtitle>
              <template #append>
                <v-btn
                  icon="$arrow-up"
                  size="x-small"
                  variant="text"
                  :disabled="saving || idx === 0"
                  class="mr-1"
                  @click.stop="moveUp(cat, idx)"
                />
                <v-btn
                  icon="$arrow-down"
                  size="x-small"
                  variant="text"
                  :disabled="saving || idx === (questionsByCat[cat.id].length - 1)"
                  class="mr-1"
                  @click.stop="moveDown(cat, idx)"
                />
                <v-btn
                  :icon="q.is_active ? '$eye-off' : '$eye'"
                  size="x-small"
                  variant="text"
                  :disabled="saving"
                  class="mr-1"
                  @click.stop="toggleActive(cat, q)"
                />
                <v-btn
                  icon="$edit"
                  size="x-small"
                  variant="text"
                  :disabled="saving"
                  @click.stop="openEditDialog(cat, q)"
                />
                <v-btn
                  icon="$delete"
                  size="x-small"
                  variant="text"
                  color="error"
                  :disabled="saving"
                  @click.stop="openDeleteDialog(cat, q)"
                />
              </template>
            </v-list-item>
          </v-list>
          <div class="mt-3">
            <v-btn
              color="primary"
              prepend-icon="$plus"
              size="small"
              :disabled="saving || !cat.is_active"
              @click="openAddDialog(cat)"
            >
              Add Question
            </v-btn>
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <div class="mt-4 text-caption text-medium-emphasis">Model: {{ model }}</div>

    <!-- Add/Edit Dialog -->
    <v-dialog v-model="showDialog" max-width="580px">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">$help-circle</v-icon>
          {{ editingQuestion ? 'Edit Question' : 'Add Question' }}
        </v-card-title>
        <v-card-text>
          <v-form ref="formRef">
            <v-textarea
              v-model="form.questionText"
              label="Question Text"
              rows="3"
              auto-grow
              :rules="[v => !!v || 'Required', v => (v?.length||0) <= 500 || 'Max 500 chars']"
            />
            <v-text-field
              v-model.number="form.sortOrder"
              type="number"
              label="Sort Order"
              :disabled="!!editingQuestion"
              :hint="editingQuestion ? 'Reordering is handled separately (drag & drop / move buttons)' : 'Lower numbers appear first'"
              persistent-hint
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="closeDialog" :disabled="saving">Cancel</v-btn>
          <v-btn color="primary" @click="save" :loading="saving">{{ editingQuestion ? 'Update' : 'Add' }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="showDeleteDialog" max-width="520px">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" color="error">$delete</v-icon>
          Delete Question
        </v-card-title>
        <v-card-text>
          <div class="mb-3">Are you sure you want to delete this question?</div>
          <v-alert type="warning" variant="tonal" class="mb-3" :icon="false">
            This action cannot be undone.
          </v-alert>
          <v-card variant="outlined" class="pa-3">
            <div class="text-caption text-medium-emphasis mb-1">Question</div>
            <div class="text-body-2">{{ deleteTargetQuestion?.question_text }}</div>
          </v-card>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="cancelDelete" :disabled="saving">Cancel</v-btn>
          <v-btn color="error" @click="confirmDelete" :loading="saving">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Category Delete Confirmation Dialog -->
    <v-dialog v-model="showCategoryDeleteDialog" max-width="560px">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" color="error">$delete</v-icon>
          Delete Category
        </v-card-title>
        <v-card-text>
          <div class="mb-3">
            Are you sure you want to delete
            <strong>{{ deleteCategoryTarget?.display_name }}</strong>
            and all of its questions?
          </div>
          <v-alert type="warning" variant="tonal" class="mb-3" :icon="false">
            This action cannot be undone. All questions in this category will be permanently deleted.
          </v-alert>
          <v-card variant="outlined" class="pa-3">
            <div class="text-caption text-medium-emphasis mb-1">Summary</div>
            <div class="text-body-2">
              {{ (questionsByCat[deleteCategoryTarget?.id] || []).length }} questions will be deleted
            </div>
          </v-card>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="cancelDeleteCategory" :disabled="saving">Cancel</v-btn>
          <v-btn color="error" @click="confirmDeleteCategory" :loading="saving">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import api from '@/services/api'

const emit = defineEmits(['update-selected-categories', 'update-question-selection', 'changed', 'edit-category'])

const loading = ref(false)
const error = ref('')
const categories = ref([])
const questionsByCat = reactive({})
const selectedCategories = ref([]) // array of category ids
const selectedQuestionsIdsByCat = reactive({}) // catId -> array of question ids

// dialog state
const showDialog = ref(false)
const formRef = ref(null)
const editingQuestion = ref(null) // question object or null
const dialogCategory = ref(null) // category object
const form = reactive({ questionText: '', sortOrder: 0 })
const saving = ref(false)
const showDeleteDialog = ref(false)
const deleteTargetQuestion = ref(null)
const deleteTargetCategory = ref(null)
// category delete state
const showCategoryDeleteDialog = ref(false)
const deleteCategoryTarget = ref(null)

const model = ref([])
const allIds = computed(() => categories.value.map(c => c.id))

const openAll = () => { model.value = [...allIds.value] }
const closeAll = () => { model.value = [] }


const load = async () => {
  try {
    loading.value = true
    error.value = ''
    const cats = await api.getFollowupCategories()
    categories.value = cats || []
    // fetch questions per category
    await Promise.all(categories.value.map(async (c) => {
      try {
        const qs = await api.getFollowupQuestions({ category_id: c.id, active_only: false })
        questionsByCat[c.id] = qs || []
        // ensure selection buckets exist and are valid
        const existing = selectedQuestionsIdsByCat[c.id] || []
        const validIdsSet = new Set((qs || []).map(q => q.id))
        selectedQuestionsIdsByCat[c.id] = existing.filter(id => validIdsSet.has(id))
      } catch (e) {
        console.warn('Failed loading questions for category', c.id, e)
        questionsByCat[c.id] = []
        selectedQuestionsIdsByCat[c.id] = []
      }
    }))
    // prune selected categories to still-existing ones
    const existingCatIds = new Set(categories.value.map(c => c.id))
    selectedCategories.value = selectedCategories.value.filter(id => existingCatIds.has(id))
    // Keep accordions closed by default
    // model.value = [...allIds.value]
  } catch (e) {
    console.error(e)
    error.value = 'Failed to load categories/questions'
  } finally {
    loading.value = false
  }
}

onMounted(load)

// event emitters
const emitSelectedCategories = () => {
  const selected = categories.value.filter(c => selectedCategories.value.includes(c.id))
  emit('update-selected-categories', selected)
}

const emitSelectedQuestions = (catId) => {
  const ids = selectedQuestionsIdsByCat[catId] || []
  const qs = (questionsByCat[catId] || []).filter(q => ids.includes(q.id))
  emit('update-question-selection', catId, qs)
}

// toggle active/inactive
const toggleActive = async (cat, q) => {
  try {
    saving.value = true
    await api.updateFollowupQuestion(q.id, { is_active: !q.is_active })
    await refreshCategoryQuestions(cat.id)
    emit('changed')
  } catch (e) {
    console.error('Failed to toggle active state', e)
  } finally {
    saving.value = false
  }
}

// delete helpers
const openDeleteDialog = (cat, q) => {
  deleteTargetCategory.value = cat
  deleteTargetQuestion.value = q
  showDeleteDialog.value = true
}

const cancelDelete = () => {
  showDeleteDialog.value = false
  deleteTargetCategory.value = null
  deleteTargetQuestion.value = null
}

const confirmDelete = async () => {
  if (!deleteTargetQuestion.value || !deleteTargetCategory.value) return
  try {
    saving.value = true
    await api.deleteFollowupQuestion(deleteTargetQuestion.value.id)
    const catId = deleteTargetCategory.value.id
    // prune selection for this category
    const ids = selectedQuestionsIdsByCat[catId] || []
    selectedQuestionsIdsByCat[catId] = ids.filter(id => id !== deleteTargetQuestion.value.id)
    await refreshCategoryQuestions(catId)
    emit('changed')
  } catch (e) {
    console.error('Failed to delete question', e)
  } finally {
    saving.value = false
    cancelDelete()
  }
}

// category editing
const openEditCategoryDialog = (cat) => {
  emit('edit-category', cat)
}

// category deletion
const openDeleteCategoryDialog = (cat) => {
  deleteCategoryTarget.value = cat
  showCategoryDeleteDialog.value = true
}

const cancelDeleteCategory = () => {
  showCategoryDeleteDialog.value = false
  deleteCategoryTarget.value = null
}

const confirmDeleteCategory = async () => {
  if (!deleteCategoryTarget.value) return
  try {
    saving.value = true
    await api.deleteFollowupCategoryWithStrategyNormalized({
      categoryId: deleteCategoryTarget.value.id,
      strategy: 'delete'
    })
    await load()
    emit('changed')
  } catch (e) {
    console.error('Failed to delete category', e)
  } finally {
    saving.value = false
    cancelDeleteCategory()
  }
}

// reordering helpers (swap adjacent sort_order values)
const moveUp = async (cat, idx) => {
  if (idx <= 0) return
  await swapQuestions(cat.id, idx, idx - 1)
}

const moveDown = async (cat, idx) => {
  const list = questionsByCat[cat.id] || []
  if (idx >= list.length - 1) return
  await swapQuestions(cat.id, idx, idx + 1)
}

const swapQuestions = async (catId, i, j) => {
  const list = questionsByCat[catId] || []
  const q1 = list[i]
  const q2 = list[j]
  if (!q1 || !q2) return
  try {
    saving.value = true
    await Promise.all([
      api.updateFollowupQuestion(q1.id, { sort_order: q2.sort_order }),
      api.updateFollowupQuestion(q2.id, { sort_order: q1.sort_order })
    ])
    await refreshCategoryQuestions(catId)
    emit('changed')
  } catch (e) {
    console.error('Failed to reorder questions', e)
  } finally {
    saving.value = false
  }
}

// dialog helpers
const openAddDialog = (cat) => {
  dialogCategory.value = cat
  editingQuestion.value = null
  form.questionText = ''
  // choose next sort order based on existing max to avoid collisions
  const list = questionsByCat[cat.id] || []
  const maxOrder = list.length ? Math.max(...list.map(q => Number(q.sort_order) || 0)) : -1
  form.sortOrder = maxOrder + 1
  showDialog.value = true
}

const openEditDialog = (cat, q) => {
  dialogCategory.value = cat
  editingQuestion.value = q
  form.questionText = q.question_text
  form.sortOrder = q.sort_order
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const refreshCategoryQuestions = async (catId) => {
  try {
    const qs = await api.getFollowupQuestions({ category_id: catId, active_only: false })
    questionsByCat[catId] = qs || []
  } catch (e) {
    console.warn('Failed to refresh questions for category', catId, e)
  }
}

const save = async () => {
  if (!dialogCategory.value) return
  const valid = await (formRef.value?.validate?.() || { valid: true })
  if (valid.valid === false) return
  try {
    saving.value = true
    if (!editingQuestion.value) {
      await api.createFollowupQuestion({
        category_id: dialogCategory.value.id,
        question_text: form.questionText.trim(),
        sort_order: form.sortOrder ?? 0
      })
    } else {
      // Only update text during edit – use the single-item endpoint
      const trimmed = form.questionText.trim()
      if (trimmed === editingQuestion.value.question_text) {
        showDialog.value = false
        return
      }
      await api.updateFollowupQuestion(editingQuestion.value.id, { question_text: trimmed })
    }
    await refreshCategoryQuestions(dialogCategory.value.id)
    showDialog.value = false
    emit('changed')
  } catch (e) {
    console.error('Failed to save question', e)
  } finally {
    saving.value = false
  }
}

// Expose methods for parent component
defineExpose({
  load
})
</script>

<style scoped>
.pa-6 { padding: 24px; }
.mr-2 { margin-right: 8px; }
.mr-4 { margin-right: 16px; }
.mb-3 { margin-bottom: 12px; }
.mb-4 { margin-bottom: 16px; }
.mt-4 { margin-top: 16px; }
.ml-2 { margin-left: 8px; }
.actions-icons { gap: 6px; }
</style>
