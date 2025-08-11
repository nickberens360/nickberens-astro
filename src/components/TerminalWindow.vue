<template>
  <div v-if="isVisible">
    <TerminalControlBar
      v-if="isMinimized"
      :title="title"
      class="terminal-minimized"
      @click="actions.restore()"
    />

    <div
      v-else
      class="terminal-window"
      :class="[`theme-${theme}`, { 'terminal-maximized': isMaximized }]"
      :style="terminalStyle"
      ref="terminalWindow"
      @click="focusInput"
      @mouseenter="mouseHandlers.enter"
      @mouseleave="mouseHandlers.leave"
    >
      <TerminalControlBar
        :title="title"
        :isMaximized="isMaximized"
        @close="actions.hide"
        @minimize="actions.minimize"
        @maximize="actions.maximize"
        @startDrag="dragHandlers.start"
        @stopDrag="dragHandlers.stop"
      />

      <TerminalContent
        :theme="theme"
        :command-history="commandHistory"
        :input-value="inputValue"
        @focus-input="focusInput"
        @update:input-value="inputValue = $event"
        @submit-command="submitCommand"
        ref="terminalContent"
      />

      <TerminalResizeHandles
        :is-maximized="isMaximized"
        :theme="theme"
        @start-resize="resizeHandlers.start"
      />
    </div>
  </div>
</template>

<script>
import { computed } from 'vue';
import TerminalControlBar from './TerminalControlBar.vue';
import TerminalContent from './TerminalContent.vue';
import TerminalResizeHandles from './TerminalResizeHandles.vue';
import { useTerminalController } from '../composables/useTerminalController.js';
import { useTerminalCommands } from '../composables/useTerminalCommands.js';

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
    const controller = useTerminalController(props);

    // Create terminal output ref for commands
    const terminalOutput = computed(() => ({
      get scrollTop() {
        return controller.terminalContent.value?.$refs.terminalOutput?.scrollTop || 0;
      },
      set scrollTop(value) {
        if (controller.terminalContent.value?.$refs.terminalOutput) {
          controller.terminalContent.value.$refs.terminalOutput.scrollTop = value;
        }
      },
      get scrollHeight() {
        return controller.terminalContent.value?.$refs.terminalOutput?.scrollHeight || 0;
      }
    }));

    // Initialize commands with unmaximize callback
    const { handleCommand } = useTerminalCommands(
      terminalOutput,
      controller.isMounted,
      controller.actions.unmaximize // Pass unmaximize callback
    );

    const submitCommand = () => {
      controller.submitCommand(handleCommand);
    };

    return {
      // All controller properties and methods
      ...controller,
      submitCommand
    };
  }
};
</script>

<style scoped>
.terminal-minimized {
  position: fixed;
  left: 0;
  bottom: 0;
  border-radius: 5px;
  width: 200px;
  cursor: pointer;
  z-index: var(--z-index-terminal);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
}

.terminal-minimized:hover {
  transform: scale(1.05);
}

.terminal-window {
  background-color: #1e1e1e;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
}

.terminal-maximized {
  border-radius: 0 !important;
}

.terminal-window.theme-light {
  background-color: rgba(240, 240, 240, 0.96);
  color: #333;
}

.terminal-window.theme-dark {
  background-color: rgba(30, 30, 30, 0.9);
  color: #f8f8f8;
}

@media (max-width: 768px) {
  .terminal-window {
    min-width: 90%;
  }
}
</style>
