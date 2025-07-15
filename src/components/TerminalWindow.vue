<template>
  <div>
    <div
      v-if="isMinimized"
      class="terminal-minimized"
      @click="isMinimized = false"
    >
      <div class="terminal-icon">
        <font-awesome-icon :icon="['fas', 'terminal']"/>
      </div>
    </div>

    <div
      v-else
      class="terminal-window"
      :class="`theme-${theme}`"
      :style="terminalStyle"
      ref="terminalWindow"
      @click="focusInput"
    >
      <TerminalControlBar
        :title="title"
        @close="$emit('close')"
        @minimize="isMinimized = true"
        @startDrag="startDrag"
        @stopDrag="stopDrag"
      />

      <div
        class="terminal-content"
        @click="focusInput"
      >
        <div
          class="terminal-output"
          ref="terminalOutput"
        >
          <div
            v-for="(item, index) in commandHistory"
            :key="item.id"
            class="command-history-item"
          >
            <div
              v-if="item.command"
              class="command-input"
            >
              <span class="prompt mr-2">~$</span>
              <span>{{ item.command }}</span>
            </div>

            <div class="command-output">
              <div
                v-for="(line, lineIndex) in item.textOutput"
                :key="`text-${lineIndex}`"
                class="output-line"
              >
                <template v-if="typeof line === 'string'">{{ line }}</template>
                <template v-else-if="line.type === 'link'">
                  {{ line.prefix }}
                  <a
                    :href="line.url"
                    class="terminal-link"
                  >{{ line.text }}
                  </a>
                  {{ line.suffix || '' }}
                </template>
                <terminal-graph-output
                  v-else-if="line.type === 'graph-history' || line.type === 'latest-commit'"
                  :line="line"
                />
              </div>

              <terminal-graph-output
                v-if="item.graphData && item.graphData.isVisible"
                :graph-data="item.graphData"
              />

              <terminal-graph-output
                v-if="item.commitData && item.commitData.isVisible"
                :commit-data="item.commitData"
              />

              <terminal-log-output
                v-if="item.commitHistory && item.commitHistory.isVisible"
                :commit-history="item.commitHistory"
              />

              <div
                v-if="item.isLoading"
                class="loading-container"
              >
                <div class="progress-bar-container">
                  <div
                    class="progress-bar"
                    :style="{ width: `${item.loadingProgress}%` }"
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>

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
            autofocus
          />
        </div>
      </div>

      <div
        class="resize-handle"
        @pointerdown="startResize"
      ></div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue';
import { library } from '@fortawesome/fontawesome-svg-core';
import { faTerminal } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';
import { getLatestCommitMessage, getCodeFrequency, getCommitHistory } from '../utils/gitInfo.js';
import {
  navItems,
  commandHistoryStore,
  nextCommandIdStore,
  terminalPositionStore,
  terminalSizeStore,
  isTerminalActive
} from '../stores/ui.js';
import { useStore } from '@nanostores/vue';
import TerminalControlBar from './TerminalControlBar.vue';
import TerminalGraphOutput, { processCodeFrequencyData } from './TerminalGraphOutput.vue';
import TerminalLogOutput, { processCommitHistory } from './TerminalLogOutput.vue';

library.add(faTerminal);

export default {
  name: 'TerminalWindow',
  components: {
    FontAwesomeIcon,
    TerminalControlBar,
    TerminalGraphOutput,
    TerminalLogOutput,
  },
  props: {
    title: {
      type: String,
      default: 'Terminal'
    },
    initialOutput: {
      type: Array,
      default: () => ['Welcome to Terminal']
    }
  },
  setup(props, { emit }) {
    // --- STATE AND STORE HOOKS ---
    const isMinimized = ref(false);
    const theme = ref('dark');
    const inputValue = ref('');
    const terminalWindow = ref(null);
    const terminalInput = ref(null);
    const terminalOutput = ref(null);

    const position = useStore(terminalPositionStore);
    const size = useStore(terminalSizeStore);
    const commandHistory = useStore(commandHistoryStore);
    const nextCommandId = useStore(nextCommandIdStore);

    // --- DRAG & RESIZE LOGIC ---
    const isDragging = ref(false);
    const dragOffset = reactive({ x: 0, y: 0 });
    const isResizing = ref(false);
    const resizeStartPos = reactive({ x: 0, y: 0 });
    const resizeStartSize = reactive({ width: 0, height: 0 });

    const terminalStyle = computed(() => ({
      top: `${position.value?.y || 100}px`,
      left: `${position.value?.x || 100}px`,
      width: `${size.value?.width || 600}px`,
      height: `${size.value?.height || 400}px`,
    }));

    const startDrag = (event) => {
      if (terminalWindow.value && event.isPrimary) {
        isDragging.value = true;
        dragOffset.x = event.clientX - position.value.x;
        dragOffset.y = event.clientY - position.value.y;
        document.addEventListener('pointermove', onDrag);
        document.addEventListener('pointerup', stopDrag);
        event.preventDefault(); // Prevent scrolling on touch devices
      }
    };
    const onDrag = (event) => {
      if (isDragging.value) {
        terminalPositionStore.set({ x: event.clientX - dragOffset.x, y: event.clientY - dragOffset.y });
      }
    };
    const stopDrag = () => {
      isDragging.value = false;
      document.removeEventListener('pointermove', onDrag);
      document.removeEventListener('pointerup', stopDrag);
    };

    const startResize = (event) => {
      if (event.isPrimary) {
        isResizing.value = true;
        resizeStartPos.x = event.clientX;
        resizeStartPos.y = event.clientY;
        resizeStartSize.width = size.value.width;
        resizeStartSize.height = size.value.height;
        document.addEventListener('pointermove', onResize);
        document.addEventListener('pointerup', stopResize);
        event.preventDefault();
        event.stopPropagation();
      }
    };
    const onResize = (event) => {
      if (isResizing.value) {
        const deltaX = event.clientX - resizeStartPos.x;
        const deltaY = event.clientY - resizeStartPos.y;
        terminalSizeStore.set({
          width: Math.max(200, resizeStartSize.width + deltaX),
          height: Math.max(28, resizeStartSize.height + deltaY),
        });
      }
    };
    const stopResize = () => {
      isResizing.value = false;
      document.removeEventListener('pointermove', onResize);
      document.removeEventListener('pointerup', stopResize);
    };

    // --- STATE UPDATE HELPERS ---
    const updateHistoryItem = (commandId, updates) => {
      const history = commandHistory.value;
      const index = history.findIndex(item => item.id === commandId);
      if (index === -1) return;

      const newHistory = [...history];
      const currentItem = newHistory[index];

      newHistory[index] = {
        ...currentItem,
        ...updates,
        textOutput: [...currentItem.textOutput, ...(updates.textOutput || [])],
      };
      commandHistoryStore.set(newHistory);
    };

    const ensureMinLoadingTime = async (promise, commandId, minTime = 1000) => {
      updateHistoryItem(commandId, { isLoading: true, loadingProgress: 0 });
      const loadingStartTime = Date.now();

      const progressInterval = setInterval(() => {
        const currentProgress = commandHistory.value.find(c => c.id === commandId)?.loadingProgress || 0;
        if (currentProgress < 90) {
          let newProgress = currentProgress + Math.random() * 3 + 1;
          updateHistoryItem(commandId, { loadingProgress: Math.min(newProgress, 90) });
        }
      }, 100);

      const result = await promise;
      const elapsedTime = Date.now() - loadingStartTime;

      if (elapsedTime < minTime) {
        await new Promise(resolve => setTimeout(resolve, minTime - elapsedTime));
      }

      clearInterval(progressInterval);
      updateHistoryItem(commandId, { loadingProgress: 100 });
      await new Promise(resolve => setTimeout(resolve, 200));
      updateHistoryItem(commandId, { isLoading: false });

      return result;
    };

    // --- ASYNC COMMAND ABSTRACTION ---
    const createAsyncGitHandler = (commandId, fetchFn, processFn, initialText) => {
      updateHistoryItem(commandId, { textOutput: [initialText] });
      ensureMinLoadingTime(fetchFn(), commandId)
        .then(data => {
          updateHistoryItem(commandId, processFn(data));
          setTimeout(() => {
            if (terminalOutput.value) terminalOutput.value.scrollTop = terminalOutput.value.scrollHeight;
          }, 0);
        })
        .catch(error => {
          updateHistoryItem(commandId, { textOutput: [`Error retrieving data: ${error.message}`] });
        });
    };

    // --- COMMAND MAP ---
    const commands = {
      clear: (args, commandId) => {
        const currentCommand = commandHistory.value.find(c => c.id === commandId);
        commandHistoryStore.set(currentCommand ? [currentCommand] : []);
      },
      help: (args, commandId) => {
        updateHistoryItem(commandId, {
          textOutput: [
            'Available commands:',
            '- clear: Clear the terminal',
            '- help: Show this help message',
            '- theme: Toggle between light and dark theme',
            '- version: Show terminal version',
            '- ls: List navigation links',
            '- git log: Show commit history',
            '- git graph: Show code frequency chart',
            '- git --latest-commit: Show latest commit message'
          ]
        });
      },
      theme: (args, commandId) => {
        theme.value = theme.value === 'dark' ? 'light' : 'dark';
        updateHistoryItem(commandId, { textOutput: [`Theme switched to ${theme.value} mode`] });
      },
      version: (args, commandId) => {
        updateHistoryItem(commandId, { textOutput: ['Terminal v1.0.0', 'Created by nickberens'] });
      },
      ls: (args, commandId) => {
        const links = navItems.get().map(item => ({ type: 'link', prefix: '- ', url: item.url, text: item.text }));
        updateHistoryItem(commandId, { textOutput: ['Navigation links:', ...links] });
      },
      git: (args, commandId) => {
        const gitAction = {
          log: () => createAsyncGitHandler(commandId, getCommitHistory, data => ({ commitHistory: processCommitHistory(data) }), 'Fetching commit history...'),
          graph: () => createAsyncGitHandler(commandId, getCodeFrequency, data => ({
            graphData: processCodeFrequencyData(data),
            textOutput: ['Code Frequency (additions/deletions over time):']
          }), 'Fetching code frequency data...'),
          '--latest-commit': () => createAsyncGitHandler(commandId, getLatestCommitMessage, data => ({
            commitData: {
              ...data,
              isVisible: true
            }
          }), 'Fetching latest commit...'),
          default: () => updateHistoryItem(commandId, { textOutput: ['Usage: git [log|graph|--latest-commit]'] })
        };
        (gitAction[args[0]?.toLowerCase()] || gitAction.default)();
      },
      'bust-cache': (args, commandId) => {
        // Clear localStorage items
        localStorage.removeItem('terminalPosition');
        localStorage.removeItem('terminalSize');
        localStorage.removeItem('commandHistory');
        localStorage.removeItem('nextCommandId');

        // Reset nanostores to default values
        terminalPositionStore.set({ x: 100, y: 100 });
        terminalSizeStore.set({ width: 600, height: 400 });

        // Keep only the current command in history
        const currentCommand = commandHistory.value.find(c => c.id === commandId);
        commandHistoryStore.set(currentCommand ? [currentCommand] : []);

        // Reset next command ID
        nextCommandIdStore.set(2);

        // Provide feedback
        updateHistoryItem(commandId, {
          textOutput: ['Cache busted! Nanostores and localStorage have been reset.']
        });
      },
      default: (baseCommand, commandId) => {
        updateHistoryItem(commandId, { textOutput: [`Command not found: ${baseCommand}`] });
      }
    };

    // --- CORE LOGIC ---
    const focusInput = (event) => {
      if (terminalInput.value && (!event || event.target.tagName !== 'A')) {
        terminalInput.value.focus();
      }
    };

    const handleCommand = (command, commandId) => {
      const parts = command.split(' ');
      const baseCommand = parts[0].toLowerCase();
      const args = parts.slice(1);
      const commandFn = commands[baseCommand] || (() => commands.default(baseCommand, commandId));
      commandFn(args, commandId);
    };

    const submitCommand = () => {
      const command = inputValue.value.trim();
      if (!command) return;

      inputValue.value = '';
      const commandId = nextCommandId.value;
      nextCommandIdStore.set(commandId + 1);

      commandHistoryStore.set([
        ...commandHistory.value,
        {
          id: commandId,
          timestamp: Date.now(),
          command: command,
          textOutput: [],
          isLoading: false,
          loadingProgress: 0,
          graphData: null,
          commitData: null,
          commitHistory: null
        }
      ]);

      handleCommand(command, commandId);

      setTimeout(() => {
        if (terminalOutput.value) {
          terminalOutput.value.scrollTop = terminalOutput.value.scrollHeight;
        }
      }, 0);
    };

    // --- TERMINAL ACTIVE STATE HANDLERS ---
    const activateTerminal = () => {
      isTerminalActive.set(true);
    };

    const deactivateTerminal = () => {
      isTerminalActive.set(false);
    };

    // --- LIFECYCLE HOOKS ---
    onMounted(() => {
      // Add initial output if history is empty
      if (props.initialOutput && props.initialOutput.length > 0 && commandHistory.value.length === 0) {
        commandHistoryStore.set([{
          id: 1,
          timestamp: Date.now(), command: '', textOutput: [...props.initialOutput],
          isLoading: false, loadingProgress: 0, graphData: null, commitData: null, commitHistory: null
        }]);
        nextCommandIdStore.set(2);
      }

      document.addEventListener('pointerup', stopDrag);
      document.addEventListener('pointerup', stopResize);
      setTimeout(focusInput, 0);

      // Add event listeners for terminal focus
      if (terminalWindow.value) {
        terminalWindow.value.addEventListener('pointerdown', activateTerminal);
        document.addEventListener('pointerdown', (event) => {
          if (terminalWindow.value && !terminalWindow.value.contains(event.target) && !isMinimized.value) {
            deactivateTerminal();
          }
        });
      }
    });

    onUnmounted(() => {
      document.removeEventListener('pointerup', stopDrag);
      document.removeEventListener('pointermove', onDrag);
      document.removeEventListener('pointerup', stopResize);
      document.removeEventListener('pointermove', onResize);

      if (terminalWindow.value) {
        terminalWindow.value.removeEventListener('pointerdown', activateTerminal);
      }
      document.removeEventListener('pointerdown', deactivateTerminal);
    });

    return {
      isMinimized,
      position,
      size,
      terminalStyle,
      startDrag,
      stopDrag,
      startResize,
      stopResize,
      commandHistory,
      inputValue,
      submitCommand,
      terminalWindow,
      terminalInput,
      terminalOutput,
      focusInput,
      theme,
      activateTerminal,
      deactivateTerminal
    };
  }
};
</script>

<style scoped>
/* All styles remain the same */
.command-history-item {
  margin-bottom: 8px;
}

.command-input {
  color: #63c5da;
  font-weight: bold;
  margin-bottom: 4px;
}

.command-output {
  margin-left: 8px;
}

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
  /*flex-grow: 1;*/
  overflow-y: auto;
  margin-bottom: 10px;
}

.output-line {
  margin-bottom: 4px;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
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

.theme-light .prompt, .theme-light .terminal-input {
  color: #333;
}

.theme-light .terminal-input {
  caret-color: #333;
}

.theme-light .terminal-input::selection {
  background-color: rgba(0, 0, 0, 0.1);
}

.terminal-window.theme-light {
  background-color: #f0f0f0;
  color: #333;
}

.terminal-window.theme-light .terminal-content {
  color: #333;
}

.terminal-window.theme-dark {
  background-color: #1e1e1e;
  color: #f8f8f8;
}

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

.theme-light .terminal-output::-webkit-scrollbar-track {
  background: #f0f0f0;
}

.theme-light .terminal-output::-webkit-scrollbar-thumb {
  background: #ccc;
}

.theme-light .terminal-output::-webkit-scrollbar-thumb:hover {
  background: #aaa;
}

@media (max-width: 768px) {
  .terminal-window {
    min-width: 90%;
    /*min-height: 350px;*/
  }
}

.loading-container {
  margin: 10px 0;
  width: 100%;
}

.progress-bar-container {
  width: 100%;
  height: 20px;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 0;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background-color: #ffffff;
  border-radius: 0;
  transition: width 0.3s ease;
}

.theme-light .progress-bar {
  background-color: #000000;
}

.theme-light .progress-bar-container {
  background-color: rgba(0, 0, 0, 0.2);
}

.resize-handle {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 15px;
  height: 15px;
  cursor: nwse-resize;
  background: transparent;
  touch-action: none;
}

.resize-handle::before {
  content: "";
  position: absolute;
  right: 3px;
  bottom: 3px;
  width: 9px;
  height: 9px;
  border-right: 2px solid rgba(255, 255, 255, 0.5);
  border-bottom: 2px solid rgba(255, 255, 255, 0.5);
}

.theme-light .resize-handle::before {
  border-right: 2px solid rgba(0, 0, 0, 0.3);
  border-bottom: 2px solid rgba(0, 0, 0, 0.3);
}

.terminal-link {
  color: #3498db;
  text-decoration: underline;
  cursor: pointer;
}

.terminal-link:hover {
  color: #2980b9;
}

.theme-light .terminal-link {
  color: #2980b9;
}

.theme-light .terminal-link:hover {
  color: #1c6ea4;
}
</style>
