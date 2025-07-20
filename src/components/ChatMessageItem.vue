<template>
  <div :class="['message', message.sender]">
    <div class="message-bubble">
      <ChatUserMessage
        v-if="message.sender === 'user'"
        :message="message"
      />
      <ChatBotMessage
        v-else
        :message="message"
        :message-index="messageIndex"
        @image-click="$emit('image-click', $event)"
        @followup-click="$emit('followup-click', $event)"
      />
    </div>
  </div>
</template>

<script>
import ChatUserMessage from './ChatUserMessage.vue';
import ChatBotMessage from './ChatBotMessage.vue';

export default {
  components: {
    ChatUserMessage,
    ChatBotMessage
  },
  props: {
    message: {
      type: Object,
      required: true
    },
    messageIndex: {
      type: Number,
      required: true
    }
  },
  emits: ['image-click', 'followup-click']
};
</script>

<style scoped>
.message {
  display: flex;
}

.message-bubble {
  padding: 0.75rem 1.25rem;
  border-radius: 18px;
  max-width: 100%;
  line-height: 1.5;
}

.message-bubble p {
  margin: 0;
}

/* User messages */
.user {
  justify-content: flex-end;
}

.user .message-bubble {
  background-color: #1c2539;
  color: white;
  border-bottom-right-radius: 4px;
  font-size: 0.95rem;
}

/* Bot messages */
.bot {
  justify-content: flex-start;
}

.bot .message-bubble {
  background-color: transparent;
  color: #f9fafb;
  border-bottom-left-radius: 4px;
}
</style>