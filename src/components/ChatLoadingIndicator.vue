<template>
  <div class="message bot">
    <div class="message-bubble">
      <div class="typing-indicator">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ChatLoadingIndicator'
};
</script>

<style scoped>
.message {
  display: flex;
}

.message-bubble {
  padding: 0.75rem 1.25rem;
  border-radius: 18px;
  max-width: 100%;
  line-height: 1.5;
}

.bot {
  justify-content: flex-start;
}

.bot .message-bubble {
  background-color: transparent;
  color: #f9fafb;
  border-bottom-left-radius: 4px;
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 5px;
}

.typing-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #666666;
  animation: typing 1.2s infinite ease-in-out;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 100% {
    transform: translateY(0);
    opacity: 0.5;
  }
  40% {
    transform: translateY(-5px);
    opacity: 1;
  }
}
</style>