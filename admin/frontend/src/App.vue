<template>
  <v-app>
    <router-view />
  </v-app>
</template>

<script setup>
import { onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'

const adminStore = useAdminStore()

onMounted(() => {
  // Initialize the admin store on app mount
  adminStore.initialize()
})
</script>

<style>
/* App-specific styles can go here */
</style>