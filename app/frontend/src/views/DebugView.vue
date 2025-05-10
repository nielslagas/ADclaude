<template>
  <div class="debug-container">
    <h1>Debug Report Data</h1>
    
    <div v-if="loading" class="loading">
      <p>Report data is loading...</p>
    </div>
    
    <div v-else class="debug-data">
      <h2>Report ID: {{ reportId }}</h2>
      
      <div class="data-section">
        <h3>Current Report Data</h3>
        <pre v-if="reportStore.currentReport">{{ JSON.stringify(reportStore.currentReport, null, 2) }}</pre>
        <p v-else>No current report data</p>
      </div>
      
      <div class="data-section">
        <h3>Report Content Type</h3>
        <pre v-if="reportStore.currentReport && reportStore.currentReport.content">
Type: {{ typeof reportStore.currentReport.content }}
Is Array: {{ Array.isArray(reportStore.currentReport.content) }}
Keys: {{ Object.keys(reportStore.currentReport.content).join(', ') }}
        </pre>
        <p v-else>No content data</p>
      </div>
      
      <div class="data-section">
        <h3>Active Section</h3>
        <p>Current active section: {{ activeSection }}</p>
        <p v-if="activeSection && reportStore.currentReport && reportStore.currentReport.content">
          Content type for this section: {{ typeof reportStore.currentReport.content[activeSection] }}
        </p>
        <pre v-if="activeSection && reportStore.currentReport && reportStore.currentReport.content">
{{ reportStore.currentReport.content[activeSection] }}
        </pre>
      </div>

      <div class="actions">
        <button @click="refreshReport" class="btn">Refresh Report Data</button>
        <div class="section-selector" v-if="reportStore.currentReport && reportStore.currentReport.content">
          <p>Select a section:</p>
          <button 
            v-for="(_, sectionId) in reportStore.currentReport.content" 
            :key="sectionId"
            @click="activeSection = sectionId"
            class="section-btn"
            :class="{ active: activeSection === sectionId }"
          >
            {{ sectionId }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useReportStore } from '@/stores/report';

const route = useRoute();
const reportStore = useReportStore();

const loading = ref(false);
const reportId = ref(route.params.id as string);
const activeSection = ref<string | null>(null);

// Fetch report details
const fetchReport = async () => {
  if (!reportId.value) return;
  
  loading.value = true;
  try {
    const report = await reportStore.fetchReport(reportId.value);
    console.log("Fetched report:", report);
    
    // Set active section to first section if none is selected
    if (
      report.content && 
      Object.keys(report.content).length > 0 && 
      !activeSection.value
    ) {
      activeSection.value = Object.keys(report.content)[0];
    }
  } catch (err) {
    console.error('Error fetching report:', err);
  } finally {
    loading.value = false;
  }
};

const refreshReport = () => {
  fetchReport();
};

onMounted(() => {
  fetchReport();
});
</script>

<style scoped>
.debug-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem;
}

.loading {
  text-align: center;
  padding: 2rem;
  background-color: #f5f5f5;
  border-radius: 4px;
}

.debug-data {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
}

.data-section {
  margin-bottom: 2rem;
  border-bottom: 1px solid #eee;
  padding-bottom: 1rem;
}

pre {
  background-color: #f5f5f5;
  padding: 1rem;
  border-radius: 4px;
  overflow: auto;
  font-family: monospace;
  white-space: pre-wrap;
}

.actions {
  margin-top: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.btn {
  padding: 0.5rem 1rem;
  background-color: #4a90e2;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.section-selector {
  margin-top: 1rem;
}

.section-btn {
  padding: 0.5rem 1rem;
  margin-right: 0.5rem;
  margin-bottom: 0.5rem;
  background-color: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
}

.section-btn.active {
  background-color: #4a90e2;
  color: white;
}
</style>