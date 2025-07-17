import { atom, map, computed } from 'nanostores';

// Helper to check if we're in a browser environment
const isBrowser = () => typeof window !== 'undefined' && typeof localStorage !== 'undefined';

// --- Load chat data from localStorage or use default ---
const loadChats = () => {
  if (isBrowser()) {
    try {
      const savedChats = localStorage.getItem('allChats');
      if (savedChats) {
        return JSON.parse(savedChats);
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  }
  return {}; // Default empty chats object
};

// --- Load active chat ID from localStorage or use default ---
const loadActiveChatId = () => {
  if (isBrowser()) {
    try {
      const savedId = localStorage.getItem('activeChatId');
      if (savedId) {
        return savedId;
      }
    } catch (error) {
      console.error('Error loading active chat ID:', error);
    }
  }
  return null; // Default to no active chat
};

// --- Load chat history visibility state from localStorage or use default ---
const loadChatHistoryVisibility = () => {
  if (isBrowser()) {
    try {
      const savedVisibility = localStorage.getItem('isChatHistoryVisible');
      if (savedVisibility !== null) {
        return JSON.parse(savedVisibility);
      }
    } catch (error) {
      console.error('Error loading chat history visibility:', error);
    }
  }
  return true; // Default to visible
};

// Initialize stores with persisted data
export const allChats = map(loadChats());
export const activeChatId = atom(loadActiveChatId());
export const isChatHistoryVisible = atom(loadChatHistoryVisibility());

// Subscribe to changes and save to localStorage
allChats.listen((value) => {
  if (isBrowser()) {
    try {
      localStorage.setItem('allChats', JSON.stringify(value));
    } catch (error) {
      console.error('Error saving chat history:', error);
    }
  }
});

activeChatId.listen((value) => {
  if (isBrowser()) {
    try {
      localStorage.setItem('activeChatId', value);
    } catch (error) {
      console.error('Error saving active chat ID:', error);
    }
  }
});

isChatHistoryVisible.listen((value) => {
  if (isBrowser()) {
    try {
      localStorage.setItem('isChatHistoryVisible', JSON.stringify(value));
    } catch (error) {
      console.error('Error saving chat history visibility:', error);
    }
  }
});

export const activeChat = computed([allChats, activeChatId], (chats, id) => {
  return id ? chats[id] : null;
});

export const activeChatMessages = computed(activeChat, (chat) => {
  return chat ? chat.messages : [];
});

export function createNewChat() {
  const newId = Date.now().toString();
  const newChat = {
    id: newId,
    // Start with a generic title. This will be updated later.
    title: "New Chat",
    messages: [],
  };

  allChats.setKey(newId, newChat);
  activeChatId.set(newId);
  return newId;
}

export function selectChat(chatId) {
  activeChatId.set(chatId);
}

export function addMessageToActiveChat(message) {
    const currentChat = activeChat.get();
    if (currentChat) {
        const updatedMessages = [...currentChat.messages, message];
        allChats.setKey(currentChat.id, { ...currentChat, messages: updatedMessages });
    }
}

// --- NEW: A function to update a chat's title ---
export function updateChatTitle(chatId, newTitle) {
    const chat = allChats.get()[chatId];
    if (chat) {
        allChats.setKey(chatId, { ...chat, title: newTitle });
    }
}
