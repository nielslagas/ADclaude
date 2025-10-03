<script setup lang="ts">
// Hybrid RAG Architecture Visualizer
// Displays a visualization of the different RAG processing strategies

const props = defineProps({
  activeSize: {
    type: String,
    default: 'medium', // small, medium, large
    validator: (value: string) => ['small', 'medium', 'large'].includes(value)
  },
  showSearchFlow: {
    type: Boolean,
    default: false
  },
  searchDistribution: {
    type: Object,
    default: () => ({ direct: 33, hybrid: 33, full: 34 })
  },
  totalResults: {
    type: Number,
    default: 0
  },
  avgSimilarity: {
    type: Number,
    default: 0
  }
});
</script>

<template>
  <div class="visualizer-container">
    <h3>Hybride AI Verwerking Architectuur</h3>
    
    <div class="architecture-diagram">
      <div class="diagram-section">
        <div class="processing-type" :class="{ active: activeSize === 'small' }">
          <div class="type-title">Direct AI</div>
          <div class="type-icon direct"></div>
          <div class="type-description">Kleine documenten worden direct verwerkt door de AI zonder vector-zoek.</div>
        </div>
        
        <div class="processing-type" :class="{ active: activeSize === 'medium' }">
          <div class="type-title">Hybride</div>
          <div class="type-icon hybrid"></div>
          <div class="type-description">Middelgrote documenten gebruiken een combinatie van AI en vector-zoek.</div>
        </div>
        
        <div class="processing-type" :class="{ active: activeSize === 'large' }">
          <div class="type-title">Volledige RAG</div>
          <div class="type-icon full"></div>
          <div class="type-description">Grote documenten gebruiken volledig vector-zoek om relevante stukken te vinden.</div>
        </div>
      </div>
      
      <div v-if="showSearchFlow" class="search-flow">
        <h4>Verwerking Verdeling</h4>
        
        <div class="distribution-bar">
          <div class="distribution-segment direct" 
               :style="{ width: `${searchDistribution.direct}%` }" 
               :title="`Direct: ${searchDistribution.direct}%`">
            {{ searchDistribution.direct > 10 ? `${searchDistribution.direct}%` : '' }}
          </div>
          <div class="distribution-segment hybrid" 
               :style="{ width: `${searchDistribution.hybrid}%` }"
               :title="`Hybride: ${searchDistribution.hybrid}%`">
            {{ searchDistribution.hybrid > 10 ? `${searchDistribution.hybrid}%` : '' }}
          </div>
          <div class="distribution-segment full" 
               :style="{ width: `${searchDistribution.full}%` }"
               :title="`Volledig: ${searchDistribution.full}%`">
            {{ searchDistribution.full > 10 ? `${searchDistribution.full}%` : '' }}
          </div>
        </div>
        
        <div class="search-stats">
          <div class="stat-item">
            <div class="stat-label">Totaal aantal fragmenten:</div>
            <div class="stat-value">{{ totalResults }}</div>
          </div>
          <div v-if="avgSimilarity" class="stat-item">
            <div class="stat-label">Gemiddelde relevantie:</div>
            <div class="stat-value">{{ (avgSimilarity * 100).toFixed(0) }}%</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.visualizer-container {
  background-color: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: var(--shadow, 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06));
  margin-bottom: 2rem;
}

.visualizer-container h3 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: var(--primary-color, #3b82f6);
  font-size: 1.25rem;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 0.75rem;
}

.architecture-diagram {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.diagram-section {
  display: flex;
  gap: 1.5rem;
  justify-content: space-between;
}

.processing-type {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 1rem;
  border-radius: 8px;
  border: 2px solid transparent;
  transition: all 0.3s ease;
}

.processing-type.active {
  border-color: #3b82f6;
  background-color: #f0f7ff;
}

.type-title {
  font-weight: 600;
  margin-bottom: 1rem;
  color: #1f2937;
  font-size: 1.1rem;
}

.type-icon {
  width: 70px;
  height: 70px;
  border-radius: 50%;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 2rem;
  position: relative;
}

.type-icon::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 40px;
  height: 40px;
  background-position: center;
  background-repeat: no-repeat;
  background-size: contain;
}

.type-icon.direct {
  background-color: #60a5fa;
}

.type-icon.direct::after {
  content: 'AI';
  font-weight: bold;
  font-size: 22px;
}

.type-icon.hybrid {
  background-color: #7c3aed;
}

.type-icon.hybrid::after {
  content: '⚙️';
  font-size: 26px;
}

.type-icon.full {
  background-color: #2563eb;
}

.type-icon.full::after {
  content: '🔍';
  font-size: 24px;
}

.type-description {
  color: #4b5563;
  font-size: 0.9rem;
  line-height: 1.4;
}

.search-flow {
  margin-top: 1rem;
  border-top: 1px solid #e5e7eb;
  padding-top: 1.5rem;
}

.search-flow h4 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #1f2937;
  font-size: 1rem;
}

.distribution-bar {
  height: 30px;
  display: flex;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 1rem;
}

.distribution-segment {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 0.8rem;
  font-weight: 600;
  transition: width 0.5s ease;
}

.distribution-segment.direct {
  background-color: #60a5fa;
}

.distribution-segment.hybrid {
  background-color: #7c3aed;
}

.distribution-segment.full {
  background-color: #2563eb;
}

.search-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
  margin-top: 1rem;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.stat-label {
  color: #4b5563;
  font-size: 0.9rem;
}

.stat-value {
  font-weight: 600;
  color: #1f2937;
}

@media (max-width: 768px) {
  .diagram-section {
    flex-direction: column;
  }
  
  .processing-type {
    margin-bottom: 1rem;
  }
}
</style>