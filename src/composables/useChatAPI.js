// composables/useChatAPI.js
import { ref } from 'vue';
import { isBackendOnline, isBackendInitialized, isBackendBuilding, lastStatusCheck, backendStatus, updateBackendStatus } from '../stores/backendStatus.js';

// Helper function to get API URL consistently
const getApiUrl = () => {
  const isDev = import.meta.env.DEV || window.location.hostname === 'localhost';
  return isDev
    ? 'http://localhost:8000'
    : import.meta.env.PUBLIC_API_URL || 'https://nickberens-astro-api.onrender.com';
};

export function useChatAPI() {
  const MAX_TEXT_LENGTH = 1000;
  const TRUNCATION_SUFFIX = '...';
  const abortController = ref(null);

  const checkBackendStatus = async () => {
    // This function is correct and does not need changes
    const now = Date.now();
    const lastCheck = lastStatusCheck.get();
    if (lastCheck && (now - lastCheck) < 5000) {
      return {
        online: isBackendOnline.get(),
        initialized: isBackendInitialized.get(),
        building: isBackendBuilding.get()
      };
    }
    const apiUrl = getApiUrl();
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

  const sendChatMessage = async (question, chatHistory, selectedModel, onChunk, onComplete, onError) => {
    // Pre-flight checks and history processing are unchanged
    await checkBackendStatus();
    const currentStatus = backendStatus.get();
    if (currentStatus !== 'online') {
      let errorMessage;
      switch (currentStatus) {
        case 'building': errorMessage = 'The backend service is starting up. Please try again in a few minutes.'; break;
        default: errorMessage = 'Cannot send message: Backend is not ready.';
      }
      onError(errorMessage);
      return;
    }

    abortController.value = new AbortController();
    const timeoutDuration = 60000;
    let timeoutId = setTimeout(() => abortController.value.abort(), timeoutDuration);

    const apiUrl = getApiUrl();

    try {
      const processedHistory = chatHistory
        .map(msg => ({
          sender: msg.sender === 'bot' ? 'assistant' : msg.sender,
          text: (msg.text || '').substring(0, MAX_TEXT_LENGTH)
        }));

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

      if (!response.ok) {
        // Error handling is unchanged
        let errorMessage = `Error: ${response.status} ${response.statusText}`;
        try { const errorData = await response.json(); if (errorData.detail) errorMessage = errorData.detail; } catch (e) {}
        if (response.status === 429) errorMessage = 'Rate limit exceeded. Please wait a moment.';
        onError(errorMessage);
        return;
      }

      // --- START OF FIX ---
      // Check the content type to decide how to process the response
      const contentType = response.headers.get('content-type');

      if (contentType && contentType.includes('application/json')) {
        // --- HANDLE JSON RESPONSE (for image queries) ---
        const data = await response.json();
        onComplete({
          model: data.model_used,
          followups: data.followup_questions,
          images: data.images,
          isInitial: true
        });
        onChunk(data.answer);
        onComplete({ isFinal: true });

      } else {
        // --- HANDLE STREAMING RESPONSE (for AI text queries) ---
        const modelUsed = response.headers.get('X-Model-Used');
        const followupHeader = response.headers.get('X-Followup-Questions');
        const followupQuestions = followupHeader ? JSON.parse(followupHeader) : [];

        onComplete({ model: modelUsed, followups: followupQuestions, isInitial: true });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          onChunk(chunk);
        }
        onComplete({ isFinal: true });
      }
      // --- END OF FIX ---

      updateBackendStatus({ online: true, initialized: true, building: false });

    } catch (error) {
      clearTimeout(timeoutId);
      let errorMessage = error.message;
      if (error.name === 'AbortError') errorMessage = 'Request timed out or was stopped.';
      onError(errorMessage);
    }
  };

  const stopLoading = () => {
    if (abortController.value) {
      abortController.value.abort();
      abortController.value = null;
    }
  };

  return { sendChatMessage, stopLoading, abortController, checkBackendStatus };
}