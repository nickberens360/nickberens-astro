/**
 * Single source of truth for all terminal default values.
 */

export const DEFAULT_TERMINAL = {
  position: {
    x: 20,
    y: 100,
  },
  size: {
    width: 315,
    height: 290,
  },
  margin: 20,
  helpOutput: [
    'Available commands:',
    '- clear: Clear the terminal',
    '- bust-cache: Clear localStorage',
    '- help: Show this help message',
    '- theme: Toggle between light and dark theme',
    '- version: Show terminal version',
    '- ls: List navigation links',
    '- git log: Show commit history',
    '- git graph: Show code frequency chart',
  ],
  output: [
    'Type "help" for a list of commands.',
  ],
}


// export const DEFAULT_TERMINAL_SIZE = {
//   width: 315,
//   height: 290,
// };
//
// export const DEFAULT_TERMINAL_MARGIN = 20;
//
// export const DEFAULT_HELP_OUTPUT = [
//   'Available commands:',
//   '- clear: Clear the terminal',
//   '- bust-cache: Clear localStorage',
//   '- help: Show this help message',
//   '- theme: Toggle between light and dark theme',
//   '- version: Show terminal version',
//   '- ls: List navigation links',
//   '- git log: Show commit history',
//   '- git graph: Show code frequency chart',
// ];
//
// export const DEFAULT_TERMINAL_OUTPUT = [
//   'Type "help" for a list of commands.',
// ];


