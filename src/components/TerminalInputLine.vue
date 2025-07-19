<template>
  <div class="terminal-input-line">
    <span class="prompt mr-2">~$</span>
    <input
      type="text"
      class="terminal-input"
      :value="inputValue"
      @input="$emit('update:inputValue', $event.target.value)"
      @keydown.enter="$emit('submit')"
      ref="terminalInput"
      placeholder=""
      autocomplete="off"
      autofocus
    />
  </div>
</template>

<script>
export default {
  name: 'TerminalInputLine',
  props: {
    inputValue: {
      type: String,
      default: ''
    }
  },
  emits: ['update:inputValue', 'submit'],
  methods: {
    focus() {
      this.$refs.terminalInput?.focus();
    }
  }
};
</script>

<style scoped>
.terminal-input-line {
  display: flex;
  align-items: center;
}

.prompt {
  color: #f8f8f8;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  margin-right: 8px;
}

.terminal-input {
  background: transparent;
  border: none;
  color: #f8f8f8;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  font-weight: bold;
  outline: none;
  flex-grow: 1;
  caret-color: #f8f8f8;
}

.terminal-input::selection {
  background-color: rgba(255, 255, 255, 0.3);
}
</style>