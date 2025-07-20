<template>
  <div
    class="chatbot-container"
    :class="`theme-${theme}`"
  >
    <ChatMessagesWindow
      :messages="messages"
      :is-loading="isLoading"
      :has-typing-message="hasTypingMessage"
      :theme="theme"
      @image-click="handleImageClick"
      @followup-click="handleFollowupClick"
      @prompt-select="handlePromptSelect"
    />
    <ChatInput
      v-model:userInput="userInput"
      v-model:selectedModel="selectedModel"
      :is-loading="isLoading"
      :has-typing-message="hasTypingMessage"
      :last-stopped-prompt="lastStoppedPrompt"
      @send-message="sendMessage"
      @stop-action="stopCurrentAction"
    />
    <ImageOverlay />
  </div>
</template>

<script>
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { useStore } from '@nanostores/vue';
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
import { useChatAPI } from '../composables/useChatAPI.js';
import { useMessageState } from '../composables/useMessageState.js';
import ChatMessagesWindow from './ChatMessagesWindow.vue';
import ChatInput from './ChatInput.vue';
import ImageOverlay from './ImageOverlay.vue';

export default {
  name: 'ChatBot',
  components: {
    ChatMessagesWindow,
    ChatInput,
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
    const messages = useStore(activeChatMessages);
    const chatId = useStore(activeChatId);
    const pendingNewChat = useStore(isPendingNewChat);
    const lastStoppedPrompt = ref('');
    const selectedModel = ref('claude');

    const {
      typingMessages,
      typingTimeouts,
      stopTyping,
      updateMessageTyping
    } = useMessageState();

    // hasTypingMessage should be computed from the actual messages
    const hasTypingMessage = computed(() => {
      return messages.value.some(msg => msg.isTyping);
    });

    const {
      sendChatMessage,
      abortController,
      stopLoading
    } = useChatAPI();

    onMounted(() => {
      if (!activeChatId.get() && !isPendingNewChat.get()) {
        createNewChat();
      }
    });

    // Watch for new chat being created
    watch(pendingNewChat, (isPending) => {
      if (isPending && lastStoppedPrompt.value) {
        lastStoppedPrompt.value = '';
      }
    });

    // Watch for chat changes and clear lastStoppedPrompt
    watch(chatId, (newChatId, oldChatId) => {
      if (newChatId !== oldChatId && newChatId) {
        lastStoppedPrompt.value = '';
      }
    });

    // Also watch the messages array - when it becomes empty (new chat), clear the retry state
    watch(messages, (newMessages) => {
      if (newMessages.length === 0 && lastStoppedPrompt.value) {
        lastStoppedPrompt.value = '';
      }
    });

    // Clear lastStoppedPrompt when user starts typing manually
    watch(userInput, (newValue) => {
      if (newValue.trim() && lastStoppedPrompt.value) {
        lastStoppedPrompt.value = '';
      }
    });

    const sendMessage = async () => {
      // Check if input is empty and we have a stopped prompt to retry
      if (userInput.value.trim() === '' && lastStoppedPrompt.value) {
        userInput.value = lastStoppedPrompt.value;
        lastStoppedPrompt.value = ''; // Clear after using
      }

      if (userInput.value.trim() === '' || isLoading.value || hasTypingMessage.value) {
        return;
      }

      const question = userInput.value;

      // Check if we have a pending new chat or no active chat
      let currentChatId = activeChatId.get();
      if (isPendingNewChat.get() || !currentChatId) {
        currentChatId = createNewChat();
        isPendingNewChat.set(false);
      }

      // Store the chat ID for this specific message session
      const messageChatId = currentChatId;

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

      try {
        const data = await sendChatMessage(question, chatHistoryForAPI, selectedModel.value);

        // Add empty bot message first
        addMessageToActiveChat({
          text: '',
          sender: 'bot',
          images: data.images || [],
          followup_questions: data.followup_questions || [],
          isTyping: true,
          wasStopped: false,
          model: data.model_used || data.llm_used || selectedModel.value
        });

        // Get the index of the message we just added
        const messagesAfterAdd = activeChatMessages.get();
        const messageIndex = messagesAfterAdd.length - 1;

        // Stop loading indicator since we're now typing
        isLoading.value = false;

        // Start realistic typing effect via message state - bound to specific chat
        await updateMessageTyping(messageIndex, data.answer, messageChatId);

      } catch (error) {
        if (error.name === 'AbortError') {
          return;
        }

        addMessageToActiveChat({
          text: `${error.message || 'Sorry, I encountered an error. Please try again.'}`,
          sender: 'bot',
          model: 'error'
        });
      } finally {
        isLoading.value = false;
      }
    };

    const stopCurrentAction = () => {

      // Get the current chat ID for stopping
      const currentChatId = activeChatId.get();

      // Store the prompt that's being stopped for potential retry
      const currentMessages = activeChatMessages.get();
      if (currentMessages.length >= 1) {
        const userMessage = currentMessages[currentMessages.length - 1];
        if (userMessage && userMessage.sender === 'user') {
          lastStoppedPrompt.value = userMessage.text;
        } else if (currentMessages.length >= 2) {
          // If the last message is a bot message, look for the user message before it
          const userMessage = currentMessages[currentMessages.length - 2];
          if (userMessage && userMessage.sender === 'user') {
            lastStoppedPrompt.value = userMessage.text;
          }
        }
      }

      if (isLoading.value) {
        // If we're in the loading phase, abort the API request
        stopLoading();
        isLoading.value = false;
      } else if (hasTypingMessage.value) {
        // If we're in the typing phase, stop the typing for the specific chat
        const typingMessageIndex = messages.value.findIndex(msg => msg.isTyping);
        if (typingMessageIndex !== -1) {
          stopTyping(typingMessageIndex, currentChatId);
        }
      }
    };

    const handlePromptSelect = (prompt) => {
      if (hasTypingMessage.value) return;
      userInput.value = prompt;
      sendMessage();
    };

    const handleFollowupClick = (question) => {
      if (hasTypingMessage.value) return;
      userInput.value = question;
      sendMessage();
    };

    const handleImageClick = (src) => {
      openImageOverlay(src);
    };

    return {
      userInput,
      messages,
      isLoading,
      hasTypingMessage,
      selectedModel,
      lastStoppedPrompt,
      sendMessage,
      handlePromptSelect,
      handleFollowupClick,
      handleImageClick,
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
  background-color: #1a1a1a;
  overflow: hidden;
}
</style>