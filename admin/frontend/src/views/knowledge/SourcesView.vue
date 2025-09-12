<template>
  <div class="sources-view">
    <div class="d-flex justify-end align-center mb-6">
      <div class="d-flex gap-2">
        <v-btn
          color="success"
          prepend-icon="$upload"
          @click="showUploadDialog = true"
          variant="outlined"
          class="mr-4"
        >
          Upload Files
        </v-btn>
        <v-btn
          color="primary"
          prepend-icon="$refresh"
          @click="loadSources"
          :loading="loading"
          variant="outlined"
        >
          Refresh
        </v-btn>
      </div>
    </div>

    <v-card>
      <v-card-title class="text-h6 d-flex align-center">
        <v-icon class="me-2">$folder</v-icon>
        Source Files and Usage
        <v-spacer></v-spacer>
        <v-text-field
          v-model="search"
          density="compact"
          variant="outlined"
          placeholder="Search sources..."
          hide-details
          class="me-2"
          style="max-width: 300px"
        ></v-text-field>
        <v-btn
          icon="$refresh"
          variant="text"
          size="small"
          @click="loadSources"
          :loading="loading"
        ></v-btn>
      </v-card-title>
      <v-card-text class="pa-0">
        <v-data-table
          :headers="sourceHeaders"
          :items="sources"
          :loading="loading"
          :search="search"
          item-key="path"
        >
          <template v-slot:item.path="{ item }">
            <div class="d-flex align-center">
              <v-icon :color="getFileIcon(item.path).color" class="me-2">
                {{ getFileIcon(item.path).icon }}
              </v-icon>
              <div class="text-truncate" style="max-width: 400px" :title="item.path">
                {{ item.path }}
              </div>
              <!-- Non-editable indicator at end of path with tooltip -->
              <v-tooltip
                v-if="isNonEditableFile(item.path)"
                :text="getNonEditableTooltip(item.path)"
                location="top"
                :max-width="300"
                content-class="kb-tooltip"
              >
                <template #activator="{ props }">
                  <v-icon
                    v-bind="props"
                    size="18"
                    color="info"
                    class="ms-2"
                  >
                    $help-circle-outline
                  </v-icon>
                </template>
              </v-tooltip>
            </div>
          </template>
          <template v-slot:item.content_type="{ item }">
            <div class="d-flex flex-wrap gap-1">
              <v-chip
                v-for="type in getContentTypes(item.content_type)"
                :key="type"
                :color="getContentTypeColor(type)"
                size="small"
              >
                {{ type }}
              </v-chip>
            </div>
          </template>
          <template v-slot:item.chunk_count="{ item }">
            <span class="text-body-2">{{ item.chunk_count }} chunks</span>
          </template>
          <template v-slot:item.actions="{ item }">
            <div class="d-flex align-center gap-1">
              <!-- Edit button with conditional tooltip/disable for non-editable types -->
              <v-tooltip
                v-if="isNonEditableFile(item.path)"
                :text="getNonEditableTooltip(item.path)"
                location="top"
                :max-width="300"
                content-class="kb-tooltip"
              >
                <template #activator="{ props }">
                  <!-- Wrap disabled button in span so tooltip still works -->
                  <span v-bind="props">
                    <v-btn
                      icon="$edit"
                      size="small"
                      variant="text"
                      color="grey"
                      :disabled="true"
                      title="View/Edit File Content"
                    ></v-btn>
                  </span>
                </template>
              </v-tooltip>
              <template v-else>
                <v-btn
                  icon="$edit"
                  size="small"
                  variant="text"
                  color="green"
                  @click="viewFileContent(item)"
                  :disabled="loading"
                  title="View/Edit File Content"
                ></v-btn>
              </template>

              <!-- Delete button -->
              <v-btn
                icon="$delete"
                size="small"
                variant="text"
                color="red"
                @click="confirmDelete(item)"
                :disabled="loading"
                title="Delete Source"
              ></v-btn>
            </div>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Edit Source Dialog -->
    <v-dialog
      v-model="showEditDialog"
      max-width="500px"
    >
      <v-card>
        <v-card-title class="text-h5">
          Edit Source
        </v-card-title>
        <v-card-text>
          <v-text-field
            label="Source Path"
            :model-value="selectedSource?.path"
            readonly
            variant="outlined"
            class="mb-4"
          ></v-text-field>
          <v-text-field
            v-model="editedContentType"
            label="Content Type"
            variant="outlined"
            placeholder="e.g., technical, experience, skills, about"
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            text="Cancel"
            variant="text"
            @click="cancelEdit"
          ></v-btn>
          <v-btn
            text="Save"
            color="primary"
            variant="elevated"
            @click="saveEdit"
            :loading="loading"
          ></v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog
      v-model="showDeleteDialog"
      max-width="500px"
    >
      <v-card>
        <v-card-title class="text-h5">
          Delete Source
        </v-card-title>
        <v-card-text>
          <p>Are you sure you want to delete this source?</p>
          <p class="text-subtitle-2 text-medium-emphasis mt-2">
            <strong>Path:</strong> {{ selectedSource?.path }}
          </p>
          <p class="text-body-2 text-medium-emphasis">
            This will permanently remove the source file and all associated chunks from the knowledge base.
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            text="Cancel"
            variant="text"
            @click="cancelDelete"
          ></v-btn>
          <v-btn
            text="Delete"
            color="red"
            variant="elevated"
            @click="deleteSource"
            :loading="loading"
          ></v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Upload Dialog -->
    <v-dialog v-model="showUploadDialog" max-width="600px">
      <v-card>
        <v-card-title class="text-h5 d-flex align-center">
          <v-icon class="me-2">$upload</v-icon>
          Upload Knowledge Files
        </v-card-title>

        <v-card-text>
          <div class="mb-4">
            <p class="text-body-2 text-medium-emphasis mb-3">
              Upload documents to add them to your knowledge base. Supported formats:
              <strong>MD, PDF, TXT, JSON, HTML, DOCX</strong>
            </p>

            <v-file-input
              v-model="selectedFiles"
              label="Select files to upload"
              prepend-icon="$attach_file"
              variant="outlined"
              multiple
              accept=".md,.pdf,.txt,.json,.html,.docx,.doc"
              show-size
              counter
              :rules="fileRules"
            />
          </div>

          <!-- Upload Progress -->
          <div v-if="uploadProgress.active" class="mb-4">
            <v-card variant="outlined">
              <v-card-text>
                <div class="d-flex align-center justify-space-between mb-2">
                  <span class="text-body-2">Uploading files...</span>
                  <span class="text-body-2">{{ uploadProgress.completed }}/{{ uploadProgress.total }}</span>
                </div>
                <v-progress-linear
                  :model-value="(uploadProgress.completed / uploadProgress.total) * 100"
                  color="success"
                  height="8"
                  rounded
                />
              </v-card-text>
            </v-card>
          </div>

          <!-- Upload Results -->
          <div v-if="uploadResults.length > 0" class="mb-4">
            <v-card variant="outlined">
              <v-card-title class="text-subtitle-1">Upload Results</v-card-title>
              <v-card-text>
                <v-list density="compact">
                  <v-list-item
                    v-for="result in uploadResults"
                    :key="result.filename"
                  >
                    <template v-slot:prepend>
                      <v-icon
                        :color="result.success ? 'success' : 'error'"
                        :icon="result.success ? '$check' : '$alert'"
                      />
                    </template>
                    <v-list-item-title>{{ result.filename }}</v-list-item-title>
                    <v-list-item-subtitle v-if="result.success">
                      {{ formatFileSize(result.size) }}
                    </v-list-item-subtitle>
                    <v-list-item-subtitle v-else class="text-error">
                      {{ result.error }}
                    </v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-card-text>
            </v-card>
          </div>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn
            @click="cancelUpload"
            :disabled="uploadProgress.active"
            variant="text"
          >
            Cancel
          </v-btn>
          <v-btn
            @click="uploadFiles"
            color="success"
            :loading="uploadProgress.active"
            :disabled="!selectedFiles || selectedFiles.length === 0"
            variant="elevated"
          >
            Upload {{ selectedFiles ? selectedFiles.length : 0 }} File{{ selectedFiles && selectedFiles.length !== 1 ? 's' : '' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- File Editor Modal -->
    <FileEditorModal
      v-model="showFileEditorModal"
      :filename="selectedFilename"
      @file-saved="handleFileSaved"
    />

    <!-- Toasts are handled globally via NotificationMessage -->
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminAPI } from '@/services/api'
import FileEditorModal from '@/components/FileEditorModal.vue'
import { useNotifications } from '@/composables/useNotifications'

const loading = ref(false)
const search = ref('')
const sources = ref([])
const showEditDialog = ref(false)
const showDeleteDialog = ref(false)
const showFileEditorModal = ref(false)
const selectedSource = ref(null)
const editedContentType = ref('')
const selectedFilename = ref('')

// Upload dialog state
const showUploadDialog = ref(false)

// Notifications
const { showSuccess, showError, showInfo, showWarning } = useNotifications()
const selectedFiles = ref(null)
const uploadResults = ref([])
const uploadProgress = ref({
  active: false,
  completed: 0,
  total: 0
})

const sourceHeaders = [
  { title: 'Source Path', key: 'path', sortable: true },
  { title: 'Content Type', key: 'content_type', sortable: true },
  { title: 'Chunks', key: 'chunk_count', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, width: '150px' }
]

// File validation rules
const fileRules = [
  files => !files || files.length <= 10 || 'Maximum 10 files at once',
  files => !files || files.every(file => file.size <= 50 * 1024 * 1024) || 'Files must be smaller than 50MB'
]

// Notification helper (now uses global toasts)
const showAlert = (message, type = 'info') => {
  const map = {
    success: showSuccess,
    error: showError,
    info: showInfo,
    warning: showWarning,
  }
  const fn = map[type] || showInfo
  fn(message)
}

// Upload methods
const uploadFiles = async () => {
  if (!selectedFiles.value || selectedFiles.value.length === 0) return

  uploadProgress.value = {
    active: true,
    completed: 0,
    total: selectedFiles.value.length
  }
  uploadResults.value = []

  try {
    const formData = new FormData()
    for (const file of selectedFiles.value) {
      formData.append('files', file)
    }

    const response = await adminAPI.uploadKnowledgeFiles(formData)

    uploadResults.value = response.results || []
    uploadProgress.value.completed = selectedFiles.value.length

    // Show success message
    if (response.successful_uploads > 0) {
      setTimeout(() => {
        // Refresh sources list to show new uploads
        loadSources()
        // Keep dialog open briefly to show results, then close
        setTimeout(() => {
          if (response.successful_uploads === selectedFiles.value.length) {
            cancelUpload() // Close if all successful
          }
        }, 2000)
      }, 1000)
    }

  } catch (error) {
    console.error('Upload failed:', error)
    uploadResults.value = selectedFiles.value.map(file => ({
      filename: file.name,
      success: false,
      error: error.response?.data?.detail || 'Upload failed'
    }))
    showError('Upload failed')
  } finally {
    uploadProgress.value.active = false
  }
}

const cancelUpload = () => {
  showUploadDialog.value = false
  selectedFiles.value = null
  uploadResults.value = []
  uploadProgress.value = {
    active: false,
    completed: 0,
    total: 0
  }
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

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

const getContentTypes = (contentTypeStr) => {
  if (!contentTypeStr || contentTypeStr === 'unknown') {
    return ['unknown']
  }
  return contentTypeStr.split(',').map(type => type.trim()).filter(type => type.length > 0)
}

const getContentTypeColor = (type) => {
  const colorMap = {
    'technical': 'blue',
    'experience': 'green',
    'skills': 'orange',
    'about': 'purple',
    'creative': 'pink',
    'project': 'teal',
    'code': 'indigo',
    'documentation': 'cyan',
    'general': 'grey',
    'unknown': 'grey'
  }
  return colorMap[type?.toLowerCase()] || 'grey'
}

const loadSources = async () => {
  loading.value = true
  try {
    const response = await adminAPI.getKnowledgeSources()
    sources.value = response.sources || []
  } catch (error) {
    console.error('Failed to load sources:', error)
    showError('Failed to load sources')
  } finally {
    loading.value = false
  }
}

const editSource = (source) => {
  selectedSource.value = source
  editedContentType.value = source.content_type || ''
  showEditDialog.value = true
}

const confirmDelete = (source) => {
  selectedSource.value = source
  showDeleteDialog.value = true
}

const saveEdit = async () => {
  if (!selectedSource.value) return

  try {
    loading.value = true
    await adminAPI.updateKnowledgeSource(selectedSource.value.path, {
      content_type: editedContentType.value
    })

    // Update local data
    const index = sources.value.findIndex(s => s.path === selectedSource.value.path)
    if (index !== -1) {
      sources.value[index].content_type = editedContentType.value
    }

    showEditDialog.value = false
  } catch (error) {
    console.error('Failed to update source:', error)
    showError('Failed to update source')
  } finally {
    loading.value = false
  }
}

const deleteSource = async () => {
  if (!selectedSource.value) return

  try {
    loading.value = true
    await adminAPI.deleteKnowledgeSource(selectedSource.value.path)

    // Remove from local data
    sources.value = sources.value.filter(s => s.path !== selectedSource.value.path)

    showDeleteDialog.value = false
  } catch (error) {
    console.error('Failed to delete source:', error)
    showError('Failed to delete source')
  } finally {
    loading.value = false
  }
}

const cancelEdit = () => {
  showEditDialog.value = false
  selectedSource.value = null
  editedContentType.value = ''
}

const cancelDelete = () => {
  showDeleteDialog.value = false
  selectedSource.value = null
}

const viewFileContent = (source) => {
  selectedSource.value = source

  // Check if this is a binary file type that can't be edited
  const ext = source.path.split('.').pop()?.toLowerCase()
  const binaryTypes = ['pdf', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'woff', 'woff2', 'ttf', 'otf']

  if (binaryTypes.includes(ext)) {
    showAlert(`Cannot edit binary file: ${source.path}. File type: ${ext.toUpperCase()}. This file contains binary data that cannot be edited as text.`, 'warning')
    return
  }

  // Use the display path provided by the backend (no path manipulation needed)
  selectedFilename.value = source.display_path || source.path
  showFileEditorModal.value = true
}

const handleFileSaved = () => {
  // Reload sources when file is saved to reflect any changes
  loadSources()
}

// Helpers to control edit availability and tooltip messaging
const isNonEditableFile = (filePath) => {
  if (!filePath) return false
  const ext = filePath.split('.').pop()?.toLowerCase()
  return ['pdf', 'docx'].includes(ext)
}

const getNonEditableTooltip = (filePath) => {
  const ext = filePath.split('.').pop()?.toLowerCase()
  if (ext === 'pdf') {
    return 'PDF files cannot be edited here. Download or replace the file instead.'
  }
  if (ext === 'docx') {
    return 'DOCX files are binary and not editable in-browser. Upload a new version or convert to Markdown/HTML to edit.'
  }
  return 'This file type is not editable.'
}

const isBinaryFile = (filePath) => {
  if (!filePath) return false
  const ext = filePath.split('.').pop()?.toLowerCase()
  const binaryTypes = ['pdf', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'woff', 'woff2', 'ttf', 'otf']
  return binaryTypes.includes(ext)
}

onMounted(() => {
  loadSources()
})
</script>

<style scoped>
.sources-view {
  max-width: 1400px;
  margin: 0 auto;
}

/* Ensure proper spacing for content type chips */
.gap-1 > .v-chip {
  margin: 2px;
}

/* Ensure tooltip text wraps nicely at ~300px */
:deep(.kb-tooltip) {
  white-space: normal;
}
</style>
