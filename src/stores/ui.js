import { atom } from 'nanostores';

// Store for the mobile menu state

// Default value for the terminal input
const DEFAULT_TERMINAL_INPUT_VALUE = 'Sh!t';

// Store for the terminal input's value, initialized with a default.
export const terminalInputValue = atom(DEFAULT_TERMINAL_INPUT_VALUE);