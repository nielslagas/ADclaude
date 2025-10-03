<script setup lang="ts">
// Document processing status component
// Used to display the processing status of a document
import SkeletonLoader from '@/components/SkeletonLoader.vue';

const props = defineProps({
  status: {
    type: String,
    required: true
  },
  document: {
    type: Object,
    required: true
  },
  progress: {
    type: Number,
    default: 0
  },
  statusMessage: {
    type: String,
    default: ''
  },
  processingStrategy: {
    type: String,
    default: ''
  },
  processingStats: {
    type: Object,
    default: null
  },
  isHybridMode: {
    type: Boolean,
    default: false
  }
});

// Get status label in Dutch
const getStatusLabel = (status: string) => {
  const statusMap: Record<string, string> = {
    'processing': 'Verwerken',
    'processed': 'Verwerkt',
    'enhanced': 'Verwerkt met AI',
    'generating': 'Genereren',
    'generated': 'Gegenereerd',
    'failed': 'Mislukt'
  };

  return statusMap[status] || status;
};

// Get strategy label in Dutch
const getStrategyLabel = (strategy: string) => {
  const strategyMap: Record<string, string> = {
    'direct_llm': 'Directe AI-verwerking',
    'hybrid': 'Hybride verwerking',
    'full_rag': 'Volledige vector-zoek verwerking'
  };

  return strategyMap[strategy] || strategy;
};

// Format processing stats in Dutch
const formatStats = () => {
  if (!props.processingStats) return '';

  const { total_chunks, direct_llm, hybrid, full_rag } = props.processingStats;

  return `
    ${total_chunks || 0} tekstfragmenten verwerkt:
    ${direct_llm || 0} direct via AI,
    ${hybrid || 0} hybride,
    ${full_rag || 0} via volledige vectorzoek
  `;
};
</script>

<template>
  <div 
    class="processing-status-container" 
    role="status" 
    :aria-label="`Document verwerking: ${getStatusLabel(status)}`"
  >
    <!-- Processing state -->
    <div v-if="status === 'processing'" class="processing-status">
      <div class="spinner" aria-hidden="true"></div>
      <div class="status-content">
        <div class="status-title">Document wordt verwerkt...</div>
        <div class="status-description">
          Dit kan enkele minuten duren afhankelijk van de grootte van het document.
        </div>
        <div v-if="progress > 0" class="progress-container">
          <div 
            class="progress-bar" 
            :style="{ width: `${progress}%` }"
            role="progressbar"
            :aria-valuenow="Math.round(progress)"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-label="`Voortgang: ${Math.round(progress)}%`"
          ></div>
          <div class="progress-text" aria-hidden="true">{{ Math.round(progress) }}%</div>
        </div>
      </div>
    </div>

    <!-- Processed/Enhanced state -->
    <div v-else-if="status === 'processed' || status === 'enhanced'" class="success-status">
      <div class="success-icon">✓</div>
      <div class="status-content">
        <div class="status-title">Document succesvol verwerkt</div>
        <div v-if="isHybridMode" class="status-description">
          Verwerkt met {{ getStrategyLabel(processingStrategy) }}
          <div v-if="processingStats" class="processing-stats">
            {{ formatStats() }}
          </div>
        </div>
      </div>
    </div>

    <!-- Failed state -->
    <div v-else-if="status === 'failed'" class="error-status">
      <div class="error-icon">!</div>
      <div class="status-content">
        <div class="status-title">Verwerking mislukt</div>
        <div v-if="statusMessage" class="status-description">
          {{ statusMessage }}
        </div>
        <div v-else class="status-description">
          Er is een fout opgetreden bij het verwerken van dit document.
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.processing-status-container {
  margin-bottom: 2rem;
}

.processing-status,
.success-status,
.error-status {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.5rem;
  border-radius: 8px;
}

.processing-status {
  background-color: #eff6ff;
  border: 1px solid #dbeafe;
}

.success-status {
  background-color: #ecfdf5;
  border: 1px solid #d1fae5;
}

.error-status {
  background-color: #fef2f2;
  border: 1px solid #fee2e2;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #dbeafe;
  border-radius: 50%;
  border-top-color: #3b82f6;
  animation: spin 1s linear infinite;
  flex-shrink: 0;
}

.success-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background-color: #10b981;
  color: white;
  border-radius: 50%;
  font-weight: bold;
  flex-shrink: 0;
}

.error-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background-color: #ef4444;
  color: white;
  border-radius: 50%;
  font-weight: bold;
  flex-shrink: 0;
}

.status-content {
  flex: 1;
}

.status-title {
  font-weight: 600;
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
}

.processing-status .status-title {
  color: #3b82f6;
}

.success-status .status-title {
  color: #10b981;
}

.error-status .status-title {
  color: #ef4444;
}

.status-description {
  color: #4b5563;
  margin-bottom: 0.5rem;
}

.progress-container {
  height: 8px;
  width: 100%;
  background-color: #dbeafe;
  border-radius: 4px;
  margin: 0.75rem 0;
  position: relative;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background-color: #3b82f6;
  border-radius: 4px;
  transition: width 0.6s ease;
}

.progress-text {
  position: absolute;
  top: -20px;
  right: 0;
  font-size: 0.8rem;
  color: #6b7280;
}

.processing-stats {
  margin-top: 0.5rem;
  font-size: 0.9rem;
  color: #6b7280;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>