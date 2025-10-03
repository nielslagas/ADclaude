import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'
import { apiClient } from './services/api'
import axios from 'axios'
import { setupGlobalErrorHandling } from './composables/useErrorHandler'

const app = createApp(App)

// Make apiClient available to all components
app.config.globalProperties.$api = apiClient
app.config.globalProperties.$axios = axios

// Create pinia store before mounting
const pinia = createPinia()
app.use(pinia)
app.use(router)

// Setup enhanced global error handling
const { errorHandler } = setupGlobalErrorHandling()
app.config.errorHandler = errorHandler

// Mount the app
console.log('Mounting app...')
app.mount('#app')
console.log('App mounted')
