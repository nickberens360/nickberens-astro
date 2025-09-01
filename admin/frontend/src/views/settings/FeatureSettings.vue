<template>
  <div>
    <v-card elevation="2">
      <v-card-title class="text-h6 font-weight-bold pa-6">Feature Flags</v-card-title>
      <v-card-text class="pa-6">
        <v-row v-if="featureFlags && Object.keys(featureFlags).length > 0">
          <v-col cols="12" md="6" lg="4" v-for="(value, key) in featureFlags" :key="key">
            <v-switch
              :model-value="value"
              @update:model-value="updateFeatureFlag(key, $event)"
              :label="String(key)
                .split('_')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ')"
              color="primary"
              inset
              hide-details
              class="mb-2"
            />
          </v-col>
        </v-row>
        
        <!-- Show if no feature flags -->
        <v-alert
          v-else
          type="info"
          variant="tonal"
        >
          No feature flags available
        </v-alert>
      </v-card-text>
      
      <!-- Save button -->
      <v-card-actions class="pa-6 pt-0">
        <v-spacer />
        <v-btn
          color="primary"
          variant="elevated"
          @click="saveFeatureFlags"
          prepend-icon="$check"
        >
          Save Changes
        </v-btn>
      </v-card-actions>
    </v-card>
  </div>
</template>

<script>
export default {
  name: 'FeatureSettings',
  props: {
    featureFlags: {
      type: Object,
      default: () => ({})
    }
  },
  emits: ['save-feature-flags'],
  methods: {
    updateFeatureFlag(key, value) {
      console.log('FeatureSettings: Updating feature flag', key, 'to', value)
      // Create a copy of the featureFlags and update it
      const updatedFlags = { ...this.featureFlags }
      updatedFlags[key] = value
      this.$emit('save-feature-flags', updatedFlags)
    },
    saveFeatureFlags() {
      console.log('FeatureSettings: Saving feature flags', this.featureFlags)
      this.$emit('save-feature-flags', this.featureFlags)
    }
  }
}
</script>
