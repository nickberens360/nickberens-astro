<template>
  <div class="d-flex justify-between items-center w-full pt-2">
    <ChatModelSelector
      :selected-model="selectedModel"
      :disabled="hasTypingMessage"
      @update:selected-model="$emit('update:selected-model', $event)"
    />
    <ChatSendButton
      :has-typing-message="hasTypingMessage"
      :show-retry="showRetry"
      :disabled="false"
      :is-loading="isLoading"
      @send="$emit('send')"
      @stop="$emit('stop')"
    />
  </div>
</template>

<script>
import ChatModelSelector from './ChatModelSelector.vue';
import ChatSendButton from './ChatSendButton.vue';

export default {
  name: 'ChatInputControls',
  components: {
    ChatModelSelector,
    ChatSendButton
  },
  props: {
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
    showRetry: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:selected-model', 'send', 'stop']
};
</script>

<style scoped>
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

@media (max-width: 768px) {
  .d-flex {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}
</style>