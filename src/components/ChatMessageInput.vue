<template>
  <input
    :value="modelValue"
    @input="$emit('update:model-value', $event.target.value)"
    @keyup.enter="$emit('send')"
    :placeholder="placeholder"
    class="message-input"
    :disabled="disabled"
  />
</template>

<script>
export default {
  props: {
    modelValue: {
      type: String,
      required: true
    },
    placeholder: {
      type: String,
      default: 'Type a message...'
    },
    disabled: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:model-value', 'send']
};
</script>

<style scoped>
.message-input {
  flex-grow: 0;
  padding: 0.75rem;
  font-size: 1rem;
  border: none !important;
  background: none !important;
  color: #f9fafb;
  width: 100%;
}

.message-input::placeholder {
  color: #999999;
}

.message-input:focus {
  outline: none;
  border-color: #555555;
  box-shadow: none !important;
}

@media (max-width: 768px) {
  .message-input {
    font-size: 0.875rem;
  }
}
</style>