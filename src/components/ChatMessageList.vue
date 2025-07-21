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
      <!-- Message Items -->
      <div
        v-for="(message, index) in messages"
        :key="index"
        :class="['message', message.sender]"
      >
        <div class="message-bubble">
          <!-- User Message Content -->
          <p v-if="message.sender === 'user'">{{ message.text }}</p>

          <!-- Bot Message Content -->
          <div v-else class="bot-message-wrapper">
            <!-- Typing Text -->
            <div>
              <div v-if="message.text" class="markdown-content-wrapper">
                <span v-html="renderMarkdownWithCursor(message.text, message.isTyping)" class="markdown-content"></span>
              </div>

              <!-- Stopped message indicator -->
              <div v-if="message.wasStopped && !message.isTyping" class="stopped-indicator">
                <span class="stopped-icon">⏹</span>
                You stopped this response
              </div>
            </div>

            <!-- Message Metadata -->
            <div>
              <!-- Images (only show after typing is complete) -->
              <div v-if="message.images && message.images.length && !message.isTyping" class="image-gallery fade-in">
                <img
                  v-for="src in message.images"
                  :key="src"
                  :src="src"
                  alt="Illustration"
                  class="chat-image"
                  @click="$emit('image-click', src)"
                />
              </div>

              <!-- Model indicator for bot messages -->
              <div v-if="message.model && !message.isTyping" class="model-indicator">
                <span class="model-badge">{{ message.model }}</span>
              </div>

              <!-- Follow-up questions (only show after typing is complete) -->
              <div v-if="shouldShowFollowups(message)" class="followup-container fade-in">
                <p class="followup-label">💡 You might also want to ask:</p>
                <div class="followup-buttons">
                  <button
                    v-for="(question, qIndex) in message.followup_questions"
                    :key="qIndex"
                    @click="$emit('followup-click', question)"
                    class="followup-button"
                  >
                    {{ question }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading Indicator -->
      <div v-if="isLoading && !hasTypingMessage" class="message bot">
        <div class="message-bubble">
          <div class="typing-indicator">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, nextTick, watch } from 'vue';
import { useScrollToBottom } from '../composables/useScrollToBottom.js';
import ChatBotWelcome from './ChatBotWelcome.vue';
import { marked } from 'marked';

export default {
  components: {
    ChatBotWelcome
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
    },
    backendStatus: {
      type: String,
      default: 'checking'
    }
  },
  emits: ['prompt-select', 'image-click', 'followup-click'],
  setup(props) {
    const messagesWindow = ref(null);
    const { scrollToBottom } = useScrollToBottom(messagesWindow);

    watch(() => props.messages, () => {
      scrollToBottom();
    }, { deep: true });

    const renderMarkdown = (text) => {
      return marked(text);
    };

    const renderMarkdownWithCursor = (text, isTyping) => {
      const renderedMarkdown = marked(text);
      if (!isTyping) return renderedMarkdown;
      return renderedMarkdown
    };

    const shouldShowFollowups = (message) => {
      return message.followup_questions &&
        message.followup_questions.length &&
        message.sender === 'bot' &&
        !message.isTyping &&
        false; // Currently disabled in original code
    };

    return {
      messagesWindow,
      renderMarkdown,
      renderMarkdownWithCursor,
      shouldShowFollowups
    };
  }
};
</script>

<style scoped>
/* Messages Window Styles */
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

/* Base message styles */
.message {
  display: flex;
}

.message-bubble {
  padding: 0.75rem 1.25rem;
  border-radius: 100px;
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

/* Bot message wrapper */
.bot-message-wrapper {
  width: 100%;
}

/* Markdown content styling */
.markdown-content-wrapper {
  display: inline;
  line-height: 1.6;
}

.markdown-content-wrapper .markdown-content {
  display: inline;
  line-height: inherit;
}

.typing-cursor {
  display: none;
  animation: blink 1s infinite;
  font-weight: bold;
  color: #1c2539;
  font-size: 1em;
  line-height: inherit;
  vertical-align: baseline;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.stopped-indicator {
  margin-top: 0.5rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  color: #9ca3af;
  font-style: italic;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  opacity: 0.7;
}

.stopped-icon {
  font-size: 0.6875em;
  color: #9ca3af;
}

/* Override markdown content styling for inline display */
.markdown-content-wrapper :deep(.markdown-content) {
  display: inline;
}

.markdown-content-wrapper :deep(.markdown-content p) {
  display: inline;
  margin: 0;
}

.markdown-content-wrapper :deep(.markdown-content h1),
.markdown-content-wrapper :deep(.markdown-content h2),
.markdown-content-wrapper :deep(.markdown-content h3) {
  display: inline;
  font-size: inherit;
  margin: 0;
  font-weight: bold;
}

/* Markdown content styling */
:deep(.markdown-content) {
  font-size: .90rem;
  line-height: 1.6;
}

:deep(.markdown-content h1) {
  font-size: 1.5rem;
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}

:deep(.markdown-content h2) {
  font-size: 1.25rem;
  margin-top: 0.75rem;
  margin-bottom: 0.5rem;
}

:deep(.markdown-content h3) {
  font-size: 1.1rem;
  margin-top: 0.75rem;
  margin-bottom: 0.5rem;
}

:deep(.markdown-content p) {
  margin-bottom: 0.75rem;
}

:deep(.markdown-content ul, .markdown-content ol) {
  padding-left: 1.5rem;
  margin-bottom: 0.75rem;
}

:deep(.markdown-content li) {
  margin-bottom: 0.25rem;
}

:deep(.markdown-content code) {
  background-color: rgba(255, 255, 255, 0.1);
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  font-family: monospace;
}

:deep(.markdown-content pre) {
  background-color: rgba(255, 255, 255, 0.1);
  padding: 0.75rem;
  border-radius: 5px;
  overflow-x: auto;
  margin-bottom: 0.75rem;
}

:deep(.markdown-content a) {
  color: #60a5fa;
  text-decoration: underline;
}

/* Image Gallery */
.fade-in {
  opacity: 0;
  animation: fadeInUp 0.5s ease-out 0.2s forwards;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(15px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.image-gallery {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.chat-image {
  width: 100%;
  height: auto;
  border-radius: 8px;
  border: 1px solid #444444;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.chat-image:hover {
  transform: scale(1.05);
}

/* Model Indicator */
.model-indicator {
  margin-top: 0.5rem;
  display: flex;
  justify-content: flex-start;
}

.model-badge {
  background-color: rgba(69, 126, 247, 0.1);
  border: 1px solid rgba(69, 126, 247, 0.3);
  color: #60a5fa;
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
  font-size: 0.6875rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

/* Typing Indicator */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 5px;
}

.typing-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #666666;
  animation: typing 1.2s infinite ease-in-out;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 100% {
    transform: translateY(0);
    opacity: 0.5;
  }
  40% {
    transform: translateY(-5px);
    opacity: 1;
  }
}

/* Followup Questions */
.followup-container {
  margin-top: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid #333333;
}

.followup-label {
  font-size: 0.875rem;
  color: #9ca3af;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.followup-buttons {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.followup-button {
  background-color: #333333;
  color: #f9fafb;
  border: 1px solid #444444;
  border-radius: 8px;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
  line-height: 1.4;
}

.followup-button:hover:not(:disabled) {
  background-color: #404040;
  border-color: #555555;
  transform: translateY(-1px);
}

.followup-button:active:not(:disabled) {
  transform: translateY(0);
}

.followup-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

@media (max-width: 768px) {
  .messages-window {
    padding: 0.5rem;
  }

  .model-badge {
    font-size: 0.625rem;
  }

  .followup-buttons {
    gap: 0.375rem;
  }

  .followup-button {
    padding: 0.375rem 0.625rem;
    font-size: 0.8125rem;
  }
}
</style>
