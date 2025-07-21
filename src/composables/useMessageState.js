// composables/useMessageState.js
import { ref, computed } from 'vue';
import { activeChatMessages, activeChatId, allChats } from '../stores/ai.js';

export function useMessageState() {
  const typingMessages = ref(new Set());
  const typingTimeouts = ref(new Map());
  const typingMessageChats = ref(new Map()); // Track which chat each typing message belongs to

  // Speed multiplier - adjust this single value to change all typing speeds
  // Values > 1 will slow down typing (longer delays)
  // Values < 1 will speed up typing (shorter delays)
  // Value of 1 maintains the original speed
  const SPEED_MULTIPLIER = 1.0;

  // Base values for typing speeds (original values)
  const BASE_TYPING_VALUES = {
    BASE_SPEED: 10,                // Base typing speed in ms
    MAJOR_PUNCTUATION_DELAY: 133,  // Extra delay for period, exclamation, question mark, colon
    MINOR_PUNCTUATION_DELAY: 67,   // Extra delay for comma, semicolon
    AFTER_MAJOR_PUNCT_DELAY: 100,  // Extra delay after period, exclamation, question mark
    AFTER_MINOR_PUNCT_DELAY: 50,   // Extra delay after comma, semicolon
    COMMON_COMBO_BOOST: 10,        // Speed boost for common letter combinations
    UPPERCASE_DELAY: 13,           // Extra delay for uppercase letters (shift key)
    RANDOM_VARIATION_RANGE: 10,    // Range for random variation (±5)
    RANDOM_VARIATION_OFFSET: 5,    // Offset for random variation
    MIN_TYPING_SPEED: 13,          // Minimum typing speed
    INITIAL_TYPING_DELAY: 333      // Initial delay before typing starts
  };

  // Typing speed constants - calculated based on base values and the speed multiplier
  const TYPING_CONSTANTS = {
    BASE_SPEED: Math.round(BASE_TYPING_VALUES.BASE_SPEED * SPEED_MULTIPLIER),
    MAJOR_PUNCTUATION_DELAY: Math.round(BASE_TYPING_VALUES.MAJOR_PUNCTUATION_DELAY * SPEED_MULTIPLIER),
    MINOR_PUNCTUATION_DELAY: Math.round(BASE_TYPING_VALUES.MINOR_PUNCTUATION_DELAY * SPEED_MULTIPLIER),
    AFTER_MAJOR_PUNCT_DELAY: Math.round(BASE_TYPING_VALUES.AFTER_MAJOR_PUNCT_DELAY * SPEED_MULTIPLIER),
    AFTER_MINOR_PUNCT_DELAY: Math.round(BASE_TYPING_VALUES.AFTER_MINOR_PUNCT_DELAY * SPEED_MULTIPLIER),
    COMMON_COMBO_BOOST: Math.round(BASE_TYPING_VALUES.COMMON_COMBO_BOOST * SPEED_MULTIPLIER),
    UPPERCASE_DELAY: Math.round(BASE_TYPING_VALUES.UPPERCASE_DELAY * SPEED_MULTIPLIER),
    RANDOM_VARIATION_RANGE: Math.round(BASE_TYPING_VALUES.RANDOM_VARIATION_RANGE * SPEED_MULTIPLIER),
    RANDOM_VARIATION_OFFSET: Math.round(BASE_TYPING_VALUES.RANDOM_VARIATION_OFFSET * SPEED_MULTIPLIER),
    MIN_TYPING_SPEED: Math.round(BASE_TYPING_VALUES.MIN_TYPING_SPEED * SPEED_MULTIPLIER),
    INITIAL_TYPING_DELAY: Math.round(BASE_TYPING_VALUES.INITIAL_TYPING_DELAY * SPEED_MULTIPLIER)
  };

  const hasTypingMessage = computed(() => {
    return activeChatMessages.get().some(msg => msg.isTyping);
  });

  const getTypingSpeed = (char, prevChar) => {
    const baseSpeed = TYPING_CONSTANTS.BASE_SPEED;

    // Slower for punctuation (thinking pauses)
    if (['.', '!', '?', ':'].includes(char)) return baseSpeed + TYPING_CONSTANTS.MAJOR_PUNCTUATION_DELAY;
    if ([',', ';'].includes(char)) return baseSpeed + TYPING_CONSTANTS.MINOR_PUNCTUATION_DELAY;

    // Slower after punctuation (pause after sentences)
    if (prevChar && ['.', '!', '?'].includes(prevChar)) return baseSpeed + TYPING_CONSTANTS.AFTER_MAJOR_PUNCT_DELAY;
    if (prevChar && [',', ';'].includes(prevChar)) return baseSpeed + TYPING_CONSTANTS.AFTER_MINOR_PUNCT_DELAY;

    // Faster for common letter combinations
    const commonCombos = ['th', 'he', 'in', 'er', 'an', 're', 'ed', 'nd', 'ha', 'at'];
    if (prevChar && commonCombos.includes(prevChar + char)) return baseSpeed - TYPING_CONSTANTS.COMMON_COMBO_BOOST;

    // Slower for uppercase letters (shift key)
    if (char === char.toUpperCase() && char !== char.toLowerCase()) return baseSpeed + TYPING_CONSTANTS.UPPERCASE_DELAY;

    // Add some randomness for natural feel
    const randomVariation = Math.random() * TYPING_CONSTANTS.RANDOM_VARIATION_RANGE - TYPING_CONSTANTS.RANDOM_VARIATION_OFFSET;

    return Math.max(TYPING_CONSTANTS.MIN_TYPING_SPEED, baseSpeed + randomVariation);
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
      const initialTimeoutId = setTimeout(typeChar, TYPING_CONSTANTS.INITIAL_TYPING_DELAY);
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
