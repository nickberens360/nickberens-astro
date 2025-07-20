<template>
  <div class="model-selector-bar">
    <div class="model-selector-container">
      <select
        :value="selectedModel"
        @change="$emit('update:selected-model', $event.target.value)"
        class="model-selector"
        :disabled="disabled"
      >
        <option value="claude">Claude (Recommended)</option>
        <option value="gemini">Gemini (Fast)</option>
      </select>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    selectedModel: {
      type: String,
      required: true
    },
    disabled: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:selected-model']
};
</script>

<style scoped>
.model-selector-bar {
  padding-left: .5rem;
}

.model-selector-container {
  display: flex;
  align-items: center;
  gap: 1rem;
  max-width: 800px;
  margin: 0 auto;
}

.model-selector {
  background-color: #222222;
  border: 1px solid #444444;
  border-radius: 6px;
  color: #b8ccfb;
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
  cursor: pointer;
}

.model-selector:focus {
  outline: none;
}

.model-selector:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .model-selector-container {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .model-selector {
    min-width: 100%;
  }

  .model-selector-bar {
    padding: 0.5rem;
  }
}
</style>