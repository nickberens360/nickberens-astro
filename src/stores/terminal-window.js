import { atom } from 'nanostores';
import { DEFAULT_TERMINAL } from '../config/terminalConfig';

// Helper to check if we're in a browser environment
const isBrowser = () => typeof window !== 'undefined' && typeof localStorage !== 'undefined';

// Helper to create a persisted atom that syncs with localStorage
const createPersistedAtom = (key, defaultValue) => {
  const loadValue = () => {
    if (isBrowser()) {
      try {
        const saved = localStorage.getItem(key);
        if (saved !== null) {
          return JSON.parse(saved);
        }
      } catch (error) {
        console.error(`Error loading "${key}" from localStorage:`, error);
      }
    }
    return typeof defaultValue === 'function' ? defaultValue() : defaultValue;
  };

  const store = atom(loadValue());

  store.listen((value) => {
    if (isBrowser()) {
      try {
        localStorage.setItem(key, JSON.stringify(value));
      } catch (error) {
        console.error(`Error saving "${key}" to localStorage:`, error);
      }
    }
  });

  return store;
};

// --- Terminal position and size stores with persisted data ---
export const terminalPositionStore = createPersistedAtom(
  'terminalPosition',
  { x: DEFAULT_TERMINAL.margin, y: DEFAULT_TERMINAL.position.y }
);

export const terminalSizeStore = createPersistedAtom(
  'terminalSize',
  DEFAULT_TERMINAL.size
);

// Default value for the terminal input
const DEFAULT_TERMINAL_INPUT_VALUE = 'bad word';

// Store for the terminal input's value, initialized with a default.
export const terminalInputValue = atom(DEFAULT_TERMINAL_INPUT_VALUE);

// Command history store with persisted data
export const commandHistoryStore = createPersistedAtom(
  'commandHistory',
  [{
    id: 1,
    timestamp: Date.now(),
    command: '',
    textOutput: DEFAULT_TERMINAL.output,
    isLoading: false,
    loadingProgress: 0,
    graphData: null,
    commitData: null
  }]
);

// Next command ID tracker with persisted value
export const nextCommandIdStore = createPersistedAtom('nextCommandId', 2);

// Store for tracking terminal active state
export const isTerminalActive = atom(false);

// Store for terminal minimized state with persisted data
export const isTerminalMinimizedStore = createPersistedAtom('isTerminalMinimized', true);

// Store for terminal hidden state with persisted data
export const isTerminalHiddenStore = createPersistedAtom('isTerminalHidden', false);

// Store for terminal maximized state with persisted data
export const isTerminalMaximizedStore = createPersistedAtom('isTerminalMaximized', false);

// Store for previous terminal position and size (before maximizing)
export const previousTerminalStateStore = atom({
  position: null,
  size: null
});