<template>
  <div class="followup-container fade-in">
    <p class="followup-label">💡 You might also want to ask:</p>
    <div class="followup-buttons">
      <button
        v-for="(question, qIndex) in questions"
        :key="qIndex"
        @click="$emit('followup-click', question)"
        class="followup-button"
        :disabled="disabled"
      >
        {{ question }}
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    questions: {
      type: Array,
      required: true
    },
    disabled: {
      type: Boolean,
      default: false
    }
  },
  emits: ['followup-click']
};
</script>

<style scoped>
.fade-in {
  opacity: 0;
  animation: fadeInUp 0.5s ease-out 0.2s forwards;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(15px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.followup-container {
  margin-top: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid #333333;
}

.followup-label {
  font-size: 0.875rem;
  color: #9ca3af;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.followup-buttons {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.followup-button {
  background-color: #333333;
  color: #f9fafb;
  border: 1px solid #444444;
  border-radius: 8px;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
  line-height: 1.4;
}

.followup-button:hover:not(:disabled) {
  background-color: #404040;
  border-color: #555555;
  transform: translateY(-1px);
}

.followup-button:active:not(:disabled) {
  transform: translateY(0);
}

.followup-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

@media (max-width: 768px) {
  .followup-buttons {
    gap: 0.375rem;
  }

  .followup-button {
    padding: 0.375rem 0.625rem;
    font-size: 0.8125rem;
  }
}
</style>