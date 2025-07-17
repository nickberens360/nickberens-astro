<template>
  <div class="chatbot-container" :class="`theme-${theme}`">
    <div class="messages-window" ref="messagesWindow">
      <div v-for="(message, index) in messages" :key="index" :class="['message', message.sender]">
        <div class="message-bubble">
          <p v-if="message.text">{{ message.text }}</p>
          <div v-if="message.images && message.images.length" class="image-gallery">
            <img v-for="src in message.images" :key="src" :src="src" alt="Illustration" class="chat-image" />
          </div>
        </div>
      </div>
      <div v-if="isLoading" class="message bot">
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
      <input
        v-model="userInput"
        @keyup.enter="sendMessage"
        placeholder="Ask about Nick's skills, projects, etc..."
        class="message-input"
        :disabled="isLoading"
      />
      <button @click="sendMessage" class="send-button" :disabled="isLoading">
        Send
      </button>
    </div>
  </div>
</template>

<script>
import { ref, nextTick, watch, onMounted } from 'vue';
import { useStore } from '@nanostores/vue';
// --- UPDATED: Import the new updateChatTitle function ---
import { activeChatId, activeChatMessages, addMessageToActiveChat, createNewChat, updateChatTitle } from '../stores/ai.js';

export default {
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
        if (!activeChatId.get()) {
            createNewChat();
        }
    });

    watch(messages, () => {
      scrollToBottom();
    }, { deep: true });

    const sendMessage = async () => {
      if (userInput.value.trim() === '' || isLoading.value) return;

      const question = userInput.value;
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
        const response = await fetch('http://localhost:8000/query', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ question: question }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        addMessageToActiveChat({
          text: data.answer,
          sender: 'bot',
          images: data.images || []
        });

      } catch (error) {
        console.error('Error fetching response:', error);
        addMessageToActiveChat({ text: 'Sorry, I encountered an error. Please try again.', sender: 'bot' });
      } finally {
        isLoading.value = false;
      }
    };

    return {
      userInput,
      messages,
      isLoading,
      messagesWindow,
      sendMessage,
    };
  },
};
</script>

<style scoped>
/* NOTE: I've added flex-grow to the chatbot container and removed the fixed height */
.chatbot-container {
  max-width: none; /* Allow it to fill the space */
  margin: 0;
  border: none;
  border-radius: 0;
  display: flex;
  flex-direction: column;
  flex-grow: 1; /* This is key */
  background-color: #f9fafb;
  overflow: hidden;
}

/* --- All other styles from your previous version remain the same --- */
.image-gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.5rem; margin-top: 0.75rem; }
.chat-image { width: 100%; height: auto; border-radius: 8px; border: 1px solid #ddd; }
.message-bubble p { margin: 0; }
.theme-dark { background-color: #111111; border-color: #333333; }
.theme-dark .messages-window { background-color: #111111; }
.theme-dark .input-form { background-color: #000000; border-top-color: #333333; }
.theme-dark .message-input { background-color: #222222; border-color: #444444; color: #f9fafb; }
.theme-dark .message-input::placeholder { color: #999999; }
.theme-dark .message-input:focus { border-color: #555555; box-shadow: 0 0 0 2px rgba(85, 85, 85, 0.2); }
.theme-dark .user .message-bubble { background-color: #333333; }
.theme-dark .bot .message-bubble { background-color: #222222; color: #f9fafb; }
.theme-dark .typing-dot { background-color: #666666; }
.theme-dark .chat-image { border-color: #444444; }
.messages-window { flex-grow: 1; padding: 1rem; overflow-y: auto; display: flex; flex-direction: column; gap: 1rem; }
.message { display: flex; }
.message-bubble { padding: 0.75rem 1.25rem; border-radius: 18px; max-width: 85%; line-height: 1.5; }
.user { justify-content: flex-end; }
.user .message-bubble { background-color: #3b82f6; color: white; border-bottom-right-radius: 4px; }
.bot { justify-content: flex-start; }
.bot .message-bubble { background-color: #e5e7eb; color: #1f2937; border-bottom-left-radius: 4px; }
.input-form { display: flex; padding: 1rem; border-top: 1px solid #e5e7eb; background-color: #ffffff; }
.message-input { flex-grow: 1; border: 1px solid #d1d5db; padding: 0.75rem; border-radius: 8px; font-size: 1rem; }
.message-input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2); }
.send-button { margin-left: 1rem; padding: 0.75rem 1.5rem; border: none; background-color: #3b82f6; color: white; border-radius: 8px; cursor: pointer; font-weight: 600; transition: background-color 0.2s; }
.send-button:hover { background-color: #2563eb; }
.send-button:disabled { background-color: #9ca3af; cursor: not-allowed; }
.typing-indicator { display: flex; align-items: center; gap: 5px; }
.typing-dot { width: 8px; height: 8px; border-radius: 50%; background-color: #9ca3af; animation: typing 1.2s infinite ease-in-out; }
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing { 0%, 100% { transform: translateY(0); opacity: 0.5; } 40% { transform: translateY(-5px); opacity: 1; } }
</style>