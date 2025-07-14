<template>
  <div>
    <div
      v-if="isMinimized"
      class="terminal-minimized"
      @click="isMinimized = false"
    >
      <div class="terminal-icon">
        <font-awesome-icon :icon="['fas', 'terminal']" />
      </div>
    </div>

    <div
      v-else
      class="terminal-window"
      :class="`theme-${theme}`"
      :style="{ top: position.y + 'px', left: position.x + 'px' }"
      ref="terminalWindow"
      @click="focusInput"
    >
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

      <div class="terminal-content" @click="focusInput">
        <div class="terminal-output" ref="terminalOutput">
          <div v-for="(item, index) in commandHistory" :key="item.id" class="command-history-item">
            <div v-if="item.command" class="command-input">
              <span class="prompt mr-2">~$</span>
              <span>{{ item.command }}</span>
            </div>

            <div class="command-output">
              <div v-for="(line, lineIndex) in item.textOutput" :key="`text-${lineIndex}`" class="output-line">
                <template v-if="typeof line === 'string'">{{ line }}</template>
                <template v-else-if="line.type === 'link'">
                  {{ line.prefix }}<a :href="line.url" class="terminal-link">{{ line.text }}</a>
                </template>
                <template v-else-if="line.type === 'graph-history'">
                  <span class="git-graph-date">{{ line.date }}:</span>
                  <span class="git-graph-additions">{{ line.additionBars }}</span>
                  <span class="git-graph-deletions">{{ line.deletionBars }}</span>
                  <span class="git-graph-stats">({{ line.additions }} additions, {{ line.deletions }} deletions)</span>
                </template>
                <template v-else-if="line.type === 'latest-commit'">
                  <div class="git-latest-commit-container">
                    <div class="git-graph-title">{{ line.title }}</div>
                    <div class="latest-commit-content">
                      <div class="latest-commit-line">
                        <span class="latest-commit-hash">[{{ line.hash }}]</span>
                        <a v-if="line.url" :href="line.url" class="terminal-link">View on GitHub</a>
                      </div>
                      <div class="latest-commit-message">{{ line.message }}</div>
                    </div>
                  </div>
                </template>
              </div>

              <div v-if="item.graphData && item.graphData.isVisible" class="git-graph-container">
                <div class="git-graph-title">{{ item.graphData.title }}</div>

                <div v-if="item.graphData.noData" class="git-graph-no-data">
                  <div class="git-graph-no-data-icon">📊</div>
                  <div class="git-graph-no-data-message">No code frequency data available</div>
                  <div class="git-graph-no-data-explanation">{{ item.graphData.note }}</div>
                </div>

                <template v-else>
                  <div v-for="(week, weekIndex) in item.graphData.weeks" :key="weekIndex" class="git-graph-row">
                    <span class="git-graph-date">{{ week.date }}:</span>
                    <span class="git-graph-additions">{{ '+'.repeat(week.additionBars) }}</span>
                    <span class="git-graph-deletions">{{ '-'.repeat(week.deletionBars) }}</span>
                    <span class="git-graph-stats">({{ week.additions }} additions, {{ week.deletions }} deletions)</span>
                  </div>
                </template>

                <div v-if="!item.graphData.noData" class="git-graph-note">{{ item.graphData.note }}</div>
              </div>

              <div v-if="item.commitData && item.commitData.isVisible" class="git-latest-commit-container">
                <div class="git-graph-title">{{ item.commitData.title }}</div>
                <div class="latest-commit-content">
                  <div class="latest-commit-line">
                    <span class="latest-commit-hash">[{{ item.commitData.hash }}]</span>
                    <a v-if="item.commitData.url" :href="item.commitData.url" class="terminal-link">View on GitHub</a>
                  </div>
                  <div class="latest-commit-message">{{ item.commitData.message }}</div>
                </div>
              </div>

              <div v-if="item.isLoading" class="loading-container">
                <div class="progress-bar-container">
                  <div class="progress-bar" :style="{ width: `${item.loadingProgress}%` }"></div>
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
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted, onUnmounted } from 'vue';
import { library } from '@fortawesome/fontawesome-svg-core';
import { faTerminal } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';
import { getLatestCommitMessage, getCodeFrequency } from '../utils/gitInfo.js';
import { navItems, commandHistoryStore, nextCommandIdStore } from '../stores/ui.js';
import { useStore } from '@nanostores/vue';
// We don't need to import ClientOnly here anymore.

library.add(faTerminal);

export default {
  name: 'TerminalWindow',
  components: {
    FontAwesomeIcon,
    // ClientOnly is no longer a component here.
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
    const isMinimized = ref(false);
    const position = reactive({ x: 100, y: 100 });
    const isDragging = ref(false);
    const dragOffset = reactive({ x: 0, y: 0 });
    const theme = ref('dark');

    const commandHistory = useStore(commandHistoryStore);
    const nextCommandId = useStore(nextCommandIdStore);

    if (props.initialOutput && props.initialOutput.length > 0 && commandHistory.value.length === 0) {
      commandHistoryStore.set([{
        id: nextCommandIdStore.get(),
        timestamp: Date.now(),
        command: '',
        textOutput: [...props.initialOutput],
        isLoading: false,
        loadingProgress: 0,
        graphData: null,
        commitData: null
      }]);
      nextCommandIdStore.set(nextCommandIdStore.get() + 1);
    }

    const inputValue = ref('');
    const terminalWindow = ref(null);
    const terminalInput = ref(null);
    const terminalOutput = ref(null);
    const isLoading = ref(false);
    const loadingStartTime = ref(0);
    const loadingProgress = ref(0);

    const ensureMinLoadingTime = async (promise, historyIndex, minTime = 3000) => {
      if (historyIndex !== -1 && historyIndex < commandHistory.value.length) {
        const updatedHistory = [...commandHistory.value];
        updatedHistory[historyIndex] = {
          ...updatedHistory[historyIndex],
          textOutput: [...updatedHistory[historyIndex].textOutput],
          isLoading: true,
          loadingProgress: 0
        };
        commandHistoryStore.set(updatedHistory);
      }

      loadingStartTime.value = Date.now();

      const progressInterval = setInterval(() => {
        if (historyIndex !== -1 && historyIndex < commandHistory.value.length) {
          const updatedHistory = [...commandHistory.value];
          if (updatedHistory[historyIndex].loadingProgress < 90) {
            let newProgress = updatedHistory[historyIndex].loadingProgress + Math.random() * 3 + 1;
            if (newProgress > 90) newProgress = 90;
            updatedHistory[historyIndex] = {
              ...updatedHistory[historyIndex],
              textOutput: [...updatedHistory[historyIndex].textOutput],
              loadingProgress: newProgress
            };
            commandHistoryStore.set(updatedHistory);
          }
        }
      }, 100);

      const result = await promise;
      const elapsedTime = Date.now() - loadingStartTime.value;

      if (elapsedTime < minTime) {
        await new Promise(resolve => setTimeout(resolve, minTime - elapsedTime));
      }

      if (historyIndex !== -1 && historyIndex < commandHistory.value.length) {
        const updatedHistory = [...commandHistory.value];
        updatedHistory[historyIndex] = {
          ...updatedHistory[historyIndex],
          textOutput: [...updatedHistory[historyIndex].textOutput],
          loadingProgress: 100
        };
        commandHistoryStore.set(updatedHistory);
      }

      clearInterval(progressInterval);
      await new Promise(resolve => setTimeout(resolve, 200));

      if (historyIndex !== -1 && historyIndex < commandHistory.value.length) {
        const updatedHistory = [...commandHistory.value];
        updatedHistory[historyIndex] = {
          ...updatedHistory[historyIndex],
          textOutput: [...updatedHistory[historyIndex].textOutput],
          isLoading: false
        };
        commandHistoryStore.set(updatedHistory);
      }

      return result;
    };

    const startDrag = (event) => {
      if (terminalWindow.value && event.button === 0) {
        isDragging.value = true;
        dragOffset.x = event.clientX - position.x;
        dragOffset.y = event.clientY - position.y;
        document.addEventListener('mousemove', onDrag);
      }
    };

    const onDrag = (event) => {
      if (isDragging.value) {
        if (event.buttons === 0) {
          stopDrag();
          return;
        }
        position.x = event.clientX - dragOffset.x;
        position.y = event.clientY - dragOffset.y;
      }
    };

    const focusInput = (event) => {
      if (terminalInput.value) {
        terminalInput.value.focus();
      }
      if (event && event.stopPropagation) {
        event.stopPropagation();
      }
    };

    const stopDrag = () => {
      if (isDragging.value) {
        isDragging.value = false;
        document.removeEventListener('mousemove', onDrag);
        focusInput(null);
      }
    };

    const submitCommand = () => {
      if (inputValue.value.trim()) {
        const command = inputValue.value.trim();
        inputValue.value = '';

        const commandId = nextCommandIdStore.get();
        nextCommandIdStore.set(commandId + 1);

        const historyItem = {
          id: commandId,
          timestamp: Date.now(),
          command: command,
          textOutput: [],
          isLoading: false,
          loadingProgress: 0,
          graphData: null,
          commitData: null
        };

        commandHistoryStore.set([...commandHistory.value, historyItem]);
        handleCommand(command, commandId);

        setTimeout(() => {
          if (terminalOutput.value) {
            terminalOutput.value.scrollTop = terminalOutput.value.scrollHeight;
          }
        }, 0);
      }
    };

    const handleCommand = (command, commandId) => {
      const historyIndex = commandHistory.value.findIndex(item => item.id === commandId);
      if (historyIndex === -1) return;

      const parts = command.split(' ');
      const baseCommand = parts[0];
      const args = parts.slice(1);

      if (baseCommand === 'clear') {
        const currentCommand = commandHistory.value[historyIndex];
        commandHistoryStore.set([currentCommand]);
      } else if (baseCommand === 'help') {
        const updatedHistory = [...commandHistory.value];
        updatedHistory[historyIndex] = { ...updatedHistory[historyIndex], textOutput: [...updatedHistory[historyIndex].textOutput] };
        updatedHistory[historyIndex].textOutput.push('Available commands:', '- clear: Clear the terminal', '- help: Show this help message', '- theme: Toggle between light and dark theme', '- version: Show terminal version', '- ls: List navigation links', '- git --latest-commit: Show the latest git commit message', '- git --graph: Show code frequency (additions/deletions over time)');
        commandHistoryStore.set(updatedHistory);
      } else if (baseCommand === 'theme') {
        theme.value = theme.value === 'dark' ? 'light' : 'dark';
        const updatedHistory = [...commandHistory.value];
        updatedHistory[historyIndex] = { ...updatedHistory[historyIndex], textOutput: [...updatedHistory[historyIndex].textOutput] };
        updatedHistory[historyIndex].textOutput.push(`Theme switched to ${theme.value} mode`);
        commandHistoryStore.set(updatedHistory);
      } else if (baseCommand === 'version') {
        const updatedHistory = [...commandHistory.value];
        updatedHistory[historyIndex] = { ...updatedHistory[historyIndex], textOutput: [...updatedHistory[historyIndex].textOutput] };
        updatedHistory[historyIndex].textOutput.push('Terminal v1.0.0', 'Created by nickberens');
        commandHistoryStore.set(updatedHistory);
      } else if (baseCommand === 'ls') {
        const updatedHistory = [...commandHistory.value];
        updatedHistory[historyIndex] = { ...updatedHistory[historyIndex], textOutput: [...updatedHistory[historyIndex].textOutput] };
        updatedHistory[historyIndex].textOutput.push('Navigation links:');
        const items = navItems.get();
        items.forEach(item => {
          updatedHistory[historyIndex].textOutput.push({ type: 'link', prefix: '- ', url: item.url, text: item.text });
        });
        commandHistoryStore.set(updatedHistory);
      } else if (baseCommand === 'git') {
        if (args.length === 0) {
          const updatedHistory = [...commandHistory.value];
          updatedHistory[historyIndex] = { ...updatedHistory[historyIndex], textOutput: [...updatedHistory[historyIndex].textOutput] };
          updatedHistory[historyIndex].textOutput.push('Usage: git [--latest-commit | --graph]');
          commandHistoryStore.set(updatedHistory);
        } else if (args[0] === '--latest-commit') {
          const updatedHistory = [...commandHistory.value];
          updatedHistory[historyIndex] = { ...updatedHistory[historyIndex], textOutput: [...updatedHistory[historyIndex].textOutput] };
          updatedHistory[historyIndex].textOutput.push('Fetching latest commit message...');
          updatedHistory[historyIndex].isLoading = true;
          commandHistoryStore.set(updatedHistory);
          ensureMinLoadingTime(getLatestCommitMessage(), historyIndex)
            .then(commitData => {
              if (historyIndex !== -1) {
                const updatedHistory = [...commandHistory.value];
                updatedHistory[historyIndex] = {
                  ...updatedHistory[historyIndex],
                  textOutput: [...updatedHistory[historyIndex].textOutput],
                  isLoading: false,
                  commitData: { title: 'Latest Commit', hash: commitData.hash, url: commitData.url, message: commitData.message, isVisible: true }
                };
                commandHistoryStore.set(updatedHistory);
                setTimeout(() => { if (terminalOutput.value) terminalOutput.value.scrollTop = terminalOutput.value.scrollHeight; }, 0);
              }
            })
            .catch(error => {
              if (historyIndex !== -1) {
                const updatedHistory = [...commandHistory.value];
                updatedHistory[historyIndex] = { ...updatedHistory[historyIndex], textOutput: [...updatedHistory[historyIndex].textOutput] };
                updatedHistory[historyIndex].isLoading = false;
                updatedHistory[historyIndex].textOutput.push('Error retrieving latest commit message', error.message);
                commandHistoryStore.set(updatedHistory);
              }
            });
        } else if (args[0] === '--graph') {
          const updatedHistory = [...commandHistory.value];
          updatedHistory[historyIndex] = { ...updatedHistory[historyIndex], textOutput: [...updatedHistory[historyIndex].textOutput] };
          updatedHistory[historyIndex].textOutput.push('Fetching code frequency data...');
          updatedHistory[historyIndex].isLoading = true;
          commandHistoryStore.set(updatedHistory);
          ensureMinLoadingTime(getCodeFrequency(), historyIndex)
            .then(frequencyData => {
              if (historyIndex !== -1) {
                const updatedHistory = [...commandHistory.value];
                const graphData = processCodeFrequencyData(frequencyData);
                updatedHistory[historyIndex] = {
                  ...updatedHistory[historyIndex],
                  textOutput: [...updatedHistory[historyIndex].textOutput, 'Code Frequency (additions/deletions over time):', ''],
                  isLoading: false,
                  graphData: graphData
                };
                commandHistoryStore.set(updatedHistory);
                setTimeout(() => { if (terminalOutput.value) terminalOutput.value.scrollTop = terminalOutput.value.scrollHeight; }, 0);
              }
            })
            .catch(error => {
              if (historyIndex !== -1) {
                const updatedHistory = [...commandHistory.value];
                updatedHistory[historyIndex] = { ...updatedHistory[historyIndex], textOutput: [...updatedHistory[historyIndex].textOutput] };
                updatedHistory[historyIndex].isLoading = false;
                updatedHistory[historyIndex].textOutput.push('Error retrieving code frequency data', error.message);
                commandHistoryStore.set(updatedHistory);
              }
            });
        } else {
          const updatedHistory = [...commandHistory.value];
          updatedHistory[historyIndex] = { ...updatedHistory[historyIndex], textOutput: [...updatedHistory[historyIndex].textOutput] };
          updatedHistory[historyIndex].textOutput.push(`Unknown git option: ${args.join(' ')}`);
          commandHistoryStore.set(updatedHistory);
        }
      } else {
        const updatedHistory = [...commandHistory.value];
        updatedHistory[historyIndex] = { ...updatedHistory[historyIndex], textOutput: [...updatedHistory[historyIndex].textOutput] };
        updatedHistory[historyIndex].textOutput.push(`Command not found: ${baseCommand}`);
        commandHistoryStore.set(updatedHistory);
      }
    };

    const processCodeFrequencyData = (frequencyData) => {
      if (frequencyData && frequencyData.computing) {
        return { title: 'Code Frequency Data', weeks: [], note: frequencyData.message, isVisible: true, noData: true };
      }
      if (frequencyData && frequencyData.error) {
        return { title: 'Code Frequency Data', weeks: [], note: frequencyData.message, isVisible: true, noData: true };
      }
      if (!Array.isArray(frequencyData)) {
        return { title: 'Code Frequency Data', weeks: [], note: 'Invalid data format received', isVisible: true, noData: true };
      }
      if (frequencyData.length === 0) {
        return { title: 'Code Frequency Data', weeks: [], note: 'No code frequency data available. This could be because the repository is new, private, or the GitHub API has not calculated the statistics yet.', isVisible: true, noData: true };
      }

      const recentData = frequencyData.slice(-10);
      let maxAddition = 0;
      let maxDeletion = 0;
      recentData.forEach(week => {
        maxAddition = Math.max(maxAddition, week[1]);
        maxDeletion = Math.max(maxDeletion, Math.abs(week[2]));
      });
      const maxValue = Math.max(maxAddition, maxDeletion);
      const graphHeight = 10;

      return {
        title: 'Additions (+) / Deletions (-) - Last 10 weeks',
        weeks: recentData.map(week => {
          const date = new Date(week[0] * 1000).toISOString().split('T')[0];
          const additions = week[1];
          const deletions = Math.abs(week[2]);
          const additionBars = Math.round((additions / maxValue) * graphHeight);
          const deletionBars = Math.round((deletions / maxValue) * graphHeight);
          return { date, additions, deletions, additionBars, deletionBars };
        }),
        note: 'Note: Graph is scaled to fit the terminal window',
        isVisible: true,
        noData: false
      };
    };

    const handleDocumentClick = (event) => {};

    onMounted(() => {
      document.addEventListener('mouseup', stopDrag);
      document.addEventListener('click', handleDocumentClick);
      setTimeout(() => { focusInput(null); }, 0);
    });

    onUnmounted(() => {
      document.removeEventListener('mouseup', stopDrag);
      document.removeEventListener('mousemove', onDrag);
      document.removeEventListener('click', handleDocumentClick);
    });

    return {
      isMinimized,
      position,
      startDrag,
      stopDrag,
      commandHistory,
      inputValue,
      submitCommand,
      handleCommand,
      terminalWindow,
      terminalInput,
      terminalOutput,
      processCodeFrequencyData,
      focusInput,
      isLoading,
      loadingProgress,
      theme
    };
  }
};
</script>

<style scoped>
/* Command history styles */
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

/* Git graph styling */
.git-graph-additions {
  color: #27c93f; /* Green color for additions */
  font-weight: bold;
  letter-spacing: 1px;
}

.git-graph-deletions {
  color: #ff5f56; /* Red color for deletions */
  font-weight: bold;
  letter-spacing: 1px;
}

.git-graph-date {
  color: #ffbd2e; /* Yellow color for dates */
  font-weight: bold;
}

.git-graph-stats {
  color: #cccccc; /* Light gray for stats */
  font-style: italic;
  font-size: 0.9em;
}

.git-graph-title {
  color: #ffffff; /* White color for title */
  font-weight: bold;
  font-size: 1.1em;
  text-decoration: underline;
  margin-bottom: 10px;
}

.git-graph-note {
  color: #aaaaaa; /* Light gray for note */
  font-style: italic;
  font-size: 0.85em;
}

/* Theme-specific git graph styling */
.theme-light .git-graph-additions {
  color: #27a83f;
}

.theme-light .git-graph-deletions {
  color: #e74c3c;
}

.theme-light .git-graph-date {
  color: #f39c12;
}

.theme-light .git-graph-stats {
  color: #666666;
}

.theme-light .git-graph-title {
  color: #333333;
}

.theme-light .git-graph-note {
  color: #777777;
}

/* Git graph container styling */
.git-graph-container {
  margin-top: 10px;
  margin-bottom: 10px;
  padding: 5px;
  border: 1px solid #444;
  border-radius: 4px;
  background-color: rgba(0, 0, 0, 0.2);
}

.git-graph-row {
  display: flex;
  align-items: center;
  margin: 2px 0;
  white-space: nowrap;
}

/* No data message styling */
.git-graph-no-data {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px 10px;
  text-align: center;
}

.git-graph-no-data-icon {
  font-size: 24px;
  margin-bottom: 10px;
}

.git-graph-no-data-message {
  font-size: 14px;
  color: #cccccc;
  font-style: italic;
  margin-bottom: 8px;
}

.git-graph-no-data-explanation {
  font-size: 12px;
  color: #aaaaaa;
  font-style: italic;
  max-width: 80%;
  text-align: center;
  margin-top: 8px;
}

.theme-light .git-graph-container {
  border-color: #ccc;
  background-color: rgba(0, 0, 0, 0.05);
}

.theme-light .git-graph-no-data-message {
  color: #666666;
}

.theme-light .git-graph-no-data-explanation {
  color: #888888;
}

/* Git latest commit container styling - similar to git graph container */
.git-latest-commit-container {
  margin-top: 10px;
  margin-bottom: 10px;
  padding: 5px;
  border: 1px solid #444;
  border-radius: 4px;
  background-color: rgba(0, 0, 0, 0.2);
}

.theme-light .git-latest-commit-container {
  border-color: #ccc;
  background-color: rgba(0, 0, 0, 0.05);
}

.latest-commit-line {
  margin: 5px 0;
}

.latest-commit-hash {
  color: #ffbd2e; /* Yellow color for hash, same as dates in graph */
  font-weight: bold;
  margin-right: 10px;
}

.latest-commit-message {
  margin-top: 8px;
  white-space: pre-wrap;
  word-break: break-all;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .terminal-window {
    width: 90%;
    height: 350px;
  }
}

/* Loading animation */
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.loading-indicator {
  display: inline-block;
  width: 10px;
  height: 16px;
  background-color: #f8f8f8;
  animation: blink 1s infinite;
  margin-left: 5px;
  vertical-align: middle;
}

.theme-light .loading-indicator {
  background-color: #333;
}

/* Progress bar styling */
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
  background-color: #ffffff; /* White color */
  border-radius: 0;
  transition: width 0.3s ease;
}

/* NOTE: The stray 'd' was here. It has been removed. */

.theme-light .progress-bar {
  background-color: #000000;
}

.theme-light .progress-bar-container {
  background-color: rgba(0, 0, 0, 0.2);
}

/* Terminal link styling */
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