/**
 * Global error handling composable
 * Provides consistent error handling across the application
 */

import { ref } from 'vue'
import { useNotificationStore } from '@/stores/notification'
import { useRouter } from 'vue-router'

interface ErrorContext {
  component?: string
  action?: string
  userId?: string
  timestamp: number
  url: string
  userAgent: string
}

interface ErrorHandlerOptions {
  showNotification?: boolean
  logError?: boolean
  redirectOnError?: string | null
  retryAction?: () => Promise<void> | void
}

export function useErrorHandler() {
  const notificationStore = useNotificationStore()
  const router = useRouter()
  
  const isHandlingError = ref(false)
  const lastError = ref<Error | null>(null)

  /**
   * Main error handling function
   */
  const handleError = async (
    error: Error | unknown,
    context: Partial<ErrorContext> = {},
    options: ErrorHandlerOptions = {}
  ) => {
    const {
      showNotification = true,
      logError = true,
      redirectOnError = null,
      retryAction = null
    } = options

    if (isHandlingError.value) return // Prevent recursive error handling

    isHandlingError.value = true
    
    try {
      // Convert unknown errors to Error objects
      const errorObj = error instanceof Error ? error : new Error(String(error))
      lastError.value = errorObj

      // Create full error context
      const fullContext: ErrorContext = {
        component: 'Unknown',
        action: 'Unknown',
        timestamp: Date.now(),
        url: window.location.href,
        userAgent: navigator.userAgent,
        ...context
      }

      // Log error if enabled
      if (logError) {
        logErrorToConsole(errorObj, fullContext)
        await logErrorToService(errorObj, fullContext)
      }

      // Show user notification if enabled
      if (showNotification) {
        showErrorNotification(errorObj, retryAction)
      }

      // Redirect if specified
      if (redirectOnError) {
        await router.push(redirectOnError)
      }

    } catch (handlingError) {
      // If error handling itself fails, fallback to basic console log
      console.error('Error handler failed:', handlingError)
      console.error('Original error:', error)
    } finally {
      isHandlingError.value = false
    }
  }

  /**
   * Handle API errors specifically
   */
  const handleApiError = async (
    error: any,
    context: Partial<ErrorContext> = {},
    options: ErrorHandlerOptions = {}
  ) => {
    let errorMessage = 'Er is een onverwachte fout opgetreden'
    let errorTitle = 'Fout'

    // Extract error information from API response
    if (error?.response) {
      const status = error.response.status
      const data = error.response.data

      switch (status) {
        case 400:
          errorTitle = 'Ongeldige aanvraag'
          errorMessage = data?.message || 'De aanvraag bevat ongeldige gegevens'
          break
        case 401:
          errorTitle = 'Niet geautoriseerd'
          errorMessage = 'U bent niet gemachtigd voor deze actie. Log opnieuw in.'
          // Automatically redirect to login
          options.redirectOnError = '/login'
          break
        case 403:
          errorTitle = 'Toegang geweigerd'
          errorMessage = 'U heeft geen toegang tot deze functie'
          break
        case 404:
          errorTitle = 'Niet gevonden'
          errorMessage = 'De opgevraagde informatie kon niet worden gevonden'
          break
        case 409:
          errorTitle = 'Conflict'
          errorMessage = data?.message || 'Er is een conflict met bestaande gegevens'
          break
        case 422:
          errorTitle = 'Validatiefout'
          errorMessage = data?.message || 'Sommige gegevens zijn niet correct ingevuld'
          break
        case 429:
          errorTitle = 'Te veel aanvragen'
          errorMessage = 'U heeft te veel aanvragen gedaan. Probeer het later opnieuw.'
          break
        case 500:
        case 502:
        case 503:
        case 504:
          errorTitle = 'Serverfout'
          errorMessage = 'Er is een probleem met de server. Probeer het later opnieuw.'
          break
        default:
          errorMessage = data?.message || `HTTP ${status}: ${error.response.statusText}`
      }
    } else if (error?.code === 'NETWORK_ERROR' || error?.message?.includes('Network Error')) {
      errorTitle = 'Netwerkfout'
      errorMessage = 'Controleer uw internetverbinding en probeer het opnieuw'
    } else if (error?.code === 'TIMEOUT') {
      errorTitle = 'Time-out'
      errorMessage = 'De aanvraag duurde te lang. Probeer het opnieuw.'
    }

    // Create a more descriptive error
    const apiError = new Error(errorMessage)
    apiError.name = errorTitle
    
    // Add additional properties for better error handling
    Object.assign(apiError, {
      status: error?.response?.status,
      statusText: error?.response?.statusText,
      code: error?.code,
      originalError: error
    })

    await handleError(apiError, context, options)
  }

  /**
   * Handle validation errors from forms
   */
  const handleValidationError = (
    errors: Record<string, string[]>,
    context: Partial<ErrorContext> = {}
  ) => {
    const firstError = Object.values(errors).flat()[0]
    const errorCount = Object.keys(errors).length
    
    const title = errorCount === 1 ? 'Validatiefout' : 'Validatiefouten'
    const message = errorCount === 1 
      ? firstError 
      : `Er zijn ${errorCount} velden die aandacht vereisen`

    notificationStore.error(title, message, {
      actions: [
        {
          label: 'Toon details',
          action: () => {
            // Could open a modal with detailed validation errors
            console.log('Validation errors:', errors)
          },
          style: 'secondary'
        }
      ]
    })
  }

  /**
   * Handle network/connectivity errors
   */
  const handleNetworkError = async (
    error: Error,
    context: Partial<ErrorContext> = {},
    retryAction?: () => Promise<void>
  ) => {
    const networkError = new Error('Geen internetverbinding of server niet bereikbaar')
    networkError.name = 'NetworkError'

    await handleError(networkError, context, {
      showNotification: true,
      retryAction
    })
  }

  /**
   * Log error to console with context
   */
  const logErrorToConsole = (error: Error, context: ErrorContext) => {
    console.group(`🚨 Error in ${context.component || 'Unknown Component'}`)
    console.error('Error:', error)
    console.table(context)
    console.groupEnd()
  }

  /**
   * Log error to external service (implement based on your monitoring service)
   */
  const logErrorToService = async (error: Error, context: ErrorContext) => {
    try {
      // Example: Send to monitoring service
      // await monitoringService.logError({
      //   message: error.message,
      //   stack: error.stack,
      //   context,
      //   level: 'error'
      // })
      
      // For now, just log to console in development
      if (process.env.NODE_ENV === 'development') {
        console.log('Would log to monitoring service:', { error, context })
      }
    } catch (loggingError) {
      console.error('Failed to log error to service:', loggingError)
    }
  }

  /**
   * Show error notification to user
   */
  const showErrorNotification = (error: Error, retryAction?: () => Promise<void> | void) => {
    const actions = []

    if (retryAction) {
      actions.push({
        label: 'Opnieuw proberen',
        action: async () => {
          try {
            await retryAction()
            notificationStore.success('Gelukt!', 'De actie is succesvol uitgevoerd.')
          } catch (retryError) {
            handleError(retryError, { action: 'retry' })
          }
        },
        style: 'primary' as const
      })
    }

    actions.push({
      label: 'Details',
      action: () => {
        console.log('Error details:', error)
      },
      style: 'secondary' as const
    })

    notificationStore.error(
      error.name || 'Fout',
      error.message,
      {
        actions,
        duration: retryAction ? 0 : 8000, // Persistent if retry available
        persistent: !!retryAction
      }
    )
  }

  /**
   * Clear the last error
   */
  const clearError = () => {
    lastError.value = null
  }

  /**
   * Check if currently handling an error
   */
  const isError = () => isHandlingError.value

  /**
   * Get the last error
   */
  const getLastError = () => lastError.value

  return {
    handleError,
    handleApiError,
    handleValidationError,
    handleNetworkError,
    clearError,
    isError,
    getLastError,
    isHandlingError: isHandlingError.value
  }
}

/**
 * Global error handler for unhandled promise rejections and errors
 */
export function setupGlobalErrorHandling() {
  const { handleError } = useErrorHandler()

  // Handle unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    handleError(event.reason, {
      component: 'Global',
      action: 'unhandledRejection'
    })
  })

  // Handle global JavaScript errors
  window.addEventListener('error', (event) => {
    handleError(event.error || new Error(event.message), {
      component: 'Global',
      action: 'globalError'
    })
  })

  // Handle Vue errors (if needed at the app level)
  return {
    errorHandler: (error: Error, instance: any, info: string) => {
      handleError(error, {
        component: instance?.$options?.name || 'Vue Component',
        action: info
      })
    }
  }
}