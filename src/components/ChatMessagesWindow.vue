<template>
  <div
    class="messages-window"
    ref="messagesWindow"
  >
    <div class="messages-content">
      <ChatBotWelcome
        v-if="messages.length === 0"
        :theme="theme"
        @select-prompt="$emit('prompt-select', $event)"
      />
      <ChatMessageItem
        v-for="(message, index) in messages"
        :key="index"
        :message="message"
        :message-index="index"
        @image-click="$emit('image-click', $event)"
        @followup-click="$emit('followup-click', $event)"
      />
      <ChatLoadingIndicator v-if="isLoading && !hasTypingMessage" />
    </div>
  </div>
</template>

<script>
import { ref, nextTick, watch } from 'vue';
import { useScrollToBottom } from '../composables/useScrollToBottom.js';
import ChatBotWelcome from './ChatBotWelcome.vue';
import ChatMessageItem from './ChatMessageItem.vue';
import ChatLoadingIndicator from './ChatLoadingIndicator.vue';

export default {
  components: {
    ChatBotWelcome,
    ChatMessageItem,
    ChatLoadingIndicator
  },
  props: {
    messages: {
      type: Array,
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
    theme: {
      type: String,
      default: 'dark'
    }
  },
  emits: ['prompt-select', 'image-click', 'followup-click'],
  setup(props) {
    const messagesWindow = ref(null);
    const { scrollToBottom } = useScrollToBottom(messagesWindow);

    watch(() => props.messages, () => {
      scrollToBottom();
    }, { deep: true });

    return {
      messagesWindow
    };
  }
};
</script>

<style scoped>
.messages-window {
  padding: 1rem;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.messages-content {
  max-width: 800px;
  width: 100%;
  margin: 0 auto;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

@media (max-width: 768px) {
  .messages-window {
    padding: 0.5rem;
  }
}
</style>