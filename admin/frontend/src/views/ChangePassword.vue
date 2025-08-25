<template>
  <v-container>
    <v-row justify="center">
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon left>$lock</v-icon>
            Change Password
          </v-card-title>
          
          <v-card-text>
            <v-form ref="form" v-model="valid" @submit.prevent="changePassword">
              <v-text-field
                v-model="currentPassword"
                :rules="[rules.required]"
                label="Current Password"
                type="password"
                prepend-icon="$lock-outline"
                required
              ></v-text-field>
              
              <v-text-field
                v-model="newPassword"
                :rules="[rules.required, rules.minLength]"
                label="New Password"
                type="password"
                prepend-icon="$lock"
                required
                hint="At least 8 characters"
              ></v-text-field>
              
              <v-text-field
                v-model="confirmPassword"
                :rules="[rules.required, rules.passwordMatch]"
                label="Confirm New Password"
                type="password"
                prepend-icon="$lock-check"
                required
              ></v-text-field>
              
              <v-alert
                v-if="error"
                type="error"
                dismissible
                @click="error = ''"
                class="mt-3"
              >
                {{ error }}
              </v-alert>
              
              <v-alert
                v-if="success"
                type="success"
                dismissible
                @click="success = ''"
                class="mt-3"
              >
                {{ success }}
              </v-alert>
            </v-form>
          </v-card-text>
          
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn
              color="grey"
              text
              @click="resetForm"
            >
              Cancel
            </v-btn>
            <v-btn
              color="primary"
              :disabled="!valid || loading"
              :loading="loading"
              @click="changePassword"
            >
              Change Password
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import api from '@/services/api'

export default {
  name: 'ChangePassword',
  data() {
    return {
      valid: false,
      loading: false,
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
      error: '',
      success: '',
      rules: {
        required: v => !!v || 'Required',
        minLength: v => (v && v.length >= 8) || 'Password must be at least 8 characters',
        passwordMatch: v => v === this.newPassword || 'Passwords must match'
      }
    }
  },
  methods: {
    async changePassword() {
      if (!this.$refs.form.validate()) {
        return
      }
      
      this.loading = true
      this.error = ''
      this.success = ''
      
      try {
        const response = await api.changePassword(this.currentPassword, this.newPassword)
        
        if (response.success) {
          this.success = 'Password changed successfully!'
          this.resetForm()
          
          // Optionally redirect to dashboard after a delay
          setTimeout(() => {
            this.$router.push('/admin')
          }, 2000)
        }
      } catch (error) {
        if (error.response && error.response.data) {
          this.error = error.response.data.detail || 'Failed to change password'
        } else {
          this.error = 'An error occurred while changing password'
        }
      } finally {
        this.loading = false
      }
    },
    
    resetForm() {
      this.currentPassword = ''
      this.newPassword = ''
      this.confirmPassword = ''
      this.error = ''
      if (this.$refs.form) {
        this.$refs.form.reset()
      }
    }
  }
}
</script>

<style scoped>
.v-card {
  margin-top: 20px;
}
</style>