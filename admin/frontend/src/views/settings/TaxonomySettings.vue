<template>
  <div class="taxonomy-settings">
    <v-card elevation="2">
      <v-card-title class="d-flex align-center justify-space-between pa-6">
        <div class="text-h6 font-weight-bold">Search & Taxonomy</div>
        <div class="d-flex align-center gap-2">
          <!-- Actions Menu -->
          <v-menu>
            <template v-slot:activator="{ props }">
              <v-btn 
                v-bind="props"
                variant="text"
                icon="$dots-vertical"
                density="comfortable"
              />
            </template>
            <v-list density="compact">
              <v-list-item @click="resetToExample">
                <template v-slot:prepend>
                  <v-icon>$undo</v-icon>
                </template>
                <v-list-item-title>Reset to Example</v-list-item-title>
              </v-list-item>
              <v-list-item @click="validateJson">
                <template v-slot:prepend>
                  <v-icon>$check</v-icon>
                </template>
                <v-list-item-title>Validate JSON</v-list-item-title>
              </v-list-item>
              <v-list-item @click="formatJson">
                <template v-slot:prepend>
                  <v-icon>$format-text</v-icon>
                </template>
                <v-list-item-title>Format JSON</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
          
          <!-- Primary Action -->
          <v-btn variant="elevated" color="primary" @click="saveDraft" prepend-icon="$save" class="ml-3">
            Save Draft
          </v-btn>
        </div>
      </v-card-title>

      <v-card-text class="pa-6">
        <v-alert v-if="error" type="error" variant="tonal" class="mb-4">{{ error }}</v-alert>
        <v-alert v-if="validMessage" type="success" variant="tonal" class="mb-4">{{ validMessage }}</v-alert>

        <!-- Taxonomy JSON Editor Section -->
        <v-card variant="flat" class="mb-6">
          <v-card-title class="text-subtitle-1 font-weight-bold pa-4">
            <v-icon color="primary" class="mr-2">$code</v-icon>
            Taxonomy JSON Editor
          </v-card-title>
          <v-card-text class="pa-4">
            <!-- Monaco Editor Container -->
            <v-card
              variant="outlined"
              class="editor-container rounded-lg overflow-hidden mb-4"
            >
              <div
                ref="editorContainer"
                style="height: 450px; width: 100%;"
              />
            </v-card>

            <div class="mt-4 d-flex align-center gap-2">
              <v-text-field
                v-model="testQuery"
                label="Test Query"
                variant="outlined"
                density="comfortable"
                prepend-inner-icon="$search"
                class="flex-1"
              />
              <v-btn color="primary" variant="elevated" @click="runTest">Test Detection</v-btn>
            </div>

            <div v-if="testResult" class="mt-3 text-medium-emphasis">
              Detected categories: <strong>{{ testResult.join(', ') || 'None' }}</strong>
            </div>
          </v-card-text>
        </v-card>

        <!-- Live Preview Section -->
        <v-card variant="flat" class="mb-6">
          <v-card-title class="text-subtitle-1 font-weight-bold pa-4">
            <v-icon color="primary" class="mr-2">$preview</v-icon>
            Live Preview
          </v-card-title>
          <v-card-text class="pa-4">
            <div class="preview-list" v-if="categoryList.length">
              <div v-for="c in categoryList" :key="c.name" class="preview-item">
                <div class="item-title">
                  <v-icon size="18" color="primary" class="mr-1">$tag</v-icon>
                  {{ c.name }}
                </div>
                <div class="item-line"><span class="label">Synonyms:</span> {{ (c.synonyms || []).join(', ') || '—' }}</div>
                <div class="item-line"><span class="label">Regex:</span> {{ (c.regex || []).join(' | ') || '—' }}</div>
              </div>
            </div>
            <div v-else class="text-medium-emphasis">No categories parsed yet.</div>
          </v-card-text>
        </v-card>
      </v-card-text>
    </v-card>
  </div>
  
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useNotifications } from '@/composables/useNotifications'
import { useTheme } from 'vuetify'
import * as monaco from 'monaco-editor'

const { showSuccess, showError } = useNotifications()
const theme = useTheme()

const LOCAL_KEY = 'taxonomy_draft_json'
const error = ref('')
const validMessage = ref('')
const taxonomyJson = ref('')
const testQuery = ref('')
const testResult = ref(null)
const editorContainer = ref(null)

let editor = null

// Computed property for Monaco theme based on Vuetify theme
const monacoTheme = computed(() =>
  theme.global.current.value.dark ? 'vs-dark' : 'vs'
)

const EXAMPLE = `{
  "version": "1",
  "categories": {
    "experience": {
      "synonyms": ["experience", "work", "resume", "cv", "company", "role"],
      "regex": ["\\b(experience|work|resume|cv|company|role)\\b"]
    },
    "skills": {
      "synonyms": ["skills", "technology", "technologies", "expertise"]
    },
    "creative": {
      "synonyms": ["illustration", "art", "design", "portfolio", "gallery"],
      "metadata": {"is_illustration_data": true}
    },
    "about": {
      "synonyms": ["about", "bio", "background", "philosophy", "passion"]
    },
    "project": {
      "synonyms": ["project", "projects", "built", "developed", "created"]
    }
  },
  "router": {"ignore_words": ["show", "me", "please"]}
}`

// Watch for theme changes and update Monaco editor theme
watch(monacoTheme, (newTheme) => {
  if (editor) {
    monaco.editor.setTheme(newTheme)
  }
})

// Watch taxonomyJson changes and update the computed categoryList
watch(taxonomyJson, () => {
  if (editor && editor.getValue() !== taxonomyJson.value) {
    editor.setValue(taxonomyJson.value || '')
  }
})

onMounted(async () => {
  // Load any previously saved draft from localStorage
  const draft = localStorage.getItem(LOCAL_KEY)
  taxonomyJson.value = draft || EXAMPLE
  
  // Wait for DOM to be ready, then create Monaco editor
  await nextTick()
  setTimeout(() => {
    if (editorContainer.value) {
      createEditor()
    }
  }, 100)
})

const categoryList = computed(() => {
  try {
    const obj = JSON.parse(taxonomyJson.value || '{}')
    const cats = obj?.categories || {}
    return Object.keys(cats).map(k => ({ name: k, ...cats[k] }))
  } catch (e) {
    return []
  }
})

// Monaco editor functions
const createEditor = () => {
  if (!editorContainer.value) {
    return
  }

  // Cleanup existing editor
  if (editor) {
    editor.dispose()
  }

  try {
    editor = monaco.editor.create(editorContainer.value, {
      value: taxonomyJson.value || '',
      language: 'json',
      theme: monacoTheme.value,
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

    // Listen for content changes
    editor.onDidChangeModelContent(() => {
      const newContent = editor.getValue()
      taxonomyJson.value = newContent
    })

    // Add keyboard shortcuts
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      saveDraft()
    })

    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.KeyF, () => {
      formatJson()
    })

  } catch (err) {
    console.error('Failed to initialize Monaco Editor:', err)
    error.value = 'Failed to initialize code editor'
  }
}

const formatJson = () => {
  if (!editor) return

  try {
    const content = editor.getValue()
    const parsed = JSON.parse(content)
    const formatted = JSON.stringify(parsed, null, 2)

    // Update editor content
    editor.setValue(formatted)
    taxonomyJson.value = formatted

    showSuccess('JSON formatted successfully!')
  } catch (err) {
    error.value = 'Invalid JSON format. Cannot format the content.'
    setTimeout(() => {
      error.value = ''
    }, 3000)
  }
}

const cleanup = () => {
  if (editor) {
    editor.dispose()
    editor = null
  }
}

function resetToExample() {
  taxonomyJson.value = EXAMPLE
  if (editor) {
    editor.setValue(EXAMPLE)
  }
  error.value = ''
  validMessage.value = ''
  showSuccess('Reset to example taxonomy')
}

function validateJson() {
  error.value = ''
  validMessage.value = ''
  try {
    const obj = JSON.parse(taxonomyJson.value)
    if (!obj || typeof obj !== 'object') throw new Error('Top-level JSON must be an object')
    if (!obj.categories || typeof obj.categories !== 'object') throw new Error("Missing 'categories' object")
    // Basic schema checks per category
    for (const [name, cfg] of Object.entries(obj.categories)) {
      if (typeof name !== 'string' || !name.trim()) throw new Error('Category name must be a non-empty string')
      if (typeof cfg !== 'object') throw new Error(`Category '${name}' must be an object`)
      if (cfg.synonyms && !Array.isArray(cfg.synonyms)) throw new Error(`Category '${name}': 'synonyms' must be an array`)
      if (cfg.regex && !Array.isArray(cfg.regex)) throw new Error(`Category '${name}': 'regex' must be an array`)
      // quick regex validation
      if (Array.isArray(cfg.regex)) {
        for (const p of cfg.regex) {
          try { new RegExp(p) } catch { throw new Error(`Category '${name}': invalid regex '${p}'`) }
        }
      }
    }
    validMessage.value = 'Looks valid ✅'
  } catch (e) {
    error.value = e.message || 'Invalid JSON'
  }
}

function saveDraft() {
  try {
    localStorage.setItem(LOCAL_KEY, taxonomyJson.value)
    showSuccess('Draft saved locally')
  } catch (e) {
    showError('Failed to save draft')
  }
}

function runTest() {
  testResult.value = []
  try {
    const obj = JSON.parse(taxonomyJson.value)
    const text = (testQuery.value || '').toLowerCase()
    const results = new Set()
    for (const [name, cfg] of Object.entries(obj.categories || {})) {
      const syn = (cfg.synonyms || []).map((s) => (s || '').toLowerCase())
      if (syn.some(s => s && text.includes(s))) results.add(name)
      for (const pat of cfg.regex || []) {
        try { if (new RegExp(pat).test(text)) results.add(name) } catch { /* ignore */ }
      }
    }
    testResult.value = Array.from(results)
  } catch (e) {
    error.value = 'Enter valid JSON before testing'
  }
}

onUnmounted(() => {
  cleanup()
})
</script>

<style scoped>
.taxonomy-settings { max-width: 1200px; }
.preview-item { 
  padding: 16px 0; 
  border-bottom: 1px solid rgba(var(--v-theme-outline), 0.12); 
}
.preview-item:last-child {
  border-bottom: none;
}
.item-title { 
  font-weight: 600; 
  margin-bottom: 8px; 
  display: flex; 
  align-items: center; 
  color: rgb(var(--v-theme-on-surface));
}
.item-line { 
  font-size: 0.875rem; 
  margin-bottom: 4px;
  color: rgba(var(--v-theme-on-surface), 0.8);
}
.item-line .label { 
  color: rgba(var(--v-theme-on-surface), 0.6); 
  margin-right: 8px; 
  font-weight: 500;
}

/* Monaco Editor Styles */
.editor-container {
  border: 2px solid rgba(var(--v-theme-primary), 0.12);
  transition: all 0.3s ease;
  background: rgb(var(--v-theme-surface));
}

.editor-container:hover {
  border-color: rgba(var(--v-theme-primary), 0.24);
}

/* Monaco Editor theme integration */
:deep(.monaco-editor) {
  border-radius: 8px;
  background: rgb(var(--v-theme-surface)) !important;
}

/* Light theme adjustments */
:deep(.monaco-editor.vs) {
  background: rgb(var(--v-theme-surface)) !important;
}

:deep(.monaco-editor.vs .margin) {
  background: rgb(var(--v-theme-surface)) !important;
}

:deep(.monaco-editor.vs .monaco-editor-background) {
  background: rgb(var(--v-theme-surface)) !important;
}

/* Dark theme adjustments */
:deep(.monaco-editor.vs-dark) {
  background: rgb(var(--v-theme-surface)) !important;
}

:deep(.monaco-editor.vs-dark .margin) {
  background: rgb(var(--v-theme-surface)) !important;
}

:deep(.monaco-editor.vs-dark .monaco-editor-background) {
  background: rgb(var(--v-theme-surface)) !important;
}

/* Ensure consistent scrollbar styling */
:deep(.monaco-scrollable-element > .scrollbar > .slider) {
  background: rgba(var(--v-theme-on-surface), 0.2);
}

:deep(.monaco-scrollable-element > .scrollbar > .slider:hover) {
  background: rgba(var(--v-theme-on-surface), 0.4);
}
</style>
