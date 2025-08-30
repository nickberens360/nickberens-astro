<template>
  <div class="overview-view">
    <!-- Upload Section -->
    <v-card class="mb-6">
      <v-card-title class="text-h6">
        <v-icon class="me-2">$upload</v-icon>
        Upload Documents
      </v-card-title>
      <v-card-text class="pa-6">
        <v-file-input
          v-model="selectedFiles"
          label="Select files to upload"
          multiple
          accept=".md,.pdf,.json,.txt,.html,.docx"
          prepend-icon="$attach_file"
          variant="outlined"
          chips
          counter
          show-size
          :rules="fileRules"
        >
          <template v-slot:selection="{ fileNames }">
            <template v-for="(fileName, index) in fileNames" :key="fileName">
              <v-chip
                v-if="index < 3"
                color="primary"
                size="small"
                class="me-2"
              >
                {{ fileName }}
              </v-chip>
              <span
                v-else-if="index === 3"
                class="text-overline grey--text"
              >
                +{{ fileNames.length - 3 }} File(s)
              </span>
            </template>
          </template>
        </v-file-input>

        <v-alert
          v-if="uploadError"
          type="error"
          class="mt-4"
          closable
          @click:close="uploadError = null"
        >
          {{ uploadError }}
        </v-alert>

        <v-alert
          v-if="uploadSuccess"
          type="success"
          class="mt-4"
          closable
          @click:close="uploadSuccess = null"
        >
          {{ uploadSuccess }}
        </v-alert>

        <div class="mt-4 d-flex gap-2">
          <v-btn
            color="primary"
            :disabled="!selectedFiles?.length || uploading"
            :loading="uploading"
            @click="uploadFiles"
            prepend-icon="$cloud_upload"
            class="mr-4"
          >
            Upload Files
          </v-btn>
          <v-btn
            variant="outlined"
            @click="clearSelection"
            :disabled="!selectedFiles?.length || uploading"
          >
            Clear
          </v-btn>
          <v-btn
            color="secondary"
            prepend-icon="$refresh"
            @click="refreshKnowledgeBase"
            :loading="refreshing"
            variant="outlined"
          >
            Refresh Index
          </v-btn>
        </div>

        <v-divider class="my-4"></v-divider>

        <div class="text-body-2 text-medium-emphasis">
          <v-icon size="small" class="me-1">$info</v-icon>
          <strong>Supported formats:</strong> .md, .pdf, .json, .txt, .html, .docx
          <br>
          <v-icon size="small" class="me-1">$info</v-icon>
          <strong>Note:</strong> Files will be automatically indexed after upload. Use "Refresh Index" to force re-indexing.
        </div>
      </v-card-text>
    </v-card>

    <!-- File List -->
    <v-card>
      <v-card-title class="text-h6 d-flex align-center">
        <v-icon class="me-2">$list</v-icon>
        Knowledge Base Files
        <v-spacer></v-spacer>
        <v-btn
          icon="$refresh"
          variant="text"
          size="small"
          @click="loadFiles"
          :loading="loadingFiles"
        ></v-btn>
      </v-card-title>
      <v-card-text class="pa-0">
        <v-data-table
          :headers="fileHeaders"
          :items="files"
          :loading="loadingFiles"
          item-key="name"
        >
          <template v-slot:item.name="{ item }">
            <div class="d-flex align-center">
              <v-icon :color="getFileIcon(item.name).color" class="me-2">
                {{ getFileIcon(item.name).icon }}
              </v-icon>
              {{ item.name }}
            </div>
          </template>
          <template v-slot:item.size="{ item }">
            {{ formatFileSize(item.size) }}
          </template>
          <template v-slot:item.modified="{ item }">
            {{ formatDate(item.modified) }}
          </template>
          <template v-slot:item.actions="{ item }">
            <v-btn
              v-if="canEdit(item.name)"
              icon="$edit"
              variant="text"
              size="small"
              color="primary"
              @click="openFileEditor(item)"
              class="me-1"
            ></v-btn>
            <v-btn
              icon="$delete"
              variant="text"
              size="small"
              color="error"
              @click="confirmDelete(item)"
            ></v-btn>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title>Confirm Delete</v-card-title>
        <v-card-text>
          Are you sure you want to delete "{{ fileToDelete?.name }}"?
          This action cannot be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" @click="deleteFile" :loading="deleting">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- File Editor Modal -->
    <FileEditorModal
      v-model="editorDialog"
      :filename="selectedFilename"
      @file-saved="onFileSaved"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminAPI } from '@/services/api'
import FileEditorModal from '@/components/FileEditorModal.vue'

const selectedFiles = ref([])
const uploading = ref(false)
const refreshing = ref(false)
const loadingFiles = ref(false)
const deleting = ref(false)
const uploadError = ref(null)
const uploadSuccess = ref(null)
const deleteDialog = ref(false)
const fileToDelete = ref(null)
const editorDialog = ref(false)
const selectedFilename = ref('')

const files = ref([])

const fileHeaders = [
  { title: 'Name', key: 'name', sortable: true },
  { title: 'Type', key: 'type', sortable: true },
  { title: 'Size', key: 'size', sortable: true },
  { title: 'Modified', key: 'modified', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, align: 'center' }
]

const fileRules = [
  value => {
    if (!value || !value.length) return true
    const maxSize = 10 * 1024 * 1024 // 10MB
    const oversized = value.some(file => file.size > maxSize)
    return !oversized || 'File size must be less than 10MB'
  }
]

const getFileIcon = (filename) => {
  const ext = filename.split('.').pop()?.toLowerCase()
  const iconMap = {
    md: { icon: '$description', color: 'blue' },
    pdf: { icon: '$picture_as_pdf', color: 'red' },
    json: { icon: '$data_object', color: 'orange' },
    txt: { icon: '$text_snippet', color: 'grey' },
    html: { icon: '$language', color: 'orange' },
    docx: { icon: '$article', color: 'blue' }
  }
  return iconMap[ext] || { icon: '$insert_drive_file', color: 'grey' }
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (dateString) => {
  if (!dateString) return 'Never'
  return new Date(dateString).toLocaleDateString()
}

const uploadFiles = async () => {
  if (!selectedFiles.value?.length) return

  uploading.value = true
  uploadError.value = null
  uploadSuccess.value = null

  try {
    const formData = new FormData()
    selectedFiles.value.forEach(file => {
      formData.append('files', file)
    })

    await adminAPI.uploadKnowledgeFiles(formData)

    uploadSuccess.value = `Successfully uploaded ${selectedFiles.value.length} file(s)`
    selectedFiles.value = []

    // Refresh data
    await loadFiles()
  } catch (error) {
    console.error('Upload error:', error)
    uploadError.value = error.response?.data?.detail || 'Failed to upload files'
  } finally {
    uploading.value = false
  }
}

const refreshKnowledgeBase = async () => {
  refreshing.value = true
  uploadError.value = null
  uploadSuccess.value = null

  try {
    // Start the refresh
    const startResult = await adminAPI.refreshKnowledgeBase(true)

    if (startResult.status === 'running') {
      uploadSuccess.value = 'Knowledge base refresh started...'

      // Poll for status updates
      const pollInterval = setInterval(async () => {
        try {
          const status = await adminAPI.getRefreshStatus()

          if (status.progress?.current_file) {
            uploadSuccess.value = `Refreshing: ${status.progress.current_file}`
          }

          if (status.status === 'completed') {
            clearInterval(pollInterval)
            uploadSuccess.value = `Knowledge base refreshed successfully! Processed ${status.progress?.files_processed || 0} files.`
            refreshing.value = false
          } else if (status.status === 'failed') {
            clearInterval(pollInterval)
            uploadError.value = `Refresh failed: ${status.progress?.current_file || 'Unknown error'}`
            refreshing.value = false
          }
        } catch (pollError) {
          console.error('Status polling error:', pollError)
          clearInterval(pollInterval)
          uploadError.value = 'Lost connection to refresh process'
          refreshing.value = false
        }
      }, 2000) // Poll every 2 seconds

      // Set a timeout for the entire process
      setTimeout(() => {
        if (refreshing.value) {
          clearInterval(pollInterval)
          uploadError.value = 'Refresh operation timed out'
          refreshing.value = false
        }
      }, 300000) // 5 minutes timeout
    } else {
      uploadSuccess.value = startResult.message || 'Knowledge base refresh completed'
    }
  } catch (error) {
    console.error('Refresh error:', error)
    uploadError.value = error.response?.data?.detail || 'Failed to refresh knowledge base'
  } finally {
    if (!refreshing.value) {
      refreshing.value = false
    }
  }
}

const loadFiles = async () => {
  loadingFiles.value = true
  try {
    const response = await adminAPI.getKnowledgeFiles()
    files.value = response.files || []
  } catch (error) {
    console.error('Failed to load files:', error)
  } finally {
    loadingFiles.value = false
  }
}

const confirmDelete = (file) => {
  fileToDelete.value = file
  deleteDialog.value = true
}

const deleteFile = async () => {
  if (!fileToDelete.value) return

  deleting.value = true
  try {
    await adminAPI.deleteKnowledgeFile(fileToDelete.value.name)
    uploadSuccess.value = `File "${fileToDelete.value.name}" deleted successfully`

    await loadFiles()
  } catch (error) {
    console.error('Delete error:', error)
    uploadError.value = 'Failed to delete file'
  } finally {
    deleting.value = false
    deleteDialog.value = false
    fileToDelete.value = null
  }
}

const clearSelection = () => {
  selectedFiles.value = []
}

const canEdit = (filename) => {
  const ext = filename.split('.').pop()?.toLowerCase()
  return ['json', 'md', 'txt', 'html'].includes(ext)
}

const openFileEditor = (file) => {
  selectedFilename.value = file.name
  editorDialog.value = true
}

const onFileSaved = (filename) => {
  uploadSuccess.value = `File "${filename}" saved successfully`
  // Optionally refresh the file list to update modified time
  loadFiles()
}

onMounted(() => {
  loadFiles()
})
</script>

<style scoped>
.overview-view {
  max-width: 1400px;
  margin: 0 auto;
}

.v-file-input :deep(.v-field__input) {
  padding-top: 8px;
}
</style>