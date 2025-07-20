<template>
  <div>
    <div
      v-if="message.text"
      class="markdown-content-wrapper"
    >
      <span
        v-html="renderMarkdown(message.text)"
        class="markdown-content"
      ></span>
      <span
        v-if="message.isTyping"
        class="typing-cursor"
      >|</span>
    </div>

    <!-- Stopped message indicator -->
    <div v-if="message.wasStopped && !message.isTyping" class="stopped-indicator">
      <span class="stopped-icon">⏹</span>
      You stopped this response
    </div>
  </div>
</template>

<script>
import { marked } from 'marked';

export default {
  props: {
    message: {
      type: Object,
      required: true
    },
    messageIndex: {
      type: Number,
      required: true
    }
  },
  setup() {
    const renderMarkdown = (text) => {
      return marked(text);
    };

    return {
      renderMarkdown
    };
  }
};
</script>

<style scoped>
.markdown-content-wrapper {
  display: inline;
  line-height: 1.6;
}

.markdown-content-wrapper .markdown-content {
  display: inline;
  line-height: inherit;
}

.typing-cursor {
  display: inline;
  animation: blink 1s infinite;
  font-weight: bold;
  color: #1c2539;
  font-size: 1em;
  line-height: inherit;
  vertical-align: baseline;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.stopped-indicator {
  margin-top: 0.5rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  color: #9ca3af;
  font-style: italic;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  opacity: 0.7;
}

.stopped-icon {
  font-size: 0.6875em;
  color: #9ca3af;
}

/* Override markdown content styling for inline display */
.markdown-content-wrapper :deep(.markdown-content) {
  display: inline;
}

.markdown-content-wrapper :deep(.markdown-content p) {
  display: inline;
  margin: 0;
}

.markdown-content-wrapper :deep(.markdown-content h1),
.markdown-content-wrapper :deep(.markdown-content h2),
.markdown-content-wrapper :deep(.markdown-content h3) {
  display: inline;
  font-size: inherit;
  margin: 0;
  font-weight: bold;
}

/* Markdown content styling */
:deep(.markdown-content) {
  font-size: .90rem;
  line-height: 1.6;
}

:deep(.markdown-content h1) {
  font-size: 1.5rem;
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}

:deep(.markdown-content h2) {
  font-size: 1.25rem;
  margin-top: 0.75rem;
  margin-bottom: 0.5rem;
}

:deep(.markdown-content h3) {
  font-size: 1.1rem;
  margin-top: 0.75rem;
  margin-bottom: 0.5rem;
}

:deep(.markdown-content p) {
  margin-bottom: 0.75rem;
}

:deep(.markdown-content ul, .markdown-content ol) {
  padding-left: 1.5rem;
  margin-bottom: 0.75rem;
}

:deep(.markdown-content li) {
  margin-bottom: 0.25rem;
}

:deep(.markdown-content code) {
  background-color: rgba(255, 255, 255, 0.1);
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  font-family: monospace;
}

:deep(.markdown-content pre) {
  background-color: rgba(255, 255, 255, 0.1);
  padding: 0.75rem;
  border-radius: 5px;
  overflow-x: auto;
  margin-bottom: 0.75rem;
}

:deep(.markdown-content a) {
  color: #60a5fa;
  text-decoration: underline;
}
</style>