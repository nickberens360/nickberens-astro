<template>
  <v-dialog v-model="dialog" max-width="600px" persistent>
    <v-card>
      <v-card-title class="text-h5 d-flex align-center">
        <v-icon color="warning" class="mr-2">$alert-triangle</v-icon>
        Delete Category: {{ category?.display_name }}
      </v-card-title>

      <v-card-text>
        <!-- Category has questions - show options -->
        <div v-if="categoryStats?.question_count > 0">
          <v-alert
            type="warning"
            variant="tonal"
            class="mb-4"
          >
            This category contains <strong>{{ categoryStats.question_count }} questions</strong>. 
            Choose how to handle them before deletion.
          </v-alert>

          <div class="mb-4">
            <div class="text-subtitle-1 font-weight-medium mb-3">Deletion Strategy</div>
            
            <v-radio-group v-model="deleteStrategy" hide-details>
              <!-- Move to another category -->
              <v-radio value="move" class="mb-2">
                <template v-slot:label>
                  <div>
                    <div class="font-weight-medium">Move questions to another category</div>
                    <div class="text-caption text-medium-emphasis">
                      Transfer all questions to a different category
                    </div>
                  </div>
                </template>
              </v-radio>

              <!-- Delete all questions -->
              <v-radio value="delete_all" class="mb-2">
                <template v-slot:label>
                  <div>
                    <div class="font-weight-medium text-error">Delete all questions permanently</div>
                    <div class="text-caption text-medium-emphasis">
                      ⚠️ This cannot be undone
                    </div>
                  </div>
                </template>
              </v-radio>

              <!-- Deactivate category -->
              <v-radio value="deactivate" class="mb-2">
                <template v-slot:label>
                  <div>
                    <div class="font-weight-medium">Deactivate instead of delete</div>
                    <div class="text-caption text-medium-emphasis">
                      Hide the category but keep questions intact
                    </div>
                  </div>
                </template>
              </v-radio>
            </v-radio-group>
          </div>

          <!-- Target category selection for move strategy -->
          <v-select
            v-if="deleteStrategy === 'move'"
            v-model="targetCategoryId"
            :items="availableCategories"
            item-title="display_name"
            item-value="id"
            label="Move questions to"
            variant="outlined"
            :rules="[v => !!v || 'Please select a target category']"
            class="mb-4"
            hide-details
          >
            <template v-slot:item="{ props, item }">
              <v-list-item v-bind="props">
                <v-list-item-title>{{ item.raw.display_name }}</v-list-item-title>
                <v-list-item-subtitle>{{ item.raw.name }}</v-list-item-subtitle>
              </v-list-item>
            </template>
          </v-select>

          <!-- Confirmation for destructive operations -->
          <v-checkbox
            v-if="deleteStrategy === 'delete_all'"
            v-model="confirmDestructive"
            hide-details
            class="mt-4"
          >
            <template v-slot:label>
              <span class="text-error">
                I understand this will permanently delete {{ categoryStats.question_count }} questions
              </span>
            </template>
          </v-checkbox>
        </div>

        <!-- Category has no questions - simple deletion -->
        <div v-else>
          <v-alert
            type="info"
            variant="tonal"
            class="mb-4"
          >
            This category has no questions and can be safely deleted.
          </v-alert>
          
          <p class="text-body-2">
            The category "{{ category?.display_name }}" will be permanently removed from your system.
          </p>
        </div>

        <!-- Summary of action -->
        <v-card
          v-if="categoryStats?.question_count > 0"
          variant="tonal"
          class="mt-4"
        >
          <v-card-text class="pa-4">
            <div class="text-subtitle-2 mb-2">Summary:</div>
            <div class="text-body-2">
              <template v-if="deleteStrategy === 'move'">
                • Move {{ categoryStats.question_count }} questions to "{{ targetCategoryName }}"<br>
                • Delete category "{{ category?.display_name }}"
              </template>
              <template v-else-if="deleteStrategy === 'delete_all'">
                • <span class="text-error">Permanently delete {{ categoryStats.question_count }} questions</span><br>
                • <span class="text-error">Delete category "{{ category?.display_name }}"</span>
              </template>
              <template v-else-if="deleteStrategy === 'deactivate'">
                • Deactivate category "{{ category?.display_name }}"<br>
                • Keep all {{ categoryStats.question_count }} questions intact<br>
                • Category will be hidden from question selection
              </template>
            </div>
          </v-card-text>
        </v-card>
      </v-card-text>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn
          text
          @click="cancel"
          :disabled="loading"
        >
          Cancel
        </v-btn>
        <v-btn
          :color="deleteStrategy === 'deactivate' ? 'warning' : 'error'"
          :loading="loading"
          :disabled="!canProceed"
          @click="confirmDelete"
        >
          <template v-if="deleteStrategy === 'deactivate'">
            Deactivate Category
          </template>
          <template v-else-if="categoryStats?.question_count > 0">
            Delete Category & {{ deleteStrategy === 'move' ? 'Move' : 'Delete' }} Questions
          </template>
          <template v-else>
            Delete Category
          </template>
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref, computed, watch } from 'vue'

export default {
  name: 'CategoryDeleteDialog',
  props: {
    modelValue: {
      type: Boolean,
      default: false
    },
    category: {
      type: Object,
      default: null
    },
    categoryStats: {
      type: Object,
      default: null
    },
    availableCategories: {
      type: Array,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:modelValue', 'confirm', 'cancel'],
  setup(props, { emit }) {
    const deleteStrategy = ref('move')
    const targetCategoryId = ref(null)
    const confirmDestructive = ref(false)

    const dialog = computed({
      get: () => props.modelValue,
      set: (value) => emit('update:modelValue', value)
    })

    const targetCategoryName = computed(() => {
      if (!targetCategoryId.value) return ''
      const target = props.availableCategories.find(c => c.id === targetCategoryId.value)
      return target?.display_name || ''
    })

    const canProceed = computed(() => {
      // No questions - can always proceed
      if (!props.categoryStats?.question_count) return true
      
      // Strategy-specific validation
      switch (deleteStrategy.value) {
        case 'move':
          return !!targetCategoryId.value
        case 'delete_all':
          return confirmDestructive.value
        case 'deactivate':
          return true
        default:
          return false
      }
    })

    // Reset form when dialog opens/closes
    watch(() => props.modelValue, (isOpen) => {
      if (isOpen) {
        // Reset to defaults
        deleteStrategy.value = 'move'
        targetCategoryId.value = null
        confirmDestructive.value = false
        
        // Auto-select first available category for move
        if (props.availableCategories.length > 0) {
          targetCategoryId.value = props.availableCategories[0].id
        }
      }
    })

    const confirmDelete = () => {
      if (!canProceed.value) return

      const deleteRequest = {
        categoryId: props.category.id,
        strategy: deleteStrategy.value,
        ...(deleteStrategy.value === 'move' && { targetCategoryId: targetCategoryId.value })
      }

      emit('confirm', deleteRequest)
    }

    const cancel = () => {
      emit('cancel')
      emit('update:modelValue', false)
    }

    return {
      deleteStrategy,
      targetCategoryId,
      confirmDestructive,
      dialog,
      targetCategoryName,
      canProceed,
      confirmDelete,
      cancel
    }
  }
}
</script>

<style scoped>
.v-card-title {
  background: rgb(var(--v-theme-error-container));
  color: rgb(var(--v-theme-on-error-container));
}

.v-radio :deep(.v-label) {
  opacity: 1;
}
</style>