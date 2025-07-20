<template>
  <div class="input-form">
    <div class="input-container">
      <ChatMessageInput
        :model-value="userInput"
        :placeholder="inputPlaceholder"
        :disabled="isLoading && !hasTypingMessage"
        @update:model-value="$emit('update:userInput', $event)"
        @send="$emit('send-message')"
      />
      <ChatInputControls
        :selected-model="selectedModel"
        :is-loading="isLoading"
        :has-typing-message="hasTypingMessage"
        :show-retry="showRetry"
        @update:selectedModel="$emit('update:selectedModel', $event)"
        @send="$emit('send-message')"
        @stop="$emit('stop-action')"
      />
    </div>
  </div>
</template>

<script>
import { computed } from 'vue';
import ChatMessageInput from './ChatMessageInput.vue';
import ChatInputControls from './ChatInputControls.vue';

export default {
  components: {
    ChatMessageInput,
    ChatInputControls
  },
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
    }
  },
  emits: [
    'update:userInput',
    'update:selectedModel',
    'send-message',
    'stop-action'
  ],
  setup(props) {
    const inputPlaceholder = computed(() => {
      return props.lastStoppedPrompt && !props.userInput.trim()
        ? 'Press Enter to retry stopped response...'
        : 'Ask about Nick\'s skills, projects, etc...';
    });

    const showRetry = computed(() => {
      // Show retry when we have a stopped prompt AND the input is empty
      return Boolean(props.lastStoppedPrompt && !props.userInput.trim());
    });

    return {
      inputPlaceholder,
      showRetry
    };
  }
};
</script>

<style scoped>
.input-form {
  display: flex;
  padding: 0 1rem 1rem;
}

.input-container {
  box-shadow: 0 -8px 20px 10px rgba(26, 26, 26, .9);
  width: 100%;
  border: 1px solid #afafaf;
  /*background-color: rgba(17, 17, 17, 0.73);*/
  color: #f9fafb;
  border-radius: 8px;
  padding: 0.5rem;
  max-width: 800px;
  margin: 0 auto;
}

@media (max-width: 768px) {
  .input-form {
    padding: 0.5rem;
  }
}
</style>