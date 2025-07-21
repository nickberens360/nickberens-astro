// composables/useMessageState.js
import { ref, computed } from 'vue';
import { activeChatMessages, activeChatId, allChats } from '../stores/ai.js';

export function useMessageState() {
  const typingMessages = ref(new Set());
  const typingTimeouts = ref(new Map());
  const typingMessageChats = ref(new Map()); // Track which chat each typing message belongs to

  const hasTypingMessage = computed(() => {
    return activeChatMessages.get().some(msg => msg.isTyping);
  });

  const getTypingSpeed = (char, prevChar) => {
    const baseSpeed = 10; // Base typing speed in ms

    // Slower for punctuation (thinking pauses)
    if (['.', '!', '?', ':'].includes(char)) return baseSpeed + 133;
    if ([',', ';'].includes(char)) return baseSpeed + 67;

    // Slower after punctuation (pause after sentences)
    if (prevChar && ['.', '!', '?'].includes(prevChar)) return baseSpeed + 100;
    if (prevChar && [',', ';'].includes(prevChar)) return baseSpeed + 50;

    // Faster for common letter combinations
    const commonCombos = ['th', 'he', 'in', 'er', 'an', 're', 'ed', 'nd', 'ha', 'at'];
    if (prevChar && commonCombos.includes(prevChar + char)) return baseSpeed - 10;

    // Slower for uppercase letters (shift key)
    if (char === char.toUpperCase() && char !== char.toLowerCase()) return baseSpeed + 13;

    // Add some randomness for natural feel
    const randomVariation = Math.random() * 10 - 5;

    return Math.max(13, baseSpeed + randomVariation);
  };

  const updateMessageTyping = (messageIndex, fullText, targetChatId) => {
    return new Promise((resolve) => {
      typingMessages.value.add(messageIndex);
      typingMessageChats.value.set(messageIndex, targetChatId); // Track the chat for this message
      let currentText = '';
      let currentIndex = 0;

      const typeChar = () => {
        // Check if typing was stopped
        if (!typingMessages.value.has(messageIndex)) {
          cleanupTypingTimeouts();
          resolve();
          return;
        }

        if (currentIndex < fullText.length) {
          const char = fullText[currentIndex];
          const prevChar = currentIndex > 0 ? fullText[currentIndex - 1] : null;

          currentText += char;

          // Update the message in the SPECIFIC chat (not necessarily the active one)
          const targetChat = allChats.get()[targetChatId];
          if (targetChat && targetChat.messages[messageIndex]) {
            const updatedMessages = [...targetChat.messages];
            updatedMessages[messageIndex] = {
              ...updatedMessages[messageIndex],
              text: currentText,
              isTyping: true
            };

            allChats.setKey(targetChatId, {
              ...targetChat,
              messages: updatedMessages
            });
          }

          currentIndex++;
          const nextSpeed = getTypingSpeed(char, prevChar);
          const timeoutId = setTimeout(typeChar, nextSpeed);
          typingTimeouts.value.set(messageIndex, timeoutId);
        } else {
          // Typing complete naturally (not stopped)
          typingMessages.value.delete(messageIndex);
          typingTimeouts.value.delete(messageIndex);
          typingMessageChats.value.delete(messageIndex); // Clean up chat tracking

          const targetChat = allChats.get()[targetChatId];
          if (targetChat && targetChat.messages[messageIndex]) {
            const updatedMessages = [...targetChat.messages];
            updatedMessages[messageIndex] = {
              ...updatedMessages[messageIndex],
              isTyping: false,
              wasStopped: false
            };

            allChats.setKey(targetChatId, {
              ...targetChat,
              messages: updatedMessages
            });
          }
          resolve();
        }
      };

      // Start typing after a brief pause (simulating thinking)
      const initialTimeoutId = setTimeout(typeChar, 333);
      typingTimeouts.value.set(messageIndex, initialTimeoutId);
    });
  };

  const cleanupTypingTimeouts = () => {
    // Clear all active timeouts
    for (const [messageIndex, timeoutId] of typingTimeouts.value.entries()) {
      clearTimeout(timeoutId);
      typingTimeouts.value.delete(messageIndex);
    }

    // Clear typing messages tracking
    typingMessages.value.clear();
    typingMessageChats.value.clear();
  };

  const stopTyping = (messageIndex, targetChatId) => {
    // Clear the timeout for this message
    if (typingTimeouts.value.has(messageIndex)) {
      clearTimeout(typingTimeouts.value.get(messageIndex));
      typingTimeouts.value.delete(messageIndex);
    }

    // Remove from typing messages set and clean up chat tracking
    typingMessages.value.delete(messageIndex);
    typingMessageChats.value.delete(messageIndex);

    // Update the message in the SPECIFIC chat to show it's no longer typing and was stopped
    const targetChat = allChats.get()[targetChatId];
    if (targetChat && targetChat.messages[messageIndex]) {
      const updatedMessages = [...targetChat.messages];
      updatedMessages[messageIndex] = {
        ...updatedMessages[messageIndex],
        isTyping: false,
        wasStopped: true
      };

      allChats.setKey(targetChatId, {
        ...targetChat,
        messages: updatedMessages
      });
    }
  };

  return {
    typingMessages,
    typingTimeouts,
    typingMessageChats,
    hasTypingMessage,
    updateMessageTyping,
    stopTyping,
    cleanupTypingTimeouts
  };
}
