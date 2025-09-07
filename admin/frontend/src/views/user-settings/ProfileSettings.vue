<template>
  <div class="profile-settings">
    <!-- Display Name Section -->
    <v-card class="mb-6" rounded="lg" elevation="1">
      <v-card-title class="d-flex align-center">
        <v-icon start>$account</v-icon>
        Display Name
      </v-card-title>
      <v-card-text>
        <v-form ref="displayNameForm" @submit.prevent="handleDisplayNameChange">
          <v-text-field
            v-model="displayName"
            label="Display Name"
            placeholder="Enter your display name"
            variant="outlined"
            density="comfortable"
            :rules="displayNameRules"
            class="mb-4"
          />
          <div class="d-flex justify-end">
            <v-btn
              type="submit"
              color="primary"
              variant="flat"
              :loading="displayNameLoading"
              :disabled="!displayNameChanged"
            >
              Update Display Name
            </v-btn>
          </div>
        </v-form>
      </v-card-text>
    </v-card>

    <!-- Email Section -->
    <v-card class="mb-6" rounded="lg" elevation="1">
      <v-card-title class="d-flex align-center">
        <v-icon start>$email</v-icon>
        Email Address
      </v-card-title>
      <v-card-text>
        <v-form ref="emailForm" @submit.prevent="handleEmailChange">
          <v-text-field
            v-model="email"
            label="Email Address"
            placeholder="Enter your email address"
            type="email"
            variant="outlined"
            density="comfortable"
            :rules="emailRules"
            class="mb-4"
          />
          <v-text-field
            v-model="emailPassword"
            label="Confirm with Password"
            placeholder="Enter your password to confirm"
            type="password"
            variant="outlined"
            density="comfortable"
            :rules="passwordRules"
            hint="For security, please enter your current password to change your email"
            persistent-hint
            class="mb-4"
          />
          <div class="d-flex justify-end">
            <v-btn
              type="submit"
              color="primary"
              variant="flat"
              :loading="emailLoading"
              :disabled="!emailChanged || !emailPassword"
            >
              Update Email
            </v-btn>
          </div>
        </v-form>
      </v-card-text>
    </v-card>

    <!-- Password Section -->
    <v-card rounded="lg" elevation="1">
      <v-card-title class="d-flex align-center">
        <v-icon start>$lock</v-icon>
        Change Password
      </v-card-title>
      <v-card-text>
        <v-form ref="passwordForm" @submit.prevent="handlePasswordChange">
          <v-text-field
            v-model="currentPassword"
            label="Current Password"
            placeholder="Enter your current password"
            :type="showCurrentPassword ? 'text' : 'password'"
            variant="outlined"
            density="comfortable"
            :rules="passwordRules"
            :append-inner-icon="showCurrentPassword ? '$eye-off' : '$eye'"
            @click:append-inner="showCurrentPassword = !showCurrentPassword"
            class="mb-4"
          />
          <v-text-field
            v-model="newPassword"
            label="New Password"
            placeholder="Enter your new password"
            :type="showNewPassword ? 'text' : 'password'"
            variant="outlined"
            density="comfortable"
            :rules="newPasswordRules"
            :append-inner-icon="showNewPassword ? '$eye-off' : '$eye'"
            @click:append-inner="showNewPassword = !showNewPassword"
            class="mb-4"
          />
          <v-text-field
            v-model="confirmPassword"
            label="Confirm New Password"
            placeholder="Confirm your new password"
            :type="showConfirmPassword ? 'text' : 'password'"
            variant="outlined"
            density="comfortable"
            :rules="confirmPasswordRules"
            :append-inner-icon="showConfirmPassword ? '$eye-off' : '$eye'"
            @click:append-inner="showConfirmPassword = !showConfirmPassword"
            :error-messages="passwordMatchError"
            class="mb-4"
          />
          
          <!-- Password Requirements -->
          <v-alert
            type="info"
            variant="tonal"
            density="compact"
            class="mb-4"
          >
            <div class="text-caption">
              Password Requirements:
              <ul class="mt-1 ml-4">
                <li>At least 8 characters long</li>
                <li>Contains at least one uppercase letter</li>
                <li>Contains at least one lowercase letter</li>
                <li>Contains at least one number</li>
                <li>Contains at least one special character</li>
              </ul>
            </div>
          </v-alert>

          <div class="d-flex justify-end">
            <v-btn
              type="submit"
              color="primary"
              variant="flat"
              :loading="passwordLoading"
              :disabled="!currentPassword || !newPassword || !confirmPassword || passwordMatchError !== ''"
            >
              Change Password
            </v-btn>
          </div>
        </v-form>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'

// Get notification system from parent
const notifications = inject('notifications')

// Store
const adminStore = useAdminStore()

// Form refs
const displayNameForm = ref()
const emailForm = ref()
const passwordForm = ref()

// Display Name fields
const displayName = ref('')
const originalDisplayName = ref('')
const displayNameLoading = ref(false)

// Email fields
const email = ref('')
const originalEmail = ref('')
const emailPassword = ref('')
const emailLoading = ref(false)

// Password fields
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const showCurrentPassword = ref(false)
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)
const passwordLoading = ref(false)

// Computed properties
const displayNameChanged = computed(() => displayName.value !== originalDisplayName.value)
const emailChanged = computed(() => email.value !== originalEmail.value)

const passwordMatchError = computed(() => {
  if (!confirmPassword.value || !newPassword.value) return ''
  return newPassword.value !== confirmPassword.value ? 'Passwords do not match' : ''
})

// Validation rules
const displayNameRules = [
  v => !!v || 'Display name is required',
  v => v.length >= 2 || 'Display name must be at least 2 characters',
  v => v.length <= 50 || 'Display name must be less than 50 characters'
]

const emailRules = [
  v => !!v || 'Email is required',
  v => /.+@.+\..+/.test(v) || 'Email must be valid'
]

const passwordRules = [
  v => !!v || 'Password is required',
  v => v.length >= 8 || 'Password must be at least 8 characters'
]

const newPasswordRules = [
  v => !!v || 'New password is required',
  v => v.length >= 8 || 'Password must be at least 8 characters',
  v => /[A-Z]/.test(v) || 'Password must contain at least one uppercase letter',
  v => /[a-z]/.test(v) || 'Password must contain at least one lowercase letter',
  v => /[0-9]/.test(v) || 'Password must contain at least one number',
  v => /[^A-Za-z0-9]/.test(v) || 'Password must contain at least one special character'
]

const confirmPasswordRules = [
  v => !!v || 'Please confirm your password',
  v => v === newPassword.value || 'Passwords do not match'
]

// Methods
const loadUserData = () => {
  // TODO: Load actual user data from the store/API
  // For now, use placeholder data
  const userData = adminStore.user || { username: 'admin', email: 'admin@example.com' }
  displayName.value = userData.display_name || userData.username || 'Admin User'
  originalDisplayName.value = displayName.value
  email.value = userData.email || 'admin@example.com'
  originalEmail.value = email.value
}

const handleDisplayNameChange = async () => {
  const valid = await displayNameForm.value.validate()
  if (!valid.valid) return

  displayNameLoading.value = true
  try {
    // TODO: Implement API call to update display name
    await new Promise(resolve => setTimeout(resolve, 1000)) // Simulate API call
    
    originalDisplayName.value = displayName.value
    notifications.showSuccess('Display name updated successfully')
  } catch (error) {
    notifications.showError('Failed to update display name. Please try again.')
    console.error('Display name update error:', error)
  } finally {
    displayNameLoading.value = false
  }
}

const handleEmailChange = async () => {
  const valid = await emailForm.value.validate()
  if (!valid.valid) return

  emailLoading.value = true
  try {
    // TODO: Implement API call to update email
    await new Promise(resolve => setTimeout(resolve, 1000)) // Simulate API call
    
    originalEmail.value = email.value
    emailPassword.value = ''
    notifications.showSuccess('Email address updated successfully')
  } catch (error) {
    notifications.showError('Failed to update email address. Please check your password and try again.')
    console.error('Email update error:', error)
  } finally {
    emailLoading.value = false
  }
}

const handlePasswordChange = async () => {
  const valid = await passwordForm.value.validate()
  if (!valid.valid) return

  if (newPassword.value !== confirmPassword.value) {
    notifications.showError('Passwords do not match')
    return
  }

  passwordLoading.value = true
  try {
    // TODO: Implement API call to change password
    await new Promise(resolve => setTimeout(resolve, 1000)) // Simulate API call
    
    // Clear password fields on success
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    showCurrentPassword.value = false
    showNewPassword.value = false
    showConfirmPassword.value = false
    
    notifications.showSuccess('Password changed successfully')
  } catch (error) {
    notifications.showError('Failed to change password. Please check your current password and try again.')
    console.error('Password change error:', error)
  } finally {
    passwordLoading.value = false
  }
}

// Lifecycle
onMounted(() => {
  loadUserData()
})
</script>

<style scoped>
.profile-settings {
  max-width: 800px;
}

/* Ensure form fields have consistent spacing */
.v-form {
  width: 100%;
}

/* Improve readability of password requirements */
.v-alert ul {
  margin: 0;
  padding: 0;
}

.v-alert li {
  margin: 2px 0;
}
</style>