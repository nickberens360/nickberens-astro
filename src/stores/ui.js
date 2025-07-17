import { atom } from 'nanostores';
import {
  DEFAULT_TERMINAL_SIZE,
  DEFAULT_TERMINAL_MARGIN,
  DEFAULT_TERMINAL_OUTPUT
} from '../config/terminalConfig';

// Helper to check if we're in a browser environment
const isBrowser = () => typeof window !== 'undefined' && typeof localStorage !== 'undefined';

// --- Load terminal window position from localStorage or use default ---
const loadTerminalPosition = () => {
  if (isBrowser()) {
    try {
      const savedPosition = localStorage.getItem('terminalPosition');
      if (savedPosition) {
        return JSON.parse(savedPosition);
      }
    } catch (error) {
      console.error('Error loading terminal position:', error);
    }
  }
  // Return a simple, static default for SSR.
  return { x: DEFAULT_TERMINAL_MARGIN, y: 100 };
};

// --- Load terminal window size from localStorage or use default ---
const loadTerminalSize = () => {
  if (isBrowser()) {
    try {
      const savedSize = localStorage.getItem('terminalSize');
      if (savedSize) {
        return JSON.parse(savedSize);
      }
    } catch (error) {
      console.error('Error loading terminal size:', error);
    }
  }
  // Use the imported default size
  return DEFAULT_TERMINAL_SIZE;
};

// --- Terminal position and size stores with persisted data ---
export const terminalPositionStore = atom(loadTerminalPosition());
export const terminalSizeStore = atom(loadTerminalSize());

// Subscribe to changes and save to localStorage
terminalPositionStore.listen((value) => {
  if (isBrowser()) {
    try {
      localStorage.setItem('terminalPosition', JSON.stringify(value));
    } catch (error) {
      console.error('Error saving terminal position:', error);
    }
  }
});

terminalSizeStore.listen((value) => {
  if (isBrowser()) {
    try {
      localStorage.setItem('terminalSize', JSON.stringify(value));
    } catch (error) {
      console.error('Error saving terminal size:', error);
    }
  }
});

// Default value for the terminal input
const DEFAULT_TERMINAL_INPUT_VALUE = 'Shoot';

// Store for the terminal input's value, initialized with a default.
export const terminalInputValue = atom(DEFAULT_TERMINAL_INPUT_VALUE);

// Load command history from localStorage or use default
const loadCommandHistory = () => {
  if (isBrowser()) {
    try {
      const savedHistory = localStorage.getItem('commandHistory');
      if (savedHistory) {
        return JSON.parse(savedHistory);
      }
    } catch (error) {
      console.error('Error loading command history:', error);
    }
  }

  // Default history if nothing in localStorage
  return [{
    id: 1,
    timestamp: Date.now(),
    command: '',
    textOutput: DEFAULT_TERMINAL_OUTPUT,
    isLoading: false,
    loadingProgress: 0,
    graphData: null,
    commitData: null
  }];
};

// Load next command ID from localStorage or use default
const loadNextCommandId = () => {
  if (isBrowser()) {
    try {
      const savedId = localStorage.getItem('nextCommandId');
      if (savedId) {
        return parseInt(savedId, 10);
      }
    } catch (error) {
      console.error('Error loading next command ID:', error);
    }
  }
  return 2; // Default next ID
};

// Command history store with persisted data
export const commandHistoryStore = atom(loadCommandHistory());

// Next command ID tracker with persisted value
export const nextCommandIdStore = atom(loadNextCommandId());

// Subscribe to changes and save to localStorage
commandHistoryStore.listen((value) => {
  if (isBrowser()) {
    try {
      localStorage.setItem('commandHistory', JSON.stringify(value));
    } catch (error) {
      console.error('Error saving command history:', error);
    }
  }
});

nextCommandIdStore.listen((value) => {
  if (isBrowser()) {
    try {
      localStorage.setItem('nextCommandId', value.toString());
    } catch (error) {
      console.error('Error saving next command ID:', error);
    }
  }
});

// Navigation items store
export const navItems = atom([
  { text: 'nickAI', url: '/nick-ai' },
  { text: 'Illustrations', url: '/illustrations' },
  { text: 'Atomic Docs', url: '/atomic-docs' },
  { text: 'Resume', url: '/resume' },
  { text: 'Contact', url: '/#contact' },
  {
    text: 'GitHub',
    url: 'https://github.com/nickberens360',
    isExternal: true,
    icon: ['fab', 'github'],
    ariaLabel: 'GitHub Profile'
  }
]);

// Store for tracking terminal active state
export const isTerminalActive = atom(false);

// Load isMinimized state from localStorage or use default
const loadIsTerminalMinimized = () => {
  if (isBrowser()) {
    try {
      const savedState = localStorage.getItem('isTerminalMinimized');
      // Check for null to handle case where it's explicitly set to false
      if (savedState !== null) {
        return JSON.parse(savedState);
      }
    } catch (error) {
      console.error('Error loading terminal minimized state:', error);
    }
  }
  return false; // Default: not minimized
};

// Store for terminal minimized state with persisted data
export const isTerminalMinimizedStore = atom(loadIsTerminalMinimized());

// Subscribe to changes and save to localStorage
isTerminalMinimizedStore.listen((value) => {
  if (isBrowser()) {
    try {
      localStorage.setItem('isTerminalMinimized', JSON.stringify(value));
    } catch (error) {
      console.error('Error saving terminal minimized state:', error);
    }
  }
});