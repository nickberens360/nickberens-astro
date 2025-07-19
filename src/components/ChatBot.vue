<template>
  <div
    class="chatbot-container"
    :class="`theme-${theme}`"
  >
    <div
      class="messages-window"
      ref="messagesWindow"
    >
      <ChatBotWelcome
        v-if="messages.length === 0"
        :theme="theme"
        @select-prompt="handlePromptSelect"
      />
      <div
        v-for="(message, index) in messages"
        :key="index"
        :class="['message', message.sender]"
      >
        <div class="message-bubble">
          <!-- User messages remain as plain text -->
          <p v-if="message.text && message.sender === 'user'">{{ message.text }}</p>

          <!-- Bot messages are rendered as markdown -->
          <div
            v-if="message.text && message.sender === 'bot'"
            v-html="renderMarkdown(message.text)"
            class="markdown-content"
          ></div>
          <div
            v-if="message.images && message.images.length"
            class="image-gallery"
          >
            <img
              v-for="src in message.images"
              :key="src"
              :src="src"
              alt="Illustration"
              class="chat-image"
              @click="handleImageClick(src)"
            />
          </div>
        </div>
      </div>
      <div
        v-if="isLoading"
        class="message bot"
      >
        <div class="message-bubble">
          <div class="typing-indicator">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </div>
        </div>
      </div>
    </div>
    <div class="input-form">
      <div class="input-container">
        <input
          v-model="userInput"
          @keyup.enter="sendMessage"
          placeholder="Ask about Nick's skills, projects, etc..."
          class="message-input"
          :disabled="isLoading"
        />
        <button
          @click="sendMessage"
          class="send-button"
          :disabled="isLoading"
        >
          Send
        </button>
      </div>
    </div>
    <ImageOverlay />
  </div>
</template>

<script>
import { ref, nextTick, watch, onMounted } from 'vue';
import { useStore } from '@nanostores/vue';
import { marked } from 'marked'; // Import the marked library
import {
  activeChatId,
  activeChatMessages,
  addMessageToActiveChat,
  createNewChat,
  updateChatTitle,
  isPendingNewChat
} from '../stores/ai.js';
import { openImageOverlay } from '../stores/ui.js';
import ChatBotWelcome from './ChatBotWelcome.vue';
import ImageOverlay from './ImageOverlay.vue';

export default {
  components: {
    ChatBotWelcome,
    ImageOverlay
  },
  props: {
    theme: {
      type: String,
      default: 'dark',
      validator: (value) => ['light', 'dark'].includes(value)
    }
  },
  setup() {
    const userInput = ref('');
    const isLoading = ref(false);
    const messagesWindow = ref(null);
    const messages = useStore(activeChatMessages);

    const scrollToBottom = () => {
      nextTick(() => {
        if (messagesWindow.value) {
          messagesWindow.value.scrollTop = messagesWindow.value.scrollHeight;
        }
      });
    };

    onMounted(() => {
      if (!activeChatId.get() && !isPendingNewChat.get()) {
        createNewChat();
      }
    });

    watch(messages, () => {
      scrollToBottom();
    }, { deep: true });

    const sendMessage = async () => {
      if (userInput.value.trim() === '' || isLoading.value) return;

      const question = userInput.value;

      // Check if we have a pending new chat
      if (isPendingNewChat.get() || !activeChatId.get()) {
        // Create a new chat before sending the message
        createNewChat();
        isPendingNewChat.set(false);
      }

      const currentChatId = activeChatId.get();
      const currentMessages = activeChatMessages.get();

      // --- NEW: Logic to update chat title ---
      // If this is the very first message in the chat, update the title.
      if (currentMessages.length === 0) {
        updateChatTitle(currentChatId, question);
      }

      addMessageToActiveChat({ text: question, sender: 'user' });
      userInput.value = '';
      isLoading.value = true;

      try {
        // Replace the hardcoded line with this:
        const isDev = import.meta.env.DEV || window.location.hostname === 'localhost';
        const apiUrl = isDev
          ? 'http://localhost:8000'
          : 'https://nickberens-astro-api.onrender.com';

        console.log(`Environment: ${isDev ? 'development' : 'production'}, API URL: ${apiUrl}`);
        const response = await fetch(`${apiUrl}/query`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          // --- UPDATED: Send the chat history with the request ---
          body: JSON.stringify({
            question: question,
            chat_history: messages.value.slice(0, -1) // Send all but the last message
          }),
        });

        if (!response.ok) {
          // Extract error details from the response when possible
          let errorMessage = `Error: ${response.status} ${response.statusText}`;

          try {
            // Try to get detailed error message from response body
            const errorData = await response.json();
            if (errorData.detail) {
              errorMessage = errorData.detail;
            }
          } catch (parseError) {
            // If we can't parse the JSON, just use the status message
          }

          // Handle rate limit (429) errors specifically
          if (response.status === 429) {
            errorMessage = 'Rate limit exceeded. Please wait a moment before sending more messages.';
          }

          throw new Error(errorMessage);
        }

        const data = await response.json();
        addMessageToActiveChat({
          text: data.answer,
          sender: 'bot',
          images: data.images || []
        });

      } catch (error) {
        console.error('Error fetching response:', error);
        // Display the specific error message instead of a generic one
        addMessageToActiveChat({
          text: `${error.message || 'Sorry, I encountered an error. Please try again.'}`,
          sender: 'bot'
        });
      } finally {
        isLoading.value = false;
      }
    };

    const handlePromptSelect = (prompt) => {
      userInput.value = prompt;
      sendMessage();
    };

    const handleImageClick = (src) => {
      openImageOverlay(src);
    };

    // Add a function to render markdown
    const renderMarkdown = (text) => {
      return marked(text);
    };

    return {
      userInput,
      messages,
      isLoading,
      messagesWindow,
      sendMessage,
      handlePromptSelect,
      handleImageClick,
      renderMarkdown
    };
  },
};
</script>

<style scoped>
/* Main container */
.chatbot-container {
  max-width: none;
  margin: 0;
  border: none;
  border-radius: 0;
  display: flex;
  flex-direction: column;
  flex-grow: 1;
  background-color: #111111;
  overflow: hidden;
}

/* Messages window */
.messages-window {
  flex-grow: 1;
  padding: 1rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  background-color: #111111;
}

/* Message structure */
.message {
  display: flex;
}

.message-bubble {
  padding: 0.75rem 1.25rem;
  border-radius: 18px;
  max-width: 85%;
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
  background-color: #457ef7;
  color: white;
  border-bottom-right-radius: 4px;
}

/* Bot messages */
.bot {
  justify-content: flex-start;
}

.bot .message-bubble {
  background-color: #222222;
  color: #f9fafb;
  border-bottom-left-radius: 4px;
}

/* Image gallery */
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

/* Typing indicator */
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

/* Input area */
.input-form {
  display: flex;
  padding: 1rem;
  border-top: 1px solid #111111;
  background-color: #111111;
}

.input-container {
  display: flex;
  align-items: center;
  width: 100%;
  background-color: #111111;
  border: 1px solid #afafaf;
  color: #f9fafb;
  border-radius: 8px;
  overflow: hidden;
  padding: 0.5rem;
  max-width: 800px;
  margin: 0 auto;
}

.message-input {
  flex-grow: 1;
  padding: 0.75rem;
  font-size: 1rem;
  border: none !important;
  background: none !important;
  color: #f9fafb;
}

.message-input::placeholder {
  color: #999999;
}

.message-input:focus {
  outline: none;
  border-color: #555555;
  box-shadow: none !important;
}

.send-button {
  margin-left: 1rem;
  padding: 0.65rem 1.5rem;
  border: none;
  background-color: #457ef7;
  color: white;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.2s;
}

.send-button:hover {
  background-color: #3967ca;
}

.send-button:disabled {
  background-color: #5c709a;
  cursor: not-allowed;
}

/* Markdown content styling */
:deep(.markdown-content) {
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

/* Responsive styles */
@media (max-width: 768px) {
  .messages-window {
    padding: 0.5rem;
  }

  .input-form {
    padding: 0.5rem;
  }

  .message-input {
    font-size: 0.875rem;
  }

  .send-button {
    padding: 0.5rem 1rem;
    font-size: 0.875rem;
  }
}
</style>
