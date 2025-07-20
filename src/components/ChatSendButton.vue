<!--suppress ALL -->
<template>
  <button
    @click="handleClick"
    class="send-button"
    :class="{
      'stop-mode': isInStopMode,
      'retry-mode': isInRetryMode && !isInStopMode
    }"
    :disabled="isDisabled"
    :title="buttonTitle"
  >
    <!-- Stop state: when loading or typing (takes priority) -->
    <span v-if="isInStopMode" class="button-content">
      <font-awesome-icon icon="stop" />
    </span>
    <!-- Retry state: when we have a stopped prompt and not loading/typing -->
    <span v-else-if="isInRetryMode" class="button-content">
      <font-awesome-icon icon="rotate-right" />
    </span>
    <!-- Default send state -->
    <span v-else class="button-content">
      <font-awesome-icon icon="arrow-up" />
    </span>
  </button>
</template>

<script>
import { computed } from 'vue';

export default {
  name: 'ChatSendButton',
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
    },
    isLoading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['send', 'stop'],
  setup(props, { emit }) {
    // Determine if we're in stop mode (loading or typing)
    const isInStopMode = computed(() => {
      return props.isLoading || props.hasTypingMessage;
    });

    // Determine if we're in retry mode (have stopped prompt but not typing)
    // Note: We can be in retry mode AND loading at the same time
    const isInRetryMode = computed(() => {
      return props.showRetry && !props.hasTypingMessage;
    });

    // Button should be disabled based on the disabled prop
    const isDisabled = computed(() => {
      return props.disabled;
    });

    // Button title for accessibility
    const buttonTitle = computed(() => {
      if (isInStopMode.value) {
        return props.isLoading ? 'Stop loading' : 'Stop typing';
      } else if (isInRetryMode.value) {
        return 'Retry stopped message';
      } else {
        return 'Send message';
      }
    });

    const handleClick = () => {
      // Don't do anything if disabled
      if (isDisabled.value) {
        return;
      }

      if (isInStopMode.value) {
        // If we're loading or typing, emit stop
        emit('stop');
      } else {
        // For both retry and normal send, emit 'send'
        // The parent component will handle using lastStoppedPrompt if needed
        emit('send');
      }
    };

    return {
      isInStopMode,
      isInRetryMode,
      isDisabled,
      buttonTitle,
      handleClick
    };
  }
};
</script>

<style scoped>
.send-button {
  margin-left: 1rem;
  margin-right: 0.5rem;
  border: none;
  background-color: rgba(87, 115, 174, 0.41);
  color: #9cbcf9;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-button:hover:not(:disabled) {
  background-color: rgba(49, 89, 175, 0.41);
}

.send-button.stop-mode {
  background-color: rgba(248, 128, 128, 0.41);
  color: #fec5c5;
}

.send-button.stop-mode:hover:not(:disabled) {
  background-color: rgba(252, 69, 69, 0.41);
}

.send-button.retry-mode {
  background-color: rgba(245, 204, 140, 0.27);
  color: #f59e0b;
}

.send-button.retry-mode:hover:not(:disabled) {
  background-color: rgba(217, 119, 6, 0.42);
}

.send-button:disabled {
  background-color: #6b7280;
  cursor: not-allowed;
  opacity: 0.5;
}

.button-content {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

/* Add a subtle animation for the stop state */
.send-button.stop-mode .button-content {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

@media (max-width: 768px) {
  .send-button {
    width: 36px;
    height: 36px;
    margin-left: 0.75rem;
    margin-right: 0.25rem;
  }
}
</style>