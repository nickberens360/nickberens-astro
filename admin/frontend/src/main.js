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

// Initialize admin token at startup (for development/demo)
// In production, this should be handled by a proper login flow
if (import.meta.env.VITE_ADMIN_TOKEN) {
  adminAPI.setAuthToken(import.meta.env.VITE_ADMIN_TOKEN)
}

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(vuetify)

app.mount('#app')