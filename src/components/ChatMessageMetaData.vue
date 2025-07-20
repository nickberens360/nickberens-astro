<template>
  <div>
    <!-- Images (only show after typing is complete) -->
    <ChatImageGallery
      v-if="message.images && message.images.length && !message.isTyping"
      :images="message.images"
      @image-click="$emit('image-click', $event)"
    />

    <!-- Model indicator for bot messages -->
    <ChatModelIndicator
      v-if="message.model && !message.isTyping"
      :model="message.model"
    />

    <!-- Follow-up questions (only show after typing is complete) -->
    <ChatFollowupQuestions
      v-if="shouldShowFollowups"
      :questions="message.followup_questions"
      @followup-click="$emit('followup-click', $event)"
    />
  </div>
</template>

<script>
import { computed } from 'vue';
import ChatImageGallery from './ChatImageGallery.vue';
import ChatModelIndicator from './ChatModelIndicator.vue';
import ChatFollowupQuestions from './ChatFollowupQuestions.vue';

export default {
  components: {
    ChatImageGallery,
    ChatModelIndicator,
    ChatFollowupQuestions
  },
  props: {
    message: {
      type: Object,
      required: true
    }
  },
  emits: ['image-click', 'followup-click'],
  setup(props) {
    const shouldShowFollowups = computed(() => {
      return props.message.followup_questions &&
        props.message.followup_questions.length &&
        props.message.sender === 'bot' &&
        !props.message.isTyping &&
        false; // Currently disabled in original code
    });

    return {
      shouldShowFollowups
    };
  }
};
</script>