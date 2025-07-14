<template>
  <div>
    <!-- Minimized terminal icon (shown when minimized) -->
    <div
      v-if="isMinimized"
      class="terminal-minimized"
      @click="isMinimized = false"
    >
      <div class="terminal-icon">
        <font-awesome-icon :icon="['fas', 'terminal']" />
      </div>
    </div>

    <!-- Terminal window (shown when not minimized) -->
    <div
      v-else
      class="terminal-window"
      :class="`theme-${theme}`"
      :style="{ top: position.y + 'px', left: position.x + 'px' }"
      ref="terminalWindow"
    >
      <!-- Terminal header with controls -->
      <div
        class="terminal-header"
        @mousedown="startDrag"
        @mouseup="stopDrag"
      >
        <div class="terminal-controls">
          <div class="control close" @click="$emit('close')"></div>
          <div class="control minimize" @click="isMinimized = true"></div>
          <div class="control maximize"></div>
        </div>
        <div class="terminal-title">{{ title }}</div>
      </div>

      <!-- Terminal content area -->
      <div class="terminal-content">
        <div class="terminal-output" ref="terminalOutput">
          <div v-for="(line, index) in outputLines" :key="index" class="output-line">
            {{ line }}
          </div>
        </div>

        <!-- Terminal input using standard input element -->
        <div class="terminal-input-line">
          <span class="prompt mr-2">~$</span>
          <input
            type="text"
            class="terminal-input"
            v-model="inputValue"
            @keydown.enter="submitCommand"
            ref="terminalInput"
            placeholder=""
            autocomplete="off"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted, onUnmounted } from 'vue';
import { library } from '@fortawesome/fontawesome-svg-core';
import { faTerminal } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';
import { getLatestCommitMessage } from '../utils/gitInfo.js';

library.add(faTerminal);

export default {
  name: 'TerminalWindow',
  components: {
    FontAwesomeIcon
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
    theme: {
      type: String,
      default: 'dark'
    }
  },
  setup(props, { emit }) {
    const isMinimized = ref(false);
    const position = reactive({ x: 100, y: 100 });
    const isDragging = ref(false);
    const dragOffset = reactive({ x: 0, y: 0 });
    const outputLines = ref([...props.initialOutput]);
    const inputValue = ref('');
    const terminalWindow = ref(null);
    const terminalInput = ref(null);
    const terminalOutput = ref(null);

    // Dragging functionality
    const startDrag = (event) => {
      // Only start dragging with left mouse button (button 0)
      if (terminalWindow.value && event.button === 0) {
        isDragging.value = true;
        dragOffset.x = event.clientX - position.x;
        dragOffset.y = event.clientY - position.y;
        document.addEventListener('mousemove', onDrag);
      }
    };

    const onDrag = (event) => {
      // Check if mouse button is still pressed, if not, stop dragging
      // This handles edge cases where mouseup might be missed
      if (isDragging.value) {
        if (event.buttons === 0) {
          stopDrag();
          return;
        }
        position.x = event.clientX - dragOffset.x;
        position.y = event.clientY - dragOffset.y;
      }
    };

    const stopDrag = () => {
      if (isDragging.value) {
        isDragging.value = false;
        document.removeEventListener('mousemove', onDrag);
      }
    };

    // Submit command from input
    const submitCommand = () => {
      if (inputValue.value.trim()) {
        handleCommand(inputValue.value.trim());
        inputValue.value = ''; // Clear the input
      }
    };

    // Command handling
    const handleCommand = (command) => {
      outputLines.value.push(`${command}`);

      // Parse command and arguments
      const parts = command.split(' ');
      const baseCommand = parts[0];
      const args = parts.slice(1);

      // Process commands
      if (baseCommand === 'clear') {
        outputLines.value = [];
      } else if (baseCommand === 'help') {
        outputLines.value.push('Available commands:');
        outputLines.value.push('- clear: Clear the terminal');
        outputLines.value.push('- help: Show this help message');
        outputLines.value.push('- theme: Toggle between light and dark theme');
        outputLines.value.push('- version: Show terminal version');
        outputLines.value.push('- git --latest-commit: Show the latest git commit message');
      } else if (baseCommand === 'theme') {
        // Toggle theme
        const newTheme = props.theme === 'dark' ? 'light' : 'dark';
        emit('update:theme', newTheme);
        outputLines.value.push(`Theme switched to ${newTheme} mode`);
      } else if (baseCommand === 'version') {
        outputLines.value.push('Terminal v1.0.0');
        outputLines.value.push('Created by nickberens');
      } else if (baseCommand === 'git') {
        if (args.length === 0) {
          outputLines.value.push('Usage: git [--latest-commit]');
        } else if (args[0] === '--latest-commit') {
          outputLines.value.push('Fetching latest commit message...');

          getLatestCommitMessage()
            .then(commitMessage => {
              outputLines.value.push('Latest commit message:');
              outputLines.value.push(commitMessage);

              // Scroll to bottom of output
              setTimeout(() => {
                if (terminalOutput.value) {
                  terminalOutput.value.scrollTop = terminalOutput.value.scrollHeight;
                }
              }, 0);
            })
            .catch(error => {
              outputLines.value.push('Error retrieving latest commit message');
              outputLines.value.push(error.message);
            });
        } else {
          outputLines.value.push(`Unknown git option: ${args.join(' ')}`);
        }
      } else {
        outputLines.value.push(`Command not found: ${baseCommand}`);
      }

      // Scroll to bottom of output
      setTimeout(() => {
        if (terminalOutput.value) {
          terminalOutput.value.scrollTop = terminalOutput.value.scrollHeight;
        }
      }, 0);
    };

    // Clean up event listeners
    onMounted(() => {
      document.addEventListener('mouseup', stopDrag);
    });

    onUnmounted(() => {
      document.removeEventListener('mouseup', stopDrag);
      document.removeEventListener('mousemove', onDrag);
    });

    return {
      isMinimized,
      position,
      startDrag,
      stopDrag,
      outputLines,
      inputValue,
      submitCommand,
      handleCommand,
      terminalWindow,
      terminalInput,
      terminalOutput
    };
  }
};
</script>

<style scoped>
/* Terminal window when minimized */
.terminal-minimized {
  position: fixed;
  left: 20px;
  top: 50%;
  transform: translateY(-50%);
  width: 50px;
  height: 50px;
  background-color: #2d2d2d;
  border-radius: 10px;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  z-index: 1000;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
}

.terminal-minimized:hover {
  transform: translateY(-50%) scale(1.05);
}

.terminal-icon {
  color: #fff;
  font-size: 24px;
}

/* Main terminal window */
.terminal-window {
  position: fixed;
  width: 600px;
  height: 400px;
  background-color: #1e1e1e;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  z-index: 1000;
}

/* Terminal header with controls */
.terminal-header {
  height: 28px;
  background-color: #3c3c3c;
  display: flex;
  align-items: center;
  padding: 0 10px;
  cursor: move;
  user-select: none;
}

.terminal-controls {
  display: flex;
  gap: 8px;
}

.control {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  cursor: pointer;
}

.close {
  background-color: #ff5f56;
}

.minimize {
  background-color: #ffbd2e;
}

.maximize {
  background-color: #27c93f;
}

.terminal-title {
  flex-grow: 1;
  text-align: center;
  color: #cccccc;
  font-size: 14px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
}

/* Terminal content area */
.terminal-content {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  padding: 10px;
  overflow: hidden;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  color: #f8f8f8;
}

.terminal-output {
  flex-grow: 1;
  overflow-y: auto;
  margin-bottom: 10px;
}

.output-line {
  margin-bottom: 4px;
  white-space: pre-wrap;
  word-break: break-all;
}

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

.theme-light .prompt,
.theme-light .terminal-input {
  color: #333;
}

.theme-light .terminal-input {
  caret-color: #333;
}

.theme-light .terminal-input::selection {
  background-color: rgba(0, 0, 0, 0.1);
}

/* Theme-based styling */
.terminal-window.theme-light {
  background-color: #f0f0f0;
  color: #333;
}

.terminal-window.theme-light .terminal-header {
  background-color: #d8d8d8;
}

.terminal-window.theme-light .terminal-title {
  color: #333;
}

.terminal-window.theme-light .terminal-content {
  color: #333;
}

.terminal-window.theme-dark {
  background-color: #1e1e1e;
  color: #f8f8f8;
}

/* Custom scrollbar for terminal output */
.terminal-output::-webkit-scrollbar {
  width: 8px;
}

.terminal-output::-webkit-scrollbar-track {
  background: #1e1e1e;
}

.terminal-output::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 4px;
}

.terminal-output::-webkit-scrollbar-thumb:hover {
  background: #777;
}

/* Light theme scrollbar */
.theme-light .terminal-output::-webkit-scrollbar-track {
  background: #f0f0f0;
}

.theme-light .terminal-output::-webkit-scrollbar-thumb {
  background: #ccc;
}

.theme-light .terminal-output::-webkit-scrollbar-thumb:hover {
  background: #aaa;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .terminal-window {
    width: 90%;
    height: 350px;
  }
}
</style>
