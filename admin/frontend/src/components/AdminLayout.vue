<template>
  <v-app>
    <v-navigation-drawer
      v-model="drawer"
      :permanent="!mobile"
      :temporary="mobile"
      app
      color="surface"
    >
      <v-list>
        <v-list-item class="px-4 py-6">
          <v-list-item-title class="text-h6 font-weight-bold">
            RAG Admin
          </v-list-item-title>
          <v-list-item-subtitle>
            Dashboard v{{ systemHealth.version }}
          </v-list-item-subtitle>
        </v-list-item>

        <v-divider class="mb-2"/>

        <v-list-item
          v-for="item in navigationItems"
          :key="item.name"
          :to="item.to"
          :active="$route.name === item.name"
          rounded="xl"
          class="mx-2 mb-1"
          :prepend-icon="item.icon"
        >
          <v-list-item-title>{{ item.title }}</v-list-item-title>
        </v-list-item>
      </v-list>

      <template #append>
        <v-divider class="mb-2"/>

        <v-list density="compact">
          <v-list-item class="px-4">
            <v-list-item-title class="text-caption text-medium-emphasis">
              System Status
            </v-list-item-title>
            <v-chip
              :color="isHealthy ? 'success' : 'error'"
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
      app
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
                {{ isDark ? 'mdi-white-balance-sunny' : 'mdi-weather-night' }}
              </v-icon>
              {{ isDark ? 'Light' : 'Dark' }} Mode
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useDisplay, useTheme } from 'vuetify';
import { useAdminStore } from '@/stores/admin';
import { formatDate } from '@/types/admin';
import TimeRangeSelector from '@/components/TimeRangeSelector.vue';

const router = useRouter();
const route = useRoute();
const { mobile } = useDisplay();
const theme = useTheme();

const adminStore = useAdminStore();

// Local state
const drawer = ref(true);

// Computed properties
const {
  stats,
  systemHealth,
  timeRange,
  isLoading,
  error,
  isConnected,
  isHealthy
} = adminStore;

const isDark = computed(() => theme.global.current.value.dark);

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
    name: 'content',
    title: 'Content',
    to: '/admin/content',
    icon: '$document'
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
    to: '/admin/knowledge',
    icon: '$knowledge'
  }
]);

const currentPageTitle = computed(() => {
  const item = navigationItems.value.find(item => item.name === route.name);
  return item?.title || 'Admin Dashboard';
});

const showTimeRangeSelector = computed(() => {
  return ['dashboard', 'performance'].includes(route.name);
});

const showError = ref(false);
const showConnectionWarning = ref(false);

// Watch for error changes
watch(() => error?.value, (newError) => {
  showError.value = Boolean(newError);
});

// Watch for connection status changes
watch([() => isConnected.value, () => isLoading.value], ([connected, loading]) => {
  showConnectionWarning.value = !connected && !loading;
});

const formatLastUpdate = computed(() => {
  if (!adminStore.lastUpdate) return 'Never';
  return formatDate(adminStore.lastUpdate);
});

// Methods
const refreshData = async () => {
  await adminStore.refreshData();
};

const setTimeRange = async (newTimeRange) => {
  await adminStore.setTimeRange(newTimeRange);
};

const resetError = () => {
  showError.value = false;
  adminStore.resetError();
};

const testConnection = async () => {
  await adminStore.testConnection();
  if (isConnected.value) {
    await refreshData();
  }
};

const toggleTheme = () => {
  theme.global.name.value = isDark.value ? 'light' : 'dark';
};

const exportData = () => {
  // TODO: Implement export functionality
  console.log('Export data functionality to be implemented');
};

// Lifecycle
onMounted(() => {
  // Close drawer on mobile by default
  if (mobile.value) {
    drawer.value = false;
  }
});

onUnmounted(() => {
  adminStore.cleanup();
});
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