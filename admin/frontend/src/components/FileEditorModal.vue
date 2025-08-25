<template>
  <v-dialog v-model="dialog" max-width="1200px" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="me-2">$edit</v-icon>
        Edit File: {{ filename }}
        <v-spacer></v-spacer>
        <v-chip 
          :color="getFileTypeColor(fileType)" 
          size="small" 
          variant="flat"
        >
          {{ fileType.toUpperCase() }}
        </v-chip>
      </v-card-title>

      <v-card-text class="pa-0">
        <v-alert
          v-if="error"
          type="error"
          class="ma-4"
          closable
          @click:close="error = null"
        >
          {{ error }}
        </v-alert>

        <v-alert
          v-if="success"
          type="success"
          class="ma-4"
          closable
          @click:close="success = null"
        >
          {{ success }}
        </v-alert>

        <!-- Loading state -->
        <v-skeleton-loader
          v-if="loading"
          type="article"
          class="ma-4"
        ></v-skeleton-loader>

        <!-- Editor container -->
        <div 
          v-else
          ref="editorContainer"
          style="height: 500px; width: 100%;"
        ></div>
      </v-card-text>

      <v-card-actions class="justify-space-between">
        <div class="d-flex align-center">
          <v-chip size="small" variant="outlined" class="me-2">
            Lines: {{ lineCount }}
          </v-chip>
          <v-chip size="small" variant="outlined" class="me-2">
            Size: {{ formatFileSize(fileSize) }}
          </v-chip>
          <v-chip 
            v-if="hasUnsavedChanges"
            color="warning" 
            size="small" 
            variant="flat"
          >
            Unsaved Changes
          </v-chip>
        </div>

        <div>
          <v-btn
            v-if="fileType === '.json'"
            text="Format JSON"
            variant="outlined"
            @click="formatJson"
            :disabled="saving"
            class="me-2"
          ></v-btn>
          <v-btn
            text="Cancel"
            @click="handleCancel"
            :disabled="saving"
          ></v-btn>
          <v-btn
            color="primary"
            :loading="saving"
            @click="saveFile"
            :disabled="!hasUnsavedChanges"
          >
            Save Changes
          </v-btn>
        </div>
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
        if (confirm('You have unsaved changes. Are you sure you want to close without saving?')) {
          dialog.value = false
        }
      } else {
        dialog.value = false
      }
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
      editorContainer,
      fileType,
      fileSize,
      lineCount,
      getFileTypeColor,
      formatFileSize,
      saveFile,
      formatJson,
      handleCancel
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

/* Ensure Monaco editor takes full container size */
:deep(.monaco-editor) {
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 4px;
}
</style>