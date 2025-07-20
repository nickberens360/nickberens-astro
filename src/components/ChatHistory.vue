<template>
  <div
    class="chat-history-drawer"
    :class="[`theme-${theme}`, { 'collapsed': !isVisible }]"
  >
    <div class="drawer-header">
      <div
        class="button-group"
        :class="{ 'button-group--stacked': !isVisible }"
      >
        <button
          @click="toggleVisibility"
          class="toggle-button"
        >
          <font-awesome-icon
            class="base-icon"
            icon="bars"
          />
        </button>
        <a href="/"
          @click="toggleVisibility"
          class="toggle-button"
        >
          <font-awesome-icon
            icon="house-chimney"
            class="base-icon"
          />
        </a>

      </div>
      <button
        @click="handleCreateNewChat"
        class="new-chat-button"
        :disabled="hasTypingMessage"
        :class="{ 'disabled': hasTypingMessage }"
        :title="hasTypingMessage ? 'Cannot create new chat while message is typing' : 'Create new chat'"
      >
        <font-awesome-icon
          icon="pen-to-square"
          class="base-icon"
        />
        <span
          v-if="isVisible"
          class="ml-2"
        >New Chat</span>
      </button>
    </div>
    <p v-if="isVisible">Recent</p>
    <div
      v-if="isVisible"
      class="history-list"
    >
      <div
        v-for="chat in chatList"
        :key="chat.id"
        :class="['history-item', { 'active': chat.id === currentChatId }]"
        @click="handleSelectChat(chat.id)"
      >
        {{ chat.title }}
      </div>
    </div>
    <div v-else>
      <div
        class="history-item-mobile mt-4"
        @click="toggleVisibility"
      >
        {{ chatList.length }}
      </div>
      <!--      <div
              v-for="chat in chatList"
              :key="chat.id"
              class="history-item-mobile"
              @click="toggleVisibility"
            >
              ...
            </div>-->
    </div>
  </div>
</template>

<script>
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';
import { useStore } from '@nanostores/vue';
import {
  allChats,
  activeChatId,
  createNewChat,
  selectChat,
  isChatHistoryVisible,
  isPendingNewChat
} from '../stores/ai.js';
import { computed, onMounted, onUnmounted } from 'vue';

export default {
  name: 'ChatHistory',
  components: { FontAwesomeIcon },
  props: {
    theme: {
      type: String,
      default: 'dark',
      validator: (value) => ['light', 'dark'].includes(value)
    }
  },
  setup() {
    const chats = useStore(allChats);
    const currentChatId = useStore(activeChatId);
    const isVisible = useStore(isChatHistoryVisible);

    // Check if any message across ALL chats is currently typing
    const hasTypingMessage = computed(() => {
      const allChatsData = chats.value;

      // Check all chats for typing messages
      for (const chatId in allChatsData) {
        const chat = allChatsData[chatId];
        if (chat.messages && chat.messages.some(msg => msg.isTyping)) {
          console.log(`Found typing message in chat ${chatId}`);
          return true;
        }
      }

      return false;
    });

    // Convert the map of chats into a sorted array for display (newest first).
    const chatList = computed(() => {
      return Object.values(chats.value).sort((a, b) => b.id.localeCompare(a.id));
    });

    const toggleVisibility = () => {
      isChatHistoryVisible.set(!isVisible.value);
    };

    // Function to check if screen is mobile size
    const isMobileSize = () => {
      return window.innerWidth < 768; // Using md breakpoint (768px)
    };

    // Function to update visibility based on screen size
    const updateVisibilityForScreenSize = () => {
      // If mobile size, collapse the chat history
      if (isMobileSize()) {
        isChatHistoryVisible.set(false);
      }
    };

    // Modified createNewChat function that checks for empty messages and closes the drawer on mobile
    const handleCreateNewChat = () => {
      // Don't allow new chat creation if there's a typing message
      if (hasTypingMessage.value) {
        console.log('Cannot create new chat while message is typing');
        return;
      }

      // Get the current active chat
      const currentChat = chats.value[currentChatId.value];

      // If there's no current chat or it has messages, set the pending state
      if (!currentChat || currentChat.messages.length > 0) {
        // Instead of creating a new chat immediately, set the pending state
        isPendingNewChat.set(true);

        // Clear the current chat if it has messages
        if (currentChat && currentChat.messages.length > 0) {
          activeChatId.set(null);
        }
      }

      // If on mobile, close the chat history drawer
      if (isMobileSize()) {
        isChatHistoryVisible.set(false);
      }
    };

    // Add a wrapper for selectChat to close the drawer on mobile
    const handleSelectChat = (chatId) => {
      // Call the original selectChat function
      selectChat(chatId);

      // If on mobile, close the chat history drawer
      if (isMobileSize()) {
        isChatHistoryVisible.set(false);
      }
    };

    // Add resize event listener on component mount
    onMounted(() => {
      // Initial check
      updateVisibilityForScreenSize();

      // Add event listener for window resize
      window.addEventListener('resize', updateVisibilityForScreenSize);
    });

    // Clean up event listener on component unmount
    onUnmounted(() => {
      window.removeEventListener('resize', updateVisibilityForScreenSize);
    });

    return {
      chatList,
      currentChatId,
      hasTypingMessage,
      handleCreateNewChat,
      handleSelectChat,
      isVisible,
      toggleVisibility
    };
  },
};
</script>

<style scoped>
.chat-history-drawer {
  width: 280px;
  background-color: #f9fafb;
  color: #1f2937;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e5e7eb;
  flex-shrink: 0;
  transition: width 0.3s ease;
}

.drawer-header {
  margin-bottom: 1rem;
}

.button-group {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.button-group--stacked {
  flex-direction: column;
}

.toggle-button {
  background: none;
  color: #1f2937;
  border: none;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 12px;
}

.base-icon {
  font-size: 16px;
  transition: transform 0.2s ease;
}

.collapsed {
  width: 50px;
  padding: 1rem 0.5rem;
}

.new-chat-button {
  position: relative;
  left: 4px;
  border: none;
  background: none !important;
  margin-top: 34px;
  outline: none;
  color: white;
  cursor: pointer;
  transition: opacity 0.2s ease;
}

.new-chat-button:disabled,
.new-chat-button.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.new-chat-button:disabled:hover,
.new-chat-button.disabled:hover {
  opacity: 0.5;
}

.history-list {
  overflow-y: auto;
  flex-grow: 1;
}

.history-item {
  padding: 0.75rem;
  border-radius: 100px;
  font-size: 14px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #6c7889;
  transition: background-color 0.2s;
}

.history-item:hover {
  background-color: #e5e7eb;
}

.history-item.active {
  background-color: #1c2539;
  font-weight: bold;
  color: #1f2937;
  padding-left: 1rem;
}

.history-item-mobile {
  display: flex;
  flex-direction: column;
  justify-content: center;
  text-align: center;
  color: #c0c9d4;
  cursor: pointer;
  height: 30px;
  width: 30px;
  border-radius: 50%;
  background-color: #213e6b;
  font-size: 12px;
  font-weight: bold;
  position: relative;
}

.history-item-mobile::after {
  content: '';
  position: absolute;
  width: 0;
  height: 0;
  border-left: 8px solid #213e6b;
  border-top: 8px solid transparent;
  border-bottom: 8px solid transparent;
  right: -3px;
  top: 50%;
  transform: translateY(0) rotate(30deg);
}

/* Dark theme styles */
.theme-dark {
  background-color: #111111;
  color: #d1d5db;
  border-right-color: #333333;
}

.theme-dark .new-chat-button {
  background-color: #333333;
}

.theme-dark .new-chat-button:disabled,
.theme-dark .new-chat-button.disabled {
  background-color: #333333;
  opacity: 0.5;
}

.theme-dark .toggle-button {
  /*background-color: #333333;*/
  color: #d1d5db;
}

.theme-dark .history-item:hover {
  background-color: #222222;
}

.theme-dark .history-item.active {
  /*background-color: #333333;*/
  color: #f9fafb;
}
</style>