<template>
  <div class="question-manager">
    <!-- Add Question Button -->
    <div class="d-flex justify-space-between align-center mb-4">
      <div class="text-subtitle-2 text-medium-emphasis">
        Questions in {{ category.display_name }}
      </div>
      <v-btn
        size="small"
        color="primary"
        prepend-icon="$plus"
        :disabled="loading || !category.is_active"
        @click="showAddDialog = true"
      >
        Add Question
      </v-btn>
    </div>

    <!-- Questions List -->
    <div v-if="questions.length > 0" class="questions-list">
      <v-list class="pa-0">
        <v-list-item
          v-for="(question, index) in questions"
          :key="question.id"
          class="question-item px-0"
          :class="{ 'question-item--inactive': !question.is_active }"
        >
          <!-- Selection Checkbox -->
          <template v-slot:prepend>
            <v-checkbox
              :model-value="selectedQuestions.includes(question)"
              @update:model-value="toggleQuestionSelection(question, $event)"
              hide-details
              density="compact"
            ></v-checkbox>
          </template>

          <!-- Drag Handle -->
          <div 
            class="drag-handle mr-3"
            @mousedown="startDrag($event, index)"
          >
            <v-icon size="20" color="grey">$drag-vertical</v-icon>
          </div>

          <!-- Question Content -->
          <div class="flex-grow-1">
            <div class="d-flex align-center">
              <div 
                v-if="editingQuestion !== question.id"
                class="question-text flex-grow-1"
                :class="{ 'text-medium-emphasis': !question.is_active }"
              >
                {{ question.question_text }}
              </div>
              <v-text-field
                v-else
                v-model="editingText"
                variant="outlined"
                density="compact"
                hide-details
                @blur="saveQuestionEdit(question)"
                @keyup.enter="saveQuestionEdit(question)"
                @keyup.escape="cancelEdit"
                autofocus
                class="flex-grow-1"
              ></v-text-field>

              <!-- Question Status -->
              <v-chip
                v-if="!question.is_active"
                size="x-small"
                color="warning"
                variant="flat"
                class="ml-2"
              >
                Inactive
              </v-chip>
            </div>

            <div class="text-caption text-medium-emphasis mt-1">
              Sort order: {{ question.sort_order }} • 
              Created: {{ formatDate(question.created_at) }}
              <span v-if="question.created_by">• By User {{ question.created_by }}</span>
            </div>
          </div>

          <!-- Actions -->
          <template v-slot:append>
            <div class="d-flex">
              <v-btn
                icon="$edit"
                size="small"
                variant="text"
                :disabled="loading"
                @click="startEdit(question)"
              ></v-btn>
              
              <v-menu>
                <template v-slot:activator="{ props }">
                  <v-btn
                    icon="$dots-vertical"
                    size="small"
                    variant="text"
                    v-bind="props"
                    :disabled="loading"
                  ></v-btn>
                </template>
                <v-list density="compact">
                  <v-list-item 
                    @click="toggleQuestionStatus(question)"
                    :prepend-icon="question.is_active ? '$eye-off' : '$eye'"
                  >
                    <v-list-item-title>
                      {{ question.is_active ? 'Deactivate' : 'Activate' }}
                    </v-list-item-title>
                  </v-list-item>
                  <v-list-item
                    @click="moveQuestionUp(index)"
                    :disabled="index === 0"
                    prepend-icon="$arrow-up"
                  >
                    <v-list-item-title>Move Up</v-list-item-title>
                  </v-list-item>
                  <v-list-item
                    @click="moveQuestionDown(index)"
                    :disabled="index === questions.length - 1"
                    prepend-icon="$arrow-down"
                  >
                    <v-list-item-title>Move Down</v-list-item-title>
                  </v-list-item>
                  <v-divider></v-divider>
                  <v-list-item
                    @click="deleteQuestion(question)"
                    prepend-icon="$delete"
                    class="text-error"
                  >
                    <v-list-item-title>Delete</v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-menu>
            </div>
          </template>
        </v-list-item>
      </v-list>
    </div>

    <!-- Empty State -->
    <v-card v-else variant="tonal" class="text-center pa-6">
      <v-icon size="48" color="grey-lighten-1">$help-circle-outline</v-icon>
      <div class="text-subtitle-1 mt-2 mb-1">No questions yet</div>
      <div class="text-body-2 text-medium-emphasis mb-4">
        Add your first question to this category
      </div>
      <v-btn
        color="primary"
        prepend-icon="$plus"
        :disabled="!category.is_active"
        @click="showAddDialog = true"
      >
        Add Question
      </v-btn>
    </v-card>

    <!-- Add/Edit Question Dialog -->
    <v-dialog v-model="showAddDialog" max-width="600px">
      <v-card>
        <v-card-title>
          {{ editingQuestion ? 'Edit Question' : 'Add Question' }}
        </v-card-title>

        <v-card-text>
          <v-form ref="questionForm">
            <v-textarea
              v-model="newQuestionText"
              label="Question Text"
              variant="outlined"
              :rules="[v => !!v || 'Question is required', v => v?.length <= 500 || 'Question must be 500 characters or less']"
              counter="500"
              rows="3"
              auto-grow
            ></v-textarea>

            <v-text-field
              v-model.number="newQuestionOrder"
              label="Sort Order"
              variant="outlined"
              type="number"
              hint="Lower numbers appear first"
              persistent-hint
            ></v-text-field>
          </v-form>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="cancelAddQuestion">Cancel</v-btn>
          <v-btn 
            color="primary"
            :loading="loading"
            @click="saveQuestion"
          >
            {{ editingQuestion ? 'Update' : 'Add' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import api from '@/services/api'

export default {
  name: 'QuestionManager',
  props: {
    category: {
      type: Object,
      required: true
    },
    selectedQuestions: {
      type: Array,
      default: () => []
    }
  },
  emits: ['questions-updated', 'selection-changed'],
  setup(props, { emit }) {
    const loading = ref(false)
    const questions = ref([])
    const showAddDialog = ref(false)
    const editingQuestion = ref(null)
    const editingText = ref('')
    const newQuestionText = ref('')
    const newQuestionOrder = ref(0)
    const questionForm = ref(null)

    // Load questions for this category
    const loadQuestions = async () => {
      try {
        loading.value = true
        const response = await api.getFollowupQuestionsNormalized({
          category_id: props.category.id,
          active_only: false
        })
        questions.value = response || []
      } catch (err) {
        console.error('Failed to load questions:', err)
        questions.value = []
      } finally {
        loading.value = false
      }
    }

    // Question selection
    const toggleQuestionSelection = (question, selected) => {
      const currentSelection = [...props.selectedQuestions]
      const index = currentSelection.findIndex(q => q.id === question.id)
      
      if (selected && index === -1) {
        currentSelection.push(question)
      } else if (!selected && index !== -1) {
        currentSelection.splice(index, 1)
      }
      
      emit('selection-changed', currentSelection)
    }

    // Question editing
    const startEdit = (question) => {
      editingQuestion.value = question.id
      editingText.value = question.question_text
    }

    const cancelEdit = () => {
      editingQuestion.value = null
      editingText.value = ''
    }

    const saveQuestionEdit = async (question) => {
      if (editingText.value.trim() === question.question_text) {
        cancelEdit()
        return
      }

      try {
        loading.value = true
        await api.updateFollowupQuestionNormalized(question.id, {
          question_text: editingText.value.trim()
        })
        
        // Update local question
        const index = questions.value.findIndex(q => q.id === question.id)
        if (index !== -1) {
          questions.value[index].question_text = editingText.value.trim()
        }
        
        cancelEdit()
        emit('questions-updated')
      } catch (err) {
        console.error('Failed to update question:', err)
      } finally {
        loading.value = false
      }
    }

    // Question operations
    const toggleQuestionStatus = async (question) => {
      try {
        loading.value = true
        await api.updateFollowupQuestionNormalized(question.id, {
          is_active: !question.is_active
        })
        
        // Update local question
        const index = questions.value.findIndex(q => q.id === question.id)
        if (index !== -1) {
          questions.value[index].is_active = !question.is_active
        }
        
        emit('questions-updated')
      } catch (err) {
        console.error('Failed to toggle question status:', err)
      } finally {
        loading.value = false
      }
    }

    const moveQuestionUp = async (index) => {
      if (index === 0) return
      await swapQuestions(index, index - 1)
    }

    const moveQuestionDown = async (index) => {
      if (index === questions.value.length - 1) return
      await swapQuestions(index, index + 1)
    }

    const swapQuestions = async (index1, index2) => {
      const q1 = questions.value[index1]
      const q2 = questions.value[index2]
      
      try {
        loading.value = true
        
        // Swap sort orders
        await Promise.all([
          api.updateFollowupQuestionNormalized(q1.id, { sort_order: q2.sort_order }),
          api.updateFollowupQuestionNormalized(q2.id, { sort_order: q1.sort_order })
        ])
        
        // Update local state
        const temp = q1.sort_order
        q1.sort_order = q2.sort_order
        q2.sort_order = temp
        
        // Re-sort questions
        questions.value.sort((a, b) => a.sort_order - b.sort_order)
        
        emit('questions-updated')
      } catch (err) {
        console.error('Failed to reorder questions:', err)
      } finally {
        loading.value = false
      }
    }

    const deleteQuestion = async (question) => {
      if (!confirm(`Are you sure you want to delete this question? This action cannot be undone.`)) {
        return
      }

      try {
        loading.value = true
        await api.deleteFollowupQuestionNormalized(question.id)
        
        // Remove from local list
        const index = questions.value.findIndex(q => q.id === question.id)
        if (index !== -1) {
          questions.value.splice(index, 1)
        }
        
        emit('questions-updated')
      } catch (err) {
        console.error('Failed to delete question:', err)
      } finally {
        loading.value = false
      }
    }

    // Add new question
    const saveQuestion = async () => {
      if (!questionForm.value) return
      
      const isValid = await questionForm.value.validate()
      if (!isValid.valid) return

      try {
        loading.value = true
        
        const questionData = {
          category_id: props.category.id,
          question_text: newQuestionText.value.trim(),
          sort_order: newQuestionOrder.value || questions.value.length
        }

        const response = await api.createFollowupQuestionNormalized(questionData)
        
        if (response.success) {
          await loadQuestions() // Refresh questions
          cancelAddQuestion()
          emit('questions-updated')
        }
      } catch (err) {
        console.error('Failed to create question:', err)
      } finally {
        loading.value = false
      }
    }

    const cancelAddQuestion = () => {
      showAddDialog.value = false
      newQuestionText.value = ''
      newQuestionOrder.value = 0
      if (questionForm.value) {
        questionForm.value.reset()
      }
    }

    // Utility functions
    const formatDate = (dateString) => {
      return new Date(dateString).toLocaleDateString()
    }

    // Drag and drop (placeholder - could be enhanced)
    const startDrag = (event, index) => {
      // Basic drag functionality could be implemented here
      console.log('Drag started for question at index:', index)
    }

    // Watch category changes
    watch(() => props.category.id, () => {
      loadQuestions()
    })

    onMounted(() => {
      loadQuestions()
    })

    return {
      loading,
      questions,
      showAddDialog,
      editingQuestion,
      editingText,
      newQuestionText,
      newQuestionOrder,
      questionForm,
      toggleQuestionSelection,
      startEdit,
      cancelEdit,
      saveQuestionEdit,
      toggleQuestionStatus,
      moveQuestionUp,
      moveQuestionDown,
      deleteQuestion,
      saveQuestion,
      cancelAddQuestion,
      formatDate,
      startDrag
    }
  }
}
</script>

<style scoped>
.question-manager {
  min-height: 200px;
}

.question-item {
  border: 1px solid rgba(var(--v-theme-outline), 0.2);
  border-radius: 8px;
  margin-bottom: 8px;
  transition: all 0.2s ease;
  padding: 12px !important;
}

.question-item:hover {
  border-color: rgba(var(--v-theme-primary), 0.5);
  box-shadow: 0 2px 8px rgba(var(--v-theme-primary), 0.1);
}

.question-item--inactive {
  opacity: 0.7;
  border-style: dashed;
}

.drag-handle {
  cursor: grab;
  display: flex;
  align-items: center;
}

.drag-handle:active {
  cursor: grabbing;
}

.question-text {
  font-size: 0.95rem;
  line-height: 1.4;
}

.questions-list {
  max-height: 60vh;
  overflow-y: auto;
}
</style>