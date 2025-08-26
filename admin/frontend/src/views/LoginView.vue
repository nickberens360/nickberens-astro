<template>
  <v-container class="fill-height" fluid>
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card>
          <v-card-title class="text-center">
            <v-icon class="mr-2">$dashboard</v-icon>
            Admin Login
          </v-card-title>
          
          <v-card-text>
            <v-text-field
              v-model="formData.username"
              label="Username"
              variant="outlined"
              prepend-inner-icon="$account"
              :error-messages="validation.username"
              @keyup.enter="login"
            ></v-text-field>
            
            <v-text-field
              v-model="formData.password"
              label="Password"
              type="password"
              variant="outlined"
              prepend-inner-icon="$lock"
              :error-messages="validation.password"
              @keyup.enter="login"
            ></v-text-field>
            
            <v-alert
              v-if="state.error"
              type="error"
              class="mb-4"
              closable
              @click="state.error = null"
            >
              {{ state.error }}
            </v-alert>
            
            <v-alert
              v-if="state.success"
              type="success"
              class="mb-4"
            >
              {{ state.success }}
            </v-alert>
          </v-card-text>
          
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn 
              color="primary" 
              size="large"
              :loading="state.loading"
              :disabled="!isFormValid"
              @click="login"
            >
              {{ state.loading ? 'Logging in...' : 'Login' }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { reactive, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'

// API base URL configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default {
  name: 'LoginView',
  setup() {
    const router = useRouter()
    const route = useRoute()
    
    const formData = reactive({
      username: '',
      password: ''
    })
    
    const state = reactive({
      loading: false,
      error: null,
      success: null
    })
    
    const validation = reactive({
      username: [],
      password: []
    })
    
    const isFormValid = computed(() => {
      return formData.username.trim() && formData.password.trim()
    })
    
    const validateForm = () => {
      validation.username = []
      validation.password = []
      
      if (!formData.username.trim()) {
        validation.username.push('Username is required')
      }
      
      if (!formData.password.trim()) {
        validation.password.push('Password is required')
      }
      
      return validation.username.length === 0 && validation.password.length === 0
    }
    
    const login = async () => {
      if (!validateForm()) {
        return
      }
      
      state.loading = true
      state.error = null
      state.success = null
      
      try {
        const response = await axios.post(`${API_BASE_URL}/auth/login`, {
          username: formData.username,
          password: formData.password
        })
        
        if (response.data.success) {
          // Store authentication token
          localStorage.setItem('admin_token', response.data.session_id)
          
          // Show success message briefly
          state.success = 'Login successful! Redirecting...'
          
          // Determine redirect destination
          const redirectTo = route.query.redirect || '/admin'
          
          // Redirect after a brief delay
          setTimeout(() => {
            router.push(redirectTo)
          }, 1000)
          
        } else {
          state.error = response.data.message || 'Login failed'
        }
        
      } catch (err) {
        console.error('Login error:', err)
        
        if (err.response?.status === 401) {
          state.error = 'Invalid username or password'
        } else if (err.response?.data?.detail) {
          state.error = err.response.data.detail
        } else if (err.response?.data?.message) {
          state.error = err.response.data.message
        } else {
          state.error = 'Login failed. Please try again.'
        }
      } finally {
        state.loading = false
      }
    }
    
    const clearForm = () => {
      formData.username = ''
      formData.password = ''
      validation.username = []
      validation.password = []
      state.error = null
      state.success = null
    }
    
    // Check if user is already authenticated on component mount
    const checkExistingAuth = async () => {
      const token = localStorage.getItem('admin_token')
      if (!token) return
      
      try {
        const response = await axios.get(`${API_BASE_URL}/auth/me`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        
        if (response.data.user) {
          // User is already authenticated, redirect
          const redirectTo = route.query.redirect || '/admin'
          router.push(redirectTo)
        }
      } catch (err) {
        // Invalid token, clear it
        localStorage.removeItem('admin_token')
      }
    }
    
    // Check auth on mount
    checkExistingAuth()
    
    return {
      formData,
      state,
      validation,
      isFormValid,
      login,
      clearForm
    }
  }
}
</script>

<style scoped>
.fill-height {
  min-height: 100vh;
}

.v-card {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.v-card-title {
  padding-top: 2rem;
  padding-bottom: 1rem;
  font-size: 1.5rem;
  font-weight: 600;
}
</style>