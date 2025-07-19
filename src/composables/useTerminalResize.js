import { ref, reactive, computed, onUnmounted } from 'vue';
import {
  terminalPositionStore,
  terminalSizeStore,
  isTerminalMaximizedStore,
  previousTerminalStateStore
} from '../stores/ui.js';
import { MAXIMIZED_TERMINAL } from '../config/terminalConfig.js';

export function useTerminalResize(terminalWindow, position, size, isMaximized, previousTerminalState) {
  // --- DRAG STATE ---
  const isDragging = ref(false);
  const dragOffset = reactive({ x: 0, y: 0 });

  // --- RESIZE STATE ---
  const isResizing = ref(false);
  const resizeDirection = ref('');
  const resizeStartPos = reactive({ x: 0, y: 0, startX: 0, startY: 0 });
  const resizeStartSize = reactive({ width: 0, height: 0 });

  // --- COMPUTED TERMINAL STYLE ---
  const terminalStyle = computed(() => {
    if (isMaximized.value) {
      const margin = MAXIMIZED_TERMINAL.margin;
      return {
        top: `${margin}px`,
        left: `${margin}px`,
        right: `${margin}px`,
        bottom: `${margin}px`,
        width: `calc(100% - ${margin * 2}px)`,
        height: `calc(100% - ${margin * 2}px)`
      };
    }

    return {
      top: `${position.value?.y || 100}px`,
      left: `${position.value?.x || 100}px`,
      width: `${size.value?.width || 600}px`,
      height: `${size.value?.height || 400}px`,
    };
  });

  // --- DRAG FUNCTIONS ---
  const startDrag = (event) => {
    if (terminalWindow.value && event.isPrimary) {
      isDragging.value = true;
      dragOffset.x = event.clientX - position.value.x;
      dragOffset.y = event.clientY - position.value.y;
      document.addEventListener('pointermove', onDrag);
      document.addEventListener('pointerup', stopDrag);
      event.preventDefault();
    }
  };

  const onDrag = (event) => {
    if (isDragging.value) {
      terminalPositionStore.set({
        x: event.clientX - dragOffset.x,
        y: event.clientY - dragOffset.y
      });
    }
  };

  const stopDrag = () => {
    isDragging.value = false;
    document.removeEventListener('pointermove', onDrag);
    document.removeEventListener('pointerup', stopDrag);
  };

  // --- RESIZE FUNCTIONS ---
  const startResize = (direction, event) => {
    if (event.isPrimary) {
      isResizing.value = true;
      resizeDirection.value = direction;
      resizeStartPos.x = event.clientX;
      resizeStartPos.y = event.clientY;
      resizeStartSize.width = size.value.width;
      resizeStartSize.height = size.value.height;

      if (position.value) {
        resizeStartPos.startX = position.value.x;
        resizeStartPos.startY = position.value.y;
      }

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

      let newWidth = resizeStartSize.width;
      let newHeight = resizeStartSize.height;
      let newX = position.value.x;
      let newY = position.value.y;

      const direction = resizeDirection.value;

      // Handle horizontal resizing
      if (direction.includes('e')) {
        newWidth = Math.max(200, resizeStartSize.width + deltaX);
      } else if (direction.includes('w')) {
        const widthChange = Math.min(deltaX, resizeStartSize.width - 200);
        newWidth = resizeStartSize.width - widthChange;
        newX = resizeStartPos.startX + widthChange;
      }

      // Handle vertical resizing
      if (direction.includes('s')) {
        newHeight = Math.max(74, resizeStartSize.height + deltaY);
      } else if (direction.includes('n')) {
        const heightChange = Math.min(deltaY, resizeStartSize.height - 74);
        newHeight = resizeStartSize.height - heightChange;
        newY = resizeStartPos.startY + heightChange;
      }

      // Update position and size
      terminalPositionStore.set({ x: newX, y: newY });
      terminalSizeStore.set({ width: newWidth, height: newHeight });
    }
  };

  const stopResize = () => {
    isResizing.value = false;
    resizeDirection.value = '';
    document.removeEventListener('pointermove', onResize);
    document.removeEventListener('pointerup', stopResize);
  };

  // --- MAXIMIZE FUNCTIONS ---
  const toggleMaximize = () => {
    if (!isMaximized.value) {
      // Save current position and size before maximizing
      previousTerminalStateStore.set({
        position: { ...position.value },
        size: { ...size.value }
      });
      isTerminalMaximizedStore.set(true);
      document.body.style.overflow = 'hidden';
    } else {
      // Restore previous position and size
      if (previousTerminalState.value.position && previousTerminalState.value.size) {
        terminalPositionStore.set(previousTerminalState.value.position);
        terminalSizeStore.set(previousTerminalState.value.size);
      }
      isTerminalMaximizedStore.set(false);
      document.body.style.overflow = '';
    }
  };

  // --- CLEANUP ---
  onUnmounted(() => {
    document.removeEventListener('pointerup', stopDrag);
    document.removeEventListener('pointermove', onDrag);
    document.removeEventListener('pointerup', stopResize);
    document.removeEventListener('pointermove', onResize);
  });

  return {
    // State
    isDragging,
    isResizing,
    resizeDirection,
    terminalStyle,

    // Drag functions
    startDrag,
    stopDrag,

    // Resize functions
    startResize,
    stopResize,

    // Maximize functions
    toggleMaximize
  };
}