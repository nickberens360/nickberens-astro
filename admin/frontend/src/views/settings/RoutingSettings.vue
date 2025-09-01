<template>
  <div>
    <v-card elevation="2">
      <v-card-title class="text-h6 font-weight-bold pa-6">Query Routing Settings</v-card-title>
      <v-card-text class="pa-6">
        <v-row>
          <v-col cols="12" md="6">
            <v-switch
              v-model="routingSettings.enable_smart_routing"
              label="Enable Smart Routing"
              color="primary"
              inset
              @change="saveRoutingSettings"
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-switch
              v-model="routingSettings.enable_fuzzy_matching"
              label="Enable Fuzzy Matching"
              color="primary"
              inset
              @change="saveRoutingSettings"
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-slider
              v-model="routingSettings.similarity_threshold"
              label="Similarity Threshold"
              :min="0.0"
              :max="1.0"
              :step="0.1"
              thumb-label="always"
              @end="saveRoutingSettings"
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-text-field
              v-model.number="routingSettings.max_search_results"
              label="Max Search Results"
              type="number"
              variant="outlined"
              :min="1"
              :max="100"
              @blur="saveRoutingSettings"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </div>
</template>

<script>
export default {
  name: 'RoutingSettings',
  props: {
    routingSettings: Object
  },
  emits: ['save-routing-settings'],
  methods: {
    saveRoutingSettings() {
      this.$emit('save-routing-settings')
    }
  }
}
</script>