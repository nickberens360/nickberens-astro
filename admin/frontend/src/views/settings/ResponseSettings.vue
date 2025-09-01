<template>
  <div>
    <v-card elevation="2">
      <v-card-title class="text-h6 font-weight-bold pa-6">Response Generation Settings</v-card-title>
      <v-card-text class="pa-6">
        <v-row>
          <v-col cols="12" md="6">
            <v-text-field
              v-model.number="responseSettings.max_context_length"
              label="Max Context Length"
              type="number"
              variant="outlined"
              :min="100"
              :max="10000"
              @blur="saveResponseSettings"
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-text-field
              v-model.number="responseSettings.max_context_documents"
              label="Max Context Documents"
              type="number"
              variant="outlined"
              :min="1"
              :max="10"
              @blur="saveResponseSettings"
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-slider
              v-model="responseSettings.context_fill_ratio"
              label="Context Fill Ratio"
              :min="0.1"
              :max="1.0"
              :step="0.1"
              thumb-label="always"
              @end="saveResponseSettings"
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-switch
              v-model="responseSettings.enable_caching"
              label="Enable Response Caching"
              color="primary"
              inset
              @change="saveResponseSettings"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </div>
</template>

<script>
export default {
  name: 'ResponseSettings',
  props: {
    responseSettings: Object
  },
  emits: ['save-response-settings'],
  methods: {
    saveResponseSettings() {
      this.$emit('save-response-settings')
    }
  }
}
</script>