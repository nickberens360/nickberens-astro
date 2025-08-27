<template>
  <v-container>
    <v-row justify="center">
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>Change Password</v-card-title>
          
          <v-card-text>
            <v-text-field
              v-model="formData.currentPassword"
              label="Current Password"
              type="password"
              variant="outlined"
            ></v-text-field>
            
            <v-text-field
              v-model="formData.newPassword"
              label="New Password (8+ chars, upper/lowercase)"
              type="password" 
              variant="outlined"
            ></v-text-field>
            
            <v-text-field
              v-model="formData.confirmPassword"
              label="Confirm New Password"
              type="password"
              variant="outlined"
            ></v-text-field>
            
            <div v-if="state.error" class="text-red mb-4">
              {{ state.error }}
            </div>
            
            <div v-if="state.success" class="text-green mb-4">
              {{ state.success }}
            </div>
            
            <div v-if="state.loading" class="text-blue mb-4">
              Changing password...
            </div>
          </v-card-text>
          
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn
              color="grey"
              @click="resetForm"
            >
              Cancel
            </v-btn>
            <v-btn
              color="primary"
              :disabled="state.loading"
              @click="changePassword"
            >
              Change Password
            </v-btn>
          </v-card-actions>
        </v-card>
        
        <!-- Debug info -->
        <v-card class="mt-4" v-if="import.meta.env.DEV && state.debugInfo">
          <v-card-title>Debug Info</v-card-title>
          <v-card-text>
            <pre>{{ state.debugInfo }}</pre>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { reactive } from 'vue'
import axios from 'axios'

// API base URL configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default {
  name: 'ChangePasswordSimple',
  setup() {
    const formData = reactive({
      currentPassword: '',
      newPassword: '',
      confirmPassword: ''
    })
    
    const state = reactive({
      loading: false,
      error: null,
      success: null,
      debugInfo: null
    })
    
    const changePassword = async () => {
      state.loading = true
      state.error = null
      state.success = null
      state.debugInfo = null
      
      // Simple validation
      if (!formData.currentPassword || !formData.newPassword || !formData.confirmPassword) {
        state.error = 'All fields are required'
        state.loading = false
        return
      }
      
      if (formData.newPassword !== formData.confirmPassword) {
        state.error = 'New passwords do not match'
        state.loading = false
        return
      }
      
      // Enhanced password validation to match backend requirements
      if (formData.newPassword.length < 12) {
        state.error = 'Password must be at least 12 characters'
        state.loading = false
        return
      }
      
      if (!/[A-Z]/.test(formData.newPassword)) {
        state.error = 'Password must contain at least one uppercase letter'
        state.loading = false
        return
      }
      
      if (!/[a-z]/.test(formData.newPassword)) {
        state.error = 'Password must contain at least one lowercase letter'
        state.loading = false
        return
      }
      
      if (!/\d/.test(formData.newPassword)) {
        state.error = 'Password must contain at least one digit'
        state.loading = false
        return
      }
      
      if (!/[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(formData.newPassword)) {
        state.error = 'Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)'
        state.loading = false
        return
      }
      
      try {
        // Attempting password change...
        
        // Authentication is now handled via HTTPOnly cookies
        // No token needed - cookies are sent automatically
        
        const response = await axios.post(`${API_BASE_URL}/auth/change-password`, {
          current_password: formData.currentPassword,
          new_password: formData.newPassword
        }, {
          headers: {
            'Content-Type': 'application/json'
          },
          withCredentials: true  // Send HTTPOnly cookies
        })
        
        // Password change successful
        state.debugInfo = `SUCCESS! Password changed successfully.`
        state.success = 'Password changed successfully! All sessions have been invalidated. Please login again.'
        
        // HTTPOnly cookies will be cleared by the server
        
        // Reset form and redirect to login
        setTimeout(() => {
          resetForm()
          window.location.href = '/login'
        }, 3000)
        
      } catch (err) {
        console.error('Password change error:', err)
        state.error = 'Failed to change password. Please try again.'
        if (import.meta.env.DEV) {
          state.debugInfo = `ERROR: ${err.response?.status ?? ''} ${err.response?.statusText ?? ''}\n${JSON.stringify(err.response?.data || err.message, null, 2)}`
        }
      } finally {
        state.loading = false
      }
    }
    
    const resetForm = () => {
      formData.currentPassword = ''
      formData.newPassword = ''
      formData.confirmPassword = ''
      state.error = null
      state.success = null
      state.debugInfo = null
    }
    
    return {
      formData,
      state,
      changePassword,
      resetForm
    }
  }
}
</script>

<style scoped>
pre {
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>