<template>
  <div
    class="chatbot-container"
    :class="`theme-${theme}`"
  >
    <div
      class="messages-window"
      ref="messagesWindow"
    >
      <div class="messages-content">
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

            <!-- Bot messages with typing effect -->
            <div v-if="message.sender === 'bot'" class="bot-message-wrapper">
              <div
                v-if="message.text"
                class="markdown-content-wrapper"
              >
              <span
                v-html="renderMarkdown(message.text)"
                class="markdown-content"
              ></span><span
                v-if="message.isTyping"
                class="typing-cursor"
              >|</span>
              </div>

              <!-- Stopped message indicator -->
              <div v-if="message.wasStopped && !message.isTyping" class="stopped-indicator">
                <span class="stopped-icon">⏹</span>
                You stopped this response
              </div>

              <!-- Model indicator for bot messages -->
              <div v-if="message.model && !message.isTyping" class="model-indicator">
                <span class="model-badge">{{ message.model }}</span>
              </div>
            </div>

            <!-- Images (only show after typing is complete) -->
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
                @click="handleImageClick(src)"
              />
            </div>

            <!-- Follow-up questions (only show after typing is complete) -->
            <div
              v-if="message.followup_questions && message.followup_questions.length && message.sender === 'bot' && !message.isTyping && false"
              class="followup-container fade-in"
            >
              <p class="followup-label">💡 You might also want to ask:</p>
              <div class="followup-buttons">
                <button
                  v-for="(question, qIndex) in message.followup_questions"
                  :key="qIndex"
                  @click="handleFollowupClick(question)"
                  class="followup-button"
                  :disabled="isLoading || hasTypingMessage"
                >
                  {{ question }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Loading indicator (only show when no message is being typed) -->
        <div
          v-if="isLoading && !hasTypingMessage"
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
    </div>
    <div class="input-form">
      <div class="input-container">
        <input
          v-model="userInput"
          @keyup.enter="sendMessage"
          :placeholder="lastStoppedPrompt && !userInput.trim() ? 'Press Enter to retry stopped response...' : 'Ask about Nick\'s skills, projects, etc...'"
          class="message-input"
          :disabled="isLoading && !hasTypingMessage"
        />
        <div class="d-flex justify-between items-center w-full pt-2">
          <div class="model-selector-bar">
            <div class="model-selector-container">
              <select
                v-model="selectedModel"
                class="model-selector"
                :disabled="isLoading || hasTypingMessage"
              >
                <option value="claude">Claude (Recommended)</option>
                <option value="gemini">Gemini (Fast)</option>
              </select>
            </div>
          </div>
          <button
            @click="hasTypingMessage ? stopCurrentAction() : sendMessage()"
            class="send-button"
            :class="{ 'stop-mode': hasTypingMessage }"
            :disabled="isLoading && !hasTypingMessage"
          >
          <span v-if="hasTypingMessage" class="stop-content">
            <span class="stop-icon">⏹</span>
            Stop
          </span>
            <span v-else-if="lastStoppedPrompt && !userInput.trim()">
            Retry
          </span>
            <span v-else>Send</span>
          </button>
        </div>
      </div>
    </div>
    <ImageOverlay />
  </div>
</template>

<script>
import { ref, nextTick, watch, onMounted, computed } from 'vue';
import { useStore } from '@nanostores/vue';
import { marked } from 'marked';
import {
  activeChatId,
  activeChatMessages,
  addMessageToActiveChat,
  createNewChat,
  updateChatTitle,
  isPendingNewChat,
  allChats
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
    const typingMessages = ref(new Set());
    const typingTimeouts = ref(new Map()); // Track typing timeouts for cancellation
    const abortController = ref(null); // For cancelling API requests
    const lastStoppedPrompt = ref(''); // Track the last stopped prompt for retry
    const selectedModel = ref('claude'); // Default to Claude

    // Model descriptions
    const modelDescriptions = {
      claude: 'Best quality responses, slower',
      gemini: 'Faster responses, good quality'
    };

    // Check if any message is currently typing
    const hasTypingMessage = computed(() => {
      return messages.value.some(msg => msg.isTyping);
    });

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

    // Stop typing function
    const stopTyping = (messageIndex) => {
      // Clear the timeout for this message
      if (typingTimeouts.value.has(messageIndex)) {
        clearTimeout(typingTimeouts.value.get(messageIndex));
        typingTimeouts.value.delete(messageIndex);
      }

      // Remove from typing messages set
      typingMessages.value.delete(messageIndex);

      // Update the message to show it's no longer typing and was stopped
      const currentMessages = activeChatMessages.get();
      const updatedMessages = [...currentMessages];
      if (updatedMessages[messageIndex]) {
        updatedMessages[messageIndex] = {
          ...updatedMessages[messageIndex],
          isTyping: false,
          wasStopped: true
        };

        const currentChatId = activeChatId.get();
        const currentChat = allChats.get()[currentChatId];
        if (currentChat) {
          allChats.setKey(currentChatId, {
            ...currentChat,
            messages: updatedMessages
          });
        }
      }
    };

    // Stop loading function
    const stopLoading = () => {
      if (abortController.value) {
        abortController.value.abort();
        abortController.value = null;
      }
      isLoading.value = false;
    };

    // Combined stop function - only for typing messages
    const stopCurrentAction = () => {
      if (hasTypingMessage.value) {
        // Store the prompt that's being stopped for potential retry
        const currentMessages = activeChatMessages.get();
        if (currentMessages.length >= 2) {
          // Get the user message that prompted this response (should be second to last)
          const userMessage = currentMessages[currentMessages.length - 2];
          if (userMessage && userMessage.sender === 'user') {
            lastStoppedPrompt.value = userMessage.text;
          }
        }

        // Find the currently typing message and stop it
        const typingMessageIndex = messages.value.findIndex(msg => msg.isTyping);
        if (typingMessageIndex !== -1) {
          stopTyping(typingMessageIndex);
        }
      }
    };

    // Realistic typing effect composable with stop functionality
    const useRealisticTyping = () => {
      const getTypingSpeed = (char, prevChar) => {
        const baseSpeed = 10; // Base typing speed in ms (reduced from 15ms for 50% faster typing)

        // Slower for punctuation (thinking pauses)
        if (['.', '!', '?', ':'].includes(char)) return baseSpeed + 133; // Reduced from +200ms
        if ([',', ';'].includes(char)) return baseSpeed + 67; // Reduced from +100ms

        // Slower after punctuation (pause after sentences)
        if (prevChar && ['.', '!', '?'].includes(prevChar)) return baseSpeed + 100; // Reduced from +150ms
        if (prevChar && [',', ';'].includes(prevChar)) return baseSpeed + 50; // Reduced from +75ms

        // Faster for common letter combinations
        const commonCombos = ['th', 'he', 'in', 'er', 'an', 're', 'ed', 'nd', 'ha', 'at'];
        if (prevChar && commonCombos.includes(prevChar + char)) return baseSpeed - 10; // Reduced from -15ms

        // Slower for uppercase letters (shift key)
        if (char === char.toUpperCase() && char !== char.toLowerCase()) return baseSpeed + 13; // Reduced from +20ms

        // Add some randomness for natural feel
        const randomVariation = Math.random() * 10 - 5; // Reduced from ±12.5ms to ±5ms

        return Math.max(13, baseSpeed + randomVariation); // Reduced minimum from 20ms to 13ms
      };

      const typeMessageRealistic = (messageIndex, fullText) => {
        return new Promise((resolve) => {
          typingMessages.value.add(messageIndex);
          let currentText = '';
          let currentIndex = 0;

          const typeChar = () => {
            // Check if typing was stopped
            if (!typingMessages.value.has(messageIndex)) {
              resolve();
              return;
            }

            if (currentIndex < fullText.length) {
              const char = fullText[currentIndex];
              const prevChar = currentIndex > 0 ? fullText[currentIndex - 1] : null;

              currentText += char;

              // Update the message in the store
              const currentMessages = activeChatMessages.get();
              const updatedMessages = [...currentMessages];
              if (updatedMessages[messageIndex]) {
                updatedMessages[messageIndex] = {
                  ...updatedMessages[messageIndex],
                  text: currentText,
                  isTyping: true
                };

                const currentChatId = activeChatId.get();
                const currentChat = allChats.get()[currentChatId];
                if (currentChat) {
                  allChats.setKey(currentChatId, {
                    ...currentChat,
                    messages: updatedMessages
                  });
                }
              }

              currentIndex++;
              const nextSpeed = getTypingSpeed(char, prevChar);
              const timeoutId = setTimeout(typeChar, nextSpeed);
              typingTimeouts.value.set(messageIndex, timeoutId);
            } else {
              // Typing complete naturally (not stopped)
              typingMessages.value.delete(messageIndex);
              typingTimeouts.value.delete(messageIndex);
              const currentMessages = activeChatMessages.get();
              const updatedMessages = [...currentMessages];
              if (updatedMessages[messageIndex]) {
                updatedMessages[messageIndex] = {
                  ...updatedMessages[messageIndex],
                  isTyping: false,
                  wasStopped: false // Mark as completed naturally
                };

                const currentChatId = activeChatId.get();
                const currentChat = allChats.get()[currentChatId];
                if (currentChat) {
                  allChats.setKey(currentChatId, {
                    ...currentChat,
                    messages: updatedMessages
                  });
                }
              }
              resolve();
            }
          };

          // Start typing after a brief pause (simulating thinking)
          const initialTimeoutId = setTimeout(typeChar, 333); // Reduced from 500ms for 50% faster typing
          typingTimeouts.value.set(messageIndex, initialTimeoutId);
        });
      };

      return { typeMessageRealistic };
    };

    const { typeMessageRealistic } = useRealisticTyping();

    const sendMessage = async () => {
      // Check if input is empty and we have a stopped prompt to retry
      if (userInput.value.trim() === '' && lastStoppedPrompt.value) {
        userInput.value = lastStoppedPrompt.value;
        lastStoppedPrompt.value = ''; // Clear after using
      }

      if (userInput.value.trim() === '' || isLoading.value || hasTypingMessage.value) return;

      const question = userInput.value;

      // Check if we have a pending new chat or no active chat
      let currentChatId = activeChatId.get();
      if (isPendingNewChat.get() || !currentChatId) {
        currentChatId = createNewChat();
        isPendingNewChat.set(false);
      }

      const currentMessages = activeChatMessages.get();

      // If this is the very first message in the chat, update the title
      if (currentMessages.length === 0) {
        updateChatTitle(currentChatId, question);
      }

      // Get chat history BEFORE adding the new user message
      const chatHistoryForAPI = currentMessages.slice();

      addMessageToActiveChat({ text: question, sender: 'user' });
      userInput.value = '';
      isLoading.value = true;

      // Create abort controller for this request
      abortController.value = new AbortController();

      try {
        const isDev = import.meta.env.DEV || window.location.hostname === 'localhost';
        const apiUrl = isDev
          ? 'http://localhost:8000'
          : 'https://nickberens-astro-api.onrender.com';

        const response = await fetch(`${apiUrl}/query`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            question: question,
            chat_history: chatHistoryForAPI,
            preferred_model: selectedModel.value // Send preferred model
          }),
          signal: abortController.value.signal
        });

        if (!response.ok) {
          let errorMessage = `Error: ${response.status} ${response.statusText}`;

          try {
            const errorData = await response.json();
            if (errorData.detail) {
              errorMessage = errorData.detail;
            }
          } catch (parseError) {
            // If we can't parse the JSON, just use the status message
          }

          if (response.status === 429) {
            errorMessage = 'Rate limit exceeded. Please wait a moment before sending more messages.';
          }

          throw new Error(errorMessage);
        }

        const data = await response.json();

        // Add empty bot message first
        addMessageToActiveChat({
          text: '',
          sender: 'bot',
          images: data.images || [],
          followup_questions: data.followup_questions || [],
          isTyping: true,
          wasStopped: false,
          model: data.model_used || data.llm_used || selectedModel.value // Track which model was used
        });

        // Get the index of the message we just added
        const messagesAfterAdd = activeChatMessages.get();
        const messageIndex = messagesAfterAdd.length - 1;

        // Stop loading indicator since we're now typing
        isLoading.value = false;

        // Start realistic typing effect
        await typeMessageRealistic(messageIndex, data.answer);

      } catch (error) {
        if (error.name === 'AbortError') {
          console.log('Request was cancelled');
          return;
        }

        console.error('Error fetching response:', error);
        addMessageToActiveChat({
          text: `${error.message || 'Sorry, I encountered an error. Please try again.'}`,
          sender: 'bot',
          model: 'error'
        });
      } finally {
        isLoading.value = false;
        abortController.value = null;
      }
    };

    const handlePromptSelect = (prompt) => {
      if (hasTypingMessage.value) return; // Prevent new messages while typing
      userInput.value = prompt;
      sendMessage();
    };

    const handleFollowupClick = (question) => {
      if (hasTypingMessage.value) return; // Prevent new messages while typing
      userInput.value = question;
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
      hasTypingMessage,
      selectedModel,
      modelDescriptions,
      lastStoppedPrompt,
      sendMessage,
      handlePromptSelect,
      handleFollowupClick,
      handleImageClick,
      renderMarkdown,
      stopTyping,
      stopLoading,
      stopCurrentAction
    };
  },
};
</script>

<style scoped>
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
  box-shadow: 0 5px 10px -5px rgba(0, 0, 0, 0.5) inset;
}

/* Message structure */
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
  /*background-color: #222222;*/
  color: #f9fafb;
  border-bottom-left-radius: 4px;
}

/* Bot message wrapper for inline cursor */
.bot-message-wrapper {
  width: 100%;
}

.markdown-content-wrapper {
  display: inline;
  line-height: 1.6;
}

.markdown-content-wrapper .markdown-content {
  display: inline;
  line-height: inherit;
}

.typing-cursor {
  display: inline;
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

/* Stopped message indicator */
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

/* Fade in animation for images and follow-ups */
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

/* Follow-up questions styling */
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
  padding: 0 1rem 1rem;
  border-top: 1px solid #111111;
  background-color: #111111;
}

.input-container {
  box-shadow: 0 -8px 20px 10px rgba(17, 17, 17, .9);
  width: 100%;
  border: 1px solid #afafaf;
  background-color: #111111;
  color: #f9fafb;
  border-radius: 8px;
  padding: 0.5rem;
  max-width: 800px;
  margin: 0 auto;
}

/* Model Selector Bar */
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

.message-input {
  flex-grow: 0;
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
  background-color: #1c2539;
  color: white;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
  min-width: 80px;
}

.send-button:hover:not(:disabled) {
  background-color: #3967ca;
}

.send-button.stop-mode {
  background-color: #dc2626;
}

.send-button.stop-mode:hover {
  background-color: #b91c1c;
}

.send-button:disabled {
  background-color: #5c709a;
  cursor: not-allowed;
}

.stop-content {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  justify-content: center;
}

.stop-icon {
  font-size: 0.875em;
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

/* Responsive styles */
@media (max-width: 768px) {
  .model-selector-container {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .model-selector {
    min-width: 100%;
  }

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

  .followup-buttons {
    gap: 0.375rem;
  }

  .followup-button {
    padding: 0.375rem 0.625rem;
    font-size: 0.8125rem;
  }

  .stop-content {
    gap: 0.25rem;
  }

  .stop-icon {
    font-size: 0.75em;
  }

  .model-selector-bar {
    padding: 0.5rem;
  }

  .model-badge {
    font-size: 0.625rem;
  }
}
</style>
