<template>
  <div class="bot-message-wrapper">
    <ChatTypingText
      :message="message"
      :message-index="messageIndex"
    />
    <ChatMessageMetadata
      :message="message"
      @image-click="$emit('image-click', $event)"
      @followup-click="$emit('followup-click', $event)"
    />
  </div>
</template>

<script>
import ChatTypingText from './ChatTypingText.vue';
import ChatMessageMetadata from './ChatMessageMetadata.vue';

export default {
  components: {
    ChatTypingText,
    ChatMessageMetadata
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
.bot-message-wrapper {
  width: 100%;
}
</style>