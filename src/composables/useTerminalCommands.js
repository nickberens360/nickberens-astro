import { nextTick } from 'vue';
import { getLatestCommitMessage, getCodeFrequency, getCommitHistory } from '../utils/gitInfo.js';
import { navItems } from '../stores/ui.js';
import {
  commandHistoryStore,
  nextCommandIdStore,
  pendingConfirmationStore
} from '../stores/terminal-window.js';
import { DEFAULT_TERMINAL } from '../config/terminalConfig.js';
import { processCodeFrequencyData, processCommitHistory } from '../utils/dataProcessing.js';
import { updateEasterEgg } from '../stores/easter-eggs.js';

export function useTerminalCommands(terminalOutput, isMounted, unmaximizeCallback) {
  // Helper function to update a specific history item
  const updateHistoryItem = (commandId, updates) => {
    const history = commandHistoryStore.get();
    const index = history.findIndex(item => item.id === commandId);
    if (index === -1) return;

    const newHistory = [...history];
    const currentItem = newHistory[index];

    newHistory[index] = {
      ...currentItem,
      ...updates,
      textOutput: [...currentItem.textOutput, ...(updates.textOutput || [])],
    };
    commandHistoryStore.set(newHistory);
  };

  // Ensure minimum loading time for better UX
  const ensureMinLoadingTime = async (promise, commandId, minTime = 1000) => {
    updateHistoryItem(commandId, { isLoading: true, loadingProgress: 0 });
    const loadingStartTime = Date.now();

    // Progress update function
    const updateProgress = async () => {
      let currentProgress = 0;

      while (currentProgress < 90 && isMounted.value) {
        await new Promise(resolve => setTimeout(resolve, 100));

        const historyItem = commandHistoryStore.get().find(c => c.id === commandId);
        if (!historyItem) break;

        currentProgress = historyItem.loadingProgress || 0;
        const newProgress = currentProgress + Math.random() * 3 + 1;
        if (isMounted.value) {
          updateHistoryItem(commandId, { loadingProgress: Math.min(newProgress, 90) });
        }
      }
    };

    const progressPromise = updateProgress();
    const result = await promise;

    const elapsedTime = Date.now() - loadingStartTime;
    if (elapsedTime < minTime) {
      await new Promise(resolve => setTimeout(resolve, minTime - elapsedTime));
    }

    if (isMounted.value) {
      updateHistoryItem(commandId, { loadingProgress: 100 });
      await new Promise(resolve => setTimeout(resolve, 200));
      updateHistoryItem(commandId, { isLoading: false });
    }

    return result;
  };

  // Generic async git handler
  const createAsyncGitHandler = (commandId, fetchFn, processFn, initialText) => {
    updateHistoryItem(commandId, { textOutput: [initialText] });
    ensureMinLoadingTime(fetchFn(), commandId)
      .then(data => {
        if (isMounted.value) {
          updateHistoryItem(commandId, processFn(data));
          nextTick(() => {
            if (terminalOutput.value && isMounted.value) {
              terminalOutput.value.scrollTop = terminalOutput.value.scrollHeight;
            }
          });
        }
      })
      .catch(error => {
        if (isMounted.value) {
          updateHistoryItem(commandId, { textOutput: [`Error retrieving data: ${error.message}`] });
        }
      });
  };

  // Check for easter egg commands
  const checkForEasterEgg = (command) => {
    const lowerCommand = command.toLowerCase();

    // Check for terminal velocity Easter egg
    if (lowerCommand.includes('terminal velocity') ||
        lowerCommand.includes('egg velocity') ||
        lowerCommand.includes('egg') ||
        lowerCommand.includes('easter') ||
        lowerCommand.includes('velocity of egg') ||
        lowerCommand.includes('velocity of an egg')) {
      return 'egg3';
    }

    return null;
  };

  // Handle confirmation responses
  const handleConfirmationResponse = (response, commandId) => {
    const confirmationState = pendingConfirmationStore.get();

    if (!confirmationState.isWaiting) return false;

    const normalizedResponse = response.toLowerCase().trim();

    // Reset confirmation state first
    pendingConfirmationStore.set({
      isWaiting: false,
      commandId: null,
      confirmationType: null,
      originalCommand: null,
      confirmationData: null
    });

    // Handle different confirmation types
    switch (confirmationState.confirmationType) {
      case 'bust-cache':
        if (normalizedResponse === 'y' || normalizedResponse === 'yes') {
          // User confirmed, proceed with clearing cache and reloading
          updateHistoryItem(commandId, {
            textOutput: ['Clearing cache and reloading page...']
          });

          setTimeout(() => {
            localStorage.clear();
            window.location.reload();
          }, 500);
        } else if (normalizedResponse === 'n' || normalizedResponse === 'no' || normalizedResponse === '') {
          // User declined (n, no, or just pressed enter)
          updateHistoryItem(commandId, {
            textOutput: ['Cache clearing canceled.']
          });
        } else {
          // Invalid response, ask again
          pendingConfirmationStore.set({
            isWaiting: true,
            commandId: commandId,
            confirmationType: 'bust-cache',
            originalCommand: 'bust-cache',
            confirmationData: null
          });

          updateHistoryItem(commandId, {
            textOutput: ['Please enter Y (yes) or N (no): (Y/n)']
          });
        }
        break;

      default:
        updateHistoryItem(commandId, {
          textOutput: ['Unknown confirmation type.']
        });
    }

    return true; // Indicates this was handled as a confirmation
  };

  // Command definitions
  const commands = {
    clear: () => {
      commandHistoryStore.set([]);
    },

    help: (args, commandId) => {
      updateHistoryItem(commandId, {
        textOutput: DEFAULT_TERMINAL.helpOutput
      });
    },

    theme: (args, commandId, theme) => {
      if (!args.length) {
        updateHistoryItem(commandId, {
          textOutput: ['Usage: theme [dark|light]', 'Please specify which theme you want to use.']
        });
        return;
      }

      const requestedTheme = args[0].toLowerCase();

      if (requestedTheme !== 'dark' && requestedTheme !== 'light') {
        updateHistoryItem(commandId, {
          textOutput: [`Invalid theme: ${requestedTheme}`, 'Available themes: dark, light']
        });
        return;
      }

      theme.setTheme(requestedTheme);
      updateHistoryItem(commandId, { textOutput: [`Theme switched to ${requestedTheme} mode`] });
    },

    version: (args, commandId) => {
      updateHistoryItem(commandId, {
        textOutput: ['Terminal v1.0.0', 'Created by nickberens']
      });
    },

    ls: (args, commandId) => {
      const links = navItems.get().map(item => ({
        type: 'link',
        prefix: '- ',
        url: item.url,
        text: item.text
      }));
      updateHistoryItem(commandId, {
        textOutput: ['Navigation links:', ...links]
      });
    },

    cd: (args, commandId) => {
      if (!args.length) {
        updateHistoryItem(commandId, {
          textOutput: [
            'Usage: cd [nav item name]',
            'Available nav items:',
            ...navItems.get().map(item => `- ${item.text}`),
            '- / or home: Navigate to the index page'
          ]
        });
        return;
      }

      // Use the callback to unmaximize instead of direct import
      if (unmaximizeCallback) {
        unmaximizeCallback();
      }

      const targetName = args.join(' ').toLowerCase();

      // Special case for home or root directory
      if (targetName === '/' || targetName === 'home' || targetName === 'hoem') {
        updateHistoryItem(commandId, {
          textOutput: ['Navigating to home page...']
        });

        setTimeout(() => {
          window.location.href = '/';
        }, 500);
        return;
      }

      const navItemsList = navItems.get();
      const matchedItem = navItemsList.find(item =>
        item.text.toLowerCase() === targetName
      );

      if (matchedItem) {
        updateHistoryItem(commandId, {
          textOutput: [`Navigating to ${matchedItem.text}...`]
        });

        setTimeout(() => {
          if (matchedItem.isExternal) {
            window.open(matchedItem.url, '_blank', 'noopener,noreferrer');
          } else {
            window.location.href = matchedItem.url;
          }
        }, 500);
      } else {
        updateHistoryItem(commandId, {
          textOutput: [
            `Nav item not found: "${args.join(' ')}"`,
            'Available nav items:',
            ...navItemsList.map(item => `- ${item.text}`),
            '- / or home: Navigate to the index page'
          ]
        });
      }
    },

    git: (args, commandId) => {
      const gitActions = {
        log: () => createAsyncGitHandler(
          commandId,
          getCommitHistory,
          data => ({ commitHistory: processCommitHistory(data) }),
          'Fetching commit history...'
        ),

        graph: () => createAsyncGitHandler(
          commandId,
          getCodeFrequency,
          data => ({
            graphData: processCodeFrequencyData(data),
            textOutput: ['Code Frequency (additions/deletions over time):']
          }),
          'Fetching code frequency data...'
        ),

        'latest-commit': () => createAsyncGitHandler(
          commandId,
          getLatestCommitMessage,
          data => ({
            commitData: {
              ...data,
              isVisible: true
            }
          }),
          'Fetching latest commit...'
        ),

        default: () => updateHistoryItem(commandId, {
          textOutput: ['Usage: git [log|graph|latest-commit]']
        })
      };

      const action = gitActions[args[0]?.toLowerCase()] || gitActions.default;
      action();
    },

    'bust-cache': (args, commandId) => {
      // Set up confirmation state
      pendingConfirmationStore.set({
        isWaiting: true,
        commandId: commandId,
        confirmationType: 'bust-cache',
        originalCommand: 'bust-cache',
        confirmationData: null
      });

      // Show confirmation prompt
      updateHistoryItem(commandId, {
        textOutput: ['Are you sure you want to clear the cache and reload the page? (Y/n)']
      });
    },

    default: (baseCommand, commandId) => {
      updateHistoryItem(commandId, {
        textOutput: [`Command not found: ${baseCommand}`]
      });
    }
  };

  // Main command handler
  const handleCommand = (command, commandId, theme) => {
    // First check if we're waiting for a confirmation response
    const confirmationState = pendingConfirmationStore.get();
    if (confirmationState.isWaiting) {
      const wasHandled = handleConfirmationResponse(command, commandId);
      if (wasHandled) return; // Exit early if this was a confirmation response
    }

    // Check if the entire command matches an easter egg
    const eggFound = checkForEasterEgg(command);

    if (eggFound) {
      // Update the easter egg store
      updateEasterEgg(eggFound);

      // Add the easter egg output
      updateHistoryItem(commandId, {
        textOutput: ['Calculating terminal velocity of an egg...'],
        easterEgg: {
          isVisible: true,
          eggName: eggFound
        }
      });
      return;
    }

    // Otherwise, process as normal command
    const parts = command.split(' ');
    const baseCommand = parts[0].toLowerCase();
    const args = parts.slice(1);

    const commandFn = commands[baseCommand] || (() => commands.default(baseCommand, commandId));
    commandFn(args, commandId, theme);
  };

  return {
    handleCommand,
    updateHistoryItem
  };
}
