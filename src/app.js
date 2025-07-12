// src/app.js
import { createPinia } from 'pinia';

// Export a function that configures your Vue app
export default (app) => {
  // Create the Pinia instance
  const pinia = createPinia();

  // Add Pinia to your Vue app
  app.use(pinia);
};