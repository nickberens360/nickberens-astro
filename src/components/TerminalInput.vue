<template>
  <div class="terminal-input-line" :class="`theme-${theme}`">
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
    },
    theme: {
      type: String,
      default: 'dark'
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

/* Theme styles */
.terminal-input-line.theme-light .prompt,
.terminal-input-line.theme-light .terminal-input {
  color: #333;
}

.terminal-input-line.theme-light .terminal-input {
  caret-color: #333;
}

.terminal-input-line.theme-light .terminal-input::selection {
  background-color: rgba(0, 0, 0, 0.1);
}
</style>