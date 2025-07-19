<template>
  <div v-if="!isHidden">
    <TerminalControlBar
      v-if="isMinimized"
      :title="title"
      class="terminal-minimized"
      @click="isTerminalMinimizedStore.set(false)"
    />

    <div
      v-else
      class="terminal-window"
      :class="[`theme-${theme}`, { 'terminal-maximized': isMaximized }]"
      :style="terminalStyle"
      ref="terminalWindow"
      @click="focusInput"
    >
      <TerminalControlBar
        :title="title"
        :isMaximized="isMaximized"
        @close="isTerminalHiddenStore.set(true);"
        @minimize="isTerminalMinimizedStore.set(true)"
        @maximize="toggleMaximize"
        @startDrag="startDrag"
        @stopDrag="stopDrag"
      />

      <TerminalContent
        :theme="theme"
        :command-history="commandHistory"
        :input-value="inputValue"
        @focus-input="focusInput"
        @unmaximize="unmaximizeTerminal"
        @update:input-value="inputValue = $event"
        @submit-command="submitCommand"
        ref="terminalContent"
      />

      <TerminalResizeHandles
        :is-maximized="isMaximized"
        :theme="theme"
        @start-resize="startResize"
      />
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import TerminalControlBar from './TerminalControlBar.vue';
import TerminalContent from './TerminalContent.vue';
import TerminalResizeHandles from './TerminalResizeHandles.vue';
import { useTerminalCommands } from '../composables/useTerminalCommands.js';
import { useTerminalResize } from '../composables/useTerminalResize.js';
import { useTerminalState } from '../composables/useTerminalState.js';

export default {
  name: 'TerminalWindow',
  components: {
    TerminalControlBar,
    TerminalContent,
    TerminalResizeHandles,
  },
  props: {
    title: {
      type: String,
      default: 'Terminal'
    },
    initialOutput: {
      type: Array,
      default: () => ['Welcome to Terminal']
    },
    hideTerminal: {
      type: Boolean,
      default: false,
    }
  },
  setup(props) {
    // --- REFS ---
    const terminalWindow = ref(null);
    const terminalContent = ref(null);

    // Create direct refs that will be properly connected
    const terminalInput = ref(null);
    const terminalOutput = ref(null);

    // --- COMPOSABLES ---
    const terminalState = useTerminalState(props, terminalInput, terminalOutput);
    const { handleCommand, unmaximizeTerminal } = useTerminalCommands(terminalOutput, terminalState.isMounted);

    const {
      terminalStyle,
      startDrag,
      stopDrag,
      startResize,
      stopResize,
      toggleMaximize,
    } = useTerminalResize(
      terminalWindow,
      terminalState.position,
      terminalState.size,
      terminalState.isMaximized,
      terminalState.previousTerminalState
    );

    // --- COMMAND SUBMISSION ---
    const submitCommand = () => {
      terminalState.submitCommand(handleCommand);
      // Ensure scroll to bottom after command submission
      setTimeout(() => {
        terminalContent.value?.scrollToBottom();
      }, 50);
    };

    // --- FOCUS INPUT ---
    const focusInput = (event) => {
      if (!event || event.target.tagName !== 'A') {
        terminalContent.value?.focusInput();
      }
    };

    // --- LIFECYCLE ---
    onMounted(() => {
      // Set up refs for the composables that need them
      terminalInput.value = {
        focus: () => terminalContent.value?.focusInput()
      };
      terminalOutput.value = {
        scrollTop: 0,
        scrollHeight: 0,
        get scrollTop() {
          return terminalContent.value?.$refs.terminalOutput?.scrollTop || 0;
        },
        set scrollTop(value) {
          if (terminalContent.value?.$refs.terminalOutput) {
            terminalContent.value.$refs.terminalOutput.scrollTop = value;
          }
        },
        get scrollHeight() {
          return terminalContent.value?.$refs.terminalOutput?.scrollHeight || 0;
        }
      };

      terminalState.cleanup.value = terminalState.initialize(
        terminalWindow,
        toggleMaximize,
        stopDrag,
        stopResize
      );
    });

    return {
      // Refs
      terminalWindow,
      terminalContent,

      // From terminalState composable
      theme: terminalState.theme,
      inputValue: terminalState.inputValue,
      isMounted: terminalState.isMounted,
      isMinimized: terminalState.isMinimized,
      isHidden: terminalState.isHidden,
      isMaximized: terminalState.isMaximized,
      commandHistory: terminalState.commandHistory,
      isTerminalMinimizedStore: terminalState.isTerminalMinimizedStore,
      isTerminalHiddenStore: terminalState.isTerminalHiddenStore,

      // From useTerminalResize composable
      terminalStyle,
      startDrag,
      stopDrag,
      startResize,
      stopResize,
      toggleMaximize,

      // Methods
      submitCommand,
      focusInput,
      unmaximizeTerminal,
    };
  }
};
</script>

<style scoped>
.terminal-minimized {
  position: fixed;
  left: 20px;
  bottom: 20px;
  border-radius: 5px;
  width: 200px;
  cursor: pointer;
  z-index: 1000;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
}

.terminal-minimized:hover {
  transform: scale(1.05);
}

.terminal-window {
  position: fixed;
  background-color: #1e1e1e;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  z-index: 1000;
}

.terminal-maximized {
  position: fixed !important;
  border-radius: 0 !important;
  z-index: 1001 !important;
}

.terminal-window.theme-light {
  background-color: #f0f0f0;
  color: #333;
}

.terminal-window.theme-dark {
  background-color: #1e1e1e;
  color: #f8f8f8;
}

@media (max-width: 768px) {
  .terminal-window {
    min-width: 90%;
  }
}
</style>