<template>
  <div
    class="chatbot-container"
    :class="`theme-${theme}`"
  >
    <div
      v-if="backendStatus === 'checking'"
      class="status-notification checking"
    >
      <p>🔄 Checking backend status...</p>
    </div>
    <div
      v-else-if="backendStatus === 'offline'"
      class="status-notification offline"
    >
      <p>❌ Backend service is currently offline. Please try again later.</p>
    </div>

    <ChatMessageList
      :messages="messages"
      :is-loading="isLoading"
      :has-typing-message="hasTypingMessage"
      :theme="theme"
      :backend-status="backendStatus"
      :chat-id="chatId"
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

    <ImageOverlay/>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useStore } from '@nanostores/vue';
import {
  activeChatId,
  activeChatMessages,
  addMessageToActiveChat,
  createNewChat,
  updateChatTitle,
  isPendingNewChat,
  updateMessageInActiveChat
} from '../stores/ai.js';
import { openImageOverlay, isChatProcessing } from '../stores/ui.js';
import { backendStatus } from '../stores/backendStatus.js';
import { useChatAPI } from '../composables/useChatAPI.js';
import ChatMessageList from './ChatMessageList.vue';
import ChatInput from './ChatInput.vue';
import ImageOverlay from './ImageOverlay.vue';

export default {
  name: 'ChatBot',
  components: { ChatMessageList, ChatInput, ImageOverlay },
  props: {
    theme: { type: String, default: 'dark' }
  },
  setup() {
    const userInput = ref('');
    const isLoading = ref(false); // Used briefly before the stream starts
    const messages = useStore(activeChatMessages);
    const chatId = useStore(activeChatId);
    const pendingNewChat = useStore(isPendingNewChat);
    const lastStoppedPrompt = ref('');
    const selectedModel = ref('claude');
    const backendStatusValue = useStore(backendStatus);

    const { sendChatMessage, stopLoading, checkBackendStatus } = useChatAPI();

    const hasTypingMessage = computed(() => messages.value.some(msg => msg.isTyping));

    let statusInterval = null;
    onMounted(async () => {
      if (!activeChatId.get() && !isPendingNewChat.get()) createNewChat();
      await checkBackendStatus();
      statusInterval = setInterval(checkBackendStatus, 15000);
    });
    onUnmounted(() => {
      if (statusInterval) clearInterval(statusInterval);
    });

    watch(userInput, (newValue) => {
      if (newValue.trim()) lastStoppedPrompt.value = '';
    });

    const sendMessage = async () => {
      if (userInput.value.trim() === '' && lastStoppedPrompt.value) {
        userInput.value = lastStoppedPrompt.value;
        lastStoppedPrompt.value = '';
      }
      if (!userInput.value.trim() || hasTypingMessage.value || backendStatusValue.value !== 'online') return;

      const currentChatId = activeChatId.get() || createNewChat();
      const chatHistoryForAPI = activeChatMessages.get().slice(-10); // Send last 10 messages
      if (activeChatMessages.get().length === 0) updateChatTitle(currentChatId, userInput.value);

      const question = userInput.value;
      addMessageToActiveChat({ text: question, sender: 'user' });
      userInput.value = '';

      isLoading.value = true;
      isChatProcessing.set(true);

      addMessageToActiveChat({ text: '', sender: 'bot', isTyping: true });
      const botMessageIndex = activeChatMessages.get().length - 1;

      const onChunk = (chunk) => {
        isLoading.value = false; // Stop loading indicator once first chunk arrives
        const currentMessages = activeChatMessages.get();
        const msg = currentMessages[botMessageIndex];
        if (msg) {
          msg.text += chunk;
          updateMessageInActiveChat(botMessageIndex, msg);
        }
      };

      const onComplete = ({ model, followups, images, isInitial, isFinal }) => {
        const currentMessages = activeChatMessages.get();
        const msg = currentMessages[botMessageIndex];
        if (!msg) return;

        if (isInitial) {
          msg.model = model;
          msg.followup_questions = followups;
          msg.images = images;
        }
        if (isFinal) {
          msg.isTyping = false;
          isChatProcessing.set(false);
        }
        updateMessageInActiveChat(botMessageIndex, msg);
      };

      const onError = (errorMessage) => {
        const currentMessages = activeChatMessages.get();
        const msg = currentMessages[botMessageIndex];
        if (msg) {
          msg.text = errorMessage;
          msg.isTyping = false;
          msg.model = 'error';
          updateMessageInActiveChat(botMessageIndex, msg);
        }
        isLoading.value = false;
        isChatProcessing.set(false);
      };

      await sendChatMessage(question, chatHistoryForAPI, selectedModel.value, onChunk, onComplete, onError);
    };

    const stopCurrentAction = () => {
      stopLoading(); // Aborts the fetch request
      isChatProcessing.set(false);
      isLoading.value = false;

      const typingMessageIndex = messages.value.findIndex(msg => msg.isTyping);
      if (typingMessageIndex !== -1) {
        const msg = messages.value[typingMessageIndex];
        msg.isTyping = false;
        msg.wasStopped = true;
        updateMessageInActiveChat(typingMessageIndex, msg);
      }
    };

    const handlePromptSelect = (prompt) => {
      userInput.value = prompt;
      sendMessage();
    };

    const handleFollowupClick = (question) => {
      userInput.value = question;
      sendMessage();
    };

    const handleImageClick = (src) => {
      openImageOverlay(src);
    };

    const handleResearchMessage = () => {
      if (!userInput.value.trim()) return;
      const currentChatId = activeChatId.get() || createNewChat();
      if (activeChatMessages.get().length === 0) updateChatTitle(currentChatId, `Research: ${userInput.value}`);
      const question = userInput.value;
      addMessageToActiveChat({ text: question, sender: 'user' });
      userInput.value = '';
      addMessageToActiveChat({
        text: `Let me research "${question}" for you...`,
        sender: 'bot',
        model: 'research',
        lmgtfyQuery: question,
        isNewResearch: true
      });
    };

    return {
      userInput,
      messages,
      isLoading,
      hasTypingMessage,
      selectedModel,
      lastStoppedPrompt,
      backendStatus: backendStatusValue,
      chatId,
      sendMessage,
      stopCurrentAction,
      handlePromptSelect,
      handleFollowupClick,
      handleImageClick,
      handleResearchMessage
    };
  },
};
</script>

<style scoped>
/* Scoped styles are unchanged */
.chatbot-container {
  display: flex;
  flex-direction: column;
  flex-grow: 1;
  background-color: #1a1a1a;
  overflow: hidden;
}

.status-notification {
  padding: 10px;
  text-align: center;
  font-weight: bold;
}

.status-notification.checking {
  background-color: #334155;
  color: #f1f5f9;
}

.status-notification.offline {
  background-color: #7f1d1d;
  color: #fecaca;
}
</style>