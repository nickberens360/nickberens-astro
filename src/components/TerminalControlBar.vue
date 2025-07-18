<template>
  <div
    class="terminal-header"
    @pointerdown="startDrag"
    @pointerup="stopDrag"
  >
    <div class="terminal-controls">
      <div
        class="control close"
        @click="$emit('close')"
      />
      <div
        class="control minimize"
        :class="{ 'disabled': isMaximized }"
        @click="!isMaximized && $emit('minimize')"
      />
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
  components: {},
  props: {
    title: {
      type: String,
      default: 'Terminal'
    },
    isMaximized: {
      type: Boolean,
      default: false
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

.control.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.terminal-title {
  flex-grow: 1;
  text-align: center;
  color: #cccccc;
  font-size: 14px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
}

/* Custom tooltip styles */
.tooltip-container {
  position: relative;
  display: inline-block;
}

.tooltip {
  visibility: hidden;
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  background-color: #333;
  color: white;
  text-align: center;
  padding: 5px 10px;
  border-radius: 4px;
  white-space: nowrap;
  z-index: 1;
  opacity: 0;
  transition: opacity 0.1s ease-in-out;
  margin-bottom: 5px;
  font-size: 0.8rem;
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tooltip::after {
  content: "";
  position: absolute;
  top: 100%;
  left: 50%;
  margin-left: -5px;
  border-width: 5px;
  border-style: solid;
  border-color: #333 transparent transparent transparent;
}

.tooltip-container:hover .tooltip {
  visibility: visible;
  opacity: 1;
}

/* Theme-specific styles */
:deep(.theme-light) .terminal-header {
  background-color: #d8d8d8;
}

:deep(.theme-light) .terminal-title {
  color: #333;
}
</style>
