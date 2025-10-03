/**
 * Advanced lazy loading composable with prefetching and error handling
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'

interface LazyLoadOptions {
  threshold?: number
  rootMargin?: string
  once?: boolean
  prefetch?: boolean
  fallback?: string
}

export function useLazyLoad(options: LazyLoadOptions = {}) {
  const {
    threshold = 0.1,
    rootMargin = '50px',
    once = true,
    prefetch = false,
    fallback = ''
  } = options

  const target = ref<HTMLElement | null>(null)
  const isIntersecting = ref(false)
  const isLoaded = ref(false)
  const error = ref<Error | null>(null)
  const observer = ref<IntersectionObserver | null>(null)

  const shouldLoad = computed(() => isIntersecting.value || prefetch)

  const createObserver = () => {
    if (!('IntersectionObserver' in window)) {
      // Fallback for browsers without IntersectionObserver support
      isIntersecting.value = true
      return
    }

    observer.value = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            isIntersecting.value = true
            
            if (once && observer.value) {
              observer.value.disconnect()
            }
          } else {
            if (!once) {
              isIntersecting.value = false
            }
          }
        })
      },
      {
        threshold,
        rootMargin
      }
    )

    if (target.value) {
      observer.value.observe(target.value)
    }
  }

  const observe = (element: HTMLElement) => {
    target.value = element
    createObserver()
  }

  const disconnect = () => {
    if (observer.value) {
      observer.value.disconnect()
      observer.value = null
    }
  }

  onMounted(() => {
    if (target.value) {
      createObserver()
    }
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    target,
    isIntersecting: computed(() => isIntersecting.value),
    isLoaded: computed(() => isLoaded.value),
    shouldLoad,
    error: computed(() => error.value),
    observe,
    disconnect,
    setLoaded: () => { isLoaded.value = true },
    setError: (err: Error) => { error.value = err }
  }
}

/**
 * Lazy load images with progressive enhancement
 */
export function useLazyImage(src: string, options: LazyLoadOptions = {}) {
  const { target, shouldLoad, isLoaded, error, observe, setLoaded, setError } = useLazyLoad(options)
  
  const imageSrc = ref(options.fallback || '')
  const imageAlt = ref('')
  const loading = ref(false)

  const loadImage = async () => {
    if (!src || loading.value || isLoaded.value) return

    loading.value = true

    try {
      const img = new Image()
      
      // Create promise for image loading
      const loadPromise = new Promise<void>((resolve, reject) => {
        img.onload = () => resolve()
        img.onerror = () => reject(new Error('Failed to load image'))
      })

      img.src = src
      
      await loadPromise
      
      imageSrc.value = src
      setLoaded()
    } catch (err) {
      setError(err as Error)
      imageSrc.value = options.fallback || ''
    } finally {
      loading.value = false
    }
  }

  // Load image when it should be loaded
  const unwatchShouldLoad = shouldLoad.value && (() => {
    if (shouldLoad.value) {
      loadImage()
    }
  })

  onUnmounted(() => {
    if (unwatchShouldLoad) {
      unwatchShouldLoad()
    }
  })

  return {
    target,
    imageSrc: computed(() => imageSrc.value),
    imageAlt: computed(() => imageAlt.value),
    loading: computed(() => loading.value),
    isLoaded,
    error,
    observe,
    setAlt: (alt: string) => { imageAlt.value = alt }
  }
}

/**
 * Lazy load components with error boundaries
 */
export function useLazyComponent<T = any>(
  componentLoader: () => Promise<T>,
  options: LazyLoadOptions = {}
) {
  const { shouldLoad, isLoaded, error, setLoaded, setError } = useLazyLoad(options)
  
  const component = ref<T | null>(null)
  const loading = ref(false)

  const loadComponent = async () => {
    if (loading.value || isLoaded.value) return

    loading.value = true

    try {
      const loadedComponent = await componentLoader()
      component.value = loadedComponent
      setLoaded()
    } catch (err) {
      setError(err as Error)
    } finally {
      loading.value = false
    }
  }

  // Load component when it should be loaded
  const unwatchShouldLoad = shouldLoad.value && (() => {
    if (shouldLoad.value) {
      loadComponent()
    }
  })

  onUnmounted(() => {
    if (unwatchShouldLoad) {
      unwatchShouldLoad()
    }
  })

  return {
    component: computed(() => component.value),
    loading: computed(() => loading.value),
    isLoaded,
    error,
    reload: loadComponent
  }
}

/**
 * Prefetch resources when idle
 */
export function usePrefetch() {
  const prefetchQueue = ref<Array<() => Promise<any>>>([])
  const isPrefetching = ref(false)

  const addToPrefetchQueue = (loader: () => Promise<any>) => {
    prefetchQueue.value.push(loader)
    processPrefetchQueue()
  }

  const processPrefetchQueue = async () => {
    if (isPrefetching.value || prefetchQueue.value.length === 0) return

    isPrefetching.value = true

    // Use requestIdleCallback if available, otherwise setTimeout
    const scheduleWork = (callback: () => void) => {
      if ('requestIdleCallback' in window) {
        requestIdleCallback(callback)
      } else {
        setTimeout(callback, 0)
      }
    }

    const processNext = () => {
      if (prefetchQueue.value.length === 0) {
        isPrefetching.value = false
        return
      }

      const loader = prefetchQueue.value.shift()
      if (loader) {
        loader()
          .catch((error) => {
            console.warn('Prefetch failed:', error)
          })
          .finally(() => {
            scheduleWork(processNext)
          })
      }
    }

    scheduleWork(processNext)
  }

  const prefetchRoute = (routeName: string) => {
    addToPrefetchQueue(async () => {
      // This would need to be implemented based on your router setup
      console.log(`Prefetching route: ${routeName}`)
    })
  }

  const prefetchImage = (src: string) => {
    addToPrefetchQueue(async () => {
      const img = new Image()
      return new Promise<void>((resolve, reject) => {
        img.onload = () => resolve()
        img.onerror = () => reject(new Error(`Failed to prefetch image: ${src}`))
        img.src = src
      })
    })
  }

  return {
    prefetchQueue: computed(() => prefetchQueue.value),
    isPrefetching: computed(() => isPrefetching.value),
    addToPrefetchQueue,
    prefetchRoute,
    prefetchImage
  }
}

/**
 * Optimize images for different screen sizes
 */
export function useResponsiveImage(
  baseSrc: string,
  sizes: Record<string, string> = {}
) {
  const defaultSizes = {
    '480w': baseSrc.replace(/\.(jpg|jpeg|png|webp)$/i, '_480w.$1'),
    '768w': baseSrc.replace(/\.(jpg|jpeg|png|webp)$/i, '_768w.$1'),
    '1024w': baseSrc.replace(/\.(jpg|jpeg|png|webp)$/i, '_1024w.$1'),
    '1920w': baseSrc.replace(/\.(jpg|jpeg|png|webp)$/i, '_1920w.$1'),
  }

  const allSizes = { ...defaultSizes, ...sizes }
  
  const srcSet = computed(() => {
    return Object.entries(allSizes)
      .map(([size, src]) => `${src} ${size}`)
      .join(', ')
  })

  const currentSrc = computed(() => {
    const width = window.innerWidth
    
    if (width <= 480) return allSizes['480w'] || baseSrc
    if (width <= 768) return allSizes['768w'] || baseSrc
    if (width <= 1024) return allSizes['1024w'] || baseSrc
    
    return allSizes['1920w'] || baseSrc
  })

  return {
    srcSet,
    currentSrc,
    sizes: computed(() => allSizes)
  }
}

/**
 * Lazy load with intersection observer directive
 */
export const vLazyLoad = {
  mounted(el: HTMLElement, binding: { value: LazyLoadOptions }) {
    const options = binding.value || {}
    const { observe } = useLazyLoad(options)
    observe(el)
  }
}

/**
 * Performance monitoring for lazy loading
 */
export function useLazyLoadPerformance() {
  const metrics = ref({
    totalElements: 0,
    loadedElements: 0,
    failedElements: 0,
    averageLoadTime: 0,
    loadTimes: [] as number[]
  })

  const startLoad = () => {
    metrics.value.totalElements++
    return performance.now()
  }

  const endLoad = (startTime: number, success: boolean = true) => {
    const loadTime = performance.now() - startTime
    metrics.value.loadTimes.push(loadTime)
    
    if (success) {
      metrics.value.loadedElements++
    } else {
      metrics.value.failedElements++
    }

    // Calculate average load time
    metrics.value.averageLoadTime = 
      metrics.value.loadTimes.reduce((a, b) => a + b, 0) / metrics.value.loadTimes.length
  }

  const getReport = () => {
    const { totalElements, loadedElements, failedElements, averageLoadTime } = metrics.value
    
    return {
      total: totalElements,
      loaded: loadedElements,
      failed: failedElements,
      successRate: totalElements > 0 ? (loadedElements / totalElements) * 100 : 0,
      averageLoadTime: Math.round(averageLoadTime),
      performance: averageLoadTime < 100 ? 'excellent' : 
                   averageLoadTime < 300 ? 'good' : 
                   averageLoadTime < 1000 ? 'fair' : 'poor'
    }
  }

  return {
    metrics: computed(() => metrics.value),
    startLoad,
    endLoad,
    getReport
  }
}