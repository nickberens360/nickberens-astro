// composables/useChatAPI.js
import { ref } from 'vue';
import { isBackendOnline, isBackendInitialized, isBackendBuilding, lastStatusCheck, backendStatus, updateBackendStatus } from '../stores/backendStatus.js';

export function useChatAPI() {
  const abortController = ref(null);

  const checkBackendStatus = async () => {
    // Don't check too frequently
    const now = Date.now();
    const lastCheck = lastStatusCheck.get();
    if (lastCheck && (now - lastCheck) < 5000) { // 5 second minimum between checks
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

    // Set status to checking before making the request
    if (isBackendOnline.get() === null) {
      updateBackendStatus({ online: null, initialized: null, building: null });
    }

    try {
      // Add timeout for the status check
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

      const response = await fetch(`${apiUrl}/status`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const status = { online: false, initialized: false, building: false };
        updateBackendStatus(status);
        console.log('Status check result:', status);
        return status;
      }

      const data = await response.json();
      const status = {
        online: true,
        initialized: data.app_initialized,
        building: data.status === "online" && !data.app_initialized
      };

      updateBackendStatus(status);
      console.log('Status check result:', status);
      return status;
    } catch (error) {
      // Different error handling based on error type
      let status;

      if (error.name === 'AbortError') {
        // Timeout occurred
        status = { online: false, initialized: false, building: false };
      } else if (error.message.includes('CORS') ||
                error.message.includes('NetworkError') ||
                error.message.includes('Failed to fetch')) {
        // Network error or CORS error indicates backend is likely building
        status = { online: false, initialized: false, building: true };
      } else {
        // Other errors
        status = { online: false, initialized: false, building: false };
      }

      updateBackendStatus(status);
      console.log('Status check error:', error.message);
      console.log('Status check result:', status);
      return status;
    }
  };

  const sendChatMessage = async (question, chatHistory, selectedModel) => {
    // Pre-flight status check
    await checkBackendStatus();

    // Check current status before proceeding
    const currentStatus = backendStatus.get();
    if (currentStatus !== 'online') {
      let errorMessage;
      switch (currentStatus) {
        case 'checking':
          errorMessage = 'Still checking backend status. Please try again in a moment.';
          break;
        case 'building':
          errorMessage = 'The backend service is starting up. Please try again in a few minutes.';
          break;
        case 'offline':
          errorMessage = 'The backend service is currently offline. Please try again later.';
          break;
        default:
          errorMessage = 'Cannot send message: Backend is not ready.';
      }
      throw new Error(errorMessage);
    }

    // Create abort controller for this request
    abortController.value = new AbortController();

    // Add timeout handling
    const timeoutDuration = 60000; // 60 seconds
    let timeoutId = setTimeout(() => abortController.value.abort(), timeoutDuration);

    const isDev = import.meta.env.DEV || window.location.hostname === 'localhost';
    const apiUrl = isDev
      ? 'http://localhost:8000'
      : 'https://nickberens-astro-api.onrender.com';
    console.log('API URL:', apiUrl);
    console.log('Current backend status before sending:', currentStatus);

    try {
      const response = await fetch(`${apiUrl}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          chat_history: chatHistory.map(msg => ({
            ...msg,
            sender: msg.sender === 'bot' ? 'assistant' : msg.sender
          })),
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
        } else if (response.status === 503) {
          // Service unavailable - likely building or restarting
          updateBackendStatus({ online: false, initialized: false, building: true });
          errorMessage = 'The backend service is currently starting up. Please try again in a few minutes.';
        } else if (response.status >= 500) {
          // Server error - mark as offline
          updateBackendStatus({ online: false, initialized: false, building: false });
          errorMessage = 'The backend service encountered an error. Please try again later.';
        }

        throw new Error(errorMessage);
      }

      const responseData = await response.json();
      updateBackendStatus({ online: true, initialized: true, building: false });
      return responseData;
    } catch (error) {
      // Clear the timeout in case of error
      clearTimeout(timeoutId);

      // Check if it's a CORS error (which often happens during backend builds)
      const isCorsError = error.message.includes('CORS') ||
                          error.message.includes('NetworkError') ||
                          error.message.includes('Failed to fetch');

      if (isCorsError) {
        // Update the backend status store with the new function
        updateBackendStatus({ online: false, initialized: false, building: true });
        throw new Error('The backend service appears to be building or restarting. Please try again in a few minutes.');
      }

      // Re-throw other errors to be handled by the caller
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
    abortController,
    checkBackendStatus
  };
}
