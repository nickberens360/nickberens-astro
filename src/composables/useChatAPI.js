// composables/useChatAPI.js
import { ref } from 'vue';

export function useChatAPI() {
  const abortController = ref(null);

  const sendChatMessage = async (question, chatHistory, selectedModel) => {
    // Create abort controller for this request
    abortController.value = new AbortController();

    // Add timeout handling
    const timeoutDuration = 20000; // 20 seconds
    let timeoutId = setTimeout(() => abortController.value.abort(), timeoutDuration);

    const isDev = import.meta.env.DEV || window.location.hostname === 'localhost';
    const apiUrl = isDev
      ? 'http://localhost:8000'
      : 'https://nickberens-astro-api.onrender.com';
      console.log('API URL:', apiUrl);

    try {
      const response = await fetch(`${apiUrl}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          chat_history: chatHistory,
          preferred_model: selectedModel
        }),
        signal: abortController.value.signal
      });

      // Clear the timeout since the request completed
      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorMessage = `Error: ${response.status} ${response.statusText}`;

        try {
          const errorData = await response.json();
          if (errorData.detail) {
            errorMessage = errorData.detail;
          }
        } catch (parseError) {
          // If we can't parse the JSON, just use the status message
        }

        if (response.status === 429) {
          errorMessage = 'Rate limit exceeded. Please wait a moment before sending more messages.';
        }

        throw new Error(errorMessage);
      }

      return await response.json();
    } catch (error) {
      // Clear the timeout in case of error
      clearTimeout(timeoutId);

      // Re-throw the error to be handled by the caller
      if (error.name === 'AbortError') {
        throw new Error('Request timed out. Please try again.');
      }
      throw error;
    }
  };

  const stopLoading = () => {
    if (abortController.value) {
      abortController.value.abort();
      abortController.value = null;
    }
  };

  return {
    sendChatMessage,
    stopLoading,
    abortController
  };
}
