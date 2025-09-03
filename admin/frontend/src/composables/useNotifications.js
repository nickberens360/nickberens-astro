import { ref } from 'vue'

const notifications = ref([])

export function useNotifications() {
  const showSuccess = (message, duration = 4000) => {
    const id = Date.now() + Math.random()
    notifications.value.push({
      id,
      type: 'success',
      message,
      duration,
      show: true
    })
    
    // Auto-remove after duration
    setTimeout(() => {
      dismiss(id)
    }, duration)
  }

  const showError = (message, duration = 6000) => {
    const id = Date.now() + Math.random()
    notifications.value.push({
      id,
      type: 'error',
      message,
      duration,
      show: true
    })
    
    // Auto-remove after duration
    setTimeout(() => {
      dismiss(id)
    }, duration)
  }

  const showInfo = (message, duration = 4000) => {
    const id = Date.now() + Math.random()
    notifications.value.push({
      id,
      type: 'info',
      message,
      duration,
      show: true
    })
    
    // Auto-remove after duration
    setTimeout(() => {
      dismiss(id)
    }, duration)
  }

  const showWarning = (message, duration = 5000) => {
    const id = Date.now() + Math.random()
    notifications.value.push({
      id,
      type: 'warning',
      message,
      duration,
      show: true
    })
    
    // Auto-remove after duration
    setTimeout(() => {
      dismiss(id)
    }, duration)
  }

  const dismiss = (notificationId) => {
    const index = notifications.value.findIndex(n => n.id === notificationId)
    if (index > -1) {
      notifications.value.splice(index, 1)
    }
  }

  const clear = () => {
    notifications.value = []
  }

  return {
    notifications,
    showSuccess,
    showError,
    showInfo,
    showWarning,
    dismiss,
    clear
  }
}