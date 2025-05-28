import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  duration?: number
  actions?: NotificationAction[]
  persistent?: boolean
  timestamp: number
}

export interface NotificationAction {
  label: string
  action: () => void
  style?: 'primary' | 'secondary' | 'danger'
}

export const useNotificationStore = defineStore('notification', () => {
  // State
  const notifications = ref<Notification[]>([])
  const maxNotifications = ref(5)

  // Getters
  const activeNotifications = computed(() => notifications.value)
  const hasNotifications = computed(() => notifications.value.length > 0)
  
  // Auto-dismiss timers
  const timers = new Map<string, NodeJS.Timeout>()

  // Actions
  const addNotification = (notification: Omit<Notification, 'id' | 'timestamp'>) => {
    const id = generateId()
    const timestamp = Date.now()
    
    const newNotification: Notification = {
      id,
      timestamp,
      duration: notification.persistent ? undefined : (notification.duration ?? getDefaultDuration(notification.type)),
      ...notification
    }

    // Add to beginning of array (newest first)
    notifications.value.unshift(newNotification)

    // Remove oldest if exceeding max
    if (notifications.value.length > maxNotifications.value) {
      const removed = notifications.value.pop()
      if (removed) {
        clearTimer(removed.id)
      }
    }

    // Set auto-dismiss timer if not persistent
    if (newNotification.duration && newNotification.duration > 0) {
      const timer = setTimeout(() => {
        removeNotification(id)
      }, newNotification.duration)
      timers.set(id, timer)
    }

    return id
  }

  const removeNotification = (id: string) => {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index > -1) {
      notifications.value.splice(index, 1)
      clearTimer(id)
    }
  }

  const clearAll = () => {
    notifications.value.forEach(n => clearTimer(n.id))
    notifications.value = []
  }

  const clearTimer = (id: string) => {
    const timer = timers.get(id)
    if (timer) {
      clearTimeout(timer)
      timers.delete(id)
    }
  }

  // Convenience methods
  const success = (title: string, message: string, options?: Partial<Notification>) => {
    return addNotification({
      type: 'success',
      title,
      message,
      ...options
    })
  }

  const error = (title: string, message: string, options?: Partial<Notification>) => {
    return addNotification({
      type: 'error',
      title,
      message,
      persistent: true, // Errors are persistent by default
      ...options
    })
  }

  const warning = (title: string, message: string, options?: Partial<Notification>) => {
    return addNotification({
      type: 'warning',
      title,
      message,
      ...options
    })
  }

  const info = (title: string, message: string, options?: Partial<Notification>) => {
    return addNotification({
      type: 'info',
      title,
      message,
      ...options
    })
  }

  // API Error Helper
  const handleApiError = (error: any, context?: string) => {
    let title = 'Er is een fout opgetreden'
    let message = 'Probeer het later opnieuw'
    let actions: NotificationAction[] = []

    if (error?.response?.status) {
      switch (error.response.status) {
        case 401:
          title = 'Niet geautoriseerd'
          message = 'U bent niet ingelogd of uw sessie is verlopen'
          actions = [{
            label: 'Inloggen',
            action: () => window.location.href = '/login',
            style: 'primary'
          }]
          break
        case 403:
          title = 'Geen toegang'
          message = 'U heeft geen rechten voor deze actie'
          break
        case 404:
          title = 'Niet gevonden'
          message = context ? `${context} kon niet worden gevonden` : 'De gevraagde resource kon niet worden gevonden'
          break
        case 422:
          title = 'Validatiefout'
          message = error.response.data?.detail || 'Controleer uw invoer en probeer opnieuw'
          break
        case 429:
          title = 'Te veel verzoeken'
          message = 'Wacht even voordat u het opnieuw probeert'
          break
        case 500:
          title = 'Serverfout'
          message = 'Er is iets misgegaan op de server. Probeer het later opnieuw'
          actions = [{
            label: 'Opnieuw proberen',
            action: () => window.location.reload(),
            style: 'secondary'
          }]
          break
        default:
          if (context) {
            title = `Fout bij ${context}`
          }
      }
    } else if (error?.message) {
      message = error.message
    }

    return addNotification({
      type: 'error',
      title,
      message,
      actions,
      persistent: true
    })
  }

  // Helper functions
  const generateId = (): string => {
    return Math.random().toString(36).substr(2, 9) + Date.now().toString(36)
  }

  const getDefaultDuration = (type: Notification['type']): number => {
    switch (type) {
      case 'success':
        return 4000
      case 'info':
        return 6000
      case 'warning':
        return 8000
      case 'error':
        return 0 // Persistent by default
      default:
        return 5000
    }
  }

  return {
    // State
    notifications: activeNotifications,
    hasNotifications,
    
    // Actions
    addNotification,
    removeNotification,
    clearAll,
    
    // Convenience methods
    success,
    error,
    warning,
    info,
    handleApiError
  }
})