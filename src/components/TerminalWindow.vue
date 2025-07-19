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

      <div class="terminal-content" @click="focusInput">
        <div class="terminal-output" ref="terminalOutput">
          <div
            v-for="(item, index) in commandHistory"
            :key="item.id"
            class="command-history-item"
          >
            <div v-if="item.command" class="command-input">
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
                    @click="unmaximizeTerminal"
                  >{{ line.text }}</a>
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
                :theme="theme"
              />

              <div v-if="item.isLoading" class="loading-container">
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

      <!-- Resize handles -->
      <div class="resize-handle resize-n" @pointerdown="startResize('n', $event)"></div>
      <div class="resize-handle resize-e" @pointerdown="startResize('e', $event)"></div>
      <div class="resize-handle resize-s" @pointerdown="startResize('s', $event)"></div>
      <div class="resize-handle resize-w" @pointerdown="startResize('w', $event)"></div>
      <div class="resize-handle resize-ne" @pointerdown="startResize('ne', $event)"></div>
      <div class="resize-handle resize-se" @pointerdown="startResize('se', $event)"></div>
      <div class="resize-handle resize-sw" @pointerdown="startResize('sw', $event)"></div>
      <div class="resize-handle resize-nw" @pointerdown="startResize('nw', $event)"></div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import TerminalControlBar from './TerminalControlBar.vue';
import TerminalGraphOutput from './TerminalGraphOutput.vue';
import TerminalLogOutput from './TerminalLogOutput.vue';
import { useTerminalCommands } from '../composables/useTerminalCommands.js';
import { useTerminalResize } from '../composables/useTerminalResize.js';
import { useTerminalState } from '../composables/useTerminalState.js';

export default {
  name: 'TerminalWindow',
  components: {
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
    },
    hideTerminal: {
      type: Boolean,
      default: false,
    }
  },
  setup(props) {
    // --- REFS ---
    const terminalWindow = ref(null);
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
      resizeDirection
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
    };

    // --- LIFECYCLE ---
    onMounted(() => {
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
      terminalInput,
      terminalOutput,

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
      focusInput: terminalState.focusInput,

      // From useTerminalResize composable
      terminalStyle,
      resizeDirection,
      startDrag,
      stopDrag,
      startResize,
      stopResize,
      toggleMaximize,

      // Methods
      submitCommand,
      unmaximizeTerminal,
    };
  }
};
</script>

<style scoped>
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

.terminal-maximized .resize-handle {
  display: none;
}

.terminal-content {
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

/* Resize handle styles */
.resize-handle {
  position: absolute;
  background: transparent;
  touch-action: none;
  z-index: 10;
}

.resize-ne, .resize-se, .resize-sw, .resize-nw {
  width: 15px;
  height: 15px;
}

.resize-n, .resize-s {
  height: 8px;
  left: 8px;
  right: 8px;
}

.resize-e, .resize-w {
  width: 8px;
  top: 8px;
  bottom: 8px;
}

.resize-n { top: 0; cursor: ns-resize; }
.resize-e { right: 0; cursor: ew-resize; }
.resize-s { bottom: 0; cursor: ns-resize; }
.resize-w { left: 0; cursor: ew-resize; }
.resize-ne { top: 0; right: 0; cursor: nesw-resize; }
.resize-se { bottom: 0; right: 0; cursor: nwse-resize; }
.resize-sw { bottom: 0; left: 0; cursor: nesw-resize; }
.resize-nw { top: 0; left: 0; cursor: nwse-resize; }

.resize-se::before {
  content: "";
  position: absolute;
  right: 3px;
  bottom: 3px;
  width: 9px;
  height: 9px;
  border-right: 2px solid rgba(255, 255, 255, 0.5);
  border-bottom: 2px solid rgba(255, 255, 255, 0.5);
}

.theme-light .resize-se::before {
  border-right: 2px solid rgba(0, 0, 0, 0.3);
  border-bottom: 2px solid rgba(0, 0, 0, 0.3);
}

.terminal-maximized .resize-handle {
  display: none;
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