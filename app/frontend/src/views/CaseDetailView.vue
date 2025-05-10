<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useCaseStore } from '@/stores/case';
import { useDocumentStore } from '@/stores/document';
import { useReportStore } from '@/stores/report';
import type { Document, Report } from '@/types';

const route = useRoute();
const router = useRouter();
const caseStore = useCaseStore();
const documentStore = useDocumentStore();
const reportStore = useReportStore();

const loading = ref(false);
const error = ref<string | null>(null);
const activeTab = ref('documents');
const showUploadForm = ref(false);
const showCreateReportForm = ref(false);
const uploadProgress = ref(0);
const selectedFile = ref<File | null>(null);
const reportTitle = ref('');
const selectedTemplate = ref('');
const templates = ref<Record<string, any>>({});
const refreshTimer = ref<number | null>(null);

// Fetch case and related data
const fetchCaseData = async () => {
  const caseId = route.params.id as string;
  if (!caseId) return;
  
  loading.value = true;
  error.value = null;
  
  try {
    console.log(`Starting to fetch case data for ID: ${caseId}`);
    
    // Fetch case details
    try {
      await caseStore.fetchCase(caseId);
      console.log("Case details fetched successfully", caseStore.currentCase);
    } catch (caseErr) {
      console.error("Error fetching case details:", caseErr);
      throw caseErr;
    }
    
    // Fetch documents
    try {
      await caseStore.fetchCaseDocuments(caseId);
      console.log("Documents fetched successfully", caseStore.documents);
    } catch (docErr) {
      console.error("Error fetching documents:", docErr);
      // Continue even if documents fetch fails
    }
    
    // Fetch reports
    try {
      await caseStore.fetchCaseReports(caseId);
      console.log("Reports fetched successfully", caseStore.reports);
    } catch (reportErr) {
      console.error("Error fetching reports:", reportErr);
      // Continue even if reports fetch fails
    }
    
    // Fetch report templates
    try {
      await reportStore.fetchReportTemplates();
      templates.value = reportStore.templates;
      console.log("Templates fetched successfully", templates.value);
      
      // Check if templates are empty (might happen if the API returned an empty object)
      if (Object.keys(templates.value).length === 0) {
        throw new Error("No templates found in API response");
      }
    } catch (templateErr) {
      console.error("Error fetching templates:", templateErr);
      console.error("Template error details:", JSON.stringify(templateErr, null, 2));
      
      // Since the app currently supports only the Staatvandienst template,
      // and fetching the templates might fail due to auth issues,
      // we'll provide a default template
      templates.value = {
        "staatvandienst": {
          "id": "staatvandienst",
          "name": "Staatvandienst Format",
          "description": "Standard format for Staatvandienst",
          "sections": {
            "samenvatting": {
              "title": "Samenvatting",
              "description": "Korte samenvatting van het rapport"
            },
            "belastbaarheid": {
              "title": "Belastbaarheid",
              "description": "Analyse van de belastbaarheid van de cliënt"
            },
            "visie_ad": {
              "title": "Visie Arbeidsdeskundige",
              "description": "Professionele visie van de arbeidsdeskundige"
            },
            "matching": {
              "title": "Matching Overwegingen",
              "description": "Overwegingen voor matching naar passend werk"
            }
          }
        }
      };
      console.log("Using default template:", templates.value);
      
      // Don't throw an error here, just log it and continue
      // This prevents the error from propagating up to the main try/catch
    }
    
  } catch (err: any) {
    console.error("Main error in fetchCaseData:", err);
    
    // Add more detailed error logging to help with debugging
    if (err.response) {
      console.error("Error response details:", {
        status: err.response.status,
        statusText: err.response.statusText,
        data: err.response.data,
        headers: err.response.headers
      });
      
      error.value = `Er is een fout opgetreden bij het ophalen van casegegevens. Status: ${err.response.status}, Foutmelding: ${err.response.data?.detail || err.message}`;
    } else if (err.request) {
      // Request was made but no response received
      console.error("No response received:", err.request);
      error.value = `Er is een fout opgetreden bij het ophalen van casegegevens: Geen antwoord van de server`;
    } else {
      // Something happened in setting up the request
      console.error("Error message:", err.message);
      error.value = `Er is een fout opgetreden bij het ophalen van casegegevens: ${err.message || 'Onbekende fout'}`;
    }
    
    // Log the complete error stack for debugging
    console.error("Complete error object:", err);
    if (err.stack) {
      console.error("Error stack:", err.stack);
    }
  } finally {
    loading.value = false;
  }
};

// Start auto-refresh for report status
const startAutoRefresh = () => {
  // Clear existing timer
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value);
  }
  
  // Refresh data every 2 seconds
  refreshTimer.value = window.setInterval(async () => {
    const caseId = route.params.id as string;
    if (caseId) {
      try {
        console.log("Auto-refreshing case data...");
        
        // Refresh based on active tab
        if (activeTab.value === 'reports') {
          // Refresh reports data
          await caseStore.fetchCaseReports(caseId);
          console.log("Reports refreshed:", caseStore.reports);
          
          // Check if all reports are in final state
          const allDone = caseStore.reports.every(
            r => r.status !== 'processing' && r.status !== 'generating'
          );
          
          // Stop refreshing if all reports are done
          if (allDone) {
            console.log("All reports processed, stopping auto-refresh");
            stopAutoRefresh();
          }
        } else if (activeTab.value === 'documents') {
          // Refresh documents data
          await caseStore.fetchCaseDocuments(caseId);
          console.log("Documents refreshed:", caseStore.documents);
          
          // Check if all documents are in final state (processed, enhanced or failed)
          const allDone = caseStore.documents.every(
            d => d.status !== 'processing'
          );
          
          // Stop refreshing if all documents are done
          if (allDone) {
            console.log("All documents processed, stopping auto-refresh");
            stopAutoRefresh();
          }
        }
      } catch (err) {
        console.error("Error auto-refreshing:", err);
      }
    }
  }, 2000) as unknown as number;
};

// Stop auto-refresh
const stopAutoRefresh = () => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value);
    refreshTimer.value = null;
  }
};

// Watch for tab changes to start/stop refresh
watch(activeTab, (newTab) => {
  if (newTab === 'reports' || newTab === 'documents') {
    // Start auto-refresh when switching to reports or documents tab
    startAutoRefresh();
  } else {
    // Stop auto-refresh when not on reports or documents tab
    stopAutoRefresh();
  }
});

// Initialize component
onMounted(() => {
  fetchCaseData();
  
  // Start auto-refresh if starting on reports or documents tab
  if (activeTab.value === 'reports' || activeTab.value === 'documents') {
    startAutoRefresh();
  }
});

// Clean up on unmount
onUnmounted(() => {
  stopAutoRefresh();
});

// Re-fetch when route changes
watch(() => route.params.id, fetchCaseData);

// Handle document upload
const handleFileSelect = (event: Event) => {
  const input = event.target as HTMLInputElement;
  if (input.files && input.files.length > 0) {
    selectedFile.value = input.files[0];
  }
};

const uploadDocument = async () => {
  if (!selectedFile.value) {
    error.value = 'Selecteer een bestand om te uploaden';
    return;
  }
  
  const caseId = route.params.id as string;
  
  try {
    // Match the expected interface in the store
    await documentStore.uploadDocument({
      case_id: caseId,
      file: selectedFile.value
    });
    
    // Refresh documents list
    await caseStore.fetchCaseDocuments(caseId);
    
    // Reset form
    showUploadForm.value = false;
    selectedFile.value = null;
    uploadProgress.value = 0;
    
    // Start auto-refresh to track document processing
    startAutoRefresh();
  } catch (err) {
    error.value = 'Er is een fout opgetreden bij het uploaden van het document.';
    console.error(err);
  }
};

// Handle report creation
const createReport = async () => {
  if (!reportTitle.value.trim()) {
    error.value = 'Rapporttitel is verplicht';
    return;
  }
  
  if (!selectedTemplate.value) {
    error.value = 'Selecteer een template voor het rapport';
    return;
  }
  
  const caseId = route.params.id as string;
  
  try {
    await reportStore.createReport({
      title: reportTitle.value,
      case_id: caseId,
      template_id: selectedTemplate.value
    });
    
    // Refresh reports list
    await caseStore.fetchCaseReports(caseId);
    
    // Reset form
    showCreateReportForm.value = false;
    reportTitle.value = '';
    selectedTemplate.value = '';
    
    // Start auto-refresh to monitor report status
    startAutoRefresh();
    
    // Make sure reports tab is active to show the new report
    activeTab.value = 'reports';
  } catch (err) {
    error.value = 'Er is een fout opgetreden bij het aanmaken van het rapport.';
    console.error(err);
  }
};

// Handle navigation to document detail
const viewDocument = (documentId: string) => {
  router.push(`/documents/${documentId}`);
};

// Handle navigation to report detail
const viewReport = (reportId: string) => {
  router.push(`/reports/${reportId}`);
};

// Format date for display
const formatDate = (dateString: string) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('nl-NL', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// Get status class for styling
const getStatusClass = (status: string) => {
  const statusMap: Record<string, string> = {
    'processing': 'status-processing',
    'processed': 'status-success',
    'enhanced': 'status-success',  // Added 'enhanced' status for documents with embeddings
    'failed': 'status-error',
    'generated': 'status-success',
    'generating': 'status-processing'
  };
  
  return statusMap[status] || 'status-default';
};

// Delete the case
const deleteCase = async () => {
  if (!confirm('Weet je zeker dat je deze case wilt verwijderen?')) {
    return;
  }
  
  const caseId = route.params.id as string;
  
  try {
    await caseStore.deleteCase(caseId);
    router.push('/cases');
  } catch (err) {
    error.value = 'Er is een fout opgetreden bij het verwijderen van de case.';
    console.error(err);
  }
};
</script>

<template>
  <div class="case-detail-container">
    <div v-if="loading && !caseStore.currentCase" class="loading">
      <p>Case wordt geladen...</p>
    </div>

    <div v-else-if="!caseStore.currentCase" class="error-state">
      <h2>Case niet gevonden</h2>
      <p>De opgevraagde case bestaat niet of je hebt geen toegang.</p>
      <button @click="router.push('/cases')" class="btn btn-primary">Terug naar Cases</button>
    </div>

    <div v-else class="case-content">
      <!-- Case Header -->
      <div class="case-header">
        <div class="case-title-section">
          <h1>{{ caseStore.currentCase.title }}</h1>
          <span class="case-status" :class="caseStore.currentCase.status">
            {{ caseStore.currentCase.status }}
          </span>
        </div>
        
        <div class="case-actions">
          <!-- Navigation and destructive actions -->
          <div class="action-group">
            <button @click="router.push('/cases')" class="btn btn-outline">
              <span class="icon">🔙</span> Terug naar Cases
            </button>
            <button @click="deleteCase" class="btn btn-danger">
              <span class="icon">🗑️</span> Verwijderen
            </button>
          </div>
        </div>
      </div>
      
      <div v-if="caseStore.currentCase.description" class="case-description">
        <p>{{ caseStore.currentCase.description }}</p>
      </div>
      
      <div class="case-meta">
        <span>Aangemaakt op: {{ formatDate(caseStore.currentCase.created_at) }}</span>
        <span v-if="caseStore.currentCase.updated_at">
          Laatst bijgewerkt: {{ formatDate(caseStore.currentCase.updated_at) }}
        </span>
      </div>

      <!-- Alert for errors -->
      <div v-if="error" class="alert alert-danger">
        {{ error }}
        <button @click="error = null" class="close-btn">&times;</button>
      </div>

      <!-- Tabs Navigation -->
      <div class="tabs">
        <button 
          @click="activeTab = 'documents'" 
          class="tab-btn" 
          :class="{ active: activeTab === 'documents' }"
        >
          Documenten ({{ caseStore.documents.length }})
        </button>
        <button 
          @click="activeTab = 'reports'" 
          class="tab-btn" 
          :class="{ active: activeTab === 'reports' }"
        >
          Rapporten ({{ caseStore.reports.length }})
        </button>
      </div>

      <!-- Documents Tab -->
      <div v-if="activeTab === 'documents'" class="tab-content">
        <div class="tab-header">
          <h2>Documenten</h2>
          <button 
            @click="showUploadForm = !showUploadForm" 
            class="btn btn-primary"
            :class="{ 'btn-secondary': showUploadForm }"
          >
            {{ showUploadForm ? 'Annuleren' : 'Document Uploaden' }}
          </button>
        </div>

        <!-- Document Upload Form -->
        <div v-if="showUploadForm" class="upload-form">
          <h3>Document Uploaden</h3>
          <div class="form-group">
            <label for="document">Selecteer een bestand (.docx of .txt)</label>
            <input 
              type="file" 
              id="document" 
              @change="handleFileSelect" 
              accept=".docx,.txt"
              class="form-control"
            />
            <small>Maximum bestandsgrootte: 10MB</small>
          </div>
          
          <div v-if="uploadProgress > 0" class="progress-container">
            <div class="progress-bar" :style="{ width: `${uploadProgress}%` }"></div>
            <span>{{ uploadProgress }}%</span>
          </div>
          
          <div class="form-actions">
            <button 
              @click="uploadDocument" 
              class="btn btn-primary" 
              :disabled="!selectedFile"
            >
              Uploaden
            </button>
            <button @click="showUploadForm = false" class="btn btn-secondary">
              Annuleren
            </button>
          </div>
        </div>

        <!-- Documents List -->
        <div v-if="caseStore.documents.length === 0" class="empty-state">
          <p>Geen documenten gevonden voor deze case.</p>
          <button @click="showUploadForm = true" class="btn btn-primary">
            Document Toevoegen
          </button>
        </div>

        <div v-else class="documents-list">
          <div 
            v-for="doc in caseStore.documents" 
            :key="doc.id" 
            class="document-item"
            @click="viewDocument(doc.id)"
          >
            <div class="document-info">
              <div class="document-name">{{ doc.filename }}</div>
              <div class="document-meta">
                <span>{{ (doc.size / 1024).toFixed(1) }} KB</span>
                <span>{{ formatDate(doc.created_at) }}</span>
              </div>
            </div>
            <div class="document-status">
              <span :class="getStatusClass(doc.status)">{{ doc.status }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Reports Tab -->
      <div v-if="activeTab === 'reports'" class="tab-content">
        <div class="tab-header">
          <h2>Rapporten</h2>
          <button 
            @click="showCreateReportForm = !showCreateReportForm" 
            class="btn btn-primary"
            :class="{ 'btn-secondary': showCreateReportForm }"
            :disabled="caseStore.documents.length === 0"
          >
            {{ showCreateReportForm ? 'Annuleren' : 'Nieuw Rapport' }}
          </button>
        </div>
        
        <div v-if="caseStore.documents.length === 0" class="alert alert-info">
          Upload eerst documenten voordat je een rapport kunt genereren.
        </div>

        <!-- Create Report Form -->
        <div v-if="showCreateReportForm" class="create-form">
          <h3>Nieuw Rapport Aanmaken</h3>
          <div class="form-group">
            <label for="report-title">Titel *</label>
            <input 
              type="text" 
              id="report-title" 
              v-model="reportTitle" 
              placeholder="Voer een titel in"
              required
              class="form-control"
            />
          </div>
          
          <div class="form-group">
            <label for="report-template">Template *</label>
            <select 
              id="report-template" 
              v-model="selectedTemplate" 
              required
              class="form-control"
            >
              <option value="" disabled>Selecteer een template</option>
              <option 
                v-for="(template, id) in templates" 
                :key="id" 
                :value="id"
              >
                {{ template.name }}
              </option>
            </select>
          </div>
          
          <div v-if="selectedTemplate && templates[selectedTemplate]" class="template-info">
            <h4>Template: {{ templates[selectedTemplate].name }}</h4>
            <p>{{ templates[selectedTemplate].description }}</p>
            <div class="template-sections">
              <h5>Secties:</h5>
              <ul>
                <li v-for="(section, id) in templates[selectedTemplate].sections" :key="id">
                  {{ section.title }} - {{ section.description }}
                </li>
              </ul>
            </div>
          </div>
          
          <div class="form-actions">
            <button 
              @click="createReport" 
              class="btn btn-primary" 
              :disabled="!reportTitle || !selectedTemplate"
            >
              Rapport Genereren
            </button>
            <button @click="showCreateReportForm = false" class="btn btn-secondary">
              Annuleren
            </button>
          </div>
        </div>

        <!-- Reports List -->
        <div v-if="caseStore.reports.length === 0" class="empty-state">
          <p>Geen rapporten gevonden voor deze case.</p>
          <button 
            @click="showCreateReportForm = true" 
            class="btn btn-primary"
            :disabled="caseStore.documents.length === 0"
          >
            Rapport Aanmaken
          </button>
        </div>

        <div v-else class="reports-list">
          <div 
            v-for="report in caseStore.reports" 
            :key="report.id" 
            class="report-item"
            @click="viewReport(report.id)"
          >
            <div class="report-info">
              <div class="report-title">{{ report.title }}</div>
              <div class="report-meta">
                <span>Template: {{ report.template_id }}</span>
                <span>{{ formatDate(report.created_at) }}</span>
              </div>
            </div>
            <div class="report-status">
              <span :class="getStatusClass(report.status)">{{ report.status }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.case-detail-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem;
}

.loading, .error-state {
  text-align: center;
  padding: 3rem 1rem;
  background-color: #f8f9fa;
  border-radius: 8px;
  margin-top: 2rem;
}

.error-state h2 {
  color: #dc2626;
  margin-bottom: 1rem;
}

.case-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.case-title-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.case-title-section h1 {
  margin: 0;
  color: var(--primary-color);
  font-size: 1.75rem;
}

.case-status {
  font-size: 0.75rem;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-weight: 500;
}

.case-status.active {
  background-color: #dcfce7;
  color: #16a34a;
}

.case-status.archived {
  background-color: #f3f4f6;
  color: #6b7280;
}

.case-status.deleted {
  background-color: #fee2e2;
  color: #dc2626;
}

.case-actions {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.action-group {
  display: flex;
  gap: 0.75rem;
}

.case-description {
  background-color: #f8f9fa;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1.5rem;
}

.case-description p {
  margin: 0;
  color: var(--text-color);
  line-height: 1.6;
}

.case-meta {
  display: flex;
  gap: 1.5rem;
  color: var(--text-light);
  font-size: 0.85rem;
  margin-bottom: 2rem;
}

.alert {
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1.5rem;
  position: relative;
}

.alert-danger {
  background-color: #fde8e8;
  color: #ef4444;
  border: 1px solid #f87171;
}

.alert-info {
  background-color: #eff6ff;
  color: #3b82f6;
  border: 1px solid #93c5fd;
  margin-top: 1rem;
}

.close-btn {
  position: absolute;
  right: 1rem;
  top: 1rem;
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  color: inherit;
}

.tabs {
  display: flex;
  border-bottom: 2px solid #e5e7eb;
  margin-bottom: 1.5rem;
}

.tab-btn {
  padding: 0.75rem 1.5rem;
  background: none;
  border: none;
  font-size: 1rem;
  font-weight: 500;
  color: var(--text-light);
  cursor: pointer;
  position: relative;
}

.tab-btn.active {
  color: var(--primary-color);
}

.tab-btn.active::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 100%;
  height: 2px;
  background-color: var(--primary-color);
}

.tab-content {
  margin-bottom: 2rem;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.tab-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: var(--text-color);
}

.upload-form, .create-form {
  background-color: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  box-shadow: var(--shadow);
}

.upload-form h3, .create-form h3 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  font-size: 1.25rem;
  color: var(--primary-color);
}

.form-group {
  margin-bottom: 1.25rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-group small {
  display: block;
  margin-top: 0.25rem;
  color: var(--text-light);
  font-size: 0.8rem;
}

.form-control {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 1rem;
}

.form-control:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(var(--primary-color-rgb), 0.2);
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

.progress-container {
  height: 20px;
  width: 100%;
  background-color: #e5e7eb;
  border-radius: 4px;
  margin: 1rem 0;
  position: relative;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background-color: #3b82f6;
  transition: width 0.3s ease;
}

.progress-container span {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 500;
  text-shadow: 0 0 2px rgba(0, 0, 0, 0.5);
}

.empty-state {
  text-align: center;
  padding: 3rem 1rem;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.empty-state p {
  margin-bottom: 1.5rem;
  color: var(--text-light);
}

.documents-list, .reports-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.document-item, .report-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background-color: white;
  border-radius: 8px;
  box-shadow: var(--shadow);
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.document-item:hover, .report-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 15px -3px rgba(0, 0, 0, 0.1);
}

.document-info, .report-info {
  flex: 1;
}

.document-name, .report-title {
  font-weight: 500;
  color: var(--primary-color);
  margin-bottom: 0.5rem;
}

.document-meta, .report-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.8rem;
  color: var(--text-light);
}

.document-status, .report-status {
  padding-left: 1rem;
}

.status-processing {
  color: #f59e0b;
  font-weight: 500;
}

.status-success {
  color: #10b981;
  font-weight: 500;
}

.status-error {
  color: #ef4444;
  font-weight: 500;
}

.status-default {
  color: #6b7280;
  font-weight: 500;
}

.template-info {
  margin-top: 1.5rem;
  padding: 1rem;
  background-color: #f3f4f6;
  border-radius: 4px;
}

.template-info h4 {
  margin-top: 0;
  margin-bottom: 0.75rem;
  color: var(--primary-color);
  font-size: 1.1rem;
}

.template-info p {
  margin-bottom: 1rem;
  color: var(--text-color);
}

.template-sections h5 {
  margin-bottom: 0.5rem;
  font-size: 0.95rem;
}

.template-sections ul {
  margin: 0;
  padding-left: 1.5rem;
}

.template-sections li {
  margin-bottom: 0.5rem;
  color: var(--text-color);
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: background-color 0.2s;
}

.btn-primary {
  background-color: #3b82f6;
  color: white;
}

.btn-primary:hover {
  background-color: #2563eb;
}

.btn-primary:disabled {
  background-color: #93c5fd;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: #e5e7eb;
  color: #4b5563;
}

.btn-secondary:hover {
  background-color: #d1d5db;
}

.btn-outline {
  background-color: transparent;
  border: 1px solid #e5e7eb;
  color: #4b5563;
}

.btn-outline:hover {
  background-color: #f3f4f6;
}

.icon {
  margin-right: 0.25rem;
  font-size: 0.9rem;
}

.btn-danger {
  background-color: #ef4444;
  color: white;
}

.btn-danger:hover {
  background-color: #dc2626;
}

@media (max-width: 768px) {
  .case-header, .tab-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .case-actions {
    width: 100%;
    flex-direction: column;
    gap: 1rem;
  }

  .action-group {
    width: 100%;
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .form-actions {
    flex-direction: column;
    width: 100%;
  }
  
  .btn {
    width: 100%;
  }
  
  .document-item, .report-item {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .document-info, .report-info {
    width: 100%;
    margin-bottom: 0.75rem;
  }
  
  .document-status, .report-status {
    padding-left: 0;
    width: 100%;
    text-align: right;
  }
}
</style>