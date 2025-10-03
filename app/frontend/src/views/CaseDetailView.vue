<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useCaseStore } from '@/stores/case';
import { useDocumentStore } from '@/stores/document';
import { useReportStore } from '@/stores/report';
import type { Document, Report } from '@/types';
import AudioRecorder from '@/components/audio/AudioRecorder.vue';
import OptimizedADReportButton from '@/components/OptimizedADReportButton.vue';

const route = useRoute();
const router = useRouter();
const caseStore = useCaseStore();
const documentStore = useDocumentStore();
const reportStore = useReportStore();

const loading = ref(false);
const error = ref<string | null>(null);
const activeTab = ref('documents');
const showUploadForm = ref(false);
const showAudioRecorder = ref(false);
const showCreateReportForm = ref(false);
const uploadProgress = ref(0);
const selectedFiles = ref<File[]>([]);
const reportTitle = ref('');
const selectedTemplate = ref('staatvandienst');
const useStructuredOutput = ref(false);
const templates = ref<Record<string, any>>({});
const isDragOver = ref(false);
const refreshTimer = ref<number | null>(null);
const successMessage = ref<string | null>(null);
const successTimer = ref<number | null>(null);

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
    selectedFiles.value = Array.from(input.files);
  }
};

const removeFile = (index: number) => {
  selectedFiles.value.splice(index, 1);
};

// Drag & Drop handlers
const handleDragOver = (event: DragEvent) => {
  event.preventDefault();
  isDragOver.value = true;
};

const handleDragLeave = (event: DragEvent) => {
  event.preventDefault();
  // Only set to false if we're leaving the drop zone itself
  if (!event.relatedTarget || !(event.target as Element).contains(event.relatedTarget as Node)) {
    isDragOver.value = false;
  }
};

const handleDrop = (event: DragEvent) => {
  event.preventDefault();
  isDragOver.value = false;
  
  if (event.dataTransfer?.files) {
    const droppedFiles = Array.from(event.dataTransfer.files);

    // Filter for accepted file types
    const validFiles = droppedFiles.filter(file => {
      const extension = file.name.toLowerCase().split('.').pop();
      const allowedExtensions = ['txt', 'docx', 'doc', 'pdf', 'jpg', 'jpeg', 'png', 'tif', 'tiff'];
      return allowedExtensions.includes(extension);
    });

    if (validFiles.length !== droppedFiles.length) {
      error.value = `Ondersteunde formaten: .docx, .txt, .pdf, .jpg, .png, .tiff. ${droppedFiles.length - validFiles.length} bestand(en) genegeerd.`;
      setTimeout(() => error.value = null, 5000);
    }
    
    // Add to existing selected files (remove duplicates)
    const existingNames = selectedFiles.value.map(f => f.name);
    const newFiles = validFiles.filter(f => !existingNames.includes(f.name));
    selectedFiles.value = [...selectedFiles.value, ...newFiles];
  }
};

const uploadDocument = async () => {
  if (!selectedFiles.value.length) {
    error.value = 'Selecteer één of meer bestanden om te uploaden';
    return;
  }

  const caseId = route.params.id as string;
  const totalFiles = selectedFiles.value.length;
  let uploadedFiles = 0;

  try {
    loading.value = true;
    error.value = null;

    // Upload each file
    for (const file of selectedFiles.value) {
      console.log('Uploading file:', file.name, 'Size:', file.size, 'Type:', file.type);

      await documentStore.uploadDocument({
        case_id: caseId,
        file: file
      });
      uploadedFiles++;
      uploadProgress.value = Math.round((uploadedFiles / totalFiles) * 100);
    }
    
    // Show success message
    successMessage.value = `${totalFiles} bestand${totalFiles > 1 ? 'en' : ''} succesvol geüpload!`;
    if (successTimer.value) clearTimeout(successTimer.value);
    successTimer.value = setTimeout(() => {
      successMessage.value = null;
      successTimer.value = null;
    }, 5000);
    
    // Refresh documents list
    await caseStore.fetchCaseDocuments(caseId);
    
    // Reset form
    showUploadForm.value = false;
    selectedFiles.value = [];
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
  
  // Always use Enhanced AD template - old workflow is deprecated
  selectedTemplate.value = 'enhanced_ad_rapport';
  
  const caseId = route.params.id as string;
  
  try {
    console.log("Creating Enhanced AD report with data:", {
      title: reportTitle.value,
      case_id: caseId,
      template_id: 'enhanced_ad_rapport',
      layout_type: "standaard"
    });
    
    // Use Enhanced AD report creation
    await reportStore.createEnhancedADReport({
      title: reportTitle.value,
      case_id: caseId,
      template_id: 'enhanced_ad_rapport',
      layout_type: "standaard"
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

// Handle enhanced AD report creation
const createEnhancedADReport = async () => {
  const caseId = route.params.id as string;
  
  // Check if there are processed documents
  if (caseStore.documents.length === 0) {
    error.value = 'Upload en verwerk eerst documenten voordat je een rapport kunt genereren';
    return;
  }
  
  const processedDocs = caseStore.documents.filter(doc => doc.status === 'processed');
  if (processedDocs.length === 0) {
    error.value = 'Er zijn geen verwerkte documenten beschikbaar. Wacht tot documentverwerking is voltooid.';
    return;
  }
  
  try {
    const reportTitle = `Arbeidsdeskundig Rapport - ${new Date().toLocaleDateString('nl-NL')}`;
    
    console.log("Creating report...");
    const result = await reportStore.createEnhancedADReport({
      title: reportTitle,
      case_id: caseId,
      template_id: "enhanced_ad_rapport",
      layout_type: "standaard"
    });
    
    // Show success message
    successMessage.value = `Rapport generatie gestart! Het rapport wordt nu gegenereerd.`;
    
    // Auto-hide success message after 8 seconds
    if (successTimer.value) {
      clearTimeout(successTimer.value);
    }
    successTimer.value = setTimeout(() => {
      successMessage.value = null;
    }, 8000);
    
    // Refresh reports list
    await caseStore.fetchCaseReports(caseId);
    
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

// Show success message and auto-hide after 5 seconds
const showSuccessMessage = (message: string) => {
  // Clear existing timer if there is one
  if (successTimer.value) {
    clearTimeout(successTimer.value);
  }

  // Show the message
  successMessage.value = message;

  // Hide the message after 5 seconds
  successTimer.value = window.setTimeout(() => {
    successMessage.value = null;
  }, 5000);
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

// Get document type icon and label
const getDocumentTypeInfo = (doc: any) => {
  const typeMap: Record<string, { icon: string, label: string }> = {
    'text': { icon: 'fa-file-alt', label: 'Tekst' },
    'docx': { icon: 'fa-file-word', label: 'Word' },
    'audio': { icon: 'fa-microphone', label: 'Audio' },
    'pdf': { icon: 'fa-file-pdf', label: 'PDF' }
  };

  // Determine the type based on document_type, mimetype, or filename extension
  let type = 'text'; // Default

  if (doc.document_type) {
    type = doc.document_type;
  } else if (doc.mimetype) {
    if (doc.mimetype.includes('audio')) {
      type = 'audio';
    } else if (doc.mimetype.includes('pdf')) {
      type = 'pdf';
    } else if (doc.mimetype.includes('word') || doc.mimetype.includes('docx')) {
      type = 'docx';
    }
  } else if (doc.filename) {
    const ext = doc.filename.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') {
      type = 'pdf';
    } else if (['docx', 'doc'].includes(ext)) {
      type = 'docx';
    } else if (['mp3', 'wav', 'ogg', 'webm', 'm4a'].includes(ext)) {
      type = 'audio';
    }
  }

  return typeMap[type] || { icon: 'fa-file', label: 'Document' };
};

// Handle audio recording being saved
const onRecordingSaved = (document: any) => {
  console.log("Recording saved, document:", document);

  // Add the recording to the documents list, if it's not already there
  if (!caseStore.documents.some(doc => doc.id === document.id)) {
    caseStore.documents.unshift(document);
  }

  // Close the audio recorder form
  showAudioRecorder.value = false;

  // Show success message
  showSuccessMessage('Audio opname succesvol opgeslagen met mock transcriptie.');

  // No need to start auto-refresh for mock documents as they are already in "processed" state
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

// Delete a specific report
const deleteReport = async (reportId: string, reportTitle: string) => {
  if (!confirm(`Weet je zeker dat je het rapport "${reportTitle}" wilt verwijderen?`)) {
    return;
  }

  try {
    await reportStore.deleteReport(reportId);
    // Refresh the reports list for this case
    const caseId = route.params.id as string;
    await caseStore.fetchCaseReports(caseId);
    showSuccessMessage('Rapport succesvol verwijderd.');
  } catch (err) {
    error.value = 'Er is een fout opgetreden bij het verwijderen van het rapport.';
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
          <div class="tab-actions">
            <button
              @click="showAudioRecorder = !showAudioRecorder; showUploadForm = false"
              class="btn action-btn"
              :class="{ 'btn-secondary': showAudioRecorder, 'btn-primary': !showAudioRecorder }"
            >
              <i class="fas fa-microphone"></i>
              {{ showAudioRecorder ? 'Annuleren' : 'Audio Opnemen' }}
            </button>
            <button
              @click="showUploadForm = !showUploadForm; showAudioRecorder = false"
              class="btn action-btn"
              :class="{ 'btn-secondary': showUploadForm, 'btn-primary': !showUploadForm }"
            >
              <i class="fas fa-file-upload"></i>
              {{ showUploadForm ? 'Annuleren' : 'Document Uploaden' }}
            </button>
          </div>
        </div>

        <!-- Document Upload Form -->
        <div v-if="showUploadForm" class="upload-form">
          <h3>Document Uploaden</h3>
          
          <!-- Drag & Drop Zone -->
          <div 
            class="drop-zone"
            :class="{ 'drag-over': isDragOver }"
            @dragover="handleDragOver"
            @dragleave="handleDragLeave"
            @drop="handleDrop"
          >
            <div class="drop-zone-content">
              <i class="fas fa-cloud-upload-alt drop-icon"></i>
              <p class="drop-text">
                Sleep bestanden hiernaartoe of 
                <label for="document" class="file-link">klik om te selecteren</label>
              </p>
              <small class="drop-hint">Ondersteunde formaten: .docx, .txt, .pdf, .jpg, .png, .tiff (max 10MB per bestand)</small>
            </div>

            <input
              type="file"
              id="document"
              @change="handleFileSelect"
              accept=".docx,.doc,.txt,.pdf,.jpg,.jpeg,.png,.tif,.tiff"
              multiple
              class="file-input-hidden"
            />
          </div>

          <!-- Selected files preview -->
          <div v-if="selectedFiles.length > 0" class="selected-files">
            <h4>Geselecteerde bestanden ({{ selectedFiles.length }}):</h4>
            <ul>
              <li v-for="(file, index) in selectedFiles" :key="index">
                {{ file.name }} ({{ Math.round(file.size / 1024) }} KB)
                <button @click="removeFile(index)" class="btn-remove">×</button>
              </li>
            </ul>
          </div>

          <div v-if="uploadProgress > 0" class="progress-container">
            <div class="progress-bar" :style="{ width: `${uploadProgress}%` }"></div>
            <span>{{ uploadProgress }}%</span>
          </div>

          <div class="form-actions">
            <button
              @click="uploadDocument"
              class="btn btn-primary"
              :disabled="!selectedFiles.length"
            >
              {{ selectedFiles.length > 1 ? `${selectedFiles.length} Bestanden` : '' }} Uploaden
            </button>
            <button @click="showUploadForm = false" class="btn btn-secondary">
              Annuleren
            </button>
          </div>
        </div>

        <!-- Audio Recorder Form -->
        <div v-if="showAudioRecorder" class="audio-form">
          <h3>Audio Opnemen</h3>
          <AudioRecorder
            :case-id="route.params.id as string"
            @recording-saved="onRecordingSaved"
          />
          <div class="form-actions">
            <button @click="showAudioRecorder = false" class="btn btn-secondary">
              Annuleren
            </button>
          </div>
        </div>

        <!-- Documents List -->
        <div v-if="caseStore.documents.length === 0" class="empty-state">
          <p>Geen documenten gevonden voor deze case.</p>
          <div class="empty-state-actions">
            <button @click="showUploadForm = true; showAudioRecorder = false" class="btn btn-primary">
              <i class="fas fa-file-upload"></i> Document Uploaden
            </button>
            <button @click="showAudioRecorder = true; showUploadForm = false" class="btn btn-primary">
              <i class="fas fa-microphone"></i> Audio Opnemen
            </button>
          </div>
        </div>

        <div v-else class="documents-list">
          <div
            v-for="doc in caseStore.documents"
            :key="doc.id"
            class="document-item"
            @click="viewDocument(doc.id)"
          >
            <div class="document-info">
              <div class="document-icon">
                <i class="fas" :class="getDocumentTypeInfo(doc).icon"></i>
              </div>
              <div class="document-details">
                <div class="document-name">{{ doc.filename || doc.title }}</div>
                <div class="document-meta">
                  <span class="document-type">{{ getDocumentTypeInfo(doc).label }}</span>
                  <span v-if="doc.size">{{ (doc.size / 1024).toFixed(1) }} KB</span>
                  <span>{{ formatDate(doc.created_at) }}</span>
                </div>
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
        </div>
        
        <!-- Single Report Generation Button -->
        <div class="report-generation-section">
          <button 
            @click="createEnhancedADReport" 
            class="btn btn-primary btn-large generate-report-btn"
            :disabled="loading || caseStore.documents.length === 0"
            title="Genereer een professioneel arbeidsdeskundig rapport"
          >
            <span class="icon">📋</span>
            <span>Genereer Rapport</span>
          </button>
          <p v-if="caseStore.documents.length === 0" class="warning-text">
            Upload eerst documenten voordat u een rapport kunt genereren.
          </p>
        </div>
        
        <!-- Legacy report form (removed) -->
        <div v-if="false" class="create-form">
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
          
          <!-- Template automatisch Enhanced AD - selectie niet meer nodig -->
          <div class="form-info">
            <div class="info-badge">
              <i class="fas fa-check-circle"></i>
              <span>Enhanced AD Rapport Template</span>
            </div>
            <p class="info-text">
              Alle rapporten worden gegenereerd met het professionele Enhanced AD template 
              met complete structuur en geoptimaliseerde content.
            </p>
          </div>
          
          <!-- Template info niet meer nodig - altijd Enhanced AD -->
          
          <div class="form-actions">
            <button 
              @click="createReport" 
              class="btn btn-primary" 
              :disabled="!reportTitle"
            >
              Enhanced AD Rapport Genereren
            </button>
            <button @click="showCreateReportForm = false" class="btn btn-secondary">
              Annuleren
            </button>
          </div>
        </div>

        <!-- Removed OptimizedADReportButton - replaced with simple workflow -->

        <!-- Reports List -->
        <div v-if="caseStore.reports.length === 0" class="empty-state">
          <p>Geen rapporten gevonden voor deze case.</p>
          
          <!-- Single Report Generation Button -->
          <div class="report-actions">
            <button 
              @click="createEnhancedADReport" 
              class="btn btn-primary btn-large generate-report-btn"
              :disabled="caseStore.documents.length === 0"
              title="Genereer een professioneel arbeidsdeskundig rapport"
            >
              <span class="icon">📋</span>
              <span>Genereer Rapport</span>
            </button>
          </div>
        </div>

        <div v-else class="reports-list">
          <div 
            v-for="report in caseStore.reports" 
            :key="report.id" 
            class="report-item"
          >
            <div class="report-info" @click="viewReport(report.id)">
              <div class="report-title">{{ report.title }}</div>
              <div class="report-meta">
                <span>Template: {{ report.template_id }}</span>
                <span>{{ formatDate(report.created_at) }}</span>
              </div>
            </div>
            <div class="report-status">
              <span :class="getStatusClass(report.status)">{{ report.status }}</span>
            </div>
            <div class="report-actions">
              <button 
                @click.stop="deleteReport(report.id, report.title)"
                class="btn btn-danger-outline btn-sm"
                title="Verwijder dit rapport"
              >
                <span class="icon">🗑️</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- Success message popup -->
    <div v-if="successMessage" class="success-notification">
      <i class="fas fa-check-circle"></i>
      {{ successMessage }}
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

.tab-actions {
  display: flex;
  gap: 0.5rem;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.upload-form, .create-form, .audio-form {
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

.empty-state-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
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
  transition: transform 0.2s, box-shadow 0.2s;
}

.document-item {
  cursor: pointer;
}

.report-item .report-info {
  cursor: pointer;
}

.document-item:hover, .report-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 15px -3px rgba(0, 0, 0, 0.1);
}

.document-info, .report-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.document-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background-color: #e5e7eb;
  border-radius: 8px;
  color: #4b5563;
  font-size: 1.2rem;
}

.document-icon .fa-microphone {
  color: #3b82f6;
}

.document-icon .fa-file-word {
  color: #2563eb;
}

.document-icon .fa-file-pdf {
  color: #dc2626;
}

.document-icon .fa-file-alt {
  color: #4b5563;
}

.document-details {
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
  flex-wrap: wrap;
}

.document-type {
  background-color: #e5e7eb;
  padding: 0.1rem 0.5rem;
  border-radius: 4px;
  font-weight: 500;
}

.document-status, .report-status {
  padding-left: 1rem;
}

.report-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.report-actions .btn {
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
}

.btn-danger-outline {
  background-color: transparent;
  border: 1px solid #dc3545;
  color: #dc3545;
}

.btn-danger-outline:hover {
  background-color: #dc3545;
  color: white;
}

.btn-sm {
  padding: 0.375rem 0.5rem;
  font-size: 0.75rem;
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

.success-notification {
  position: fixed;
  bottom: 20px;
  right: 20px;
  background-color: #d1e7dd;
  color: #0f5132;
  padding: 12px 20px;
  border-radius: 6px;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  animation: slideIn 0.3s ease-out;
  display: flex;
  align-items: center;
  gap: 10px;
}

.success-notification i {
  font-size: 1.2rem;
}

/* Enhanced AD Template Info Styles */
.form-info {
  margin: 1rem 0;
  padding: 1rem;
  background: linear-gradient(135deg, #e0f2fe 0%, #f3e5f5 100%);
  border-radius: 8px;
  border-left: 4px solid #1976d2;
}

.info-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.info-badge i {
  color: #1976d2;
  font-size: 1.1rem;
}

.info-badge span {
  font-weight: 600;
  color: #1976d2;
  font-size: 1rem;
}

.info-text {
  color: #666;
  font-size: 0.9rem;
  line-height: 1.4;
  margin: 0;
}

@keyframes slideIn {
  from {
    transform: translateY(100px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
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

  .tab-actions, .empty-state-actions {
    width: 100%;
    flex-direction: column;
    gap: 0.5rem;
    margin-top: 1rem;
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

/* Checkbox styling for structured output */
.checkbox-group {
  margin: 1rem 0;
}

.checkbox-label {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.95rem;
}

.checkbox-input {
  margin: 0;
  width: 18px;
  height: 18px;
  accent-color: #2563eb;
  flex-shrink: 0;
  margin-top: 2px;
}

.checkbox-text {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.help-text {
  font-size: 0.8rem;
  color: #6b7280;
  line-height: 1.3;
  margin-top: 2px;
}

/* AD Workflow Section */
.ad-workflow-section {
  padding: 2rem 0;
}

.workflow-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 3rem;
  border-radius: 16px;
  text-align: center;
  box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
  max-width: 500px;
  margin: 0 auto;
}

.workflow-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.workflow-card h3 {
  font-size: 1.75rem;
  margin-bottom: 1rem;
  font-weight: 600;
}

.workflow-card p {
  font-size: 1.125rem;
  margin-bottom: 2rem;
  opacity: 0.95;
}

.btn-large {
  padding: 1rem 2.5rem;
  font-size: 1.125rem;
  font-weight: 600;
  background: white;
  color: #667eea;
  border: none;
  border-radius: 8px;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn-large:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
}

.btn-large .icon {
  font-size: 1.25rem;
}

/* Single Report Generation Button Styling */
.generate-report-btn {
  background: linear-gradient(135deg, #1e40af, #2563eb);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1rem 2rem;
  border-radius: 8px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  font-weight: 600;
  font-size: 1.1rem;
  text-align: center;
  transition: all 0.2s ease-in-out;
  border: none;
  cursor: pointer;
  min-width: 200px;
}

.generate-report-btn:hover {
  background: linear-gradient(135deg, #1d4ed8, #3b82f6);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  transform: translateY(-1px);
}

.generate-report-btn:disabled {
  background: #93c5fd;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.generate-report-btn .icon {
  font-size: 1.2rem;
}

.report-generation-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  margin: 2rem 0;
  padding: 2rem;
  background: #f9fafb;
  border-radius: 12px;
}

.report-generation-section .warning-text {
  color: #dc2626;
  font-size: 0.9rem;
  margin-top: 0.5rem;
}

.report-actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: center;
  margin-top: 1.5rem;
}

@media (min-width: 768px) {
  .report-actions {
    flex-direction: row;
    justify-content: center;
  }
  
  .btn-enhanced-ad {
    min-width: 200px;
  }
}

/* Drag & Drop Zone Styling */
.drop-zone {
  border: 2px dashed #cbd5e0;
  border-radius: 12px;
  padding: 2rem;
  text-align: center;
  background-color: #f7fafc;
  transition: all 0.3s ease;
  cursor: pointer;
  position: relative;
  margin-bottom: 1.5rem;
}

.drop-zone:hover {
  border-color: #4299e1;
  background-color: #ebf8ff;
}

.drop-zone.drag-over {
  border-color: #3182ce;
  background-color: #bee3f8;
  transform: scale(1.02);
}

.drop-zone-content {
  pointer-events: none;
}

.drop-icon {
  font-size: 3rem;
  color: #a0aec0;
  margin-bottom: 1rem;
  transition: color 0.3s ease;
}

.drop-zone:hover .drop-icon,
.drop-zone.drag-over .drop-icon {
  color: #4299e1;
}

.drop-text {
  font-size: 1.1rem;
  color: #4a5568;
  margin-bottom: 0.5rem;
}

.file-link {
  color: #3182ce;
  text-decoration: underline;
  cursor: pointer;
  font-weight: 600;
}

.file-link:hover {
  color: #2c5282;
}

.drop-hint {
  color: #718096;
  font-size: 0.9rem;
}

.file-input-hidden {
  position: absolute;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
  top: 0;
  left: 0;
}

/* Multiple file upload styling */
.selected-files {
  margin: 1rem 0;
  padding: 1rem;
  background-color: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.selected-files h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.95rem;
  color: #374151;
}

.selected-files ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.selected-files li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid #e5e7eb;
  font-size: 0.9rem;
}

.selected-files li:last-child {
  border-bottom: none;
}

.btn-remove {
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
  line-height: 1;
  transition: background-color 0.2s;
}

.btn-remove:hover {
  background-color: #dc2626;
}

/* Mobile responsive drag & drop */
@media (max-width: 768px) {
  .drop-zone {
    padding: 1.5rem 1rem;
  }
  
  .drop-icon {
    font-size: 2.5rem;
  }
  
  .drop-text {
    font-size: 1rem;
  }
  
  .selected-files {
    padding: 0.75rem;
  }
  
  .selected-files li {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.75rem 0;
  }
  
  .btn-remove {
    align-self: flex-end;
    margin-top: 0.25rem;
  }
}
</style>