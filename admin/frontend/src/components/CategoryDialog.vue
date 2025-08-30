<template>
  <v-dialog v-model="dialog" max-width="500px" persistent>
    <v-card>
      <v-card-title>
        <span class="text-h5">{{ isEdit ? 'Edit Category' : 'New Category' }}</span>
      </v-card-title>

      <v-card-text>
        <v-form ref="form" v-model="valid">
          <v-text-field
            v-model="categoryData.name"
            label="Category Name"
            :rules="[
              v => !!v || 'Name is required',
              v => (v && v.length >= 2) || 'Name must be at least 2 characters',
              v => (v && v.length <= 50) || 'Name must be 50 characters or less'
            ]"
            variant="outlined"
            maxlength="50"
            counter
            required
          ></v-text-field>

          <v-text-field
            v-model="categoryData.display_name"
            label="Display Name"
            :rules="[
              v => !!v || 'Display name is required',
              v => (v && v.length >= 2) || 'Display name must be at least 2 characters',
              v => (v && v.length <= 100) || 'Display name must be 100 characters or less'
            ]"
            variant="outlined"
            maxlength="100"
            counter
            required
          ></v-text-field>

          <v-textarea
            v-model="categoryData.description"
            label="Description"
            :rules="[
              v => !v || v.length <= 500 || 'Description must be 500 characters or less'
            ]"
            variant="outlined"
            maxlength="500"
            counter
            rows="3"
            hint="Optional description for this category"
            persistent-hint
          ></v-textarea>

          <v-text-field
            v-model.number="categoryData.sort_order"
            label="Sort Order"
            type="number"
            :rules="[
              v => v >= 0 || 'Sort order must be 0 or greater',
              v => v <= 999 || 'Sort order must be 999 or less'
            ]"
            variant="outlined"
            hint="Lower numbers appear first (0-999)"
            persistent-hint
          ></v-text-field>

          <v-switch
            v-model="categoryData.is_active"
            label="Active"
            color="primary"
            hide-details
            class="mt-4"
          >
            <template v-slot:label>
              <div class="d-flex align-center">
                <span>Active</span>
                <v-tooltip activator="parent" location="top">
                  Inactive categories won't appear in the question selection interface
                </v-tooltip>
              </div>
            </template>
          </v-switch>
        </v-form>
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
          color="primary"
          :loading="loading"
          :disabled="!valid"
          @click="save"
        >
          {{ isEdit ? 'Update' : 'Create' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref, computed, watch } from 'vue'

export default {
  name: 'CategoryDialog',
  props: {
    modelValue: {
      type: Boolean,
      default: false
    },
    category: {
      type: Object,
      default: null
    },
    loading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:modelValue', 'save', 'cancel'],
  setup(props, { emit }) {
    const form = ref(null)
    const valid = ref(false)
    
    const categoryData = ref({
      name: '',
      display_name: '',
      description: '',
      sort_order: 0,
      is_active: true
    })

    const dialog = computed({
      get: () => props.modelValue,
      set: (value) => emit('update:modelValue', value)
    })

    const isEdit = computed(() => props.category && props.category.id)

    // Watch for category prop changes to populate form
    watch(() => props.category, (newCategory) => {
      if (newCategory) {
        categoryData.value = {
          name: newCategory.name || '',
          display_name: newCategory.display_name || '',
          description: newCategory.description || '',
          sort_order: newCategory.sort_order || 0,
          is_active: newCategory.is_active !== undefined ? newCategory.is_active : true
        }
      } else {
        // Reset for new category
        categoryData.value = {
          name: '',
          display_name: '',
          description: '',
          sort_order: 0,
          is_active: true
        }
      }
    }, { immediate: true })

    // Auto-generate display_name from name if not manually set
    watch(() => categoryData.value.name, (newName) => {
      if (!isEdit.value && newName && !categoryData.value.display_name) {
        // Convert snake_case or kebab-case to Title Case
        const titleCase = newName
          .replace(/[_-]/g, ' ')
          .replace(/\b\w/g, l => l.toUpperCase())
        categoryData.value.display_name = titleCase
      }
    })

    const save = async () => {
      if (!form.value) return
      
      const validation = await form.value.validate()
      if (!validation.valid) return

      const saveData = {
        ...categoryData.value,
        // Include ID for edit operations
        ...(isEdit.value && { id: props.category.id })
      }

      emit('save', saveData)
    }

    const cancel = () => {
      emit('cancel')
      emit('update:modelValue', false)
    }

    return {
      form,
      valid,
      categoryData,
      dialog,
      isEdit,
      save,
      cancel
    }
  }
}
</script>

<style scoped>
.v-card-title {
  background: rgb(var(--v-theme-surface-light));
  border-bottom: 1px solid rgba(var(--v-theme-outline), 0.12);
}
</style>