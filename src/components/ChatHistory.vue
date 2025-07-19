<template>
  <div
    class="chat-history-drawer"
    :class="[`theme-${theme}`, { 'collapsed': !isVisible }]"
  >
    <div class="drawer-header">
      <button
        @click="toggleVisibility"
        class="toggle-button"
      >
        <font-awesome-icon
          :icon="['fas', 'bars']"
        />
      </button>
      <button
        v-if="isVisible"
        @click="createNewChat"
        class="new-chat-button"
      >
        New Chat
      </button>
    </div>
    <button
      v-if="!isVisible"
      class="toggle-button"
      @click="createNewChat"
    >
      ✏️
    </button>
    <p v-if="isVisible">Recent</p>
    <div
      v-if="isVisible"
      class="history-list"
    >
      <div
        v-for="chat in chatList"
        :key="chat.id"
        :class="['history-item', { 'active': chat.id === currentChatId }]"
        @click="selectChat(chat.id)"
      >
        {{ chat.title }}
      </div>
    </div>
    <div v-else>
      <div
        v-for="chat in chatList"
        :key="chat.id"
      >
        ...
      </div>
    </div>
  </div>
</template>

<script>
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';
import { useStore } from '@nanostores/vue';
import { allChats, activeChatId, createNewChat, selectChat, isChatHistoryVisible, isPendingNewChat } from '../stores/ai.js';
import { computed, onMounted, onUnmounted } from 'vue';

export default {
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
      createNewChat: handleCreateNewChat, // Replace with our wrapper function
      selectChat: handleSelectChat, // Use our wrapper function instead of the original
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
  /*display: flex;
  justify-content: space-between;
  align-items: center;*/
  margin-bottom: 1rem;
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

.collapsed {
  width: 50px;
  padding: 1rem 0.5rem;
}

.new-chat-button {
  border: none;
  background: none !important;
  font-weight: bold;
  font-size: 18px;
  margin-top: 34px;
  outline: none;
  color: white;
  cursor: pointer;
}

.history-list {
  overflow-y: auto;
  flex-grow: 1;
}

.history-item {
  padding: 0.75rem;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: background-color 0.2s;
}

.history-item:hover {
  background-color: #e5e7eb;
}

.history-item.active {
  /*background-color: #d1d5db;*/
  font-weight: bold;
  color: #1f2937;
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
