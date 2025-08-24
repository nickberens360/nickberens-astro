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
    console.log('Admin store initialization failed, likely due to authentication:', error)
  }
})
</script>

<style>
/* App-specific styles can go here */
</style>