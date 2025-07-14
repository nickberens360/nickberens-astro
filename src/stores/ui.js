import { atom } from 'nanostores';

// Store for the mobile menu state

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
