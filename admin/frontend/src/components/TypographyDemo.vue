<template>
  <div class="typography-demo">
    <v-container>
      <!-- Header -->
      <div class="mb-8">
        <h1 class="typography-display-2 mb-4">Typography System Demo</h1>
        <p class="typography-body-1">
          Comprehensive typography system using Inter for UI/display text and JetBrains Mono for code/technical content.
        </p>
      </div>

      <v-row>
        <!-- Display Typography -->
        <v-col cols="12" md="6">
          <v-card class="pa-6 mb-6">
            <v-card-title class="typography-h4 pb-4">Display Typography</v-card-title>
            
            <div class="mb-4">
              <div class="typography-display-1 mb-2">Display 1</div>
              <div class="typography-caption text-medium-emphasis">48px, Bold, Inter</div>
            </div>
            
            <div class="mb-4">
              <div class="typography-display-2 mb-2">Display 2</div>
              <div class="typography-caption text-medium-emphasis">36px, Bold, Inter</div>
            </div>
            
            <div class="mb-4">
              <div class="typography-display-3 mb-2">Display 3</div>
              <div class="typography-caption text-medium-emphasis">30px, Bold, Inter</div>
            </div>
          </v-card>
        </v-col>

        <!-- Headings -->
        <v-col cols="12" md="6">
          <v-card class="pa-6 mb-6">
            <v-card-title class="typography-h4 pb-4">Headings</v-card-title>
            
            <div class="mb-3">
              <div class="typography-h1 mb-1">Heading 1</div>
              <div class="typography-caption text-medium-emphasis">30px, Bold, Inter</div>
            </div>
            
            <div class="mb-3">
              <div class="typography-h2 mb-1">Heading 2</div>
              <div class="typography-caption text-medium-emphasis">24px, Semibold, Inter</div>
            </div>
            
            <div class="mb-3">
              <div class="typography-h3 mb-1">Heading 3</div>
              <div class="typography-caption text-medium-emphasis">20px, Semibold, Inter</div>
            </div>
            
            <div class="mb-3">
              <div class="typography-h4 mb-1">Heading 4</div>
              <div class="typography-caption text-medium-emphasis">18px, Medium, Inter</div>
            </div>
            
            <div class="mb-3">
              <div class="typography-h5 mb-1">Heading 5</div>
              <div class="typography-caption text-medium-emphasis">16px, Medium, Inter</div>
            </div>
            
            <div class="mb-3">
              <div class="typography-h6 mb-1">HEADING 6</div>
              <div class="typography-caption text-medium-emphasis">14px, Medium, Inter</div>
            </div>
          </v-card>
        </v-col>

        <!-- Body Typography -->
        <v-col cols="12" md="6">
          <v-card class="pa-6 mb-6">
            <v-card-title class="typography-h4 pb-4">Body Typography</v-card-title>
            
            <div class="mb-4">
              <div class="typography-body-1 mb-2">
                Body 1: This is regular body text with comfortable line height. 
                Perfect for paragraphs and longer text content.
              </div>
              <div class="typography-caption text-medium-emphasis">16px, Regular, Inter</div>
            </div>
            
            <div class="mb-4">
              <div class="typography-body-2 mb-2">
                Body 2: Smaller body text for secondary information and compact layouts.
                Good for captions and auxiliary content.
              </div>
              <div class="typography-caption text-medium-emphasis">14px, Regular, Inter</div>
            </div>
            
            <div class="mb-4">
              <div class="typography-caption mb-2">
                Caption: Small text for labels, metadata, and fine print.
              </div>
              <div class="typography-caption text-medium-emphasis">12px, Regular, Inter</div>
            </div>
            
            <div class="mb-4">
              <div class="typography-overline mb-2">OVERLINE TEXT</div>
              <div class="typography-caption text-medium-emphasis">12px, Medium, Inter</div>
            </div>
          </v-card>
        </v-col>

        <!-- Code Typography -->
        <v-col cols="12" md="6">
          <v-card class="pa-6 mb-6">
            <v-card-title class="typography-h4 pb-4">Code & Technical</v-card-title>
            
            <div class="mb-4">
              <div class="mb-2">
                <span>Inline code: </span>
                <span class="typography-code-inline">const message = "Hello World"</span>
              </div>
              <div class="typography-caption text-medium-emphasis">JetBrains Mono, Inline</div>
            </div>
            
            <div class="mb-4">
              <div class="typography-code-block mb-2">
// Code block example
function calculateMetrics(data) {
  return {
    total: data.length,
    average: data.reduce((a, b) => a + b, 0) / data.length
  };
}
              </div>
              <div class="typography-caption text-medium-emphasis">JetBrains Mono, Block</div>
            </div>
            
            <div class="mb-4">
              <div class="typography-technical mb-2">
                Technical text: API endpoint /api/v1/queries?limit=25&offset=0
              </div>
              <div class="typography-caption text-medium-emphasis">JetBrains Mono, Technical</div>
            </div>
          </v-card>
        </v-col>

        <!-- Admin Dashboard Specific -->
        <v-col cols="12">
          <v-card class="pa-6 mb-6">
            <v-card-title class="typography-h4 pb-4">Admin Dashboard Styles</v-card-title>
            
            <v-row>
              <v-col cols="12" sm="6" md="3">
                <div class="text-center">
                  <div class="metric-value text-primary">1,247</div>
                  <div class="metric-label">Total Queries</div>
                </div>
              </v-col>
              
              <v-col cols="12" sm="6" md="3">
                <div class="text-center">
                  <div class="metric-value text-success">98.2%</div>
                  <div class="metric-label">Success Rate</div>
                </div>
              </v-col>
              
              <v-col cols="12" sm="6" md="3">
                <div class="text-center">
                  <div class="metric-value text-info">245ms</div>
                  <div class="metric-label">Avg Response Time</div>
                </div>
              </v-col>
              
              <v-col cols="12" sm="6" md="3">
                <div class="text-center">
                  <div class="metric-value text-warning">42</div>
                  <div class="metric-label">Active Sessions</div>
                </div>
              </v-col>
            </v-row>
            
            <v-divider class="my-6"></v-divider>
            
            <div class="mb-4">
              <div class="dashboard-section-title mb-3">Recent Query Examples</div>
              
              <div class="mb-3">
                <div class="query-text bg-surface-variant pa-3 rounded mb-2">
                  What is Nick's experience with Vue.js development?
                </div>
                <div class="response-text">
                  Based on the knowledge base, Nick has extensive experience with Vue.js, 
                  including Vue 3 with Composition API, Vuetify, and state management with Pinia.
                </div>
              </div>
              
              <div class="mb-3">
                <div class="query-text bg-surface-variant pa-3 rounded mb-2">
                  How can I implement reactive forms in Vue 3?
                </div>
                <div class="response-text">
                  You can implement reactive forms using Vue 3's ref() and reactive() 
                  for form state management, combined with computed properties for validation.
                </div>
              </div>
            </div>
          </v-card>
        </v-col>

        <!-- Font Utilities -->
        <v-col cols="12" md="6">
          <v-card class="pa-6 mb-6">
            <v-card-title class="typography-h4 pb-4">Font Utilities</v-card-title>
            
            <div class="mb-3">
              <div class="font-display typography-body-1 mb-1">Display Font Family</div>
              <div class="typography-caption text-medium-emphasis">.font-display</div>
            </div>
            
            <div class="mb-3">
              <div class="font-body typography-body-1 mb-1">Body Font Family</div>
              <div class="typography-caption text-medium-emphasis">.font-body</div>
            </div>
            
            <div class="mb-3">
              <div class="font-mono typography-body-1 mb-1">Monospace Font Family</div>
              <div class="typography-caption text-medium-emphasis">.font-mono</div>
            </div>
            
            <v-divider class="my-4"></v-divider>
            
            <div class="mb-2">
              <span class="font-light">Light</span> ·
              <span class="font-regular">Regular</span> ·
              <span class="font-medium">Medium</span> ·
              <span class="font-semibold">Semibold</span> ·
              <span class="font-bold">Bold</span> ·
              <span class="font-extrabold">Extra Bold</span>
            </div>
            <div class="typography-caption text-medium-emphasis">Font Weight Utilities</div>
          </v-card>
        </v-col>

        <!-- Letter Spacing -->
        <v-col cols="12" md="6">
          <v-card class="pa-6 mb-6">
            <v-card-title class="typography-h4 pb-4">Letter Spacing</v-card-title>
            
            <div class="mb-3">
              <div class="tracking-tighter typography-body-1 mb-1">Tighter Letter Spacing</div>
              <div class="typography-caption text-medium-emphasis">.tracking-tighter</div>
            </div>
            
            <div class="mb-3">
              <div class="tracking-tight typography-body-1 mb-1">Tight Letter Spacing</div>
              <div class="typography-caption text-medium-emphasis">.tracking-tight</div>
            </div>
            
            <div class="mb-3">
              <div class="tracking-normal typography-body-1 mb-1">Normal Letter Spacing</div>
              <div class="typography-caption text-medium-emphasis">.tracking-normal</div>
            </div>
            
            <div class="mb-3">
              <div class="tracking-wide typography-body-1 mb-1">Wide Letter Spacing</div>
              <div class="typography-caption text-medium-emphasis">.tracking-wide</div>
            </div>
            
            <div class="mb-3">
              <div class="tracking-wider typography-body-1 mb-1">Wider Letter Spacing</div>
              <div class="typography-caption text-medium-emphasis">.tracking-wider</div>
            </div>
            
            <div class="mb-3">
              <div class="tracking-widest typography-body-1 mb-1">WIDEST LETTER SPACING</div>
              <div class="typography-caption text-medium-emphasis">.tracking-widest</div>
            </div>
          </v-card>
        </v-col>
      </v-row>

      <!-- Vuetify Component Integration -->
      <v-row>
        <v-col cols="12">
          <v-card class="pa-6">
            <v-card-title class="typography-h4 pb-4">Vuetify Component Integration</v-card-title>
            
            <v-row>
              <v-col cols="12" md="4">
                <h5 class="typography-h5 mb-3">Buttons</h5>
                <div class="d-flex flex-column ga-2">
                  <v-btn color="primary" block>Primary Button</v-btn>
                  <v-btn color="secondary" variant="outlined" block>Secondary Button</v-btn>
                  <v-btn color="success" variant="tonal" block>Success Button</v-btn>
                </div>
              </v-col>
              
              <v-col cols="12" md="4">
                <h5 class="typography-h5 mb-3">Form Fields</h5>
                <div class="d-flex flex-column ga-2">
                  <v-text-field
                    label="Email Address"
                    placeholder="Enter your email"
                    variant="outlined"
                  />
                  <v-select
                    label="Select Option"
                    :items="['Option 1', 'Option 2', 'Option 3']"
                    variant="outlined"
                  />
                </div>
              </v-col>
              
              <v-col cols="12" md="4">
                <h5 class="typography-h5 mb-3">Chips & Labels</h5>
                <div class="d-flex flex-wrap ga-2 mb-3">
                  <v-chip color="primary" size="small">Vue.js</v-chip>
                  <v-chip color="secondary" size="small">TypeScript</v-chip>
                  <v-chip color="success" size="small">Vuetify</v-chip>
                  <v-chip color="info" size="small">JavaScript</v-chip>
                </div>
                
                <v-list density="compact" class="bg-transparent">
                  <v-list-item>
                    <v-list-item-title>Primary List Item</v-list-item-title>
                    <v-list-item-subtitle>Secondary text</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <v-list-item-title>Another List Item</v-list-item-title>
                    <v-list-item-subtitle>With subtitle</v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-col>
            </v-row>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
// No reactive data needed for this demo component
</script>

<style scoped>
.typography-demo {
  /* Additional styles if needed */
}

/* Ensure proper spacing in demo */
.v-card-title {
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}
</style>