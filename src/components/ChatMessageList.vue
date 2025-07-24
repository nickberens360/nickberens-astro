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
      <div
        v-for="(message, index) in messages"
        :key="index"
        :class="['message', message.sender]"
      >
        <div class="message-bubble">
          <p v-if="message.sender === 'user'">{{ message.text }}</p>

          <div
            v-else
            class="bot-message-wrapper"
          >
            <div>
              <div
                v-if="message.text"
                class="markdown-content-wrapper"
              >
                <span
                  v-html="renderMarkdown(message.text)"
                  class="markdown-content"
                ></span>
                <span
                  v-if="message.isTyping"
                  class="typing-cursor"
                >|</span>
              </div>

              <div
                v-if="!message.text && message.isTyping"
                class="typing-indicator"
              >
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
              </div>

              <div
                v-if="message.wasStopped && !message.isTyping"
                class="stopped-indicator"
              >
                <span class="stopped-icon">⏹</span>
                Response stopped
              </div>

              <div
                v-if="message.lmgtfyQuery && !message.isTyping"
                class="lmgtfy-wrapper fade-in"
              >
                <CustomLMGTFY
                  :search-query="message.lmgtfyQuery"
                  :play-animation="message.isNewResearch === true"
                  :chat-id="chatId"
                  :message-index="index"
                  @height-changed="handleHeightChanged"
                />
              </div>
            </div>

            <div>
              <div
                v-if="message.images && message.images.length && !message.isTyping"
                class="image-gallery fade-in"
              >
                <img
                  v-for="src in message.images"
                  :key="src"
                  :src="src"
                  alt="Illustration"
                  class="chat-image"
                  @click="$emit('image-click', src)"
                />
              </div>

              <div
                v-if="message.model && !message.isTyping"
                class="model-indicator"
              >
                <span
                  class="model-badge"
                  :class="{
                   'error': message.model === 'error' || backendStatus === 'offline'
                  }"
                >
                  {{ message.model }}
                </span>
              </div>

              <div
                v-if="shouldShowFollowups(message)"
                class="followup-container fade-in"
              >
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
    </div>
  </div>
</template>

<script>
import { ref, nextTick, watch, onMounted } from 'vue';
import { useScrollToBottom } from '../composables/useScrollToBottom.js';
import ChatBotWelcome from './ChatBotWelcome.vue';
import CustomLMGTFY from './CustomLMGTFY.vue';
import { marked } from 'marked';

export default {
  components: { ChatBotWelcome, CustomLMGTFY },
  props: {
    messages: { type: Array, required: true },
    isLoading: { type: Boolean, default: false },
    hasTypingMessage: { type: Boolean, default: false },
    backendStatus: { type: String, default: null },
    theme: { type: String, default: 'dark' },
    chatId: { type: String, default: null }
  },
  emits: ['prompt-select', 'image-click', 'followup-click'],
  setup(props) {
    const messagesWindow = ref(null);
    const { scrollToBottom } = useScrollToBottom(messagesWindow);

    watch(() => props.messages, () => {
      nextTick(() => {
        setTimeout(() => scrollToBottom(), 50);
      });
    }, { deep: true });

    onMounted(() => {
      if (props.messages.length > 0) {
        nextTick(() => setTimeout(() => scrollToBottom(), 100));
      }
    });

    const renderMarkdown = (text) => {
      return marked(text || '');
    };

    const shouldShowFollowups = (message) => {
      return message.followup_questions &&
        message.followup_questions.length &&
        message.sender === 'bot' &&
        !message.isTyping;
    };

    const handleHeightChanged = () => {
      nextTick(() => setTimeout(() => scrollToBottom(), 100));
    };

    return {
      messagesWindow,
      renderMarkdown,
      shouldShowFollowups,
      handleHeightChanged
    };
  }
};
</script>

<style scoped>
/* All previous styles are unchanged */
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

.message {
  display: flex;
}

.message-bubble {
  padding: 0.75rem 1.25rem;
  border-radius: 1.25rem;
  max-width: 100%;
  line-height: 1.5;
}

.user {
  justify-content: flex-end;
}

.user .message-bubble {
  background-color: #1c2539;
  color: white;
  border-bottom-right-radius: 4px;
}

.bot {
  width: 100%;
}

.bot .message-bubble {
  width: 100%;
  background-color: #2c2c2c;
  color: #f9fafb;
  border-bottom-left-radius: 4px;
}

/* Real typing cursor style */
.typing-cursor {
  display: inline-block;
  animation: blink 1s infinite;
  font-weight: bold;
  vertical-align: baseline;
  color: #60a5fa;
}

@keyframes blink {
  0%, 50% {
    opacity: 1;
  }
  51%, 100% {
    opacity: 0;
  }
}

/* Other styles like typing-indicator, followup-container etc. remain the same */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 5px
}

.typing-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #666;
  animation: typing 1.2s infinite ease-in-out
}

.typing-dot:nth-child(2) {
  animation-delay: .2s
}

.typing-dot:nth-child(3) {
  animation-delay: .4s
}

@keyframes typing {
  0%, 100% {
    transform: translateY(0);
    opacity: .5
  }
  40% {
    transform: translateY(-5px);
    opacity: 1
  }
}

.stopped-indicator {
  margin-top: .5rem;
  padding: .25rem .5rem;
  font-size: .75rem;
  color: #9ca3af;
  font-style: italic
}

.image-gallery {
  display: grid;
  grid-template-columns:repeat(auto-fill, minmax(150px, 1fr));
  gap: .5rem;
  margin-top: .75rem
}

.chat-image {
  width: 100%;
  height: auto;
  border-radius: 8px;
  border: 1px solid #444;
  cursor: pointer;
  transition: transform .2s ease
}

.chat-image:hover {
  transform: scale(1.05)
}

.model-indicator {
  margin-top: .5rem
}

.model-badge {
  background-color: rgba(132, 250, 96, .1);
  border: 1px solid rgba(132, 250, 96, .3);
  color: #84fa60;
  padding: .125rem .375rem;
  border-radius: 4px;
  font-size: .6875rem;
  font-weight: 500;
  text-transform: uppercase
}

.model-badge.error {
  background-color: rgba(239, 68, 68, .1);
  border-color: rgba(239, 68, 68, .3);
  color: #ef4444
}

.followup-container {
  margin-top: 1rem;
  padding-top: .75rem;
  border-top: 1px solid #333
}

.followup-label {
  font-size: .875rem;
  color: #9ca3af;
  margin-bottom: .5rem
}

.followup-buttons {
  display: flex;
  flex-direction: column;
  gap: .5rem
}

.followup-button {
  background-color: #333;
  color: #f9fafb;
  border: 1px solid #444;
  border-radius: 8px;
  padding: .5rem .75rem;
  font-size: .875rem;
  cursor: pointer;
  transition: background-color .2s;
  text-align: left
}

.followup-button:hover {
  background-color: #404040
}
</style>