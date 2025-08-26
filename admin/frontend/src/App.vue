<template>
  <v-app>
    <router-view />
  </v-app>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'

const adminStore = useAdminStore()

onMounted(async () => {
  // Initialize the admin store on app mount, but let router handle auth redirects
  try {
    await adminStore.initialize()
  } catch (error) {
    // Silent catch - authentication failures are expected
    console.debug('Admin store initialization failed:', error.message || error)
  }
})
</script>

<style>
/* App-specific styles can go here */
</style>