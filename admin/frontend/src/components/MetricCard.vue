<template>
  <v-card
    :loading="loading"
    class="ds-card metric-card modern-card"
    :class="{ 'cursor-pointer': clickable }"
    @click="handleClick"
    :key="`metric-${title}-${value}-${loading}`"
  >
    <v-card-text class="ds-p-6">
      <!-- Header with Icon and Title -->
      <div class="d-flex align-center justify-space-between ds-mb-4">
        <div class="ds-text-base ds-font-medium text-medium-emphasis">
          {{ title }}
        </div>
        <v-avatar
          v-if="icon"
          size="40"
          :color="getIconBackground(color)"
          variant="flat"
        >
          <v-icon
            :color="color"
            size="20"
          >
            {{ icon }}
          </v-icon>
        </v-avatar>
      </div>

      <!-- Large Value Display -->
      <div class="d-flex align-center justify-space-between">
        <div class="flex-grow-1">
          <div class="metric-value ds-text-3xl ds-font-bold text-high-emphasis">
            <span v-if="typeof value === 'number'">
              <CountUp
                :end-val="value"
                :duration="1.5"
              />{{ unit }}
            </span>
            <span v-else>{{ value }}{{ unit }}</span>
          </div>

          <!-- Change Indicator -->
          <div
            v-if="change !== undefined"
            class="d-flex align-center ds-mt-2"
          >
            <v-icon
              :color="getTrendColor(change, inverse)"
              :icon="getTrendIcon(change)"
              size="16"
              class="mr-1"
            />
            <span
              class="text-sm font-weight-medium"
              :class="[`text-${getTrendColor(change, inverse)}`]"
            >
              {{ formatChange(change) }}
            </span>
            <span class="text-caption text-medium-emphasis ml-1">
              vs last month
            </span>
          </div>

          <div
            v-if="subtitle"
            class="text-caption text-medium-emphasis mt-1"
          >
            {{ subtitle }}
          </div>
        </div>
      </div>

      <v-progress-linear
        v-if="showProgress && progressValue !== undefined"
        :model-value="progressValue"
        :color="progressColor || color"
        class="mt-4"
        height="6"
        rounded
      />
    </v-card-text>
  </v-card>
</template>

<script setup>
import { computed, watch } from 'vue'
import { getTrendIcon, getTrendColor, formatNumber } from '@/types/admin'
import CountUp from '@/components/CountUp.vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [Number, String],
    required: true
  },
  unit: {
    type: String,
    default: ''
  },
  subtitle: {
    type: String,
    default: ''
  },
  icon: {
    type: String,
    default: ''
  },
  iconColor: {
    type: String,
    default: 'primary'
  },
  color: {
    type: String,
    default: 'primary'
  },
  change: {
    type: Number,
    default: undefined
  },
  changeLabel: {
    type: String,
    default: 'vs previous'
  },
  inverse: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  clickable: {
    type: Boolean,
    default: false
  },
  showProgress: {
    type: Boolean,
    default: false
  },
  progressValue: {
    type: Number,
    default: undefined
  },
  progressColor: {
    type: String,
    default: ''
  }
})


const emit = defineEmits(['click'])

const handleClick = () => {
  if (props.clickable) {
    emit('click')
  }
}

const formatChange = (change) => {
  if (Math.abs(change) < 0.01) return '0%'
  const sign = change > 0 ? '+' : ''
  return `${sign}${change.toFixed(1)}%`
}

const getIconBackground = (color) => {
  // Return a light background color based on the new modern color scheme
  const colorMap = {
    primary: 'rgba(99, 102, 241, 0.1)', // Modern indigo
    secondary: 'rgba(100, 116, 139, 0.1)', // Slate gray
    info: 'rgba(59, 130, 246, 0.1)', // Blue
    success: 'rgba(16, 185, 129, 0.1)', // Modern green
    warning: 'rgba(245, 158, 11, 0.1)', // Modern amber
    error: 'rgba(239, 68, 68, 0.1)' // Modern red
  }
  return colorMap[color] || 'rgba(99, 102, 241, 0.1)'
}
</script>

<style scoped>
.modern-card {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.modern-card.cursor-pointer:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(var(--v-shadow-key-umbra-opacity), 0.08);
}

.metric-value {
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.text-sm {
  font-size: 0.875rem;
  line-height: 1.25rem;
}

.v-avatar {
  /* Clean avatar without border */
}
</style>