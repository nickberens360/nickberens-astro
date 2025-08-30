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
          @dragover="handleDragOver($event)"
          @drop="handleDrop($event, index)"
        >
          <!-- Drag Handle and Selection Checkbox -->
          <template v-slot:prepend>
            <div class="d-flex align-center">
              <!-- Drag Handle -->
              <div 
                class="drag-handle mr-2"
                draggable="true"
                @dragstart="handleDragStart($event, index, question)"
                @dragend="handleDragEnd"
              >
                <v-icon size="20" color="grey">$drag-vertical</v-icon>
              </div>
              
              <!-- Selection Checkbox -->
              <v-checkbox
                :model-value="selectedQuestions.includes(question)"
                @update:model-value="toggleQuestionSelection(question, $event)"
                hide-details
                density="compact"
                class="mr-4"
              ></v-checkbox>
            </div>
          </template>

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

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="showDeleteDialog" max-width="500px">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon icon="$delete" color="error" class="mr-2"></v-icon>
          Delete Question
        </v-card-title>

        <v-card-text>
          <div class="text-body-1 mb-4">
            Are you sure you want to delete this question?
          </div>
          
          <v-card 
            variant="outlined" 
            class="mb-4 pa-3"
            color="error"
            style="border: 1px solid rgba(var(--v-theme-error), 0.3);"
          >
            <div class="text-body-2 text-medium-emphasis mb-1">Question to be deleted:</div>
            <div class="text-body-1">{{ questionToDelete?.question_text }}</div>
          </v-card>

          <v-alert
            type="warning" 
            variant="tonal"
            class="text-body-2"
            :icon="false"
          >
            <strong>Warning:</strong> This action cannot be undone. The question will be permanently removed from this category.
          </v-alert>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn 
            @click="cancelDelete"
            :disabled="loading"
          >
            Cancel
          </v-btn>
          <v-btn 
            color="error"
            variant="elevated"
            :loading="loading"
            @click="confirmDelete"
          >
            Delete Question
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
    const showDeleteDialog = ref(false)
    const questionToDelete = ref(null)
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

    const deleteQuestion = (question) => {
      questionToDelete.value = question
      showDeleteDialog.value = true
    }

    const confirmDelete = async () => {
      if (!questionToDelete.value) return

      try {
        loading.value = true
        await api.deleteFollowupQuestionNormalized(questionToDelete.value.id)
        
        // Remove from local list
        const index = questions.value.findIndex(q => q.id === questionToDelete.value.id)
        if (index !== -1) {
          questions.value.splice(index, 1)
        }
        
        emit('questions-updated')
        cancelDelete()
      } catch (err) {
        console.error('Failed to delete question:', err)
      } finally {
        loading.value = false
      }
    }

    const cancelDelete = () => {
      showDeleteDialog.value = false
      questionToDelete.value = null
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

    // Drag and drop functionality
    const draggedItem = ref(null)
    const draggedIndex = ref(-1)

    const handleDragStart = (event, index, question) => {
      draggedItem.value = question
      draggedIndex.value = index
      event.dataTransfer.effectAllowed = 'move'
      event.dataTransfer.setData('text/html', event.target.outerHTML)
      
      // Add visual feedback to the list item
      const listItem = event.target.closest('.question-item')
      if (listItem) {
        listItem.classList.add('dragging')
      }
    }

    const handleDragOver = (event) => {
      event.preventDefault()
      event.dataTransfer.dropEffect = 'move'
      
      // Add visual feedback for valid drop targets
      const listItem = event.target.closest('.question-item')
      if (listItem && !listItem.classList.contains('dragging')) {
        // Clear previous drag-over states
        document.querySelectorAll('.drag-over').forEach(el => {
          el.classList.remove('drag-over')
        })
        listItem.classList.add('drag-over')
      }
    }

    const handleDrop = async (event, dropIndex) => {
      event.preventDefault()
      
      if (draggedIndex.value === dropIndex || draggedIndex.value === -1) {
        return
      }

      try {
        loading.value = true
        
        // Reorder questions in local array
        const questionsCopy = [...questions.value]
        const draggedQuestion = questionsCopy.splice(draggedIndex.value, 1)[0]
        questionsCopy.splice(dropIndex, 0, draggedQuestion)
        
        // Update sort orders for all affected questions
        const updates = []
        for (let i = 0; i < questionsCopy.length; i++) {
          if (questionsCopy[i].sort_order !== i) {
            updates.push(
              api.updateFollowupQuestionNormalized(questionsCopy[i].id, {
                sort_order: i
              })
            )
            questionsCopy[i].sort_order = i
          }
        }
        
        // Execute all updates
        await Promise.all(updates)
        
        // Update local state
        questions.value = questionsCopy
        
        emit('questions-updated')
        
      } catch (err) {
        console.error('Failed to reorder questions:', err)
        // Reload questions on error to reset state
        await loadQuestions()
      } finally {
        loading.value = false
      }
    }

    const handleDragEnd = (event) => {
      // Reset visual feedback
      const listItem = event.target.closest('.question-item')
      if (listItem) {
        listItem.classList.remove('dragging')
      }
      
      // Clear all drag-over states
      document.querySelectorAll('.drag-over').forEach(el => {
        el.classList.remove('drag-over')
      })
      
      draggedItem.value = null
      draggedIndex.value = -1
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
      showDeleteDialog,
      questionToDelete,
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
      confirmDelete,
      cancelDelete,
      saveQuestion,
      cancelAddQuestion,
      formatDate,
      handleDragStart,
      handleDragOver,
      handleDrop,
      handleDragEnd
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
  border-radius: 4px;
  padding: 4px;
  transition: background-color 0.2s ease;
}

.drag-handle:hover {
  background-color: rgba(var(--v-theme-primary), 0.1);
}

.drag-handle:active {
  cursor: grabbing;
}

/* Drag feedback styles */
.question-item[draggable="true"]:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.15);
}

.drag-over {
  border-color: rgba(var(--v-theme-primary), 0.8) !important;
  background-color: rgba(var(--v-theme-primary), 0.05) !important;
  transform: translateY(-2px);
}

.dragging {
  opacity: 0.5 !important;
  transform: rotate(5deg);
  z-index: 1000;
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