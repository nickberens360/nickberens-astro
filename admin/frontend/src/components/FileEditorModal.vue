<template>
  <v-dialog v-model="dialog" max-width="1400px" persistent>
    <v-card class="dialog-card" elevation="12">
      <v-card-title class="dialog-header pa-6 d-flex justify-space-between align-center">
        <div class="d-flex align-center">
          <v-icon class="me-3" color="primary">$edit</v-icon>
          <div>
            <h2 class="text-h6 font-weight-bold">File Editor</h2>
            <p class="text-body-2 text-medium-emphasis ma-0">{{ filename }}</p>
          </div>
        </div>
        <v-spacer/>
        <v-chip
          :color="getFileTypeColor(fileType)"
          size="small"
          variant="flat"
          class="me-2"
        >
          {{ fileType.toUpperCase() }}
        </v-chip>
      </v-card-title>

      <v-divider class="border-opacity-25"/>

      <v-card-text class="pa-6" style="background: rgba(var(--v-theme-surface), 0.3);">
        <v-alert
          v-if="error"
          type="error"
          variant="tonal"
          class="mb-4 rounded-lg"
          closable
          @click:close="error = null"
        >
          <template #prepend>
            <v-icon>$alert</v-icon>
          </template>
          {{ error }}
        </v-alert>

        <v-alert
          v-if="success"
          type="success"
          variant="tonal"
          class="mb-4 rounded-lg"
          closable
          @click:close="success = null"
        >
          <template #prepend>
            <v-icon>$check</v-icon>
          </template>
          {{ success }}
        </v-alert>

        <!-- Loading state -->
        <v-skeleton-loader
          v-if="loading"
          type="article"
          class="mb-4 rounded-lg"
        />

        <!-- Editor container -->
        <v-card
          v-else
          variant="outlined"
          class="editor-container rounded-lg overflow-hidden"
        >
          <div
            ref="editorContainer"
            style="height: 500px; width: 100%;"
          /></v-card>
      </v-card-text>

      <v-divider class="border-opacity-25"/>

      <v-card-actions class="pa-6 justify-space-between">
        <div class="d-flex align-center gap-2">
          <v-chip size="small" variant="tonal" color="info" class="mr-4">
            <v-icon start size="small">$text</v-icon>
            {{ lineCount }} lines
          </v-chip>
          <v-chip size="small" variant="tonal" color="info" class="mr-4">
            <v-icon start size="small">$file</v-icon>
            {{ formatFileSize(fileSize) }}
          </v-chip>
          <v-chip
            v-if="hasUnsavedChanges"
            color="warning"
            size="small"
            variant="flat"
          >
            <v-icon start size="small">$pencil</v-icon>
            Unsaved Changes
          </v-chip>
        </div>

        <div class="d-flex gap-2">
          <v-btn
            v-if="fileType === '.json'"
            prepend-icon="$format-text"
            variant="outlined"
            @click="formatJson"
            :disabled="saving"
            class="rounded-lg"
          >
            Format JSON
          </v-btn>
          <v-btn
            prepend-icon="$close"
            variant="outlined"
            @click="handleCancel"
            :disabled="saving"
            class="rounded-lg mr-2"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            prepend-icon="$save"
            :loading="saving"
            @click="saveFile"
            :disabled="!hasUnsavedChanges"
            class="rounded-lg"
            variant="flat"
          >
            Save Changes
          </v-btn>
        </div>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Unsaved Changes Confirmation Dialog -->
  <v-dialog v-model="showCloseConfirm" max-width="480">
    <v-card class="dialog-card" elevation="8">
      <v-card-title class="dialog-header pa-6">
        <div class="d-flex align-center">
          <v-icon class="me-3" color="warning">$alert</v-icon>
          <div>
            <h2 class="text-h6 font-weight-bold">Discard Changes?</h2>
            <p class="text-body-2 text-medium-emphasis ma-0">Unsaved changes will be lost</p>
          </div>
        </div>
      </v-card-title>

      <v-divider class="border-opacity-25"/>

      <v-card-text class="pa-6">
        <p class="text-body-2 mb-0">You have unsaved changes that will be lost if you close without saving. Are you sure you want to continue?</p>
      </v-card-text>

      <v-divider class="border-opacity-25"/>

      <v-card-actions class="pa-6">
        <v-spacer/>
        <v-btn
          prepend-icon="$close"
          variant="outlined"
          @click="cancelClose"
          class="rounded-lg"
        >
          Cancel
        </v-btn>
        <v-btn
          color="warning"
          prepend-icon="$delete"
          variant="flat"
          @click="confirmClose"
          class="rounded-lg"
        >
          Discard Changes
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as monaco from 'monaco-editor'
import { adminAPI } from '@/services/api'

export default {
  name: 'FileEditorModal',
  props: {
    modelValue: {
      type: Boolean,
      default: false
    },
    filename: {
      type: String,
      default: ''
    }
  },
  emits: ['update:modelValue', 'file-saved'],
  setup(props, { emit }) {
    const dialog = ref(false)
    const loading = ref(false)
    const saving = ref(false)
    const error = ref(null)
    const success = ref(null)
    const hasUnsavedChanges = ref(false)
    const showCloseConfirm = ref(false)
    const editorContainer = ref(null)

    let editor = null
    const originalContent = ref('')
    const currentContent = ref('')
    const fileType = ref('')
    const fileSize = ref(0)
    const lineCount = ref(0)

    // Watch for dialog changes
    watch(() => props.modelValue, (newValue) => {
      dialog.value = newValue
      if (newValue && props.filename) {
        loadFile()
      }
    })

    watch(dialog, (newValue) => {
      emit('update:modelValue', newValue)
      if (!newValue) {
        cleanup()
      } else if (newValue && currentContent.value && editorContainer.value) {
        // If dialog is opening and we already have content, create editor
        setTimeout(() => {
          createEditor()
        }, 300)
      }
    })

    const getLanguage = (filename) => {
      const ext = filename.split('.').pop()?.toLowerCase()
      const languageMap = {
        'js': 'javascript',
        'json': 'json',
        'md': 'markdown',
        'html': 'html',
        'css': 'css',
        'txt': 'plaintext',
        'py': 'python',
        'yml': 'yaml',
        'yaml': 'yaml'
      }
      return languageMap[ext] || 'plaintext'
    }

    const getFileTypeColor = (type) => {
      const colorMap = {
        '.json': 'orange',
        '.md': 'blue',
        '.html': 'red',
        '.txt': 'grey',
        '.css': 'purple',
        '.js': 'yellow'
      }
      return colorMap[type] || 'grey'
    }

    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    const loadFile = async () => {
      if (!props.filename) return

      loading.value = true
      error.value = null

      try {
        const response = await adminAPI.getKnowledgeFileContent(props.filename)

        let content = response.content || ''

        // Auto-format JSON content for better readability
        const ext = props.filename.split('.').pop()?.toLowerCase()
        if (ext === 'json' && content.trim()) {
          try {
            const parsed = JSON.parse(content)
            content = JSON.stringify(parsed, null, 2) // Pretty print with 2 spaces
          } catch (jsonError) {
            // If JSON parsing fails, keep original content
            console.warn('Failed to parse JSON for formatting:', jsonError)
          }
        }

        originalContent.value = content
        currentContent.value = content
        fileType.value = '.' + (ext || 'txt')
        fileSize.value = response.size || 0
        hasUnsavedChanges.value = false

        await nextTick()
        // Small delay to ensure DOM is fully rendered
        setTimeout(() => {
          if (editorContainer.value) {
            createEditor()
          }
        }, 200)
      } catch (err) {
        console.error('Failed to load file:', err)
        error.value = err.response?.data?.detail || 'Failed to load file content'
      } finally {
        loading.value = false
      }
    }

    const createEditor = () => {
      if (!editorContainer.value) {
        return
      }

      // Cleanup existing editor
      if (editor) {
        editor.dispose()
      }

      try {
        const language = getLanguage(props.filename)

        editor = monaco.editor.create(editorContainer.value, {
          value: currentContent.value || '',
          language: language,
          theme: 'vs-dark',
          automaticLayout: true,
          minimap: { enabled: true },
          scrollBeyondLastLine: false,
          wordWrap: 'on',
          fontSize: 14,
          lineNumbers: 'on',
          folding: true,
          bracketMatching: 'always',
          autoIndent: 'advanced',
          formatOnPaste: true,
          formatOnType: true
        })

        // Update line count
        lineCount.value = editor.getModel().getLineCount()

        // Listen for content changes
        editor.onDidChangeModelContent(() => {
          const newContent = editor.getValue()
          currentContent.value = newContent
          hasUnsavedChanges.value = newContent !== originalContent.value
          lineCount.value = editor.getModel().getLineCount()
        })

        // Add keyboard shortcuts
        editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
          if (hasUnsavedChanges.value) {
            saveFile()
          }
        })
      } catch (err) {
        console.error('Failed to initialize Monaco Editor:', err)
        error.value = 'Failed to initialize code editor'
      }
    }

    const saveFile = async () => {
      if (!hasUnsavedChanges.value) return

      saving.value = true
      error.value = null
      success.value = null

      try {
        const response = await adminAPI.updateKnowledgeFileContent(
          props.filename,
          currentContent.value
        )

        originalContent.value = currentContent.value
        hasUnsavedChanges.value = false
        fileSize.value = response.size || fileSize.value

        success.value = 'File saved successfully!'
        emit('file-saved', props.filename)

        // Auto-close dialog after successful save
        setTimeout(() => {
          success.value = null
          dialog.value = false
        }, 1000)

      } catch (err) {
        console.error('Failed to save file:', err)
        error.value = err.response?.data?.detail || 'Failed to save file'
      } finally {
        saving.value = false
      }
    }

    const formatJson = () => {
      if (!editor || fileType.value !== '.json') return

      try {
        const content = editor.getValue()
        const parsed = JSON.parse(content)
        const formatted = JSON.stringify(parsed, null, 2)

        // Update editor content
        editor.setValue(formatted)

        // Update our refs
        currentContent.value = formatted
        hasUnsavedChanges.value = formatted !== originalContent.value
        lineCount.value = editor.getModel().getLineCount()

        success.value = 'JSON formatted successfully!'
        setTimeout(() => {
          success.value = null
        }, 2000)

      } catch (err) {
        error.value = 'Invalid JSON format. Cannot format the content.'
        setTimeout(() => {
          error.value = null
        }, 3000)
      }
    }

    const handleCancel = () => {
      if (hasUnsavedChanges.value) {
        showCloseConfirm.value = true
      } else {
        dialog.value = false
      }
    }

    const confirmClose = () => {
      showCloseConfirm.value = false
      dialog.value = false
    }

    const cancelClose = () => {
      showCloseConfirm.value = false
    }

    const cleanup = () => {
      if (editor) {
        editor.dispose()
        editor = null
      }
      originalContent.value = ''
      currentContent.value = ''
      hasUnsavedChanges.value = false
      error.value = null
      success.value = null
      lineCount.value = 0
    }

    onMounted(() => {
      // Initialize dialog state
      dialog.value = props.modelValue
    })

    onUnmounted(() => {
      cleanup()
    })

    return {
      dialog,
      loading,
      saving,
      error,
      success,
      hasUnsavedChanges,
      showCloseConfirm,
      editorContainer,
      fileType,
      fileSize,
      lineCount,
      getFileTypeColor,
      formatFileSize,
      saveFile,
      formatJson,
      handleCancel,
      confirmClose,
      cancelClose
    }
  }
}
</script>

<style scoped>
.v-card {
  height: auto;
  max-height: 90vh;
}

.v-card-text {
  max-height: 60vh;
  overflow: hidden;
}

/* Dialog Styles */
.dialog-card {
  border-radius: 16px !important;
  overflow: hidden;
}

.dialog-header {
  background: linear-gradient(135deg, rgba(var(--v-theme-primary), 0.04), rgba(var(--v-theme-primary), 0.02));
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.08);
}

.editor-container {
  border: 2px solid rgba(var(--v-theme-primary), 0.12);
  transition: border-color 0.3s ease;
}

.editor-container:hover {
  border-color: rgba(var(--v-theme-primary), 0.24);
}

/* Ensure Monaco editor takes full container size */
:deep(.monaco-editor) {
  border-radius: 8px;
}

:deep(.monaco-editor .margin) {
  background: rgba(var(--v-theme-surface), 0.8);
}

:deep(.monaco-editor .monaco-editor-background) {
  background: rgba(var(--v-theme-surface-variant), 0.3);
}
</style>