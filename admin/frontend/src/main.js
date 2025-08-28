import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import vuetify from './plugins/vuetify'

// Monaco Editor Web Worker setup
import './monaco-env.js'

// Global CSS
import './styles/main.css'
import './styles/typography.css'

// Admin API setup
import { adminAPI } from './services/api'

// Authentication is now handled via HTTPOnly cookies exclusively
// No development token injection needed - use proper login flow

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(vuetify)

app.mount('#app')