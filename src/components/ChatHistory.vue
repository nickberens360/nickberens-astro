<template>
  <div class="chat-history-drawer" :class="`theme-${theme}`">
    <button @click="createNewChat" class="new-chat-button">
      ✏️ New Chat
    </button>
    <p>Recent</p>
    <div class="history-list">
      <div
        v-for="chat in chatList"
        :key="chat.id"
        :class="['history-item', { 'active': chat.id === currentChatId }]"
        @click="selectChat(chat.id)"
      >
        {{ chat.title }}
      </div>
    </div>
  </div>
</template>

<script>
import { useStore } from '@nanostores/vue';
import { allChats, activeChatId, createNewChat, selectChat } from '../stores/ai.js';
import { computed } from 'vue';

export default {
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

    // Convert the map of chats into a sorted array for display (newest first).
    const chatList = computed(() => {
      return Object.values(chats.value).sort((a, b) => b.id.localeCompare(a.id));
    });

    return {
      chatList,
      currentChatId,
      createNewChat,
      selectChat,
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
}
.new-chat-button {
  background-color: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0.75rem;
  font-size: 1rem;
  cursor: pointer;
  margin-bottom: 1rem;
  text-align: center;
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
.theme-dark .history-item:hover {
  background-color: #222222;
}
.theme-dark .history-item.active {
  /*background-color: #333333;*/
  color: #f9fafb;
}
</style>
