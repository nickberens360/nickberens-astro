<template>
  <v-app>
    <v-navigation-drawer
      v-model="drawer"
      :permanent="!mobile"
      :temporary="mobile"
      style="position: fixed;"
      color="surface"
      width="280"
      class="sidebar-drawer"
    >
      <!-- Brand Logo Section -->
      <div class="sidebar-header pa-6">
        <div class="d-flex align-center">
          <div class="brand-logo">
            <v-avatar color="primary" size="40">
              <v-icon size="24" color="white">$dashboard</v-icon>
            </v-avatar>
          </div>
          <div class="ml-3">
            <div class="brand-title text-h6 font-weight-bold">
              RAG LMS
            </div>
          </div>
        </div>
      </div>

      <v-divider class="mb-4"/>

      <!-- Main Menu Section -->
      <div class="px-4">
        <div class="menu-label text-caption font-weight-medium text-medium-emphasis mb-3">
          MAIN MENU
        </div>
        <v-list nav density="compact" class="py-0">
          <template v-for="item in navigationItems" :key="item.name">
            <!-- Main navigation item -->
            <v-list-item
              v-if="!item.children"
              :to="item.to"
              :active="$route.name === item.name"
              rounded="lg"
              class="mb-1 nav-item"
              :prepend-icon="item.icon"
              color="primary"
            >
              <v-list-item-title class="font-weight-medium">{{ item.title }}</v-list-item-title>
            </v-list-item>

            <!-- Navigation item with children -->
            <v-list-group
              v-else
              :key="item.name"
              :value="item.name"
              class="mb-1"
            >
              <template v-slot:activator="{ props }">
                <v-list-item
                  v-bind="props"
                  :prepend-icon="item.icon"
                  rounded="lg"
                  class="nav-item"
                  color="primary"
                  :active="$route.name === item.name || item.children.some(child => $route.name === child.name)"
                  @click="navigateToParent(item)"
                >
                  <v-list-item-title class="font-weight-medium">{{ item.title }}</v-list-item-title>
                </v-list-item>
              </template>

              <v-list-item
                v-for="child in item.children"
                :key="child.name"
                :to="child.to"
                :active="$route.name === child.name"
                rounded="lg"
                class="ms-4 nav-item"
                color="primary"
              >
                <v-list-item-title class="font-weight-medium">{{ child.title }}</v-list-item-title>
              </v-list-item>
            </v-list-group>
          </template>
        </v-list>
      </div>


      <template #append>
        <v-divider class="mb-2"/>

        <v-list density="compact">
          <v-list-item class="px-4">
            <v-list-item-title class="text-caption text-medium-emphasis">
              System Status
            </v-list-item-title>
            <v-chip
              :color="getStatusColor(systemHealth.status)"
              size="x-small"
              variant="flat"
            >
              {{ systemHealth.status }}
            </v-chip>
          </v-list-item>

          <v-list-item
            class="px-4"
            @click="refreshData"
          >
            <v-list-item-title class="text-caption text-medium-emphasis">
              Last Updated
            </v-list-item-title>
            <v-list-item-subtitle class="text-caption">
              {{ formatLastUpdate }}
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </template>
    </v-navigation-drawer>

    <v-app-bar
      style="position: fixed;"
      color="background"
      elevation="0"
      height="80"
      class="modern-header px-8"
    >
      <v-app-bar-nav-icon
        v-if="mobile"
        @click="drawer = !drawer"
      />

      <v-toolbar-title class="text-h5 font-weight-bold">
        {{ currentPageTitle }}
      </v-toolbar-title>

      <v-spacer/>

      <!-- Time Range Selector -->
      <TimeRangeSelector
        v-if="showTimeRangeSelector"
        :model-value="timeRange"
        @update:model-value="setTimeRange"
        class="mr-4"
      />

      <!-- Notifications (hidden until notification system is implemented) -->
      <v-btn
        v-if="false"
        icon
        variant="text"
        size="large"
        class="mr-2"
      >
        <v-badge
          color="error"
          :content="notificationCount"
          :value="notificationCount > 0"
          dot
        >
          <v-icon>$bell</v-icon>
        </v-badge>
        <v-tooltip
          activator="parent"
          location="bottom"
        >
          Notifications
        </v-tooltip>
      </v-btn>

      <!-- User Profile -->
      <v-menu>
        <template #activator="{ props }">
          <div v-bind="props" class="user-profile-section d-flex align-center pa-2 rounded-lg cursor-pointer">
            <v-avatar size="40" class="mr-3" color="primary">
              <v-icon color="white">$account</v-icon>
            </v-avatar>
            <div class="user-info d-none d-sm-block">
              <div class="user-name text-subtitle-1 font-weight-medium">{{ userDisplayName }}</div>
              <div class="user-role text-caption text-medium-emphasis">{{ userRole }}</div>
            </div>
            <v-icon class="ml-2 d-none d-sm-block">$chevron-down</v-icon>
          </div>
        </template>

        <v-list width="200">
          <v-list-item @click="refreshData">
            <v-list-item-title>
              <v-icon start>$refresh</v-icon>
              Refresh Data
            </v-list-item-title>
          </v-list-item>
          
          <v-list-item @click="exportData">
            <v-list-item-title>
              <v-icon start>$export</v-icon>
              Export Data
            </v-list-item-title>
          </v-list-item>

          <v-divider/>

          <v-list-item @click="toggleTheme">
            <v-list-item-title>
              <v-icon start>
                {{ isDark ? '$light-mode' : '$weather-night' }}
              </v-icon>
              {{ isDark ? 'Light' : 'Dark' }} Mode
            </v-list-item-title>
          </v-list-item>

          <v-divider/>

          <v-list-item to="/admin/change-password">
            <v-list-item-title>
              <v-icon start>$lock</v-icon>
              Change Password
            </v-list-item-title>
          </v-list-item>

          <v-divider/>

          <v-list-item @click="handleLogout">
            <v-list-item-title>
              <v-icon start>$logout</v-icon>
              Logout
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </v-app-bar>

    <v-main>
      <v-container
        fluid
        class="pa-8"
        style="background-color: rgb(var(--v-theme-background));"
      >
        <router-view v-slot="{ Component }">
          <Transition
            name="fade"
            mode="out-in"
          >
            <component :is="Component"/>
          </Transition>
        </router-view>
      </v-container>
    </v-main>

    <!-- Error Snackbar -->
    <v-snackbar
      v-model="showError"
      color="error"
      multi-line
      timeout="6000"
      location="bottom"
    >
      {{ error }}

      <template #actions>
        <v-btn
          text="Close"
          variant="text"
          @click="resetError"
        />
      </template>
    </v-snackbar>

    <!-- Connection Status -->
    <v-snackbar
      v-model="showConnectionWarning"
      color="warning"
      persistent
      location="top"
    >
      <v-icon start>$alert</v-icon>
      Connection to admin API lost. Retrying...

      <template #actions>
        <v-btn
          text="Retry"
          variant="text"
          @click="testConnection"
        />
      </template>
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useDisplay, useTheme } from 'vuetify'
import { storeToRefs } from 'pinia'
import { useAdminStore } from '@/stores/admin'
import { formatDate } from '@/types/admin'
import TimeRangeSelector from '@/components/TimeRangeSelector.vue'

const router = useRouter()
const route = useRoute()
const { mobile } = useDisplay()
const theme = useTheme()

const adminStore = useAdminStore()

// Local state
const drawer = ref(true)

// Computed properties
const {
  stats,
  systemHealth,
  timeRange,
  isLoading,
  error,
  isConnected,
  isHealthy
} = storeToRefs(adminStore);

const isDark = computed(() => theme.global.current.value.dark)

const userDisplayName = computed(() => {
  // Get real user data from the admin store
  return adminStore.user?.username || 'Admin User'
})

const userRole = computed(() => {
  // Get real user role from the admin store
  const role = adminStore.user?.role || 'viewer'
  // Format role for display
  return role.charAt(0).toUpperCase() + role.slice(1)
})

const notificationCount = computed(() => {
  // Placeholder for future notification system
  // TODO: Implement real notification counting from backend
  return 0
})

const navigationItems = computed(() => [
  {
    name: 'dashboard',
    title: 'Dashboard',
    to: '/',
    icon: '$dashboard'
  },
  {
    name: 'queries',
    title: 'Queries',
    to: '/queries',
    icon: '$search'
  },
  {
    name: 'performance',
    title: 'Performance',
    to: '/performance',
    icon: '$chart'
  },
  {
    name: 'sessions',
    title: 'Sessions',
    to: '/sessions',
    icon: '$users'
  },
  {
    name: 'knowledge',
    title: 'Knowledge Base',
    to: '/knowledge/sources',
    icon: '$knowledge',
    //do nest children
  },
  {
    name: 'settings',
    title: 'Settings',
    to: '/settings/followup',
    icon: '$settings'
  }
]);

const currentPageTitle = computed(() => {
  // First try to get title from route meta
  if (route.meta?.title) {
    return route.meta.title;
  }

  // Fallback: Check main navigation items
  const item = navigationItems.value.find(item => item.name === route.name);
  if (item) return item.title;

  return 'Admin Dashboard';
});

const showTimeRangeSelector = computed(() => {
  return ['dashboard', 'performance'].includes(route.name);
});

const showError = ref(false)
const showConnectionWarning = ref(false)

// Watch for error changes
watch(error, (newError) => {
  showError.value = Boolean(newError)
})

// Watch for connection status changes
watch([isConnected, isLoading], ([connected, loading]) => {
  showConnectionWarning.value = !connected && !loading
})

const formatLastUpdate = computed(() => {
  if (!adminStore.lastUpdate) return 'Never'
  return formatDate(adminStore.lastUpdate)
})

// Methods
const getStatusColor = (status) => {
  switch (status?.toLowerCase()) {
    case 'healthy':
    case 'ok':
    case 'running':
      return 'success'
    case 'error':
    case 'failed':
    case 'down':
      return 'error'
    case 'warning':
    case 'degraded':
      return 'warning'
    case 'unknown':
    case 'loading':
      return 'info'
    default:
      return 'grey'
  }
}

const refreshData = async () => {
  await adminStore.refreshData()
}

const setTimeRange = async (newTimeRange) => {
  await adminStore.setTimeRange(newTimeRange)
}

const resetError = () => {
  showError.value = false
  adminStore.resetError()
}

const testConnection = async () => {
  await adminStore.testConnection()
  if (isConnected.value) {
    await refreshData()
  }
}

const toggleTheme = () => {
  theme.global.name.value = isDark.value ? 'light' : 'dark'
}

const exportData = () => {
  // TODO: Implement export functionality
  // Export data functionality to be implemented
}

const navigateToParent = (item) => {
  // Navigate to the parent route which will redirect to the default child
  if (item.to) {
    router.push(item.to)
  }
}

const handleLogout = async () => {
  try {
    await adminStore.logout()
    router.push({ name: 'login' })
  } catch (error) {
    console.error('Logout failed:', error)
  }
}

// Lifecycle
onMounted(() => {
  // Close drawer on mobile by default
  if (mobile.value) {
    drawer.value = false
  }
})

onUnmounted(() => {
  adminStore.cleanup()
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.sidebar-drawer {
  /* Clean drawer without border */
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.04);
}

.modern-header {
  /* Clean header without border */
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  backdrop-filter: blur(10px);
}

.sidebar-header {
  background: rgba(var(--v-theme-primary), 0.03);
}

.brand-title {
  color: rgb(var(--v-theme-primary));
}

.menu-label {
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.nav-item {
  margin-bottom: 4px;
}

.nav-item.v-list-item--active {
  background: rgba(var(--v-theme-primary), 0.1);
  color: rgb(var(--v-theme-primary));
}

.nav-item.v-list-item--active .v-icon {
  color: rgb(var(--v-theme-primary));
}

.user-profile-section:hover {
  background: rgba(var(--v-theme-on-surface), 0.04);
}

.cursor-pointer {
  cursor: pointer;
}
</style>