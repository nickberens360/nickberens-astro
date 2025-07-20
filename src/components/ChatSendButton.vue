<template>
  <button
    @click="handleClick"
    class="send-button"
    :class="{ 'stop-mode': hasTypingMessage }"
    :disabled="isDisabled"
  >
    <span v-if="hasTypingMessage" class="stop-content">
      <span class="stop-icon">⏹</span>
      Stop
    </span>
    <span v-else-if="showRetry && !hasTypingMessage">
      Retry
    </span>
    <span v-else>Send</span>
  </button>
</template>

<script>
import { computed } from 'vue';

export default {
  props: {
    hasTypingMessage: {
      type: Boolean,
      default: false
    },
    showRetry: {
      type: Boolean,
      default: false
    },
    disabled: {
      type: Boolean,
      default: false
    }
  },
  emits: ['send', 'stop'],
  setup(props, { emit }) {
    // Button should be disabled when loading AND not typing (original logic)
    const isDisabled = computed(() => {
      return props.disabled;
    });

    const handleClick = () => {
      if (props.hasTypingMessage) {
        emit('stop');
      } else {
        emit('send');
      }
    };

    return {
      isDisabled,
      handleClick
    };
  }
};
</script>

<style scoped>
.send-button {
  margin-left: 1rem;
  padding: 0.65rem 1.5rem;
  border: none;
  background-color: #1c2539;
  color: white;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
  min-width: 80px;
}

.send-button:hover:not(:disabled) {
  background-color: #2b3751;
}

.send-button.stop-mode {
  background-color: #682929;
}

.send-button.stop-mode:hover {
  background-color: #894040;
}

.send-button:disabled {
  background-color: #303b53;
  cursor: not-allowed;
}

.stop-content {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  justify-content: center;
}

.stop-icon {
  font-size: 0.875em;
}

@media (max-width: 768px) {
  .send-button {
    padding: 0.5rem 1rem;
    font-size: 0.875rem;
  }

  .stop-content {
    gap: 0.25rem;
  }

  .stop-icon {
    font-size: 0.75em;
  }
}
</style>