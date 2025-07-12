<template>
  <div class="terminal-input-container d-flex align-center">
    <span class="mr-2">~$</span>
    <div
      :contenteditable="true"
      @input="updateValue"
      @keydown="handleKeydown"
      @focus="isFocused = true"
      @blur="isFocused = false"
      class="terminal-input"
      ref="editableDiv"
      autofocus
      :data-placeholder="placeholder"
      :class="{ 'empty': isEmpty, 'focused': isFocused }"
    ></div>
  </div>
</template>

<script>
export default {
  name: 'TerminalInput',
  props: {
    modelValue: {
      type: String,
      default: '$'
    },
    placeholder: {
      type: String,
      default: ''
    },
    submitOnEnter: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      isEmpty: true,
      isFocused: false
    };
  },
  mounted() {
    const el = this.$refs.editableDiv;
    el.textContent = this.modelValue;
    el.focus();
    this.setCaretToEnd(el);
    this.isEmpty = !this.modelValue || this.modelValue === '$';
  },
  watch: {
    modelValue(newValue) {
      const el = this.$refs.editableDiv;
      if (el.textContent !== newValue) {
        el.textContent = newValue;
        this.setCaretToEnd(el);
        this.isEmpty = !newValue || newValue === '$';
      }
    }
  },
  methods: {
    updateValue(event) {
      const content = event.target.textContent;
      this.$emit('update:modelValue', content);
      this.isEmpty = !content || content === '$';
    },
    handleKeydown(event) {
      if (event.key === 'Enter' && this.submitOnEnter) {
        event.preventDefault();
        this.$emit('submit', this.$refs.editableDiv.textContent);
      }
    },
    focus() {
      const el = this.$refs.editableDiv;
      el.focus();
      this.setCaretToEnd(el);
    },
    clear() {
      const el = this.$refs.editableDiv;
      el.textContent = this.modelValue.startsWith('$') ? '$' : '';
      this.$emit('update:modelValue', el.textContent);
      this.isEmpty = true;
      this.setCaretToEnd(el);
    },
    setCaretToEnd(el) {
      const range = document.createRange();
      const selection = window.getSelection();
      range.selectNodeContents(el);
      range.collapse(false); // Move caret to end
      selection.removeAllRanges();
      selection.addRange(range);
    }
  }
};
</script>

<style scoped>
.terminal-input {
  display: flex;
  flex-direction: column;
  justify-content: center;
  position: relative;
  background: transparent;
  caret-color: transparent;
  outline: none;
  font-weight: bold;
  white-space: pre-wrap;
  height: 20px;
}
.terminal-input::selection {
  background-color: #00ff00;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.terminal-input:after {
  content: '';
  position: absolute;
  display: inline-block;
  z-index: -1;
  top: 0;
  right: -10px;
  height: 100%;
  width: 10px;
  background-color: white;
  pointer-events: none;
  animation: blink 1s infinite;
}

.focused.terminal-input:after {
  background-color: #00ff00;
}

/* Add focus styles if needed */
.terminal-input:focus {
  outline: none;
}

/* Focused state styling */
.terminal-input.focused {
  border-color: #00ff00;
}

/* Placeholder styling */
.terminal-input.empty:before {
  content: attr(data-placeholder);
  color: #666;
  opacity: 0.6;
  position: absolute;
  pointer-events: none;
}
</style>
