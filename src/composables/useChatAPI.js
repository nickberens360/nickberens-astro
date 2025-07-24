// composables/useChatAPI.js
import { ref } from 'vue';
import { isBackendOnline, isBackendInitialized, isBackendBuilding, lastStatusCheck, backendStatus, updateBackendStatus } from '../stores/backendStatus.js';

export function useChatAPI() {
  // Constants for text truncation
  const MAX_TEXT_LENGTH = 1000;
  const TRUNCATION_SUFFIX = '...';

  const abortController = ref(null);

  // This function does not need changes.
  const checkBackendStatus = async () => {
    const now = Date.now();
    const lastCheck = lastStatusCheck.get();
    if (lastCheck && (now - lastCheck) < 5000) {
      return {
        online: isBackendOnline.get(),
        initialized: isBackendInitialized.get(),
        building: isBackendBuilding.get()
      };
    }

    const isDev = import.meta.env.DEV || window.location.hostname === 'localhost';
    const apiUrl = isDev
      ? 'http://localhost:8000'
      : 'https://nickberens-astro-api.onrender.com';

    if (isBackendOnline.get() === null && isBackendInitialized.get() === null && isBackendBuilding.get() === null) {
      updateBackendStatus({ online: null, initialized: null, building: null });
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000);

      const response = await fetch(`${apiUrl}/status`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const status = { online: false, initialized: false, building: false };
        updateBackendStatus(status);
        return status;
      }

      const data = await response.json();
      const status = {
        online: true,
        initialized: data.app_initialized,
        building: data.status === "online" && !data.app_initialized
      };

      updateBackendStatus(status);
      return status;
    } catch (error) {
      let status;
      if (error.name === 'AbortError') {
        status = { online: false, initialized: false, building: false };
      } else if (error.message.includes('CORS') || error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
        status = { online: false, initialized: false, building: true };
      } else {
        status = { online: false, initialized: false, building: false };
      }
      updateBackendStatus(status);
      return status;
    }
  };

  // --- MODIFIED FUNCTION ---
  const sendChatMessage = async (question, chatHistory, selectedModel, onChunk, onComplete, onError) => {
    await checkBackendStatus();

    const currentStatus = backendStatus.get();
    if (currentStatus !== 'online') {
      let errorMessage;
      switch (currentStatus) {
        case 'checking': errorMessage = 'Still checking backend status. Please try again in a moment.'; break;
        case 'building': errorMessage = 'The backend service is starting up. Please try again in a few minutes.'; break;
        case 'offline': errorMessage = 'The backend service is currently offline. Please try again later.'; break;
        default: errorMessage = 'Cannot send message: Backend is not ready.';
      }
      // Use the onError callback instead of throwing
      onError(errorMessage);
      return;
    }

    abortController.value = new AbortController();
    const timeoutDuration = 60000;
    let timeoutId = setTimeout(() => abortController.value.abort(), timeoutDuration);

    const isDev = import.meta.env.DEV || window.location.hostname === 'localhost';
    const apiUrl = isDev
      ? 'http://localhost:8000'
      : import.meta.env.PUBLIC_API_URL || 'https://nickberens-astro-api.onrender.com';

    try {
      // Your robust history processing logic is preserved
      const processedHistory = chatHistory
        .filter(msg => {
          if (!msg?.sender) return false;
          const hasValidText = msg.text?.trim()?.length > 0;
          const hasBotContent = msg.sender === 'bot' && (msg.images?.length > 0 || msg.followup_questions?.length > 0);
          return hasValidText || hasBotContent;
        })
        .map(msg => {
          let text = msg.text?.trim() || '';
          if (text.length > MAX_TEXT_LENGTH) {
            text = text.substring(0, MAX_TEXT_LENGTH - TRUNCATION_SUFFIX.length) + TRUNCATION_SUFFIX;
          }
          return {
            sender: msg.sender === 'bot' ? 'assistant' : msg.sender,
            text: text
          };
        });

      const response = await fetch(`${apiUrl}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: question,
          chat_history: processedHistory,
          preferred_model: selectedModel
        }),
        signal: abortController.value.signal
      });

      clearTimeout(timeoutId);

      // --- START of streaming changes ---

      if (!response.ok) {
        let errorMessage = `Error: ${response.status} ${response.statusText}`;
        try {
          const errorData = await response.json();
          if (errorData.detail) errorMessage = errorData.detail;
        } catch (parseError) {}

        if (response.status === 429) errorMessage = 'Rate limit exceeded. Please wait a moment.';
        else if (response.status === 503) {
          updateBackendStatus({ online: false, initialized: false, building: true });
          errorMessage = 'The backend service is currently starting up. Please try again.';
        } else if (response.status >= 500) {
          updateBackendStatus({ online: false, initialized: false, building: false });
          errorMessage = 'The backend service encountered an error. Please try again later.';
        }
        // Use onError callback
        onError(errorMessage);
        return;
      }

      // Handle metadata from headers first
      const modelUsed = response.headers.get('X-Model-Used');
      const followupHeader = response.headers.get('X-Followup-Questions');
      const followupQuestions = followupHeader ? JSON.parse(followupHeader) : [];

      // Signal that metadata has been received
      onComplete({ model: modelUsed, followups: followupQuestions, isInitial: true });

      // Process the text stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        onChunk(chunk);
      }

      // Signal that the stream has finished
      onComplete({ isFinal: true });
      updateBackendStatus({ online: true, initialized: true, building: false });

      // --- END of streaming changes ---

    } catch (error) {
      clearTimeout(timeoutId);

      const isCorsError = error.message.includes('CORS') || error.message.includes('NetworkError') || error.message.includes('Failed to fetch');
      let errorMessage = error.message;

      if (isCorsError) {
        updateBackendStatus({ online: false, initialized: false, building: true });
        errorMessage = 'The backend service seems to be restarting. Please try again in a moment.';
      } else if (error.name === 'AbortError') {
        errorMessage = 'Request timed out or was stopped.';
      }

      // Use onError callback for all errors
      onError(errorMessage);
    }
  };

  // This function does not need changes.
  const stopLoading = () => {
    if (abortController.value) {
      abortController.value.abort();
      abortController.value = null;
    }
  };

  return {
    sendChatMessage,
    stopLoading,
    abortController,
    checkBackendStatus
  };
}