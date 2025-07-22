<template>
  <div class="chatbot-container" :class="`theme-${theme}`">
    <!-- Better status notifications -->
    <div v-if="backendStatus === 'checking'" class="status-notification checking">
      <p>🔄 Checking backend status...</p>
    </div>

    <div v-else-if="backendStatus === 'building'" class="status-notification building">
      <p>⚠️ Backend service is building. This may take 1-2 minutes on the first visit.</p>
    </div>

    <div v-else-if="backendStatus === 'initializing'" class="status-notification initializing">
      <p>🔄 Backend service is initializing. Please wait a moment...</p>
    </div>

    <div v-else-if="backendStatus === 'offline'" class="status-notification offline">
      <p>❌ Backend service is currently offline or rebuilding. Please try again later.</p>
    </div>

    <ChatMessageList
      :messages="messages"
      :is-loading="isLoading"
      :has-typing-message="hasTypingMessage"
      :theme="theme"
      :backend-status="backendStatus"
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
      :backend-status="backendStatus"
      @send-message="sendMessage"
      @stop-action="stopCurrentAction"
      @research-message="handleResearchMessage"
    />

    <ImageOverlay />
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { useStore } from '@nanostores/vue';
import {
  activeChatId,
  activeChatMessages,
  addMessageToActiveChat,
  createNewChat,
  updateChatTitle,
  isPendingNewChat,
} from '../stores/ai.js';
import { openImageOverlay, isChatProcessing } from '../stores/ui.js';
import { backendStatus } from '../stores/backendStatus.js';
import { useChatAPI } from '../composables/useChatAPI.js';
import { useMessageState } from '../composables/useMessageState.js';
import ChatMessageList from './ChatMessageList.vue';
import ChatInput from './ChatInput.vue';
import ImageOverlay from './ImageOverlay.vue';

export default {
  name: 'ChatBot',
  components: {
    ChatMessageList,
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

    // Backend status store
    const backendStatusValue = useStore(backendStatus);

    const {
      typingMessages,
      typingTimeouts,
      stopTyping,
      updateMessageTyping,
      cleanupTypingTimeouts
    } = useMessageState();

    // hasTypingMessage should be computed from the actual messages
    const hasTypingMessage = computed(() => {
      return messages.value.some(msg => msg.isTyping);
    });

    const {
      sendChatMessage,
      abortController,
      stopLoading,
      checkBackendStatus
    } = useChatAPI();

    // Function to check backend status
    const checkStatus = async () => {
      try {
        await checkBackendStatus();
      } catch (error) {
        console.error('Error checking backend status:', error);
      }
    };

    // Store interval ID for proper cleanup
    let statusInterval = null;

    onMounted(async () => {
      if (!activeChatId.get() && !isPendingNewChat.get()) {
        createNewChat();
      }

      // Initial status check
      await checkStatus();

      // More frequent checks when status is unknown/building
      statusInterval = setInterval(async () => {
        const currentStatus = backendStatus.get();
        if (currentStatus === 'checking' || currentStatus === 'building') {
          await checkStatus();
        }
      }, 15000); // Check every 15 seconds when building
    });

    onUnmounted(() => {
      if (statusInterval) {
        clearInterval(statusInterval);
      }
      cleanupTypingTimeouts();
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

      // Check current status before proceeding
      const currentStatus = backendStatus.get();

      if (currentStatus !== 'online') {
        let statusMessage;
        switch (currentStatus) {
          case 'checking':
            statusMessage = "Still checking backend status. Please try again in a moment.";
            break;
          case 'building':
            statusMessage = "The backend service is starting up. This may take 1-2 minutes on the first visit.";
            break;
          case 'offline':
            statusMessage = "The backend service is currently offline or rebuilding. Please try again later.";
            break;
          default:
            statusMessage = "Cannot send message: Backend is not ready.";
        }

        addMessageToActiveChat({
          text: statusMessage,
          sender: 'bot',
          model: 'system'
        });
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
      isChatProcessing.set(true);

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
        isChatProcessing.set(false);
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
        isChatProcessing.set(false);
      } else if (hasTypingMessage.value) {
        // If we're in the typing phase, stop the typing for the specific chat
        const typingMessageIndex = messages.value.findIndex(msg => msg.isTyping);
        if (typingMessageIndex !== -1) {
          stopTyping(typingMessageIndex, currentChatId);
          isChatProcessing.set(false);
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

    const handleResearchMessage = () => {
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

      const currentMessages = activeChatMessages.get();

      // If this is the very first message in the chat, update the title
      if (currentMessages.length === 0) {
        updateChatTitle(currentChatId, `Research: ${question}`);
      }

      // Add user message
      addMessageToActiveChat({ text: question, sender: 'user' });

      // Add bot message with custom LMGTFY component
      addMessageToActiveChat({
        text: `Let me Google "${question}" for you...`,
        sender: 'bot',
        model: 'research',
        lmgtfyQuery: question,
        isNewResearch: true  // Explicitly mark as new research to trigger animation
      });

      userInput.value = '';
    };

    return {
      userInput,
      messages,
      isLoading,
      hasTypingMessage,
      selectedModel,
      lastStoppedPrompt,
      backendStatus: backendStatusValue,
      sendMessage,
      handlePromptSelect,
      handleFollowupClick,
      handleImageClick,
      handleResearchMessage,
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

.status-notification {
  padding: 10px;
  margin-bottom: 10px;
  border-radius: 4px;
  text-align: center;
  font-weight: bold;
  border: 1px solid;
}

.status-notification.checking {
  background-color: rgba(209, 236, 241, 0.8);
  color: #0c5460;
  border-color: #0c5460;
}

.status-notification.building {
  background-color: rgba(248, 215, 218, 0.8);
  color: #721c24;
  border-color: #721c24;
}

.status-notification.offline {
  background-color: rgba(248, 215, 218, 0.8);
  color: #721c24;
  border-color: #721c24;
}

.theme-dark .status-notification.checking {
  background-color: rgba(12, 52, 64, 0.8);
  color: #d1ecf1;
  border-color: #0c5460;
}

.theme-dark .status-notification.building {
  background-color: rgba(44, 18, 21, 0.8);
  color: #f8d7da;
  border-color: #721c24;
}

.theme-dark .status-notification.offline {
  background-color: rgba(44, 18, 21, 0.8);
  color: #f8d7da;
  border-color: #721c24;
}
</style>