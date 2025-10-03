<template>
  <div 
    v-if="hasError" 
    class="error-boundary"
    role="alert"
    aria-labelledby="error-title"
    aria-describedby="error-description"
  >
    <div class="error-container">
      <!-- Error Icon -->
      <div class="error-icon" aria-hidden="true">
        <svg width="64" height="64" viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="32" cy="32" r="30"/>
          <path d="M22 22l20 20M42 22l-20 20"/>
        </svg>
      </div>

      <!-- Error Content -->
      <div class="error-content">
        <h2 id="error-title" class="error-title">{{ errorData.title }}</h2>
        <p id="error-description" class="error-description">{{ errorData.message }}</p>
        
        <!-- Detailed Error Info (for development) -->
        <details v-if="showDetails && errorData.details" class="error-details">
          <summary class="error-details-toggle">Technische details</summary>
          <pre class="error-stack">{{ errorData.details }}</pre>
        </details>
        
        <!-- Recovery Actions -->
        <div class="error-actions" role="group" aria-label="Herstel opties">
          <button 
            v-if="errorData.canRetry"
            @click="handleRetry"
            class="btn btn-primary"
            :disabled="isRetrying"
            :aria-label="isRetrying ? 'Bezig met opnieuw proberen' : 'Probeer opnieuw'"
          >
            <svg v-if="isRetrying" class="btn-icon animate-spin" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M10 3a7 7 0 100 14 7 7 0 000-14zm0 2a5 5 0 110 10 5 5 0 010-10z" opacity="0.25"/>
              <path d="M10 3a7 7 0 017 7h-2a5 5 0 00-5-5V3z"/>
            </svg>
            <svg v-else class="btn-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>
            </svg>
            {{ isRetrying ? 'Bezig...' : 'Opnieuw proberen' }}
          </button>
          
          <button 
            v-if="errorData.canGoBack"
            @click="handleGoBack"
            class="btn btn-outline"
            aria-label="Ga terug naar vorige pagina"
          >
            <svg class="btn-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clip-rule="evenodd"/>
            </svg>
            Ga terug
          </button>
          
          <button 
            v-if="errorData.canReload"
            @click="handleReload"
            class="btn btn-secondary"
            aria-label="Herlaad de pagina"
          >
            <svg class="btn-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>
            </svg>
            Pagina herladen
          </button>
          
          <button 
            @click="handleDismiss"
            class="btn btn-ghost"
            aria-label="Sluit foutmelding"
          >
            <svg class="btn-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
            </svg>
            Sluiten
          </button>
        </div>
        
        <!-- Help Links -->
        <div v-if="errorData.helpLinks && errorData.helpLinks.length > 0" class="error-help">
          <h3>Hulp nodig?</h3>
          <ul class="help-links">
            <li v-for="link in errorData.helpLinks" :key="link.text">
              <a 
                :href="link.url" 
                :target="link.external ? '_blank' : '_self'"
                :rel="link.external ? 'noopener noreferrer' : ''"
                class="help-link"
              >
                {{ link.text }}
                <svg v-if="link.external" class="external-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                  <path fill-rule="evenodd" d="M10.586 3H7a1 1 0 110-2h6a1 1 0 011 1v6a1 1 0 11-2 0V4.414l-6.293 6.293a1 1 0 01-1.414-1.414L10.586 3z" clip-rule="evenodd"/>
                </svg>
                <span v-if="link.external" class="sr-only">(opent in nieuw venster)</span>
              </a>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
  
  <!-- Normal content -->
  <div v-else>
    <slot />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onErrorCaptured } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '@/stores/notification'

interface ErrorData {
  title: string
  message: string
  details?: string
  type: 'network' | 'validation' | 'permission' | 'server' | 'client' | 'unknown'
  canRetry: boolean
  canGoBack: boolean
  canReload: boolean
  helpLinks?: Array<{
    text: string
    url: string
    external: boolean
  }>
}

interface Props {
  showDetails?: boolean
  onRetry?: () => Promise<void> | void
  onError?: (error: Error) => void
}

const props = withDefaults(defineProps<Props>(), {
  showDetails: process.env.NODE_ENV === 'development'
})

const emit = defineEmits<{
  'error': [error: Error]
  'retry': []
  'dismiss': []
}>()

const router = useRouter()
const notificationStore = useNotificationStore()

const hasError = ref(false)
const isRetrying = ref(false)
const currentError = ref<Error | null>(null)

// Error mapping for user-friendly Dutch messages
const errorMap: Record<string, Partial<ErrorData>> = {
  // Network errors
  'NetworkError': {
    title: 'Verbindingsprobleem',
    message: 'Er is een probleem met de internetverbinding. Controleer uw verbinding en probeer het opnieuw.',
    type: 'network',
    canRetry: true,
    canReload: true,
    helpLinks: [
      { text: 'Controleer uw internetverbinding', url: '#', external: false }
    ]
  },
  'TypeError: Failed to fetch': {
    title: 'Kan geen verbinding maken',
    message: 'De server is momenteel niet bereikbaar. Probeer het later opnieuw.',
    type: 'network',
    canRetry: true,
    canReload: true
  },
  
  // Authentication errors
  'Unauthorized': {
    title: 'Toegang geweigerd',
    message: 'U bent niet gemachtigd om deze actie uit te voeren. Log opnieuw in.',
    type: 'permission',
    canGoBack: true,
    helpLinks: [
      { text: 'Inloggen', url: '/login', external: false }
    ]
  },
  
  // Validation errors
  'ValidationError': {
    title: 'Invoerfout',
    message: 'Sommige gegevens zijn niet correct ingevuld. Controleer uw invoer.',
    type: 'validation',
    canGoBack: true
  },
  
  // Server errors
  'InternalServerError': {
    title: 'Serverfout',
    message: 'Er is een fout opgetreden op de server. Ons team is op de hoogte gesteld.',
    type: 'server',
    canRetry: true,
    canGoBack: true,
    helpLinks: [
      { text: 'Status pagina', url: 'https://status.example.com', external: true },
      { text: 'Contact support', url: 'mailto:support@example.com', external: true }
    ]
  },
  
  // File processing errors
  'FileProcessingError': {
    title: 'Bestandsverwerkingsfout',
    message: 'Het bestand kon niet worden verwerkt. Controleer het bestandsformaat en probeer opnieuw.',
    type: 'client',
    canRetry: true,
    helpLinks: [
      { text: 'Ondersteunde bestandsformaten', url: '#', external: false }
    ]
  }
}

const errorData = computed<ErrorData>(() => {
  if (!currentError.value) {
    return {
      title: 'Onbekende fout',
      message: 'Er is een onverwachte fout opgetreden.',
      type: 'unknown',
      canRetry: false,
      canGoBack: true,
      canReload: true
    }
  }

  const error = currentError.value
  const errorType = error.name || 'Unknown'
  const errorMessage = error.message || 'Unknown error'
  
  // Try to match error by name first, then by message
  let matchedError = errorMap[errorType] || errorMap[errorMessage]
  
  // Fallback for HTTP status codes
  if (!matchedError && errorMessage.includes('404')) {
    matchedError = {
      title: 'Pagina niet gevonden',
      message: 'De opgevraagde pagina bestaat niet of is verplaatst.',
      type: 'client',
      canGoBack: true,
      canReload: false
    }
  } else if (!matchedError && errorMessage.includes('500')) {
    matchedError = errorMap['InternalServerError']
  }
  
  // Final fallback
  if (!matchedError) {
    matchedError = {
      title: 'Onverwachte fout',
      message: 'Er is een onverwachte fout opgetreden. Probeer het later opnieuw.',
      type: 'unknown',
      canRetry: true,
      canGoBack: true,
      canReload: true
    }
  }

  return {
    title: matchedError.title!,
    message: matchedError.message!,
    details: props.showDetails ? error.stack || error.message : undefined,
    type: matchedError.type!,
    canRetry: matchedError.canRetry || false,
    canGoBack: matchedError.canGoBack || false,
    canReload: matchedError.canReload || false,
    helpLinks: matchedError.helpLinks || []
  }
})

// Error capture
onErrorCaptured((error: Error) => {
  handleError(error)
  return false // Prevent the error from propagating further
})

const handleError = (error: Error) => {
  currentError.value = error
  hasError.value = true
  
  // Emit error event
  emit('error', error)
  
  // Call custom error handler if provided
  if (props.onError) {
    props.onError(error)
  }
  
  // Log error for monitoring
  console.error('ErrorBoundary caught error:', error)
}

const handleRetry = async () => {
  if (isRetrying.value) return
  
  isRetrying.value = true
  
  try {
    if (props.onRetry) {
      await props.onRetry()
    }
    
    // If retry succeeds, clear the error
    hasError.value = false
    currentError.value = null
    emit('retry')
    
    notificationStore.success(
      'Gelukt!', 
      'De actie is succesvol uitgevoerd.'
    )
  } catch (error) {
    // If retry fails, update the error
    handleError(error as Error)
    
    notificationStore.error(
      'Opnieuw proberen mislukt',
      'Er is nog steeds een probleem. Probeer het later opnieuw.'
    )
  } finally {
    isRetrying.value = false
  }
}

const handleGoBack = () => {
  router.go(-1)
}

const handleReload = () => {
  window.location.reload()
}

const handleDismiss = () => {
  hasError.value = false
  currentError.value = null
  emit('dismiss')
}

// Expose methods for external use
defineExpose({
  handleError,
  clearError: handleDismiss,
  hasError: computed(() => hasError.value)
})
</script>

<style scoped>
.error-boundary {
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-2xl);
  background-color: var(--bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
}

.error-container {
  max-width: 600px;
  width: 100%;
  text-align: center;
}

.error-icon {
  color: var(--error-color);
  margin-bottom: var(--spacing-xl);
  display: flex;
  justify-content: center;
}

.error-content {
  text-align: left;
}

.error-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  margin-bottom: var(--spacing-md);
  text-align: center;
}

.error-description {
  font-size: var(--font-size-lg);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-xl);
  line-height: var(--line-height-relaxed);
  text-align: center;
}

.error-details {
  margin-bottom: var(--spacing-xl);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  background-color: var(--bg-muted);
}

.error-details-toggle {
  padding: var(--spacing-md);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  user-select: none;
}

.error-details-toggle:hover {
  background-color: var(--bg-secondary);
}

.error-stack {
  padding: var(--spacing-md);
  margin: 0;
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  color: var(--text-muted);
  white-space: pre-wrap;
  word-break: break-all;
  background-color: var(--bg-primary);
  border-top: 1px solid var(--border-color);
  overflow-x: auto;
}

.error-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-md);
  justify-content: center;
  margin-bottom: var(--spacing-xl);
}

.error-help {
  padding-top: var(--spacing-xl);
  border-top: 1px solid var(--border-color);
}

.error-help h3 {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--spacing-md);
  text-align: center;
}

.help-links {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  align-items: center;
}

.help-link {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  color: var(--primary-color);
  text-decoration: none;
  font-size: var(--font-size-sm);
  transition: color var(--transition-fast);
}

.help-link:hover {
  color: var(--primary-hover);
  text-decoration: underline;
}

.external-icon {
  opacity: 0.7;
}

/* Responsive adjustments */
@media (max-width: 640px) {
  .error-boundary {
    padding: var(--spacing-lg);
    min-height: 300px;
  }
  
  .error-title {
    font-size: var(--font-size-xl);
  }
  
  .error-description {
    font-size: var(--font-size-base);
  }
  
  .error-actions {
    flex-direction: column;
    align-items: stretch;
  }
  
  .help-links {
    align-items: stretch;
  }
  
  .help-link {
    justify-content: center;
  }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .error-boundary {
    background-color: var(--gray-800);
    border-color: var(--gray-700);
  }
  
  .error-details {
    background-color: var(--gray-700);
    border-color: var(--gray-600);
  }
  
  .error-details-toggle:hover {
    background-color: var(--gray-600);
  }
  
  .error-stack {
    background-color: var(--gray-800);
    border-color: var(--gray-600);
  }
}

/* Animation for error appearance */
.error-boundary {
  animation: error-fade-in 0.3s ease-out;
}

@keyframes error-fade-in {
  from {
    opacity: 0;
    transform: translateY(1rem);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Focus styles for error actions */
.error-details-toggle:focus {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}
</style>