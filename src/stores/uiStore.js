// src/stores/uiStore.js
import { defineStore } from 'pinia';

export const useUiStore = defineStore('ui', {
  state: () => ({
    terminalInputText: ''
  }),
  actions: {
    updateTerminalInputText(text) {
      this.terminalInputText = text;
    }
  },
  getters: {
    getTerminalInputText: (state) => state.terminalInputText
  }
});