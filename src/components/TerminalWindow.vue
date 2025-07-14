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
      @click="focusInput"
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
      <div class="terminal-content" @click="focusInput">
        <div class="terminal-output" ref="terminalOutput">
          <div v-for="(line, index) in outputLines" :key="index" class="output-line" v-html="line">
          </div>

          <!-- Git Graph Visualization -->
          <div v-if="graphData.isVisible" class="git-graph-container">
            <div class="git-graph-title">{{ graphData.title }}</div>

            <!-- No data message -->
            <div v-if="graphData.noData" class="git-graph-no-data">
              <div class="git-graph-no-data-icon">📊</div>
              <div class="git-graph-no-data-message">No code frequency data available</div>
              <div class="git-graph-no-data-explanation">{{ graphData.note }}</div>
            </div>

            <!-- Graph data rows -->
            <template v-else>
              <div v-for="(week, index) in graphData.weeks" :key="index" class="git-graph-row">
                <span class="git-graph-date">{{ week.date }}:</span>

                <span class="git-graph-additions">
                  {{ '+'.repeat(week.additionBars) }}
                </span>

                <span class="git-graph-deletions">
                  {{ '-'.repeat(week.deletionBars) }}
                </span>

                <span class="git-graph-stats">
                  ({{ week.additions }} additions, {{ week.deletions }} deletions)
                </span>
              </div>
            </template>

            <div v-if="!graphData.noData" class="git-graph-note">{{ graphData.note }}</div>
          </div>
        </div>

        <!-- Loading indicator -->
        <div v-if="isLoading" class="loading-container">
          <span class="loading-text">Loading data</span>
          <span class="loading-indicator"></span>
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
    const isLoading = ref(false);
    const loadingStartTime = ref(0);

    // Helper function to ensure minimum loading time
    const ensureMinLoadingTime = async (promise, minTime = 3000) => {
      isLoading.value = true;
      loadingStartTime.value = Date.now();

      // Wait for the promise to resolve
      const result = await promise;

      // Calculate how much time has passed
      const elapsedTime = Date.now() - loadingStartTime.value;

      // If less than minTime has passed, wait for the remaining time
      if (elapsedTime < minTime) {
        await new Promise(resolve => setTimeout(resolve, minTime - elapsedTime));
      }

      isLoading.value = false;
      return result;
    };

    // Add this to your reactive state
    const graphData = ref({
      title: '',
      weeks: [],
      note: '',
      isVisible: false
    });

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

    const focusInput = (event) => {
      // Focus the input element if it exists
      if (terminalInput.value) {
        terminalInput.value.focus();
      }

      // If this was triggered by a click event, stop propagation
      // to prevent the document click handler from being triggered
      if (event && event.stopPropagation) {
        event.stopPropagation();
      }
    };

    const stopDrag = () => {
      if (isDragging.value) {
        isDragging.value = false;
        document.removeEventListener('mousemove', onDrag);
        // Focus the input after dragging stops
        focusInput(null);
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
        graphData.value.isVisible = false; // Also hide the GitHub graph
      } else if (baseCommand === 'help') {
        outputLines.value.push('Available commands:');
        outputLines.value.push('- clear: Clear the terminal');
        outputLines.value.push('- help: Show this help message');
        outputLines.value.push('- theme: Toggle between light and dark theme');
        outputLines.value.push('- version: Show terminal version');
        outputLines.value.push('- git --latest-commit: Show the latest git commit message');
        outputLines.value.push('- git --graph: Show code frequency (additions/deletions over time)');
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

          ensureMinLoadingTime(getLatestCommitMessage())
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
        } else if (args[0] === '--graph') {
          outputLines.value.push('Fetching code frequency data...');

          ensureMinLoadingTime(getCodeFrequency())
            .then(frequencyData => {
              outputLines.value.push('Code Frequency (additions/deletions over time):');
              outputLines.value.push('');

              // Render the ASCII graph or show "no data" message
              renderCodeFrequencyGraph(frequencyData);

              // Scroll to bottom of output
              setTimeout(() => {
                if (terminalOutput.value) {
                  terminalOutput.value.scrollTop = terminalOutput.value.scrollHeight;
                }
              }, 0);
            })
            .catch(error => {
              outputLines.value.push('Error retrieving code frequency data');
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

    // Render code frequency graph
    const renderCodeFrequencyGraph = (frequencyData) => {
      // Check if GitHub is still computing the data
      if (frequencyData && frequencyData.computing) {
        graphData.value = {
          title: 'Code Frequency Data',
          weeks: [],
          note: frequencyData.message,
          isVisible: true,
          noData: true
        };

        outputLines.value.push('[Statistics being calculated]');
        outputLines.value.push('');
        return;
      }

      // Check if there was an error
      if (frequencyData && frequencyData.error) {
        graphData.value = {
          title: 'Code Frequency Data',
          weeks: [],
          note: frequencyData.message,
          isVisible: true,
          noData: true
        };

        outputLines.value.push('[Error retrieving statistics]');
        outputLines.value.push(frequencyData.message);
        outputLines.value.push('');
        return;
      }

      // Ensure frequencyData is an array
      if (!Array.isArray(frequencyData)) {
        outputLines.value.push('Error: Invalid frequency data format');
        return;
      }

      // Check if we have any data
      if (frequencyData.length === 0) {
        // Set up graph data with no-data message
        graphData.value = {
          title: 'Code Frequency Data',
          weeks: [],
          note: 'No code frequency data available. This could be because the repository is new, private, or the GitHub API has not calculated the statistics yet.',
          isVisible: true,
          noData: true
        };

        // Add a message to the output lines
        outputLines.value.push('[No graph data available]');
        outputLines.value.push('');
        return;
      }

      // Get the last 10 weeks of data (or less if not available)
      const recentData = frequencyData.slice(-10);

      // Find max values for scaling
      let maxAddition = 0;
      let maxDeletion = 0;

      recentData.forEach(week => {
        maxAddition = Math.max(maxAddition, week[1]);
        maxDeletion = Math.max(maxDeletion, Math.abs(week[2]));
      });

      const maxValue = Math.max(maxAddition, maxDeletion);
      const graphHeight = 10; // Height of the graph in lines

      // Update the graph data structure
      graphData.value = {
        title: 'Additions (+) / Deletions (-) - Last 10 weeks',
        weeks: recentData.map(week => {
          const date = new Date(week[0] * 1000).toISOString().split('T')[0];
          const additions = week[1];
          const deletions = Math.abs(week[2]);

          // Scale the values to fit in the terminal
          const additionBars = Math.round((additions / maxValue) * graphHeight);
          const deletionBars = Math.round((deletions / maxValue) * graphHeight);

          return {
            date,
            additions,
            deletions,
            additionBars,
            deletionBars
          };
        }),
        note: 'Note: Graph is scaled to fit the terminal window',
        isVisible: true,
        noData: false
      };

      // Add a message to the output lines
      outputLines.value.push('[Graph data displayed below]');
      outputLines.value.push('');
    };

    // Handle clicks outside the terminal window
    const handleDocumentClick = (event) => {
      // If the click is outside the terminal window, we don't need to do anything
      // The input will naturally lose focus
      // When the terminal window is clicked, the focusInput handler will take care of focusing
    };

    // Clean up event listeners
    onMounted(() => {
      document.addEventListener('mouseup', stopDrag);
      document.addEventListener('click', handleDocumentClick);

      // Focus the input when the component is mounted
      setTimeout(() => {
        focusInput(null);
      }, 0);
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
      outputLines,
      inputValue,
      submitCommand,
      handleCommand,
      terminalWindow,
      terminalInput,
      terminalOutput,
      renderCodeFrequencyGraph,
      graphData,  // Add this line
      focusInput,  // Expose focusInput function
      isLoading   // Add loading state
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

.loading-text {
  color: #27c93f;
  font-weight: bold;
}

.theme-light .loading-text {
  color: #27a83f;
}
</style>
