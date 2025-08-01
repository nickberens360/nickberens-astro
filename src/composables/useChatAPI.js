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
  const isUserStopped = ref(false);

  // Add rate limit state
  const rateLimits = ref({
    claude: false,
    gemini: false
  });

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
      const response = await fetch(`${apiUrl}/health`, {
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
        initialized: data.rag_system === "initialized",
        building: data.status === "healthy" && data.rag_system === "not_initialized"
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

  // Rate limits function - simplified since /rate-limits endpoint no longer exists
  const checkRateLimits = async () => {
    // Return default rate limits since the endpoint is no longer available
    // The new backend handles rate limiting internally and will provide updates via response headers
    const defaultLimits = { claude: false, gemini: false };
    rateLimits.value = { ...rateLimits.value, ...defaultLimits };
    return defaultLimits;
  };

  const sendChatMessage = async (question, chatHistory, selectedModel, onChunk, onComplete, onError, onStop) => {
    // Reset the user stopped flag for new requests
    isUserStopped.value = false;

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
        .filter(msg =>
          (typeof msg.text === 'string' && msg.text.trim().length > 0) || // Include messages with valid text
          (msg.images && msg.images.length > 0) || // Include messages with images
          (msg.followups && msg.followups.length > 0) // Include messages with follow-up questions
        )
        .map(msg => ({
          sender: msg.sender === 'bot' ? 'assistant' : msg.sender,
          text: msg.text ? msg.text.substring(0, MAX_TEXT_LENGTH) : '' // Ensure text is handled safely
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

      // Extract rate limits from headers
      const rateLimitsHeader = response.headers.get('X-Rate-Limits');
      if (rateLimitsHeader) {
        try {
          const newRateLimits = JSON.parse(rateLimitsHeader);
          rateLimits.value = { ...rateLimits.value, ...newRateLimits };
        } catch (e) {
          console.warn('Failed to parse rate limits from header:', e);
        }
      }

      // Check the content type to decide how to process the response
      const contentType = response.headers.get('content-type');

      if (contentType && contentType.includes('application/json')) {
        // --- HANDLE JSON RESPONSE (for Auto-RAG and image queries) ---
        const data = await response.json();

        // Update rate limits from JSON response if available
        if (data.rate_limits) {
          rateLimits.value = { ...rateLimits.value, ...data.rate_limits };
        }

        onComplete({
          model: data.model_used || 'auto-rag',
          followups: data.followup_questions || [],
          images: data.images || [],
          rateLimits: rateLimits.value,
          isInitial: true
        });

        // Handle both old format (answer) and new Auto-RAG format (response)
        const responseText = data.answer || data.response || '';
        onChunk(responseText);
        onComplete({ isFinal: true });

      } else {
        // --- HANDLE STREAMING RESPONSE (for AI text queries) ---
        const modelUsed = response.headers.get('X-Model-Used');
        const followupHeader = response.headers.get('X-Followup-Questions');
        const followupQuestions = followupHeader ? JSON.parse(followupHeader) : [];

        onComplete({
          model: modelUsed,
          followups: followupQuestions,
          rateLimits: rateLimits.value,
          isInitial: true
        });

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

      updateBackendStatus({ online: true, initialized: true, building: false });

    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError' && isUserStopped.value) {
        // User manually stopped the request
        if (onStop) {
          onStop('Message paused');
        }
      } else {
        // Actual error or timeout
        let errorMessage = error.message;
        if (error.name === 'AbortError') errorMessage = 'Request timed out.';
        onError(errorMessage);
      }
    }
  };

  const stopLoading = () => {
    if (abortController.value) {
      isUserStopped.value = true;
      abortController.value.abort();
      abortController.value = null;
    }
  };

  return {
    sendChatMessage,
    stopLoading,
    abortController,
    checkBackendStatus,
    checkRateLimits,
    rateLimits
  };
}