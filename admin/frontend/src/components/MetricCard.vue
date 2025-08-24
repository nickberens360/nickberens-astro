<template>
  <v-card
    :loading="loading"
    class="metric-card"
    :class="{ 'cursor-pointer': clickable }"
    @click="handleClick"
    :key="`metric-${title}-${value}-${loading}`"
  >
    <v-card-text>
      <div class="d-flex align-center justify-space-between mb-2">
        <div class="text-caption text-medium-emphasis">
          {{ title }}
        </div>
        <v-icon
          v-if="icon"
          :color="iconColor"
          size="small"
        >
          {{ icon }}
        </v-icon>
      </div>

      <div class="d-flex align-center justify-space-between">
        <div>
          <div
            class="text-h4 font-weight-bold"
            :class="[`text-${color}`]"
          >
            <span v-if="typeof value === 'number'">
              <CountUp
                :end-val="value"
                :duration="1.5"
              />{{ unit }}
            </span>
            <span v-else>{{ value }}{{ unit }}</span>
          </div>

          <div
            v-if="subtitle"
            class="text-caption text-medium-emphasis mt-1"
          >
            {{ subtitle }}
          </div>
        </div>

        <div
          v-if="change !== undefined"
          class="text-right"
        >
          <v-chip
            :color="getTrendColor(change, inverse)"
            size="small"
            variant="flat"
            class="mb-1"
          >
            <v-icon
              :icon="getTrendIcon(change)"
              start
              size="x-small"
            />
            {{ formatChange(change) }}
          </v-chip>
          
          <div
            v-if="changeLabel"
            class="text-caption text-medium-emphasis"
          >
            {{ changeLabel }}
          </div>
        </div>
      </div>

      <v-progress-linear
        v-if="showProgress && progressValue !== undefined"
        :model-value="progressValue"
        :color="progressColor || color"
        class="mt-3"
        height="4"
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
</script>

<style scoped>
.metric-card {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.metric-card.cursor-pointer:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.metric-card .v-card-text {
  padding: 20px;
}
</style>