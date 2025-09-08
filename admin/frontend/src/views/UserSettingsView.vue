<template>
  <div class="user-settings-page">
    <div class="user-settings-layout">
      <!-- Navigation Sidebar -->
      <nav class="user-settings-nav">
        <v-list class="user-settings-nav-list" nav density="comfortable" rounded="lg">
          <v-list-item
            v-for="tab in navigationTabs"
            :key="tab.value"
            :value="tab.value"
            :active="currentTab === tab.value"
            @click="navigateToTab(tab.value)"
            class="user-settings-nav-item"
            :class="{ 'user-settings-nav-item--active': currentTab === tab.value }"
            rounded="lg"
          >
            <template v-slot:prepend>
              <v-icon :icon="tab.icon" size="20" />
            </template>
            <v-list-item-title class="user-settings-nav-title">{{ tab.title }}</v-list-item-title>
          </v-list-item>
        </v-list>
      </nav>
      
      <!-- Content Area -->
      <main class="user-settings-content">
        <!-- Page Header -->
        <div class="user-settings-header">
          <h2 class="text-h4 font-weight-bold mb-2">User Settings</h2>
          <p class="text-body-1 text-medium-emphasis">Manage your account settings and preferences</p>
        </div>
        
        <!-- Route Content -->
        <router-view />
      </main>
    </div>
    
    <!-- Global Notifications -->
    <v-snackbar
      v-model="showNotification"
      :color="notificationColor"
      :timeout="notificationTimeout"
      location="top"
      variant="flat"
    >
      {{ notificationMessage }}
      <template #actions>
        <v-btn
          text="Close"
          variant="text"
          @click="showNotification = false"
        />
      </template>
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, provide } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

// Notification system
const showNotification = ref(false)
const notificationMessage = ref('')
const notificationColor = ref('success')
const notificationTimeout = ref(3000)

// Navigation tabs - for now just Profile, but structured for future expansion
const navigationTabs = [
  {
    value: 'profile',
    title: 'Profile',
    icon: '$account'
  }
  // Future tabs could include:
  // { value: 'security', title: 'Security', icon: '$lock' },
  // { value: 'preferences', title: 'Preferences', icon: '$cog' },
  // { value: 'notifications', title: 'Notifications', icon: '$bell' }
]

const currentTab = computed(() => {
  // Since we only have profile for now, default to it
  return 'profile'
})

const navigateToTab = (tabValue) => {
  // For future expansion when we have multiple tabs
  const routeMap = {
    'profile': 'user-settings-profile'
  }

  const routeName = routeMap[tabValue]
  if (routeName && route.name !== routeName) {
    router.push({ name: routeName })
  }
}

// Provide notification system to child components
const showSuccessNotification = (message) => {
  notificationMessage.value = message
  notificationColor.value = 'success'
  notificationTimeout.value = 3000
  showNotification.value = true
}

const showErrorNotification = (message) => {
  notificationMessage.value = message
  notificationColor.value = 'error'
  notificationTimeout.value = 5000
  showNotification.value = true
}

provide('notifications', {
  showSuccess: showSuccessNotification,
  showError: showErrorNotification
})
</script>

<style scoped>
.user-settings-page {
  max-width: 100%;
  margin: 0 auto;
}

.user-settings-layout {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

.user-settings-nav {
  flex-shrink: 0;
  width: 280px;
  position: sticky;
  top: 115px;
}

.user-settings-nav-list {
  background: transparent;
  padding: 0;
}

.user-settings-nav-item {
  margin: 8px;
  border-radius: 12px;
  transition: all 0.2s ease;
}

.user-settings-nav-item:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}

.user-settings-nav-item--active {
  background: rgba(var(--v-theme-primary), 0.12);
  color: rgb(var(--v-theme-primary));
}

.user-settings-nav-title {
  font-weight: 500;
  font-size: 0.95rem;
}

.user-settings-content {
  flex: 1;
  min-width: 0;
}

.user-settings-header {
  margin-bottom: 32px;
}

/* Responsive Design */
@media (max-width: 1024px) {
  .user-settings-layout {
    flex-direction: column;
    gap: 16px;
  }

  .user-settings-nav {
    width: 100%;
    position: relative;
    top: auto;
  }

  .user-settings-nav .v-list {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 4px;
    padding: 8px;
  }

  .user-settings-nav-item {
    flex: 1;
    min-width: 140px;
    margin: 0;
  }

  .user-settings-nav-title {
    font-size: 0.85rem;
  }
}

@media (max-width: 768px) {
  .user-settings-page {
    padding: 0 16px;
  }

  .user-settings-nav .v-list {
    flex-direction: column;
    gap: 0;
  }

  .user-settings-nav-item {
    min-width: auto;
    margin: 4px 8px;
  }
}
</style>