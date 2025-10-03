<template>
  <div 
    v-if="showMonitor" 
    class="performance-monitor"
    role="complementary"
    aria-label="Performance monitoring"
  >
    <div class="monitor-header">
      <h3>Performance Monitor</h3>
      <button 
        @click="toggleMonitor"
        class="monitor-toggle"
        :aria-label="isExpanded ? 'Collapse monitor' : 'Expand monitor'"
      >
        <svg 
          class="monitor-icon" 
          :class="{ 'monitor-icon-rotated': isExpanded }"
          width="16" 
          height="16" 
          viewBox="0 0 16 16" 
          fill="currentColor"
        >
          <path d="M8 4l4 4-4 4V4z"/>
        </svg>
      </button>
    </div>

    <Transition name="slide-down">
      <div v-if="isExpanded" class="monitor-content">
        <!-- Core Web Vitals -->
        <div class="monitor-section">
          <h4>Core Web Vitals</h4>
          <div class="metrics-grid">
            <div 
              class="metric-card"
              :class="`metric-${getScoreColor(webVitals.lcp.score)}`"
            >
              <div class="metric-label">LCP</div>
              <div class="metric-value">{{ webVitals.lcp.value }}ms</div>
              <div class="metric-description">Largest Contentful Paint</div>
            </div>

            <div 
              class="metric-card"
              :class="`metric-${getScoreColor(webVitals.fid.score)}`"
            >
              <div class="metric-label">FID</div>
              <div class="metric-value">{{ webVitals.fid.value }}ms</div>
              <div class="metric-description">First Input Delay</div>
            </div>

            <div 
              class="metric-card"
              :class="`metric-${getScoreColor(webVitals.cls.score)}`"
            >
              <div class="metric-label">CLS</div>
              <div class="metric-value">{{ webVitals.cls.value }}</div>
              <div class="metric-description">Cumulative Layout Shift</div>
            </div>
          </div>
        </div>

        <!-- Loading Performance -->
        <div class="monitor-section">
          <h4>Loading Performance</h4>
          <div class="performance-stats">
            <div class="stat-item">
              <span class="stat-label">Page Load:</span>
              <span class="stat-value">{{ loadPerformance.pageLoad }}ms</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">DOM Ready:</span>
              <span class="stat-value">{{ loadPerformance.domReady }}ms</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Resources:</span>
              <span class="stat-value">{{ loadPerformance.resources }}</span>
            </div>
          </div>
        </div>

        <!-- Lazy Loading Stats -->
        <div class="monitor-section" v-if="lazyLoadStats.total > 0">
          <h4>Lazy Loading</h4>
          <div class="performance-stats">
            <div class="stat-item">
              <span class="stat-label">Success Rate:</span>
              <span class="stat-value">{{ lazyLoadStats.successRate.toFixed(1) }}%</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Avg Load Time:</span>
              <span class="stat-value">{{ lazyLoadStats.averageLoadTime }}ms</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Total Elements:</span>
              <span class="stat-value">{{ lazyLoadStats.total }}</span>
            </div>
          </div>
        </div>

        <!-- Memory Usage -->
        <div class="monitor-section" v-if="memoryInfo">
          <h4>Memory Usage</h4>
          <div class="memory-chart">
            <div class="memory-bar">
              <div 
                class="memory-used"
                :style="{ width: `${memoryUsagePercentage}%` }"
              ></div>
            </div>
            <div class="memory-stats">
              <span>{{ formatBytes(memoryInfo.usedJSHeapSize) }} / {{ formatBytes(memoryInfo.totalJSHeapSize) }}</span>
            </div>
          </div>
        </div>

        <!-- Network Information -->
        <div class="monitor-section" v-if="networkInfo">
          <h4>Network</h4>
          <div class="performance-stats">
            <div class="stat-item">
              <span class="stat-label">Connection:</span>
              <span class="stat-value">{{ networkInfo.effectiveType }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Downlink:</span>
              <span class="stat-value">{{ networkInfo.downlink }} Mbps</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">RTT:</span>
              <span class="stat-value">{{ networkInfo.rtt }}ms</span>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="monitor-actions">
          <button @click="collectMetrics" class="monitor-btn monitor-btn-primary">
            Refresh Metrics
          </button>
          <button @click="exportMetrics" class="monitor-btn monitor-btn-secondary">
            Export Data
          </button>
          <button @click="clearMetrics" class="monitor-btn monitor-btn-danger">
            Clear Data
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useLazyLoadPerformance } from '@/composables/useLazyLoad'

interface WebVital {
  value: number
  score: 'good' | 'needs-improvement' | 'poor'
}

interface WebVitals {
  lcp: WebVital
  fid: WebVital
  cls: WebVital
}

const props = withDefaults(defineProps<{
  enabled?: boolean
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left'
}>(), {
  enabled: process.env.NODE_ENV === 'development',
  position: 'bottom-right'
})

const showMonitor = computed(() => props.enabled)
const isExpanded = ref(false)

// Performance metrics
const webVitals = ref<WebVitals>({
  lcp: { value: 0, score: 'good' },
  fid: { value: 0, score: 'good' },
  cls: { value: 0, score: 'good' }
})

const loadPerformance = ref({
  pageLoad: 0,
  domReady: 0,
  resources: 0
})

const memoryInfo = ref<MemoryInfo | null>(null)
const networkInfo = ref<any>(null)

// Lazy loading performance
const { getReport } = useLazyLoadPerformance()
const lazyLoadStats = computed(() => getReport())

// Memory usage percentage
const memoryUsagePercentage = computed(() => {
  if (!memoryInfo.value) return 0
  return (memoryInfo.value.usedJSHeapSize / memoryInfo.value.totalJSHeapSize) * 100
})

// Collect Core Web Vitals
const collectWebVitals = () => {
  // LCP (Largest Contentful Paint)
  if ('PerformanceObserver' in window) {
    const lcpObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries()
      const lastEntry = entries[entries.length - 1] as any
      if (lastEntry) {
        const value = Math.round(lastEntry.startTime)
        webVitals.value.lcp = {
          value,
          score: value <= 2500 ? 'good' : value <= 4000 ? 'needs-improvement' : 'poor'
        }
      }
    })

    try {
      lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] })
    } catch (e) {
      console.warn('LCP observation not supported')
    }

    // FID (First Input Delay)
    const fidObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries()
      entries.forEach((entry: any) => {
        const value = Math.round(entry.processingStart - entry.startTime)
        webVitals.value.fid = {
          value,
          score: value <= 100 ? 'good' : value <= 300 ? 'needs-improvement' : 'poor'
        }
      })
    })

    try {
      fidObserver.observe({ entryTypes: ['first-input'] })
    } catch (e) {
      console.warn('FID observation not supported')
    }

    // CLS (Cumulative Layout Shift)
    let clsValue = 0
    const clsObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries()
      entries.forEach((entry: any) => {
        if (!entry.hadRecentInput) {
          clsValue += entry.value
        }
      })
      
      webVitals.value.cls = {
        value: Math.round(clsValue * 1000) / 1000,
        score: clsValue <= 0.1 ? 'good' : clsValue <= 0.25 ? 'needs-improvement' : 'poor'
      }
    })

    try {
      clsObserver.observe({ entryTypes: ['layout-shift'] })
    } catch (e) {
      console.warn('CLS observation not supported')
    }
  }
}

// Collect load performance
const collectLoadPerformance = () => {
  if ('performance' in window && 'timing' in window.performance) {
    const timing = window.performance.timing
    
    loadPerformance.value = {
      pageLoad: timing.loadEventEnd - timing.navigationStart,
      domReady: timing.domContentLoadedEventEnd - timing.navigationStart,
      resources: window.performance.getEntriesByType('resource').length
    }
  }
}

// Collect memory information
const collectMemoryInfo = () => {
  if ('memory' in window.performance) {
    memoryInfo.value = (window.performance as any).memory
  }
}

// Collect network information
const collectNetworkInfo = () => {
  if ('connection' in navigator) {
    const connection = (navigator as any).connection
    networkInfo.value = {
      effectiveType: connection.effectiveType || 'unknown',
      downlink: connection.downlink || 0,
      rtt: connection.rtt || 0
    }
  }
}

// Collect all metrics
const collectMetrics = () => {
  collectWebVitals()
  collectLoadPerformance()
  collectMemoryInfo()
  collectNetworkInfo()
}

// Toggle monitor
const toggleMonitor = () => {
  isExpanded.value = !isExpanded.value
}

// Get score color
const getScoreColor = (score: string) => {
  switch (score) {
    case 'good': return 'good'
    case 'needs-improvement': return 'warning'
    case 'poor': return 'poor'
    default: return 'good'
  }
}

// Format bytes
const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// Export metrics
const exportMetrics = () => {
  const data = {
    timestamp: new Date().toISOString(),
    webVitals: webVitals.value,
    loadPerformance: loadPerformance.value,
    lazyLoadStats: lazyLoadStats.value,
    memoryInfo: memoryInfo.value,
    networkInfo: networkInfo.value,
    userAgent: navigator.userAgent,
    url: window.location.href
  }

  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `performance-metrics-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

// Clear metrics
const clearMetrics = () => {
  webVitals.value = {
    lcp: { value: 0, score: 'good' },
    fid: { value: 0, score: 'good' },
    cls: { value: 0, score: 'good' }
  }
  loadPerformance.value = {
    pageLoad: 0,
    domReady: 0,
    resources: 0
  }
  memoryInfo.value = null
  networkInfo.value = null
}

// Auto-refresh metrics
let metricsInterval: number | null = null

onMounted(() => {
  if (showMonitor.value) {
    // Initial collection
    setTimeout(collectMetrics, 1000)
    
    // Auto-refresh every 30 seconds
    metricsInterval = window.setInterval(collectMetrics, 30000)
  }
})

onUnmounted(() => {
  if (metricsInterval) {
    clearInterval(metricsInterval)
  }
})
</script>

<style scoped>
.performance-monitor {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  width: 320px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  z-index: 1000;
  font-size: var(--font-size-sm);
}

.monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-muted);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}

.monitor-header h3 {
  margin: 0;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.monitor-toggle {
  background: none;
  border: none;
  padding: var(--spacing-xs);
  cursor: pointer;
  border-radius: var(--radius);
  transition: all var(--transition-fast);
}

.monitor-toggle:hover {
  background: var(--bg-secondary);
}

.monitor-icon {
  transition: transform var(--transition-fast);
}

.monitor-icon-rotated {
  transform: rotate(90deg);
}

.monitor-content {
  max-height: 600px;
  overflow-y: auto;
  padding: 0;
}

.monitor-section {
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
}

.monitor-section:last-child {
  border-bottom: none;
}

.monitor-section h4 {
  margin: 0 0 var(--spacing-sm) 0;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-sm);
}

.metric-card {
  padding: var(--spacing-sm);
  border-radius: var(--radius);
  text-align: center;
  border: 1px solid var(--border-color);
}

.metric-good {
  background: var(--success-light);
  border-color: var(--success-color);
}

.metric-warning {
  background: var(--warning-light);
  border-color: var(--warning-color);
}

.metric-poor {
  background: var(--error-light);
  border-color: var(--error-color);
}

.metric-label {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
}

.metric-value {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  margin: var(--spacing-xs) 0;
}

.metric-description {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  line-height: var(--line-height-tight);
}

.performance-stats {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-label {
  color: var(--text-secondary);
}

.stat-value {
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.memory-chart {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.memory-bar {
  height: 8px;
  background: var(--bg-muted);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.memory-used {
  height: 100%;
  background: linear-gradient(90deg, var(--success-color), var(--warning-color), var(--error-color));
  border-radius: var(--radius-full);
  transition: width var(--transition-normal);
}

.memory-stats {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  text-align: center;
}

.monitor-actions {
  display: flex;
  gap: var(--spacing-xs);
  padding: var(--spacing-md);
  background: var(--bg-muted);
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}

.monitor-btn {
  flex: 1;
  padding: var(--spacing-xs) var(--spacing-sm);
  border: none;
  border-radius: var(--radius);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.monitor-btn-primary {
  background: var(--primary-color);
  color: var(--text-inverse);
}

.monitor-btn-primary:hover {
  background: var(--primary-hover);
}

.monitor-btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.monitor-btn-secondary:hover {
  background: var(--bg-primary);
}

.monitor-btn-danger {
  background: var(--error-color);
  color: var(--text-inverse);
}

.monitor-btn-danger:hover {
  background: var(--error-dark);
}

/* Transitions */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
}

.slide-down-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Position variants */
.performance-monitor[data-position="top-left"] {
  top: 1rem;
  left: 1rem;
  bottom: auto;
  right: auto;
}

.performance-monitor[data-position="top-right"] {
  top: 1rem;
  right: 1rem;
  bottom: auto;
  left: auto;
}

.performance-monitor[data-position="bottom-left"] {
  bottom: 1rem;
  left: 1rem;
  top: auto;
  right: auto;
}

/* Mobile responsiveness */
@media (max-width: 640px) {
  .performance-monitor {
    width: calc(100vw - 2rem);
    left: 1rem;
    right: 1rem;
  }
  
  .metrics-grid {
    grid-template-columns: 1fr;
  }
  
  .monitor-actions {
    flex-direction: column;
  }
}

/* Dark mode */
@media (prefers-color-scheme: dark) {
  .performance-monitor {
    background: var(--gray-800);
    border-color: var(--gray-700);
  }
  
  .monitor-header {
    background: var(--gray-700);
    border-color: var(--gray-600);
  }
  
  .monitor-section {
    border-color: var(--gray-700);
  }
  
  .monitor-actions {
    background: var(--gray-700);
  }
}
</style>