<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useCaseStore } from '@/stores/case';
import { useDocumentStore } from '@/stores/document';
import { useReportStore } from '@/stores/report';
import { useNotificationStore } from '@/stores/notification';
import AudioRecorder from '@/components/audio/AudioRecorder.vue';
import StaticADReportTemplate from '@/components/StaticADReportTemplate.vue';

const route = useRoute();
const router = useRouter();
const caseStore = useCaseStore();
const documentStore = useDocumentStore();
const reportStore = useReportStore();
const notificationStore = useNotificationStore();

// Workflow stages
type WorkflowStage = 'upload' | 'processing' | 'review' | 'complete';
const currentStage = ref<WorkflowStage>('upload');

// Upload state
const selectedFiles = ref<File[]>([]);
const showAudioRecorder = ref(false);
const uploadProgress = ref(0);
const isUploading = ref(false);

// Processing state
const isGenerating = ref(false);
const generationProgress = ref(0);
const generatedReportId = ref<string | null>(null);

// Report data
const reportData = ref<any>(null);
const reportTitle = ref('AD Rapport');

// Get case ID from route
const caseId = computed(() => route.params.id as string);

onMounted(async () => {
  if (caseId.value) {
    await caseStore.fetchCase(caseId.value);
    await caseStore.fetchCaseDocuments(caseId.value);
    
    // Check if there are already documents
    if (caseStore.documents.length > 0) {
      currentStage.value = 'processing';
    }
    
    // Check if there's already a report
    await caseStore.fetchCaseReports(caseId.value);
    if (caseStore.reports.length > 0) {
      const latestReport = caseStore.reports[0];
      generatedReportId.value = latestReport.id;
      await loadReport(latestReport.id);
    }
  }
});

// File selection
const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files) {
    selectedFiles.value = Array.from(target.files);
  }
};

// Upload files
const uploadFiles = async () => {
  if (selectedFiles.value.length === 0) {
    notificationStore.addNotification({
      type: 'warning',
      title: 'Geen bestanden',
      message: 'Selecteer eerst bestanden om te uploaden.'
    });
    return;
  }
  
  isUploading.value = true;
  uploadProgress.value = 0;
  
  try {
    for (let i = 0; i < selectedFiles.value.length; i++) {
      const file = selectedFiles.value[i];
      await documentStore.uploadDocument(caseId.value, file);
      uploadProgress.value = ((i + 1) / selectedFiles.value.length) * 100;
    }
    
    notificationStore.addNotification({
      type: 'success',
      title: 'Upload voltooid',
      message: `${selectedFiles.value.length} bestand(en) succesvol geüpload.`
    });
    
    // Move to processing stage
    currentStage.value = 'processing';
    selectedFiles.value = [];
  } catch (error) {
    console.error('Upload error:', error);
    notificationStore.addNotification({
      type: 'error',
      title: 'Upload mislukt',
      message: 'Er is een fout opgetreden bij het uploaden van de bestanden.'
    });
  } finally {
    isUploading.value = false;
    uploadProgress.value = 0;
  }
};

// Handle audio upload
const handleAudioUpload = async (blob: Blob) => {
  const file = new File([blob], `audio_${Date.now()}.webm`, { type: blob.type });
  
  try {
    await documentStore.uploadDocument(caseId.value, file);
    
    notificationStore.addNotification({
      type: 'success',
      title: 'Audio opgeslagen',
      message: 'Audio opname is succesvol geüpload.'
    });
    
    showAudioRecorder.value = false;
    currentStage.value = 'processing';
  } catch (error) {
    console.error('Audio upload error:', error);
    notificationStore.addNotification({
      type: 'error',
      title: 'Upload mislukt',
      message: 'Er is een fout opgetreden bij het uploaden van de audio.'
    });
  }
};

// Generate AD Report with structured data
const generateReport = async () => {
  isGenerating.value = true;
  generationProgress.value = 0;
  
  try {
    // Create enhanced AD report
    const report = await reportStore.createEnhancedADReport({
      case_id: caseId.value,
      title: reportTitle.value || `AD Rapport - ${new Date().toLocaleDateString('nl-NL')}`,
      template_id: 'enhanced_ad_rapport',
      layout_type: 'standaard'
    });
    
    generatedReportId.value = report.report_id || report.id;
    
    // Poll for completion with longer timeout
    let attempts = 0;
    const maxAttempts = 60; // 5 minutes max (60 * 5 seconds) to allow for LLM processing
    
    while (attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds
      
      const updatedReport = await reportStore.fetchReport(generatedReportId.value);
      generationProgress.value = Math.min(90, (attempts / maxAttempts) * 100);
      
      if (updatedReport.status === 'generated' || updatedReport.status === 'completed') {
        generationProgress.value = 95;
        
        // Generate structured AD data if not already present
        try {
          if (!updatedReport.structured_data && !updatedReport.content?.structured_data) {
            notificationStore.addNotification({
              type: 'info',
              title: 'Structuur genereren',
              message: 'AD rapport structuur wordt gegenereerd...'
            });
            
            await reportStore.generateADStructure(generatedReportId.value);
            await reportStore.fetchReport(generatedReportId.value); // Refresh to get structured data
          }
        } catch (structureError) {
          console.error('Error generating structured data:', structureError);
          // Continue anyway, report is still usable without structured data
        }
        
        generationProgress.value = 100;
        
        // Load the report data
        await loadReport(generatedReportId.value);
        
        notificationStore.addNotification({
          type: 'success',
          title: 'Rapport gereed',
          message: 'Het AD rapport is succesvol gegenereerd.'
        });
        
        currentStage.value = 'review';
        break;
      } else if (updatedReport.status === 'failed' || updatedReport.status === 'error') {
        throw new Error('Rapport generatie mislukt: ' + (updatedReport.error || 'Onbekende fout'));
      }
      
      attempts++;
    }
    
    if (attempts >= maxAttempts) {
      throw new Error('Timeout bij genereren rapport (probeer het later opnieuw)');
    }
  } catch (error) {
    console.error('Generation error:', error);
    console.error('Error details:', {
      message: error.message,
      status: error.response?.status,
      data: error.response?.data,
      generatedReportId: generatedReportId.value
    });
    notificationStore.addNotification({
      type: 'error',
      title: 'Generatie mislukt',
      message: `Er is een fout opgetreden bij het genereren van het rapport: ${error.message || 'Onbekende fout'}`
    });
  } finally {
    isGenerating.value = false;
    generationProgress.value = 0;
  }
};

// Load report data
const loadReport = async (reportId: string) => {
  try {
    const report = await reportStore.fetchReport(reportId);
    
    // Check for structured data
    if (report.content?.structured_data) {
      reportData.value = report.content.structured_data;
    } else {
      // Transform regular content to structured format
      reportData.value = transformToStructuredData(report);
    }
    
    currentStage.value = 'review';
  } catch (error) {
    console.error('Error loading report:', error);
    notificationStore.addNotification({
      type: 'error',
      title: 'Laad fout',
      message: 'Kon rapport niet laden.'
    });
  }
};

// Transform regular report to structured data
const transformToStructuredData = (report: any) => {
  // This is a fallback for reports without structured_data
  return {
    werknemer: {
      naam: '[Uit rapport data]',
      geboortedatum: '[Te bepalen]',
      adres: '[Te bepalen]',
      postcode_plaats: '[Te bepalen]',
      telefoonnummer: '[Te bepalen]',
      email: '[Te bepalen]'
    },
    werkgever: {
      naam: caseStore.currentCase?.title || '[Bedrijf]',
      contactpersoon: '[Te bepalen]',
      functie_contactpersoon: '[Te bepalen]',
      adres: '[Te bepalen]',
      postcode_plaats: '[Te bepalen]',
      telefoonnummer: '[Te bepalen]',
      email: '[Te bepalen]'
    },
    // ... andere secties
  };
};

// Export report
const exportReport = async (format: 'docx' | 'pdf' = 'docx') => {
  if (!generatedReportId.value) return;
  
  try {
    await reportStore.downloadReportAsDocx(generatedReportId.value, 'standaard');
    
    notificationStore.addNotification({
      type: 'success',
      title: 'Export gestart',
      message: `Rapport wordt gedownload als ${format.toUpperCase()}.`
    });
  } catch (error) {
    console.error('Export error:', error);
    notificationStore.addNotification({
      type: 'error',
      title: 'Export mislukt',
      message: 'Er is een fout opgetreden bij het exporteren.'
    });
  }
};

// Reset workflow
const resetWorkflow = () => {
  currentStage.value = 'upload';
  selectedFiles.value = [];
  reportData.value = null;
  generatedReportId.value = null;
};

// Stage progression
const canProceedToNext = computed(() => {
  switch (currentStage.value) {
    case 'upload':
      return caseStore.documents.length > 0;
    case 'processing':
      return !isGenerating.value;
    case 'review':
      return reportData.value !== null;
    default:
      return false;
  }
});
</script>

<template>
  <div class="simple-workflow">
    <!-- Header -->
    <div class="workflow-header">
      <router-link to="/cases" class="back-link">
        ← Terug naar cases
      </router-link>
      <h1>AD Rapport Generator</h1>
    </div>

    <!-- Progress Indicator -->
    <div class="workflow-progress">
      <div class="progress-step" :class="{ active: currentStage === 'upload', complete: ['processing', 'review', 'complete'].includes(currentStage) }">
        <div class="step-number">1</div>
        <div class="step-label">Upload</div>
      </div>
      <div class="progress-line" :class="{ complete: ['processing', 'review', 'complete'].includes(currentStage) }"></div>
      <div class="progress-step" :class="{ active: currentStage === 'processing', complete: ['review', 'complete'].includes(currentStage) }">
        <div class="step-number">2</div>
        <div class="step-label">Genereer</div>
      </div>
      <div class="progress-line" :class="{ complete: ['review', 'complete'].includes(currentStage) }"></div>
      <div class="progress-step" :class="{ active: currentStage === 'review', complete: currentStage === 'complete' }">
        <div class="step-number">3</div>
        <div class="step-label">Bekijk & Export</div>
      </div>
    </div>

    <!-- Stage Content -->
    <div class="workflow-content">
      
      <!-- Stage 1: Upload -->
      <div v-if="currentStage === 'upload'" class="stage-upload">
        <h2>Stap 1: Upload Documenten</h2>
        <p>Upload documenten of neem audio op voor het AD rapport.</p>
        
        <!-- Existing documents -->
        <div v-if="caseStore.documents.length > 0" class="existing-docs">
          <h3>Bestaande documenten ({{ caseStore.documents.length }})</h3>
          <ul class="doc-list">
            <li v-for="doc in caseStore.documents" :key="doc.id">
              📄 {{ doc.filename }}
            </li>
          </ul>
        </div>
        
        <!-- File upload -->
        <div class="upload-section">
          <input
            type="file"
            multiple
            @change="handleFileSelect"
            accept=".pdf,.docx,.doc,.txt"
            class="file-input"
            id="file-upload"
          />
          <label for="file-upload" class="file-label">
            <span class="icon">📁</span>
            Selecteer bestanden
          </label>
          
          <div v-if="selectedFiles.length > 0" class="selected-files">
            <p>Geselecteerde bestanden:</p>
            <ul>
              <li v-for="file in selectedFiles" :key="file.name">
                {{ file.name }} ({{ (file.size / 1024 / 1024).toFixed(2) }} MB)
              </li>
            </ul>
            <button @click="uploadFiles" :disabled="isUploading" class="btn btn-primary">
              {{ isUploading ? 'Uploaden...' : 'Upload bestanden' }}
            </button>
          </div>
          
          <div v-if="uploadProgress > 0" class="progress-bar">
            <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
          </div>
        </div>
        
        <!-- Audio recorder -->
        <div class="audio-section">
          <button @click="showAudioRecorder = !showAudioRecorder" class="btn btn-outline">
            <span class="icon">🎤</span>
            {{ showAudioRecorder ? 'Sluit audio recorder' : 'Open audio recorder' }}
          </button>
          
          <div v-if="showAudioRecorder" class="audio-recorder-wrapper">
            <AudioRecorder @audio-saved="handleAudioUpload" />
          </div>
        </div>
        
        <!-- Next button -->
        <div v-if="caseStore.documents.length > 0" class="stage-actions">
          <button @click="currentStage = 'processing'" class="btn btn-primary btn-large">
            Ga verder naar genereren →
          </button>
        </div>
      </div>
      
      <!-- Stage 2: Processing -->
      <div v-if="currentStage === 'processing'" class="stage-processing">
        <h2>Stap 2: Genereer AD Rapport</h2>
        <p>Het systeem zal nu een volledig AD rapport genereren op basis van de geüploade documenten.</p>
        
        <!-- Documents overview -->
        <div class="docs-overview">
          <h3>Documenten voor verwerking ({{ caseStore.documents.length }})</h3>
          <ul class="doc-list compact">
            <li v-for="doc in caseStore.documents" :key="doc.id">
              ✓ {{ doc.filename }}
            </li>
          </ul>
        </div>
        
        <!-- Report title -->
        <div class="report-config">
          <label>
            Rapport titel:
            <input 
              v-model="reportTitle" 
              type="text" 
              placeholder="AD Rapport"
              class="input-field"
            />
          </label>
        </div>
        
        <!-- Generate button -->
        <div class="stage-actions">
          <button 
            @click="generateReport" 
            :disabled="isGenerating" 
            class="btn btn-primary btn-large"
          >
            <span v-if="!isGenerating">🚀 Start Generatie</span>
            <span v-else>⏳ Genereren... ({{ Math.round(generationProgress) }}%)</span>
          </button>
        </div>
        
        <!-- Progress indicator -->
        <div v-if="isGenerating" class="generation-progress">
          <div class="progress-bar large">
            <div class="progress-fill animated" :style="{ width: generationProgress + '%' }"></div>
          </div>
          <p class="progress-message">Dit kan enkele minuten duren. Even geduld...</p>
        </div>
      </div>
      
      <!-- Stage 3: Review & Export -->
      <div v-if="currentStage === 'review'" class="stage-review">
        <h2>Stap 3: Bekijk & Exporteer</h2>
        
        <!-- Report viewer -->
        <div class="report-viewer">
          <StaticADReportTemplate 
            v-if="reportData"
            :report-data="reportData" 
          />
        </div>
        
        <!-- Export actions -->
        <div class="stage-actions">
          <button @click="exportReport('docx')" class="btn btn-primary btn-large">
            📄 Download als Word
          </button>
          <button @click="exportReport('pdf')" class="btn btn-outline btn-large">
            📑 Download als PDF
          </button>
          <button @click="resetWorkflow" class="btn btn-secondary">
            🔄 Nieuw rapport
          </button>
        </div>
      </div>
      
    </div>
  </div>
</template>

<style scoped>
.simple-workflow {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.workflow-header {
  margin-bottom: 2rem;
}

.back-link {
  color: #2563eb;
  text-decoration: none;
  margin-bottom: 1rem;
  display: inline-block;
}

.workflow-header h1 {
  margin: 0;
  color: #1f2937;
}

/* Progress Indicator */
.workflow-progress {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 3rem;
}

.progress-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #e5e7eb;
  color: #6b7280;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  transition: all 0.3s;
}

.progress-step.active .step-number {
  background: #2563eb;
  color: white;
  transform: scale(1.1);
}

.progress-step.complete .step-number {
  background: #10b981;
  color: white;
}

.step-label {
  font-size: 0.875rem;
  color: #6b7280;
}

.progress-step.active .step-label {
  color: #2563eb;
  font-weight: 600;
}

.progress-line {
  width: 200px;
  height: 2px;
  background: #e5e7eb;
  transition: background 0.3s;
}

.progress-line.complete {
  background: #10b981;
}

/* Content Stages */
.workflow-content {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.stage-upload h2,
.stage-processing h2,
.stage-review h2 {
  color: #1f2937;
  margin-bottom: 1rem;
}

/* Upload Section */
.existing-docs {
  background: #f9fafb;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.doc-list {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0;
}

.doc-list li {
  padding: 0.5rem 0;
  border-bottom: 1px solid #e5e7eb;
}

.doc-list.compact li {
  padding: 0.25rem 0;
}

.upload-section {
  margin: 2rem 0;
}

.file-input {
  display: none;
}

.file-label {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: #f3f4f6;
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.file-label:hover {
  background: #e5e7eb;
  border-color: #9ca3af;
}

.selected-files {
  margin-top: 1rem;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 8px;
}

/* Audio Section */
.audio-section {
  margin: 2rem 0;
}

.audio-recorder-wrapper {
  margin-top: 1rem;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 8px;
}

/* Processing Stage */
.docs-overview {
  background: #f0fdf4;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.report-config {
  margin: 2rem 0;
}

.input-field {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 1rem;
  margin-top: 0.5rem;
}

.generation-progress {
  margin-top: 2rem;
}

.progress-bar {
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar.large {
  height: 12px;
}

.progress-fill {
  height: 100%;
  background: #2563eb;
  transition: width 0.3s;
}

.progress-fill.animated {
  background: linear-gradient(90deg, #2563eb, #3b82f6, #2563eb);
  background-size: 200% 100%;
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.progress-message {
  text-align: center;
  color: #6b7280;
  margin-top: 1rem;
}

/* Review Stage */
.report-viewer {
  margin: 2rem 0;
  max-height: 600px;
  overflow-y: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 2rem;
  background: #fff;
}

/* Actions */
.stage-actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #e5e7eb;
}

/* Buttons */
.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-primary {
  background: #2563eb;
  color: white;
}

.btn-primary:hover {
  background: #1d4ed8;
}

.btn-primary:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.btn-outline {
  background: white;
  color: #2563eb;
  border: 1px solid #2563eb;
}

.btn-outline:hover {
  background: #eff6ff;
}

.btn-secondary {
  background: #6b7280;
  color: white;
}

.btn-secondary:hover {
  background: #4b5563;
}

.btn-large {
  padding: 1rem 2rem;
  font-size: 1.125rem;
}
</style>