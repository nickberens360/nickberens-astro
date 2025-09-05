<template>
  <div class="notifications-container">
    <v-snackbar
      v-for="notification in notifications"
      :key="notification.id"
      v-model="notification.show"
      :color="notification.type"
      :timeout="notification.duration"
      location="top right"
      class="settings-notification"
      @update:model-value="handleUpdate(notification.id, $event)"
    >
      {{ notification.message }}
      <template v-slot:actions>
        <v-btn
          variant="text"
          size="small"
          @click="dismiss(notification.id)"
        >
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { useNotifications } from '@/composables/useNotifications'

const { notifications, dismiss } = useNotifications()

// Watch for new notifications and auto-show them
watch(notifications, (newNotifications) => {
  newNotifications.forEach(notification => {
    if (!notification.hasOwnProperty('show')) {
      notification.show = true
    }
  })
}, { deep: true, immediate: true })

const handleUpdate = (notificationId, show) => {
  if (!show) {
    dismiss(notificationId)
  }
}

onMounted(() => {
  // Ensure all existing notifications are shown
  notifications.value.forEach(notification => {
    if (!notification.hasOwnProperty('show')) {
      notification.show = true
    }
  })
})
</script>

<style scoped>
.notifications-container {
  position: fixed;
  top: 0;
  right: 0;
  z-index: 9999;
  pointer-events: none;
}

.settings-notification {
  pointer-events: all;
}
</style>