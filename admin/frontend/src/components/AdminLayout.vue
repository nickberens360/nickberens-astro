<template>
  <v-app>
    <v-navigation-drawer
      v-model="drawer"
      :permanent="!mobile"
      :temporary="mobile"
      style="position: fixed;"
      color="surface"
    >
      <v-list>
        <v-list-item class="px-4 py-0 pb-2">
          <v-list-item-title class="text-h6 font-weight-bold">
            RAG Admin
          </v-list-item-title>
          <v-list-item-subtitle>
            Dashboard v{{ systemHealth.version }}
          </v-list-item-subtitle>
        </v-list-item>

        <v-divider class="mb-2"/>

        <template v-for="item in navigationItems" :key="item.name">
          <!-- Main navigation item -->
          <v-list-item
            v-if="!item.children"
            :to="item.to"
            :active="$route.name === item.name"
            rounded="xl"
            class="mx-2 mb-1"
            :prepend-icon="item.icon"
          >
            <v-list-item-title>{{ item.title }}</v-list-item-title>
          </v-list-item>

          <!-- Navigation item with children -->
          <v-list-group
            v-else
            :key="item.name"
            :value="item.name"
            class="mx-2 mb-1"
          >
            <template v-slot:activator="{ props }">
              <v-list-item
                v-bind="props"
                :prepend-icon="item.icon"
                rounded="xl"
                :active="$route.name === item.name || item.children.some(child => $route.name === child.name)"
                @click="navigateToParent(item)"
              >
                <v-list-item-title>{{ item.title }}</v-list-item-title>
              </v-list-item>
            </template>

            <v-list-item
              v-for="child in item.children"
              :key="child.name"
              :to="child.to"
              :active="$route.name === child.name"
              rounded="xl"
              class="ms-4"
            >
              <v-list-item-title>{{ child.title }}</v-list-item-title>
            </v-list-item>
          </v-list-group>
        </template>
      </v-list>

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
      color="surface"
      elevation="1"
    >
      <v-app-bar-nav-icon
        v-if="mobile"
        @click="drawer = !drawer"
      />

      <v-toolbar-title>
        {{ currentPageTitle }}
      </v-toolbar-title>

      <v-spacer/>

      <v-btn
        :loading="isLoading"
        icon="$refresh"
        variant="text"
        @click="refreshData"
      >
        <v-icon>$refresh</v-icon>
        <v-tooltip
          activator="parent"
          location="bottom"
        >
          Refresh Data
        </v-tooltip>
      </v-btn>

      <TimeRangeSelector
        v-if="showTimeRangeSelector"
        :model-value="timeRange"
        @update:model-value="setTimeRange"
      />

      <v-menu>
        <template #activator="{ props }">
          <v-btn
            icon="$menu"
            variant="text"
            v-bind="props"
          >
            <v-icon>$menu</v-icon>
          </v-btn>
        </template>

        <v-list>
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
        class="pa-6"
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

const navigationItems = computed(() => [
  {
    name: 'dashboard',
    title: 'Dashboard',
    to: '/admin',
    icon: '$dashboard'
  },
  {
    name: 'queries',
    title: 'Queries',
    to: '/admin/queries',
    icon: '$search'
  },
  {
    name: 'performance',
    title: 'Performance',
    to: '/admin/performance',
    icon: '$chart'
  },
  {
    name: 'sessions',
    title: 'Sessions',
    to: '/admin/sessions',
    icon: '$users'
  },
  {
    name: 'knowledge',
    title: 'Knowledge Base',
    to: '/admin/knowledge/sources',
    icon: '$knowledge',
    //do nest children
  }
]);

const currentPageTitle = computed(() => {
  // Check main navigation items
  let item = navigationItems.value.find(item => item.name === route.name);
  if (item) return item.title;

  // Check nested children
  for (const navItem of navigationItems.value) {
    if (navItem.children) {
      const childItem = navItem.children.find(child => child.name === route.name);
      if (childItem) return childItem.title;
    }
  }

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

.v-navigation-drawer {
  border-right: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}

.v-app-bar {
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}
</style>