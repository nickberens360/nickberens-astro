<template>
  <div class="terminal-example">
    <h1>Terminal Window Example</h1>

    <div class="controls">
      <button @click="showTerminal = !showTerminal">
        {{ showTerminal ? 'Hide Terminal' : 'Show Terminal' }}
      </button>
      <button @click="changeTheme">
        Toggle Theme (Current: {{ currentTheme }})
      </button>
    </div>

    <TerminalWindow
      v-if="showTerminal"
      :title="terminalTitle"
      v-model:theme="currentTheme"
      :initialOutput="initialOutput"
      @close="showTerminal = false"
    />
  </div>
</template>

<script>
import { ref } from 'vue';
import TerminalWindow from '../components/TerminalWindow.vue';

export default {
  name: 'TerminalWindowExample',
  components: {
    TerminalWindow
  },
  setup() {
    const showTerminal = ref(true);
    const currentTheme = ref('dark');
    const terminalTitle = ref('nickberens ~ bash');

    const initialOutput = [
      'Welcome to Terminal',
      'Type "help" for available commands',
      'Type "theme" to toggle the theme',
      'Type "clear" to clear the terminal'
    ];

    const changeTheme = () => {
      currentTheme.value = currentTheme.value === 'dark' ? 'light' : 'dark';
    };

    return {
      showTerminal,
      currentTheme,
      terminalTitle,
      initialOutput,
      changeTheme
    };
  }
};
</script>

<style scoped>
.terminal-example {
  padding: 20px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
}

h1 {
  margin-bottom: 20px;
}

.controls {
  margin-bottom: 20px;
  display: flex;
  gap: 10px;
}

button {
  padding: 8px 16px;
  background-color: #3c3c3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

button:hover {
  background-color: #555;
}
</style>
