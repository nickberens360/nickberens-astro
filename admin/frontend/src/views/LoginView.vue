<template>
  <v-container class="fill-height" fluid>
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card class="elevation-12">
          <v-toolbar color="primary" dark flat>
            <v-toolbar-title>Admin Login</v-toolbar-title>
          </v-toolbar>
          <v-card-text>
            <v-form @submit.prevent="handleLogin">
              <v-text-field
                v-model="username"
                label="Username"
                prepend-inner-icon="$account"
                required
                :error-messages="errors.username"
                @keyup.enter="handleLogin"
              ></v-text-field>

              <v-text-field
                v-model="password"
                label="Password"
                type="password"
                prepend-inner-icon="$lock"
                required
                :error-messages="errors.password"
                @keyup.enter="handleLogin"
              ></v-text-field>

              <v-alert
                v-if="errors.general"
                type="error"
                class="mb-4"
                dense
              >
                {{ errors.general }}
              </v-alert>
            </v-form>
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn
              color="primary"
              :loading="loading"
              @click="handleLogin"
            >
              Login
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { useAdminStore } from '@/stores/admin'

export default {
  name: 'LoginView',
  data() {
    return {
      username: '',
      password: '',
      loading: false,
      errors: {
        username: [],
        password: [],
        general: ''
      }
    }
  },
  setup() {
    const adminStore = useAdminStore()
    return { adminStore }
  },
  methods: {
    clearErrors() {
      this.errors = {
        username: [],
        password: [],
        general: ''
      }
    },
    
    validateForm() {
      this.clearErrors()
      let isValid = true

      if (!this.username.trim()) {
        this.errors.username.push('Username is required')
        isValid = false
      }

      if (!this.password) {
        this.errors.password.push('Password is required')
        isValid = false
      }

      return isValid
    },

    async handleLogin() {
      if (!this.validateForm()) {
        return
      }

      this.loading = true
      this.clearErrors()

      try {
        await this.adminStore.login(this.username, this.password)
        
        // Redirect to dashboard or the intended page
        const redirect = this.$route.query.redirect || '/admin'
        this.$router.push(redirect)
        
      } catch (error) {
        console.error('Login error:', error)
        
        if (error.response?.status === 401) {
          this.errors.general = 'Invalid username or password'
        } else if (error.response?.data?.detail) {
          this.errors.general = error.response.data.detail
        } else if (error.message) {
          this.errors.general = error.message
        } else {
          this.errors.general = 'Login failed. Please try again.'
        }
      } finally {
        this.loading = false
      }
    }
  },
  
  mounted() {
    // Check if user is already logged in
    if (this.adminStore.isAuthenticated) {
      this.$router.push({ name: 'dashboard' })
    }
  }
}
</script>

<style scoped>
.fill-height {
  min-height: 100vh;
}
</style>