<template>
  <div class="input-form">
    <div class="input-container">
      <!-- ChatMessageInput functionality -->
      <input
        :value="userInput"
        @input="$emit('update:userInput', $event.target.value)"
        @keyup.enter="$emit('send-message')"
        :placeholder="inputPlaceholder"
        class="message-input"
        :disabled="hasTypingMessage || backendStatus !== 'online'"
        aria-label="Chat message input"
        :aria-describedby="hasTypingMessage ? 'typing-status' : null"
      />

      <div class="d-flex justify-between items-center w-full pt-2">
        <!-- ChatModelSelector functionality -->
        <div class="model-selector-bar">
          <div class="model-selector-container">
            <select
              :value="selectedModel"
              @change="$emit('update:selectedModel', $event.target.value)"
              class="model-selector"
              :disabled="hasTypingMessage || backendStatus !== 'online'"
            >
              <option value="claude">Claude (Recommended)</option>
              <option value="gemini">Gemini (Fast)</option>
            </select>
          </div>
        </div>

        <!-- ChatSendButton functionality -->
        <button
          @click="handleSendButtonClick"
          class="send-button"
          :class="{
            'stop-mode': isInStopMode,
            'retry-mode': isInRetryMode && !isInStopMode
          }"
          :disabled="false"
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
      </div>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue';

export default {
  name: 'ChatInput',
  props: {
    userInput: {
      type: String,
      required: true
    },
    selectedModel: {
      type: String,
      required: true
    },
    isLoading: {
      type: Boolean,
      default: false
    },
    hasTypingMessage: {
      type: Boolean,
      default: false
    },
    lastStoppedPrompt: {
      type: String,
      default: ''
    },
    backendStatus: {
      type: String,
      default: 'checking'
    }
  },
  emits: [
    'update:userInput',
    'update:selectedModel',
    'send-message',
    'stop-action'
  ],
  setup(props, { emit }) {
    // Input placeholder logic
    const inputPlaceholder = computed(() => {
      // First check backend status
      if (props.backendStatus !== 'online') {
        switch (props.backendStatus) {
          case 'checking':
            return '🔄 Checking backend status...';
          case 'building':
            return '⚠️ Backend building, please wait...';
          case 'initializing':
            return '🔄 Backend initializing, please wait...';
          case 'offline':
            return '❌ Backend offline, please try again later';
          default:
            return 'Backend not ready...';
        }
      }

      // If backend is online, show normal placeholders
      return props.lastStoppedPrompt && !props.userInput.trim()
        ? 'Press Enter to retry stopped response...'
        : 'Ask about Nick\'s skills, projects, etc...';
    });

    // Send button state logic
    const isInStopMode = computed(() => {
      return props.isLoading || props.hasTypingMessage;
    });

    const isInRetryMode = computed(() => {
      // Show retry when we have a stopped prompt AND the input is empty
      // AND we're not currently typing (loading is OK - we want stop during loading)
      return Boolean(
        props.lastStoppedPrompt &&
        !props.userInput.trim() &&
        !props.hasTypingMessage
      );
    });

    const buttonTitle = computed(() => {
      if (isInStopMode.value) {
        return props.isLoading ? 'Stop loading' : 'Stop typing';
      } else if (isInRetryMode.value) {
        return 'Retry stopped message';
      } else {
        return 'Send message';
      }
    });

    const handleSendButtonClick = () => {
      if (isInStopMode.value) {
        // If we're loading or typing, emit stop
        emit('stop-action');
      } else {
        // For both retry and normal send, emit 'send-message'
        emit('send-message');
      }
    };

    return {
      inputPlaceholder,
      isInStopMode,
      isInRetryMode,
      buttonTitle,
      handleSendButtonClick
    };
  }
};
</script>

<style scoped>
/* Input form styles */
.input-form {
  display: flex;
  padding: 0 1rem 1rem;
}

.input-container {
  box-shadow: 0 -8px 20px 10px rgba(26, 26, 26, .9);
  width: 100%;
  border: 1px solid #afafaf;
  color: #f9fafb;
  border-radius: 8px;
  padding: 0.5rem;
  max-width: 800px;
  margin: 0 auto;
}

/* Message input styles */
.message-input {
  flex-grow: 0;
  padding: 0.75rem;
  font-size: 1rem;
  border: none !important;
  background: none !important;
  color: #f9fafb;
  width: 100%;
}

.message-input::placeholder {
  color: #999999;
}

.message-input:focus {
  outline: none;
  border-color: #555555;
  box-shadow: none !important;
}

/* Input controls styles */
.d-flex {
  display: flex;
}

.justify-between {
  justify-content: space-between;
}

.items-center {
  align-items: center;
}

.w-full {
  width: 100%;
}

.pt-2 {
  padding-top: 0.5rem;
}

/* Model selector styles */
.model-selector-bar {
  padding-left: .5rem;
}

.model-selector-container {
  display: flex;
  align-items: center;
  gap: 1rem;
  max-width: 800px;
  margin: 0 auto;
}

.model-selector {
  background-color: #222222;
  border: 1px solid #444444;
  border-radius: 6px;
  color: #b8ccfb;
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
  cursor: pointer;
}

.model-selector:focus {
  outline: none;
}

.model-selector:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Send button styles */
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

/* Responsive styles */

</style>
