import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import vuetify from './plugins/vuetify'

// Monaco Editor Web Worker setup
import './monaco-env.js'

// Global CSS
import './styles/main.css'

// Admin API setup
import { adminAPI } from './services/api'

// Initialize admin token at startup (development only)
// Never define VITE_ADMIN_TOKEN in production builds.
if (import.meta.env.DEV) {
  const devToken = import.meta.env.VITE_ADMIN_TOKEN
  if (devToken) {
    adminAPI.setAuthToken(devToken)
  }
}

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(vuetify)

app.mount('#app')