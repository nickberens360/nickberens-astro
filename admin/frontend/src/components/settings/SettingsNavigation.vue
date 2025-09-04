<template>
  <nav class="settings-nav">
    <v-list class="settings-nav-list" nav density="comfortable" rounded="lg">
      <v-list-item
        v-for="tab in navigationTabs"
        :key="tab.value"
        :value="tab.value"
        :active="currentTab === tab.value"
        @click="navigateToTab(tab.value)"
        class="settings-nav-item"
        :class="{ 'settings-nav-item--active': currentTab === tab.value }"
        rounded="lg"
      >
        <template v-slot:prepend>
          <v-icon :icon="tab.icon" size="20" />
        </template>
        <v-list-item-title class="settings-nav-title">{{ tab.title }}</v-list-item-title>
      </v-list-item>
    </v-list>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const navigationTabs = [
  {
    value: 'followup',
    title: 'Follow-up Questions',
    icon: '$help-circle'
  },
  {
    value: 'welcome',
    title: 'Welcome Questions',
    icon: '$message-text'
  },
  {
    value: 'api-keys',
    title: 'API Keys',
    icon: '$key'
  },
  {
    value: 'response',
    title: 'Response Settings',
    icon: '$message-reply'
  },
  {
    value: 'routing',
    title: 'Query Routing',
    icon: '$route'
  },
  {
    value: 'features',
    title: 'Feature Flags',
    icon: '$feature-flag'
  },
  {
    value: 'system',
    title: 'System Config',
    icon: '$settings'
  },
  {
    value: 'security',
    title: 'Security & Privacy',
    icon: '$shield-check'
  }
]

const currentTab = computed(() => {
  const routeName = route.name
  if (routeName === 'settings-followup') return 'followup'
  if (routeName === 'settings-welcome') return 'welcome'
  if (routeName === 'settings-api-keys') return 'api-keys'
  if (routeName === 'settings-response') return 'response'
  if (routeName === 'settings-routing') return 'routing'
  if (routeName === 'settings-features') return 'features'
  if (routeName === 'settings-system') return 'system'
  if (routeName === 'settings-security') return 'security'
  return 'followup' // default
})

const navigateToTab = (tabValue) => {
  const routeMap = {
    'followup': 'settings-followup',
    'welcome': 'settings-welcome',
    'api-keys': 'settings-api-keys',
    'response': 'settings-response',
    'routing': 'settings-routing',
    'features': 'settings-features',
    'system': 'settings-system',
    'security': 'settings-security'
  }

  const routeName = routeMap[tabValue]
  if (routeName && route.name !== routeName) {
    router.push({ name: routeName })
  }
}
</script>

<style scoped>
.settings-nav {
  flex-shrink: 0;
  width: 280px;
  position: sticky;
  top: 24px;
}

.settings-nav-list {
  background: transparent;
  padding: 0;
}

.settings-nav-item {
  margin: 8px;
  border-radius: 12px;
  transition: all 0.2s ease;
}

.settings-nav-item:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}

.settings-nav-item--active {
  background: rgba(var(--v-theme-primary), 0.12);
  color: rgb(var(--v-theme-primary));
}

.settings-nav-title {
  font-weight: 500;
  font-size: 0.95rem;
}

/* Mobile responsiveness */
@media (max-width: 1024px) {
  .settings-nav {
    width: 100%;
    position: relative;
    top: auto;
  }
  
  .settings-nav .v-list {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 4px;
    padding: 8px;
  }
  
  .settings-nav-item {
    flex: 1;
    min-width: 140px;
    margin: 0;
  }
  
  .settings-nav-title {
    font-size: 0.85rem;
  }
}

@media (max-width: 768px) {
  .settings-nav .v-list {
    flex-direction: column;
    gap: 0;
  }
  
  .settings-nav-item {
    min-width: auto;
    margin: 4px 8px;
  }
}
</style>