<template>
  <div class="terminal-input-container d-flex align-center">
    <span class="mr-2">~$</span>
    <div
      :contenteditable="true"
      @input="updateValue"
      @keydown="handleKeydown"
      @focus="onFocus"
      @blur="isFocused = false"
      @click="onFocus"
      @mouseup="onFocus"
      class="terminal-input"
      ref="editableDiv"
      autofocus
      :data-placeholder="placeholder"
      :class="{ 'empty': isEmpty, 'focused': isFocused }"
    ></div>
  </div>
</template>

<script>
import { useStore } from '@nanostores/vue';
import { terminalInputValue } from '../stores/ui';

export default {
  name: 'TerminalInput',
  props: {
    placeholder: {
      type: String,
      default: ''
    },
    submitOnEnter: {
      type: Boolean,
      default: false
    }
  },
  setup() {
    const terminalInputValueStore = useStore(terminalInputValue);
    return {
      inputValue: terminalInputValueStore,
    };
  },
  data() {
    return {
      isFocused: true
    };
  },
  computed: {
    isEmpty() {
      return !this.inputValue;
    }
  },
  mounted() {
    const el = this.$refs.editableDiv;
    el.textContent = this.inputValue;
    el.focus();
    this.setCaretToEnd(el);
  },
  watch: {
    inputValue(newValue) {
      const el = this.$refs.editableDiv;
      if (el.textContent !== newValue) {
        el.textContent = newValue;
      }
    }
  },
  methods: {
    updateValue(event) {
      terminalInputValue.set(event.target.textContent);
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
      terminalInputValue.set('');
      this.setCaretToEnd(this.$refs.editableDiv);
    },
    onFocus() {
      this.isFocused = true;
      setTimeout(() => {
        this.setCaretToEnd(this.$refs.editableDiv);
      }, 0);
    },
    setCaretToEnd(el) {
      if (!el) return;
      const range = document.createRange();
      const selection = window.getSelection();
      if (el.childNodes.length === 0) {
        el.appendChild(document.createTextNode(''));
      }
      range.selectNodeContents(el);
      range.collapse(false);
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
  background-color: white;
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
  animation: unset;
}

.focused.terminal-input:after {
  animation: blink 1s infinite;
}

.terminal-input:focus {
  outline: none;
}

.terminal-input.focused {
  border-color: #00ff00;
}

.terminal-input.empty:before {
  content: attr(data-placeholder);
  color: #666;
  opacity: 0.6;
  position: absolute;
  pointer-events: none;
}
</style>
