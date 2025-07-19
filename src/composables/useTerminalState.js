import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { useStore } from '@nanostores/vue';
import {
  commandHistoryStore,
  nextCommandIdStore,
  terminalPositionStore,
  terminalSizeStore,
  isTerminalActive,
  isTerminalMinimizedStore,
  isTerminalHiddenStore,
  isTerminalMaximizedStore,
  previousTerminalStateStore
} from '../stores/ui.js';

export function useTerminalState(props, terminalInput, terminalOutput) {
  // --- REACTIVE STATE ---
  const savedTheme = localStorage.getItem('terminalTheme');
  const validThemes = ['dark', 'light'];
  const theme = ref(validThemes.includes(savedTheme) ? savedTheme : 'dark');
  const inputValue = ref('');
  const isMounted = ref(false);

  // --- THEME MANAGEMENT ---
  const setTheme = (newTheme) => {
    theme.value = newTheme;
    localStorage.setItem('terminalTheme', newTheme);
  };

  // --- STORE SUBSCRIPTIONS ---
  const isMinimized = useStore(isTerminalMinimizedStore);
  const isTerminalHidden = useStore(isTerminalHiddenStore);
  const position = useStore(terminalPositionStore);
  const size = useStore(terminalSizeStore);
  const commandHistory = useStore(commandHistoryStore);
  const nextCommandId = useStore(nextCommandIdStore);
  const isMaximized = useStore(isTerminalMaximizedStore);
  const previousTerminalState = useStore(previousTerminalStateStore);

  // --- COMPUTED VALUES ---
  const isHidden = computed(() => isTerminalHidden.value);

  // --- TERMINAL FOCUS MANAGEMENT ---
  const focusInput = (event) => {
    if (terminalInput.value && (!event || event.target.tagName !== 'A')) {
      terminalInput.value.focus();
    }
  };

  // --- TERMINAL ACTIVE STATE ---
  const activateTerminal = () => {
    isTerminalActive.set(true);
  };

  const deactivateTerminal = () => {
    isTerminalActive.set(false);
  };

  // --- INITIALIZATION LOGIC ---
  const initializeTerminalVisibility = () => {
    const isNickAiRoute = window.location.pathname.includes('/nick-ai');
    if (isNickAiRoute && props.hideTerminal) {
      isTerminalHiddenStore.set(true);
    } else if (typeof isTerminalHidden.value !== 'boolean') {
      isTerminalHiddenStore.set(props.hideTerminal);
    }
  };

  const initializeTerminalPosition = () => {
    const savedPosition = localStorage.getItem('terminalPosition');
    if (!savedPosition) {
      const margin = 20;
      const terminalHeight = size.value.height;
      const terminalWidth = size.value.width;

      // Calculate initial position (bottom left with margin)
      let newY = window.innerHeight - terminalHeight - margin;
      let newX = margin;

      // Ensure X stays within window boundaries
      newX = Math.max(margin, newX); // Not below left edge
      newX = Math.min(newX, window.innerWidth - terminalWidth - margin); // Not beyond right edge

      // Ensure Y stays within window boundaries
      newY = Math.max(margin, newY); // Not above top edge
      newY = Math.min(newY, window.innerHeight - terminalHeight - margin); // Not below bottom edge

      terminalPositionStore.set({ x: newX, y: newY });
    }
  };

  const initializeCommandHistory = () => {
    if (props.initialOutput && props.initialOutput.length > 0 && commandHistory.value.length === 0) {
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
  };

  // --- SCROLL MANAGEMENT ---
  const scrollToBottom = () => {
    nextTick(() => {
      if (terminalOutput.value && isMounted.value) {
        terminalOutput.value.scrollTo(terminalOutput.value.getScrollHeight());
      }
    });
  };

  // --- COMMAND SUBMISSION ---
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

  // --- EVENT HANDLERS ---
  const handleKeyDown = (event, toggleMaximize) => {
    if (event.key === 'Escape' && isMaximized.value) {
      toggleMaximize();
    }
  };

  const handleOutsideClick = (terminalWindow) => (event) => {
    if (terminalWindow.value && !terminalWindow.value.contains(event.target) && !isMinimized.value) {
      deactivateTerminal();
    }
  };

  // --- LIFECYCLE MANAGEMENT ---
  const setupEventListeners = (terminalWindow, toggleMaximize, stopDrag, stopResize) => {
    const outsideClickHandler = handleOutsideClick(terminalWindow);
    const keyDownHandler = (event) => handleKeyDown(event, toggleMaximize);

    // Create a combined handler for pointerup events
    const combinedPointerUpHandler = (event) => {
      stopDrag(event);
      stopResize(event);
    };

    // Add event listeners with the combined handler
    document.addEventListener('pointerup', combinedPointerUpHandler);
    document.addEventListener('keydown', keyDownHandler);
    document.addEventListener('pointerdown', outsideClickHandler);

    if (terminalWindow.value) {
      terminalWindow.value.addEventListener('pointerdown', activateTerminal);
    }

    // Return cleanup function with the combined handler
    return () => {
      document.removeEventListener('pointerup', combinedPointerUpHandler);
      document.removeEventListener('keydown', keyDownHandler);
      document.removeEventListener('pointerdown', outsideClickHandler);

      if (terminalWindow.value) {
        terminalWindow.value.removeEventListener('pointerdown', activateTerminal);
      }
    };
  };

  // --- MAIN INITIALIZATION ---
  const initialize = (terminalWindow, toggleMaximize, stopDrag, stopResize) => {
    isMounted.value = true;

    // Initialize terminal state
    initializeTerminalVisibility();
    initializeTerminalPosition();
    initializeCommandHistory();

    // Setup event listeners and get cleanup function
    const cleanup = setupEventListeners(terminalWindow, toggleMaximize, stopDrag, stopResize);

    // Focus input and scroll to bottom
    nextTick(() => {
      focusInput();
      scrollToBottom();
    });

    return cleanup;
  };

  // --- CLEANUP ---
  const cleanup = ref(null);

  onMounted(() => {
    // Note: initialize will be called from the component with required params
  });

  onUnmounted(() => {
    isMounted.value = false;
    if (cleanup.value) {
      cleanup.value();
    }
  });

  return {
    // Reactive state
    theme,
    inputValue,
    isMounted,

    // Store values
    isMinimized,
    isHidden,
    isMaximized,
    commandHistory,
    position,
    size,
    previousTerminalState,
    isTerminalMinimizedStore,
    isTerminalHiddenStore,

    // Methods
    focusInput,
    submitCommand,
    scrollToBottom,
    activateTerminal,
    deactivateTerminal,
    initialize,
    setTheme,

    // Store cleanup reference
    cleanup
  };
}
