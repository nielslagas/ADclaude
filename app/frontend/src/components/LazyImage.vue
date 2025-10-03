<template>
  <div 
    ref="containerRef"
    class="lazy-image-container"
    :class="{
      'lazy-image-loading': loading,
      'lazy-image-loaded': isLoaded,
      'lazy-image-error': error
    }"
    :style="containerStyle"
  >
    <!-- Loading placeholder -->
    <div 
      v-if="!isLoaded && !error" 
      class="lazy-image-placeholder"
      :aria-label="loading ? 'Afbeelding wordt geladen' : 'Afbeelding nog niet geladen'"
    >
      <div v-if="loading" class="lazy-image-spinner" aria-hidden="true">
        <svg class="animate-spin" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" opacity="0.25"/>
          <path d="M12 2a10 10 0 0110 10" opacity="0.75"/>
        </svg>
      </div>
      <div v-else class="lazy-image-icon" aria-hidden="true">
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="3" y="3" width="26" height="26" rx="2"/>
          <circle cx="8.5" cy="8.5" r="1.5"/>
          <path d="M21 15l-5-5L5 21"/>
        </svg>
      </div>
    </div>

    <!-- Error state -->
    <div 
      v-if="error" 
      class="lazy-image-error-state"
      role="img"
      :aria-label="`Fout bij laden van afbeelding: ${error.message}`"
    >
      <div class="lazy-image-error-icon" aria-hidden="true">
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="16" cy="16" r="14"/>
          <line x1="16" y1="8" x2="16" y2="16"/>
          <line x1="16" y1="20" x2="16.01" y2="20"/>
        </svg>
      </div>
      <span class="lazy-image-error-text">Kan afbeelding niet laden</span>
      <button 
        v-if="canRetry"
        @click="handleRetry"
        class="lazy-image-retry-btn"
        :disabled="loading"
        aria-label="Probeer afbeelding opnieuw te laden"
      >
        Opnieuw proberen
      </button>
    </div>

    <!-- Actual image -->
    <img
      v-if="imageSrc && !error"
      :src="imageSrc"
      :alt="alt"
      :width="width"
      :height="height"
      :loading="nativeLoading"
      :decoding="decoding"
      :srcset="srcset"
      :sizes="sizes"
      class="lazy-image"
      :class="{ 'lazy-image-fade-in': isLoaded }"
      @load="handleImageLoad"
      @error="handleImageError"
    />

    <!-- Progressive enhancement with WebP support -->
    <picture v-if="webpSrc && imageSrc && !error">
      <source :srcset="webpSrc" type="image/webp">
      <img
        :src="imageSrc"
        :alt="alt"
        :width="width"
        :height="height"
        :loading="nativeLoading"
        :decoding="decoding"
        class="lazy-image"
        :class="{ 'lazy-image-fade-in': isLoaded }"
        @load="handleImageLoad"
        @error="handleImageError"
      />
    </picture>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useLazyLoad, useLazyLoadPerformance } from '@/composables/useLazyLoad'

interface Props {
  src: string
  alt: string
  width?: number | string
  height?: number | string
  aspectRatio?: string
  placeholder?: string
  webpSrc?: string
  srcset?: string
  sizes?: string
  loading?: 'lazy' | 'eager' | 'auto'
  decoding?: 'sync' | 'async' | 'auto'
  threshold?: number
  rootMargin?: string
  canRetry?: boolean
  objectFit?: 'cover' | 'contain' | 'fill' | 'scale-down'
}

const props = withDefaults(defineProps<Props>(), {
  loading: 'lazy',
  decoding: 'async',
  threshold: 0.1,
  rootMargin: '50px',
  canRetry: true,
  objectFit: 'cover'
})

const emit = defineEmits<{
  'load': [event: Event]
  'error': [error: Error]
  'retry': []
}>()

const containerRef = ref<HTMLElement>()
const loadStartTime = ref<number>(0)
const retryCount = ref(0)
const maxRetries = 3

// Performance monitoring
const { startLoad, endLoad } = useLazyLoadPerformance()

// Lazy loading
const {
  target,
  shouldLoad,
  isLoaded,
  error,
  observe,
  setLoaded,
  setError
} = useLazyLoad({
  threshold: props.threshold,
  rootMargin: props.rootMargin,
  once: true,
  prefetch: false
})

const imageSrc = ref('')
const loading = ref(false)

// Native lazy loading support
const nativeLoading = computed(() => {
  // Use native lazy loading if supported and not eager
  if ('loading' in HTMLImageElement.prototype && props.loading !== 'eager') {
    return props.loading
  }
  return undefined
})

// Container styles
const containerStyle = computed(() => {
  const styles: Record<string, string> = {}
  
  if (props.width) {
    styles.width = typeof props.width === 'number' ? `${props.width}px` : props.width
  }
  
  if (props.height) {
    styles.height = typeof props.height === 'number' ? `${props.height}px` : props.height
  }
  
  if (props.aspectRatio) {
    styles.aspectRatio = props.aspectRatio
  }
  
  return styles
})

// Load image when it should be visible
const loadImage = async () => {
  if (!props.src || loading.value || isLoaded.value) return

  loading.value = true
  loadStartTime.value = startLoad()

  try {
    // Create a new image to preload
    const img = new Image()
    
    // Set up the image with all attributes
    if (props.srcset) img.srcset = props.srcset
    if (props.sizes) img.sizes = props.sizes
    
    // Wait for image to load
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve()
      img.onerror = () => reject(new Error('Failed to load image'))
      img.src = props.src
    })

    // Image loaded successfully
    imageSrc.value = props.src
    setLoaded()
    endLoad(loadStartTime.value, true)
    
  } catch (err) {
    const error = err as Error
    setError(error)
    endLoad(loadStartTime.value, false)
    emit('error', error)
  } finally {
    loading.value = false
  }
}

// Handle successful image load
const handleImageLoad = (event: Event) => {
  if (!isLoaded.value) {
    setLoaded()
    endLoad(loadStartTime.value, true)
  }
  emit('load', event)
}

// Handle image load error
const handleImageError = (event: Event) => {
  const error = new Error('Image failed to load')
  setError(error)
  endLoad(loadStartTime.value, false)
  emit('error', error)
}

// Retry loading
const handleRetry = async () => {
  if (retryCount.value >= maxRetries) return

  retryCount.value++
  setError(null)
  imageSrc.value = ''
  
  emit('retry')
  
  // Add a small delay before retrying
  await new Promise(resolve => setTimeout(resolve, 1000))
  
  await loadImage()
}

// Watch for when image should load
watch(shouldLoad, (should) => {
  if (should && !isLoaded.value && !loading.value) {
    loadImage()
  }
})

// Set up intersection observer
onMounted(() => {
  if (containerRef.value) {
    observe(containerRef.value)
  }
})
</script>

<style scoped>
.lazy-image-container {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--bg-muted);
  border-radius: var(--radius);
  overflow: hidden;
  min-height: 120px;
}

.lazy-image {
  width: 100%;
  height: 100%;
  object-fit: v-bind('props.objectFit');
  opacity: 0;
  transition: opacity 0.3s ease-in-out;
}

.lazy-image-fade-in {
  opacity: 1;
}

.lazy-image-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: var(--bg-muted);
  color: var(--text-muted);
}

.lazy-image-spinner {
  animation: spin 1s linear infinite;
  color: var(--primary-color);
  margin-bottom: var(--spacing-sm);
}

.lazy-image-icon {
  color: var(--text-muted);
  margin-bottom: var(--spacing-sm);
}

.lazy-image-error-state {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: var(--error-light);
  color: var(--error-color);
  padding: var(--spacing-md);
  text-align: center;
}

.lazy-image-error-icon {
  margin-bottom: var(--spacing-sm);
}

.lazy-image-error-text {
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-md);
}

.lazy-image-retry-btn {
  background: var(--error-color);
  color: var(--text-inverse);
  border: none;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius);
  font-size: var(--font-size-xs);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.lazy-image-retry-btn:hover:not(:disabled) {
  background: var(--error-dark);
  transform: translateY(-1px);
}

.lazy-image-retry-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.lazy-image-loading {
  /* Loading state styles */
}

.lazy-image-loaded {
  /* Loaded state styles */
}

.lazy-image-error {
  /* Error state styles */
}

/* Animation for spinner */
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Responsive adjustments */
@media (max-width: 640px) {
  .lazy-image-container {
    min-height: 80px;
  }
  
  .lazy-image-error-state {
    padding: var(--spacing-sm);
  }
  
  .lazy-image-error-text {
    font-size: var(--font-size-xs);
  }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .lazy-image-placeholder {
    background-color: var(--gray-700);
    color: var(--gray-400);
  }
  
  .lazy-image-error-state {
    background-color: rgba(239, 68, 68, 0.1);
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  .lazy-image {
    transition: none;
  }
  
  .lazy-image-spinner {
    animation: none;
  }
  
  .lazy-image-retry-btn:hover:not(:disabled) {
    transform: none;
  }
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .lazy-image-container {
    border: 2px solid var(--border-color);
  }
  
  .lazy-image-retry-btn {
    border: 2px solid var(--error-color);
  }
}
</style>