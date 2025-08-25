<template>
  <div class="sources-view">
    <div class="d-flex justify-space-between align-center mb-6">
      <h2 class="text-h5">Knowledge Sources</h2>
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

    <v-card elevation="2">
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
            </div>
          </template>
          <template v-slot:item.content_type="{ item }">
            <v-chip
              :color="getContentTypeColor(item.content_type)"
              size="small"
            >
              {{ item.content_type || 'unknown' }}
            </v-chip>
          </template>
          <template v-slot:item.chunk_count="{ item }">
            <span class="text-body-2">{{ item.chunk_count }} chunks</span>
          </template>
          <template v-slot:item.actions="{ item }">
            <div class="d-flex align-center gap-1">
              <v-btn
                icon="$view"
                size="small"
                variant="text"
                color="green"
                @click="viewFileContent(item)"
                :disabled="loading"
                title="View/Edit File Content"
              ></v-btn>
              <v-btn
                icon="$edit"
                size="small"
                variant="text"
                color="blue"
                @click="editSource(item)"
                :disabled="loading"
                title="Edit Metadata"
              ></v-btn>
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

    <!-- File Editor Modal -->
    <FileEditorModal
      v-model="showFileEditorModal"
      :filename="selectedFilename"
      @file-saved="handleFileSaved"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminAPI } from '@/services/api'
import FileEditorModal from '@/components/FileEditorModal.vue'

const loading = ref(false)
const search = ref('')
const sources = ref([])
const showEditDialog = ref(false)
const showDeleteDialog = ref(false)
const showFileEditorModal = ref(false)
const selectedSource = ref(null)
const editedContentType = ref('')
const selectedFilename = ref('')

const sourceHeaders = [
  { title: 'Source Path', key: 'path', sortable: true },
  { title: 'Content Type', key: 'content_type', sortable: true },
  { title: 'Chunks', key: 'chunk_count', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, width: '150px' }
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

const getContentTypeColor = (type) => {
  const colorMap = {
    'technical': 'blue',
    'experience': 'green',
    'skills': 'orange',
    'about': 'purple',
    'creative': 'pink',
    'project': 'teal',
    'code': 'indigo',
    'documentation': 'cyan'
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
  const binaryTypes = ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'woff', 'woff2', 'ttf', 'otf']
  
  if (binaryTypes.includes(ext)) {
    alert(`Cannot edit binary file: ${source.path}\n\nFile type: ${ext.toUpperCase()}\nThis file contains binary data that cannot be edited as text.`)
    return
  }
  
  // Extract the relative path from the full source path
  let relativePath = source.path
  if (relativePath.startsWith('backend/knowledge/')) {
    relativePath = relativePath.replace('backend/knowledge/', '')
  } else if (relativePath.startsWith('public/')) {
    relativePath = relativePath.replace('public/', '')
  }
  
  selectedFilename.value = relativePath
  showFileEditorModal.value = true
}

const handleFileSaved = () => {
  // Reload sources when file is saved to reflect any changes
  loadSources()
}

const isBinaryFile = (filePath) => {
  if (!filePath) return false
  const ext = filePath.split('.').pop()?.toLowerCase()
  const binaryTypes = ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'woff', 'woff2', 'ttf', 'otf']
  return binaryTypes.includes(ext)
}

onMounted(() => {
  loadSources()
})
</script>

<style scoped>
.sources-view {
  padding: 24px;
}
</style>