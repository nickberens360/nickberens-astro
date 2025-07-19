<template>
  <div class="terminal-content" @click="$emit('focusInput')">
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
                @click="$emit('unmaximize')"
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

          <terminal-progress-bar
            v-if="item.isLoading"
            :progress="item.loadingProgress"
            :theme="theme"
          />
        </div>
      </div>
    </div>

    <terminal-input-line
      :input-value="inputValue"
      @update:input-value="$emit('update:inputValue', $event)"
      @submit="$emit('submitCommand')"
      ref="terminalInput"
    />
  </div>
</template>

<script>
import TerminalGraphOutput from './TerminalGraphOutput.vue';
import TerminalLogOutput from './TerminalLogOutput.vue';
import TerminalInputLine from './TerminalInputLine.vue';
import TerminalProgressBar from './TerminalProgressBar.vue';

export default {
  name: 'TerminalContent',
  components: {
    TerminalGraphOutput,
    TerminalLogOutput,
    TerminalInputLine,
    TerminalProgressBar,
  },
  props: {
    theme: {
      type: String,
      default: 'dark'
    },
    commandHistory: {
      type: Array,
      default: () => []
    },
    inputValue: {
      type: String,
      default: ''
    }
  },
  emits: ['focusInput', 'unmaximize', 'update:inputValue', 'submitCommand'],
  methods: {
    // Expose focus method for parent component
    focusInput() {
      this.$refs.terminalInput?.focus();
    }
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

.prompt {
  color: #f8f8f8;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  margin-right: 8px;
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

.terminal-link {
  color: #3498db;
  text-decoration: underline;
  cursor: pointer;
}

.terminal-link:hover {
  color: #2980b9;
}

/* Theme variations would go here */
</style>