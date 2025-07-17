import { atom, map, computed } from 'nanostores';

export const allChats = map({});
export const activeChatId = atom(null);

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