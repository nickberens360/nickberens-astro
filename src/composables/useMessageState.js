// composables/useMessageState.js
import { ref, computed } from 'vue';
import { activeChatMessages, activeChatId, allChats } from '../stores/ai.js';

export function useMessageState() {
  const typingMessages = ref(new Set());
  const typingTimeouts = ref(new Map());

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

  const updateMessageTyping = (messageIndex, fullText) => {
    return new Promise((resolve) => {
      console.log(`Starting typing animation for message ${messageIndex}`);
      typingMessages.value.add(messageIndex);
      let currentText = '';
      let currentIndex = 0;

      const typeChar = () => {
        // Check if typing was stopped
        if (!typingMessages.value.has(messageIndex)) {
          console.log(`Typing stopped for message ${messageIndex}`);
          resolve();
          return;
        }

        if (currentIndex < fullText.length) {
          const char = fullText[currentIndex];
          const prevChar = currentIndex > 0 ? fullText[currentIndex - 1] : null;

          currentText += char;

          // Update the message in the store
          const currentMessages = activeChatMessages.get();
          const updatedMessages = [...currentMessages];
          if (updatedMessages[messageIndex]) {
            updatedMessages[messageIndex] = {
              ...updatedMessages[messageIndex],
              text: currentText,
              isTyping: true
            };

            const currentChatId = activeChatId.get();
            const currentChat = allChats.get()[currentChatId];
            if (currentChat) {
              allChats.setKey(currentChatId, {
                ...currentChat,
                messages: updatedMessages
              });
            }
          }

          currentIndex++;
          const nextSpeed = getTypingSpeed(char, prevChar);
          const timeoutId = setTimeout(typeChar, nextSpeed);
          typingTimeouts.value.set(messageIndex, timeoutId);
        } else {
          // Typing complete naturally (not stopped)
          console.log(`Typing completed naturally for message ${messageIndex}`);
          typingMessages.value.delete(messageIndex);
          typingTimeouts.value.delete(messageIndex);

          const currentMessages = activeChatMessages.get();
          const updatedMessages = [...currentMessages];
          if (updatedMessages[messageIndex]) {
            updatedMessages[messageIndex] = {
              ...updatedMessages[messageIndex],
              isTyping: false,
              wasStopped: false
            };

            const currentChatId = activeChatId.get();
            const currentChat = allChats.get()[currentChatId];
            if (currentChat) {
              allChats.setKey(currentChatId, {
                ...currentChat,
                messages: updatedMessages
              });
            }
          }
          resolve();
        }
      };

      // Start typing after a brief pause (simulating thinking)
      const initialTimeoutId = setTimeout(typeChar, 333);
      typingTimeouts.value.set(messageIndex, initialTimeoutId);
    });
  };

  const stopTyping = (messageIndex) => {
    console.log(`Stopping typing for message ${messageIndex}`);

    // Clear the timeout for this message
    if (typingTimeouts.value.has(messageIndex)) {
      clearTimeout(typingTimeouts.value.get(messageIndex));
      typingTimeouts.value.delete(messageIndex);
    }

    // Remove from typing messages set
    typingMessages.value.delete(messageIndex);

    // Update the message to show it's no longer typing and was stopped
    const currentMessages = activeChatMessages.get();
    const updatedMessages = [...currentMessages];
    if (updatedMessages[messageIndex]) {
      updatedMessages[messageIndex] = {
        ...updatedMessages[messageIndex],
        isTyping: false,
        wasStopped: true
      };

      const currentChatId = activeChatId.get();
      const currentChat = allChats.get()[currentChatId];
      if (currentChat) {
        allChats.setKey(currentChatId, {
          ...currentChat,
          messages: updatedMessages
        });
      }
    }
  };

  return {
    typingMessages,
    typingTimeouts,
    hasTypingMessage,
    updateMessageTyping,
    stopTyping
  };
}