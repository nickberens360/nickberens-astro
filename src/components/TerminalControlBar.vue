<template>
  <div
    class="terminal-header"
    @pointerdown="startDrag"
    @pointerup="stopDrag"
  >
    <div class="terminal-controls">
      <div
        class="control close"
        @click="$emit('minimize')"
      ></div>
      <div
        class="control minimize"
        @click="$emit('minimize')"
      ></div>
      <div
        class="control maximize"
        @click="$emit('maximize')"
      />
    </div>
    <div class="terminal-title">{{ title }}</div>
  </div>
</template>

<script>
export default {
  name: 'TerminalControlBar',
  props: {
    title: {
      type: String,
      default: 'Terminal'
    }
  },
  emits: ['close', 'minimize', 'maximize', 'startDrag', 'stopDrag'],
  setup(props, { emit }) {
    const startDrag = (event) => {
      if (event.isPrimary) {
        emit('startDrag', event);
        event.preventDefault(); // Prevent default touch actions
      }
    };

    const stopDrag = () => {
      emit('stopDrag');
    };

    return {
      startDrag,
      stopDrag
    };
  }
};
</script>

<style scoped>
/* Terminal header with controls */
.terminal-header {
  height: 28px;
  z-index: 1000;
  background-color: #3c3c3c;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  padding: 0 10px;
  cursor: move;
  user-select: none;
  touch-action: none;
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

/* Theme-specific styles */
:deep(.theme-light) .terminal-header {
  background-color: #d8d8d8;
}

:deep(.theme-light) .terminal-title {
  color: #333;
}
</style>
