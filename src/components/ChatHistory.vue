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
          class="base-icon-button collapse-icon-button"
        >
          <font-awesome-icon
            class="base-icon"
            icon="bars"
          />
        </button>
        <a
          href="/"
          class="base-icon-button"
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
        :disabled="hasTypingMessage || currentChatHasNoMessages || isProcessing"
        :class="{ 'disabled': hasTypingMessage || currentChatHasNoMessages || isProcessing }"
        :title="hasTypingMessage ? 'Cannot create new chat while message is typing' :
                currentChatHasNoMessages ? 'Cannot create new chat when welcome screen is displayed' :
                isProcessing ? 'Cannot create new chat while processing your prompt' :
                'Create new chat'"
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
    <p v-if="isVisible" class="history-heading">Recent</p>
    <div
      :class="{ 'disabled-history-items': hasTypingMessage || isProcessing }"
    >
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
        class="history-item-collapsed"
        @click="toggleVisibility"
      >
        {{ chatList.length }}
      </div>
    </div>
    </div>
    <!-- Add the clear localStorage button at the bottom -->
    <button
      @click="clearLocalStorage"
      class="clear-storage-button"
    >
      <font-awesome-icon
        icon="trash"
        class="base-icon"
      />
      <span
        v-if="isVisible"
        class="ml-2"
      >Clear localStorage</span>
    </button>
    <p
      v-if="isVisible"
      class="text-center text-italic text-sm text-hint"
    >Having issues? Try clearing localStorage.</p>
  </div>
</template>

<script>
import { useStore } from '@nanostores/vue';
import {
  allChats,
  activeChatId,
  createNewChat,
  selectChat,
  isChatHistoryVisible,
  isPendingNewChat
} from '../stores/ai.js';
import { isChatProcessing } from '../stores/ui.js';
import { computed, onMounted, onUnmounted, ref } from 'vue';

export default {
  name: 'ChatHistory',
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
    const isProcessing = useStore(isChatProcessing);

    // Check if any message across ALL chats is currently typing
    const hasTypingMessage = computed(() => {
      const allChatsData = chats.value;

      // Check all chats for typing messages
      for (const chatId in allChatsData) {
        const chat = allChatsData[chatId];
        if (chat.messages && chat.messages.some(msg => msg.isTyping)) {
          return true;
        }
      }

      return false;
    });

    // Add computed property to check if the current chat has no messages
    const currentChatHasNoMessages = computed(() => {
      // If there's no current chat ID, return true (welcome screen is shown)
      if (!currentChatId.value) return true;

      // Get the current chat
      const currentChat = chats.value[currentChatId.value];

      // If the chat doesn't exist or has no messages, return true
      return !currentChat || !currentChat.messages || currentChat.messages.length === 0;
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

    // Track the drawer state before it was collapsed due to screen size
    const wasVisibleBeforeCollapse = ref(null);

    // Function to update visibility based on screen size
    const updateVisibilityForScreenSize = () => {
      if (isMobileSize()) {
        // If we're going to mobile and drawer is currently visible,
        // remember this state before collapsing
        if (isVisible.value && wasVisibleBeforeCollapse.value === null) {
          wasVisibleBeforeCollapse.value = true;
        }
        isChatHistoryVisible.set(false);
      } else {
        // If we're going back to desktop and we had stored a previous state,
        // restore it
        if (wasVisibleBeforeCollapse.value !== null) {
          isChatHistoryVisible.set(wasVisibleBeforeCollapse.value);
          wasVisibleBeforeCollapse.value = null; // Reset the stored state
        }
      }
    };

    // Modified createNewChat function that checks for empty messages and closes the drawer on mobile
    const handleCreateNewChat = () => {
      // Don't allow new chat creation if there's a typing message or if processing
      if (hasTypingMessage.value || isProcessing.value) {
        console.log('Cannot create new chat while message is typing or processing');
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

    // Add the clearLocalStorage function
    const clearLocalStorage = () => {
      if (confirm('Are you sure you want to clear all chat history? This action cannot be undone.')) {
        localStorage.clear();
        window.location.reload(); // Reload the page to reflect changes
      }
    };

    return {
      chatList,
      currentChatId,
      currentChatHasNoMessages,
      hasTypingMessage,
      isProcessing,
      handleCreateNewChat,
      handleSelectChat,
      isVisible,
      toggleVisibility,
      clearLocalStorage
    };
  },
};
</script>

<style scoped>
.chat-history-drawer {
  width: 280px;
  background-color: #111111;
  color: #d1d5db;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #333333;
  flex-shrink: 0;
  transition: width 0.3s ease;
}

.button-group--stacked {
  flex-direction: column;
}

.base-icon-button {
  background: none;
  color: #d1d5db;
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
  background: none !important; /* Keeping !important from original rule */
  margin-bottom: 1rem;
  outline: none;
  color: white;
  cursor: pointer;
  transition: opacity 0.2s ease;
}
.button-group {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.drawer-header {
  margin-bottom: 1rem;
}

.history-heading {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: .75rem;
}

.collapsed .collapse-icon-button {
  margin-bottom: 1rem;
}
.collapsed .history-item-collapsed {
  margin-top: 0 !important;
}




.new-chat-button:disabled,
.new-chat-button.disabled {
  background-color: #333333;
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
  background-color: #222222;
}

.history-item.active {
  background-color: #1c2539;
  font-weight: bold;
  color: #f9fafb;
  padding-left: 1rem;
}

.history-item-collapsed {
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

.history-item-collapsed::after {
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
.disabled-history-items .history-item {
  pointer-events: none;
  opacity: 0.5;
  cursor: not-allowed;
}
/* Add style for the clear localStorage button */
.clear-storage-button {
  margin-top: auto;
  padding: 0.75rem;
  border: none;
  color: #d1d5db;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  border-radius: 4px;
  transition: background-color 0.2s;
  background-color: #222222;
}

.clear-storage-button:hover {
  background-color: #1c1c1c;
  color: #f9fafb;
}

.clear-storage-button .base-icon {
  color: #ff6b6b;
}

.text-hint {
  color: #9ca3af;
  margin-top: 0.5rem;
}
</style>
