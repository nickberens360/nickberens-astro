<template>
  <div class="model-indicator">
    <span class="model-badge">{{ model }}</span>
  </div>
</template>

<script>
export default {
  props: {
    model: {
      type: String,
      required: true
    }
  }
};
</script>

<style scoped>
.model-indicator {
  margin-top: 0.5rem;
  display: flex;
  justify-content: flex-start;
}

.model-badge {
  background-color: rgba(69, 126, 247, 0.1);
  border: 1px solid rgba(69, 126, 247, 0.3);
  color: #60a5fa;
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
  font-size: 0.6875rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

@media (max-width: 768px) {
  .model-badge {
    font-size: 0.625rem;
  }
}
</style>