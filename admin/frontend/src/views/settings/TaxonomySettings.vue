<template>
  <div class="taxonomy-settings">
    <v-card elevation="2">
      <v-card-title class="d-flex align-center justify-space-between pa-6">
        <div class="text-h6 font-weight-bold">Search & Taxonomy</div>
        <div class="d-flex align-center gap-2">
          <v-btn variant="tonal" color="secondary" @click="resetToExample" prepend-icon="$undo">
            Reset to Example
          </v-btn>
          <v-btn variant="tonal" color="primary" @click="validateJson" prepend-icon="$check">
            Validate JSON
          </v-btn>
          <v-btn variant="elevated" color="primary" @click="saveDraft" prepend-icon="$save">
            Save Draft (local)
          </v-btn>
        </div>
      </v-card-title>

      <v-card-text class="pa-6">
        <v-alert v-if="error" type="error" variant="tonal" class="mb-4">{{ error }}</v-alert>
        <v-alert v-if="validMessage" type="success" variant="tonal" class="mb-4">{{ validMessage }}</v-alert>

        <div class="grid">
          <div class="col-editor">
            <div class="field-label">Taxonomy JSON</div>
            <v-textarea
              v-model="taxonomyJson"
              variant="outlined"
              rows="18"
              auto-grow
              class="mono"
              :spellcheck="false"
            />

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
          </div>

          <div class="col-preview">
            <v-card variant="text">
              <v-card-title class="text-subtitle-1 font-weight-bold">Live Preview</v-card-title>
              <v-card-text>
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
          </div>
        </div>
      </v-card-text>
    </v-card>
  </div>
  
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useNotifications } from '@/composables/useNotifications'

const { showSuccess, showError } = useNotifications()

const LOCAL_KEY = 'taxonomy_draft_json'
const error = ref('')
const validMessage = ref('')
const taxonomyJson = ref('')
const testQuery = ref('')
const testResult = ref(null)

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

onMounted(() => {
  // Load any previously saved draft from localStorage
  const draft = localStorage.getItem(LOCAL_KEY)
  taxonomyJson.value = draft || EXAMPLE
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

function resetToExample() {
  taxonomyJson.value = EXAMPLE
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
</script>

<style scoped>
.taxonomy-settings { max-width: 1200px; }
.grid { display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 24px; }
.col-editor { min-width: 0; }
.col-preview { min-width: 0; }
.mono :deep(textarea) { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }
.field-label { font-weight: 600; margin-bottom: 8px; }
.preview-item { padding: 12px 0; border-bottom: 1px solid rgba(0,0,0,0.06); }
.item-title { font-weight: 600; margin-bottom: 6px; display: flex; align-items: center; }
.item-line { font-size: 0.9rem; }
.item-line .label { color: rgba(var(--v-theme-on-surface), 0.6); margin-right: 6px; }
@media (max-width: 1024px) { .grid { grid-template-columns: 1fr; } }
</style>
