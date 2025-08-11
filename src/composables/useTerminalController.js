import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue';
import { useStore } from '@nanostores/vue';
import {
  commandHistoryStore,
  nextCommandIdStore,
  terminalPositionStore,
  terminalSizeStore,
  isTerminalMinimizedStore,
  isTerminalHiddenStore,
  isTerminalMaximizedStore,
  previousTerminalStateStore
} from '../stores/terminal-window.js';

export function useTerminalController(props) {
  // === REFS ===
  const terminalWindow = ref(null);
  const terminalContent = ref(null);
  const isMounted = ref(false);

  // === THEME & INPUT ===
  const savedTheme = localStorage.getItem('terminalTheme');
  const validThemes = ['dark', 'light'];
  const theme = ref(validThemes.includes(savedTheme) ? savedTheme : 'dark');
  const inputValue = ref('');

  // === MOUSE HOVER STATE ===
  const isHovered = ref(false);
  const isTouching = ref(false);

  // === STORE SUBSCRIPTIONS ===
  const isMinimized = useStore(isTerminalMinimizedStore);
  const isHidden = useStore(isTerminalHiddenStore);
  const isMaximized = useStore(isTerminalMaximizedStore);
  const position = useStore(terminalPositionStore);
  const size = useStore(terminalSizeStore);
  const previousState = useStore(previousTerminalStateStore);
  const commandHistory = useStore(commandHistoryStore);
  const nextCommandId = useStore(nextCommandIdStore);

  // === COMPUTED VALUES ===
  const isVisible = computed(() => !isHidden.value);
  const isExpanded = computed(() => isVisible.value && !isMinimized.value);
  const shouldBlockScroll = computed(() => {
    // Block scroll if maximized OR if hovering/touching over a non-maximized terminal
    return (isExpanded.value && isMaximized.value) ||
      (isExpanded.value && !isMaximized.value && (isHovered.value || isTouching.value));
  });

  const terminalStyle = computed(() => {
    if (isMaximized.value) {
      return {
        position: 'fixed',
        top: '0',
        left: '0',
        right: '0',
        bottom: '0',
        width: '100%',
        height: '100%',
        zIndex: 'var(--z-index-terminal)',
        borderRadius: '0'
      };
    }

    return {
      position: 'fixed',
      top: `${position.value?.y || 100}px`,
      left: `${position.value?.x || 100}px`,
      width: `${size.value?.width || 600}px`,
      height: `${size.value?.height || 400}px`,
      zIndex: 'var(--z-index-terminal)'
    };
  });

  // === BODY SCROLL MANAGEMENT ===
  let wheelEventListener = null;
  let touchMoveListener = null;
  
  const preventScroll = (e) => {
    // Check if the scroll event is coming from within the terminal
    const terminalOutput = terminalContent.value?.$refs?.terminalOutput;
    if (terminalOutput && terminalOutput.contains(e.target)) {
      // Allow scrolling within terminal
      return;
    }
    e.preventDefault();
  };
  
  const blockBodyScroll = () => {
    // Prevent wheel events
    wheelEventListener = (e) => preventScroll(e);
    document.addEventListener('wheel', wheelEventListener, { passive: false });
    
    // Prevent touch move events for mobile
    touchMoveListener = (e) => preventScroll(e);
    document.addEventListener('touchmove', touchMoveListener, { passive: false });
    
    // Add overflow hidden as backup
    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';
  };
  
  const unblockBodyScroll = () => {
    // Remove event listeners
    if (wheelEventListener) {
      document.removeEventListener('wheel', wheelEventListener);
      wheelEventListener = null;
    }
    if (touchMoveListener) {
      document.removeEventListener('touchmove', touchMoveListener);
      touchMoveListener = null;
    }
    
    // Remove overflow hidden
    document.body.style.overflow = '';
    document.documentElement.style.overflow = '';
  };
  
  const manageBodyScroll = () => {
    if (shouldBlockScroll.value) {
      blockBodyScroll();
    } else {
      unblockBodyScroll();
    }
  };

  // Watch for any state changes that affect body scroll
  watch(shouldBlockScroll, manageBodyScroll, { immediate: true });

  // === TERMINAL ACTIONS ===
  const actions = {
    show() {
      isTerminalHiddenStore.set(false);
      if (isMinimized.value) {
        isTerminalMinimizedStore.set(false);
      }
    },

    hide() {
      isTerminalHiddenStore.set(true);
    },

    minimize() {
      isTerminalMinimizedStore.set(true);
    },

    restore() {
      isTerminalMinimizedStore.set(false);
    },

    maximize() {
      if (isMaximized.value) {
        // Unmaximize
        isTerminalMaximizedStore.set(false);

        // Restore previous state if available
        if (previousState.value?.position && previousState.value?.size) {
          terminalPositionStore.set(previousState.value.position);
          terminalSizeStore.set(previousState.value.size);
        }
      } else {
        // Save current state before maximizing
        previousTerminalStateStore.set({
          position: { ...position.value },
          size: { ...size.value }
        });

        // Maximize
        isTerminalMaximizedStore.set(true);
      }
    },

    toggleMaximize() {
      actions.maximize();
    },

    // Unified unmaximize method for all use cases
    unmaximize() {
      if (isMaximized.value) {
        actions.maximize(); // This will unmaximize since it's already maximized
      }
    }
  };

  // === THEME MANAGEMENT ===
  const setTheme = (newTheme) => {
    if (validThemes.includes(newTheme)) {
      theme.value = newTheme;
      localStorage.setItem('terminalTheme', newTheme);
    }
  };

  // === INPUT MANAGEMENT ===
  const focusInput = (event) => {
    if (!event || event.target.tagName !== 'A') {
      terminalContent.value?.focusInput();
    }
  };

  const submitCommand = (handleCommand) => {
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

    handleCommand(command, commandId, { value: theme.value, setTheme });
    scrollToBottom();
  };

  // === SCROLL MANAGEMENT ===
  const scrollToBottom = () => {
    nextTick(() => {
      if (terminalContent.value && isMounted.value) {
        const outputEl = terminalContent.value.$refs?.terminalOutput;
        if (outputEl) {
          outputEl.scrollTop = outputEl.scrollHeight;
        }
      }
    });
  };

  // === KEYBOARD HANDLING ===
  const handleKeyDown = (event) => {
    if (event.key === 'Escape' && isMaximized.value) {
      actions.unmaximize();
    }
  };

  // === DRAG & RESIZE STATE ===
  const dragState = ref({
    isDragging: false,
    offset: { x: 0, y: 0 }
  });

  const resizeState = ref({
    isResizing: false,
    direction: '',
    startPos: { x: 0, y: 0 },
    startSize: { width: 0, height: 0 },
    startPosition: { x: 0, y: 0 }
  });

  // === MOUSE HANDLERS ===
  const mouseHandlers = {
    enter() {
      if (isExpanded.value && !isMaximized.value) {
        isHovered.value = true;
      }
    },

    leave() {
      isHovered.value = false;
    }
  };

  // === TOUCH HANDLERS ===
  const touchHandlers = {
    start(event) {
      if (isExpanded.value && !isMaximized.value) {
        isTouching.value = true;
      }
    },

    end() {
      isTouching.value = false;
    }
  };

  // === WHEEL HANDLER ===
  const wheelHandler = (event) => {
    // This is now handled by the document-level wheel listener
    // We keep this handler empty to avoid conflicts
  };

  // === DRAG HANDLERS ===
  const dragHandlers = {
    start(event) {
      if (!event.isPrimary || isMaximized.value) return;

      dragState.value.isDragging = true;
      dragState.value.offset.x = event.clientX - position.value.x;
      dragState.value.offset.y = event.clientY - position.value.y;

      document.addEventListener('pointermove', dragHandlers.move);
      document.addEventListener('pointerup', dragHandlers.stop);
      event.preventDefault();
    },

    move(event) {
      if (!dragState.value.isDragging) return;

      const margin = 20;
      let newX = event.clientX - dragState.value.offset.x;
      let newY = event.clientY - dragState.value.offset.y;

      // Keep within bounds
      newX = Math.max(margin, Math.min(newX, window.innerWidth - size.value.width - margin));
      newY = Math.max(margin, Math.min(newY, window.innerHeight - size.value.height - margin));

      terminalPositionStore.set({ x: newX, y: newY });
    },

    stop() {
      dragState.value.isDragging = false;
      document.removeEventListener('pointermove', dragHandlers.move);
      document.removeEventListener('pointerup', dragHandlers.stop);
    }
  };

  // === RESIZE HANDLERS ===
  const resizeHandlers = {
    start(direction, event) {
      if (!event.isPrimary || isMaximized.value) return;

      const state = resizeState.value;
      state.isResizing = true;
      state.direction = direction;
      state.startPos.x = event.clientX;
      state.startPos.y = event.clientY;
      state.startSize.width = size.value.width;
      state.startSize.height = size.value.height;
      state.startPosition.x = position.value.x;
      state.startPosition.y = position.value.y;

      document.addEventListener('pointermove', resizeHandlers.move);
      document.addEventListener('pointerup', resizeHandlers.stop);
      event.preventDefault();
      event.stopPropagation();
    },

    move(event) {
      if (!resizeState.value.isResizing) return;

      const state = resizeState.value;
      const deltaX = event.clientX - state.startPos.x;
      const deltaY = event.clientY - state.startPos.y;
      const direction = state.direction;

      let newWidth = state.startSize.width;
      let newHeight = state.startSize.height;
      let newX = state.startPosition.x;
      let newY = state.startPosition.y;

      // Handle horizontal resizing
      if (direction.includes('e')) {
        newWidth = Math.max(300, state.startSize.width + deltaX);
      }
      if (direction.includes('w')) {
        const widthChange = Math.min(deltaX, state.startSize.width - 300);
        newWidth = state.startSize.width - widthChange;
        newX = state.startPosition.x + widthChange;
      }

      // Handle vertical resizing
      if (direction.includes('s')) {
        newHeight = Math.max(200, state.startSize.height + deltaY);
      }
      if (direction.includes('n')) {
        const heightChange = Math.min(deltaY, state.startSize.height - 200);
        newHeight = state.startSize.height - heightChange;
        newY = state.startPosition.y + heightChange;
      }

      terminalPositionStore.set({ x: newX, y: newY });
      terminalSizeStore.set({ width: newWidth, height: newHeight });
    },

    stop() {
      resizeState.value.isResizing = false;
      resizeState.value.direction = '';
      document.removeEventListener('pointermove', resizeHandlers.move);
      document.removeEventListener('pointerup', resizeHandlers.stop);
    }
  };

  // === INITIALIZATION ===
  const initialize = () => {
    // Initialize visibility
    const isNickAiRoute = window.location.pathname.includes('/nick-ai');
    if (isNickAiRoute && props.hideTerminal) {
      isTerminalHiddenStore.set(true);
    }

    // Initialize position if needed
    if (!position.value || position.value.x === undefined) {
      const margin = 20;
      const terminalHeight = size.value?.height || 400;
      const terminalWidth = size.value?.width || 600;

      let newY = window.innerHeight - terminalHeight - margin;
      let newX = margin;

      newX = Math.max(margin, Math.min(newX, window.innerWidth - terminalWidth - margin));
      newY = Math.max(margin, Math.min(newY, window.innerHeight - terminalHeight - margin));

      terminalPositionStore.set({ x: newX, y: newY });
    }

    // Initialize command history
    if (props.initialOutput?.length > 0 && commandHistory.value.length === 0) {
      commandHistoryStore.set([{
        id: 1,
        timestamp: Date.now(),
        command: '',
        textOutput: [...props.initialOutput],
        isLoading: false,
        loadingProgress: 0,
        graphData: null,
        commitData: null,
        commitHistory: null
      }]);
      nextCommandIdStore.set(2);
    }

    // Set up global event listeners
    document.addEventListener('keydown', handleKeyDown);

    isMounted.value = true;

    // Initial focus and scroll
    nextTick(() => {
      focusInput();
      scrollToBottom();
    });
  };

  // === LIFECYCLE ===
  onMounted(initialize);

  onUnmounted(() => {
    // Clean up event listeners
    document.removeEventListener('keydown', handleKeyDown);
    document.removeEventListener('pointermove', dragHandlers.move);
    document.removeEventListener('pointerup', dragHandlers.stop);
    document.removeEventListener('pointermove', resizeHandlers.move);
    document.removeEventListener('pointerup', resizeHandlers.stop);

    // Restore body scroll
    unblockBodyScroll();

    isMounted.value = false;
  });

  return {
    // Refs
    terminalWindow,
    terminalContent,
    isMounted,

    // State
    theme,
    inputValue,
    isMinimized,
    isHidden,
    isMaximized,
    isVisible,
    isExpanded,
    isHovered,
    isTouching,
    position,
    size,
    commandHistory,
    nextCommandId,
    terminalStyle,

    // Actions
    actions,
    setTheme,
    focusInput,
    submitCommand,
    scrollToBottom,

    // Event Handlers
    dragHandlers,
    resizeHandlers,
    mouseHandlers,
    touchHandlers,
    wheelHandler,

    // Store references
    stores: {
      isTerminalMinimizedStore,
      isTerminalHiddenStore,
      isTerminalMaximizedStore
    }
  };
}
