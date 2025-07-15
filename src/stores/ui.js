import { atom } from 'nanostores';

// Store for the mobile menu state

// Load terminal window position from localStorage or use default
const loadTerminalPosition = () => {
  try {
    const savedPosition = localStorage.getItem('terminalPosition');
    if (savedPosition) {
      return JSON.parse(savedPosition);
    }
  } catch (error) {
    console.error('Error loading terminal position:', error);
  }
  return { x: 100, y: 100 }; // Default position
};

// Load terminal window size from localStorage or use default
const loadTerminalSize = () => {
  try {
    const savedSize = localStorage.getItem('terminalSize');
    if (savedSize) {
      return JSON.parse(savedSize);
    }
  } catch (error) {
    console.error('Error loading terminal size:', error);
  }
  return { width: 600, height: 400 }; // Default size
};

// Terminal position and size stores with persisted data
export const terminalPositionStore = atom(loadTerminalPosition());
export const terminalSizeStore = atom(loadTerminalSize());

// Subscribe to changes and save to localStorage
terminalPositionStore.listen((value) => {
  try {
    localStorage.setItem('terminalPosition', JSON.stringify(value));
  } catch (error) {
    console.error('Error saving terminal position:', error);
  }
});

terminalSizeStore.listen((value) => {
  try {
    localStorage.setItem('terminalSize', JSON.stringify(value));
  } catch (error) {
    console.error('Error saving terminal size:', error);
  }
});

// Default value for the terminal input
const DEFAULT_TERMINAL_INPUT_VALUE = 'Sh!t';

// Store for the terminal input's value, initialized with a default.
export const terminalInputValue = atom(DEFAULT_TERMINAL_INPUT_VALUE);

// Load command history from localStorage or use default
const loadCommandHistory = () => {
  try {
    const savedHistory = localStorage.getItem('commandHistory');
    if (savedHistory) {
      return JSON.parse(savedHistory);
    }
  } catch (error) {
    console.error('Error loading command history:', error);
  }

  // Default history if nothing in localStorage
  return [{
    id: 1,
    timestamp: Date.now(),
    command: '',
    textOutput: ['Welcome to Terminal'],
    isLoading: false,
    loadingProgress: 0,
    graphData: null,
    commitData: null
  }];
};

// Load next command ID from localStorage or use default
const loadNextCommandId = () => {
  try {
    const savedId = localStorage.getItem('nextCommandId');
    if (savedId) {
      return parseInt(savedId, 10);
    }
  } catch (error) {
    console.error('Error loading next command ID:', error);
  }
  return 2; // Default next ID
};

// Command history store with persisted data
export const commandHistoryStore = atom(loadCommandHistory());

// Next command ID tracker with persisted value
export const nextCommandIdStore = atom(loadNextCommandId());

// Subscribe to changes and save to localStorage
commandHistoryStore.listen((value) => {
  try {
    localStorage.setItem('commandHistory', JSON.stringify(value));
  } catch (error) {
    console.error('Error saving command history:', error);
  }
});

nextCommandIdStore.listen((value) => {
  try {
    localStorage.setItem('nextCommandId', value.toString());
  } catch (error) {
    console.error('Error saving next command ID:', error);
  }
});

// Navigation items store
export const navItems = atom([
  { text: 'Home', url: '/' },
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
