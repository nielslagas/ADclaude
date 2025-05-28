<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useReportStore } from '@/stores/report';
import { useCaseStore } from '@/stores/case';
import { useNotificationStore } from '@/stores/notification';
import { marked } from 'marked'; // Dit moet geïnstalleerd worden via npm install marked
import CommentSystem from '@/components/CommentSystem.vue';

const route = useRoute();
const router = useRouter();
const reportStore = useReportStore();
const caseStore = useCaseStore();
const notificationStore = useNotificationStore();

const loading = ref(false);
const processingStatusTimer = ref<number | null>(null);
const reportId = ref(route.params.id as string);
const activeSection = ref<string | null>(null);
const regeneratingSection = ref<string | null>(null);
const toggleMarkdown = ref(false);
const showSourcesDialog = ref(false);
const loadingSources = ref(false);
const sources = ref<any[]>([]);
const showPreviewDialog = ref(false);
const downloadingReport = ref(false);
const isLoadingInitial = ref(true);

// Computed properties
const isReportGenerating = computed(() => {
  return reportStore.currentReport?.status === 'processing' || 
         reportStore.currentReport?.status === 'generating';
});

const isReportComplete = computed(() => {
  return reportStore.currentReport?.status === 'generated';
});

const isReportFailed = computed(() => {
  return reportStore.currentReport?.status === 'failed';
});

const reportSections = computed(() => {
  if (!reportStore.currentReport?.content) return [];
  return Object.keys(reportStore.currentReport.content);
});

const hasReportContent = computed(() => {
  return reportSections.value.length > 0;
});

const currentSectionContent = computed(() => {
  if (!activeSection.value || !reportStore.currentReport?.content) return '';
  return reportStore.currentReport.content[activeSection.value] || '';
});

const statusIndicator = computed(() => {
  const status = reportStore.currentReport?.status;
  switch (status) {
    case 'processing':
    case 'generating':
      return {
        text: 'Wordt gegenereerd...',
        class: 'status-processing',
        icon: '⏳'
      };
    case 'generated':
      return {
        text: 'Gereed',
        class: 'status-success',
        icon: '✅'
      };
    case 'failed':
      return {
        text: 'Mislukt',
        class: 'status-error',
        icon: '❌'
      };
    default:
      return {
        text: status || 'Onbekend',
        class: 'status-default',
        icon: '❓'
      };
  }
});

// Fetch report details
const fetchReport = async () => {
  if (!reportId.value) return;
  
  loading.value = true;
  try {
    const report = await reportStore.fetchReport(reportId.value);
    
    // If report is still generating, start polling
    if (report.status === 'processing' || report.status === 'generating') {
      startStatusPolling();
    }
    
    // Fetch case details if we don't have them already
    if (!caseStore.currentCase || caseStore.currentCase.id !== report.case_id) {
      await caseStore.fetchCase(report.case_id);
    }
    
    // Fetch template information if not already available
    if (Object.keys(reportStore.templates).length === 0) {
      await reportStore.fetchReportTemplates();
    }
    
    // Set active section to first section if there are sections and none is selected
    if (
      report.content && 
      Object.keys(report.content).length > 0 && 
      !activeSection.value
    ) {
      activeSection.value = Object.keys(report.content)[0];
    }
  } catch (err) {
    notificationStore.addNotification({
      type: 'error',
      title: 'Fout bij laden rapport',
      message: 'Er is een fout opgetreden bij het ophalen van het rapport.'
    });
    console.error(err);
  } finally {
    loading.value = false;
    isLoadingInitial.value = false;
  }
};

// Poll for report status updates if it's processing
const startStatusPolling = () => {
  // Clear any existing timer
  if (processingStatusTimer.value) {
    clearInterval(processingStatusTimer.value);
  }
  
  // Poll every 2 seconds
  processingStatusTimer.value = window.setInterval(async () => {
    try {
      console.log('Polling report status...');
      // Force a fresh fetch without caching
      const report = await reportStore.fetchReport(reportId.value);
      console.log('Poll response, report status:', report.status);
      
      // If report is no longer processing, stop polling
      if (report.status !== 'processing' && report.status !== 'generating') {
        console.log('Report status is now complete, stopping polling');
        stopStatusPolling();
        
        // Force an immediate UI refresh
        if (report.status === 'generated' && !activeSection.value && report.content) {
          // Set active section to first section if there are sections
          const sections = Object.keys(report.content);
          if (sections.length > 0) {
            activeSection.value = sections[0];
          }
        }
      }
    } catch (err) {
      console.error('Error polling report status:', err);
      stopStatusPolling();
    }
  }, 2000) as unknown as number;
};

// Stop the polling
const stopStatusPolling = () => {
  if (processingStatusTimer.value) {
    clearInterval(processingStatusTimer.value);
    processingStatusTimer.value = null;
  }
};

// Delete report
const deleteReport = async () => {
  if (!confirm('Weet je zeker dat je dit rapport wilt verwijderen?')) {
    return;
  }
  
  try {
    await reportStore.deleteReport(reportId.value);
    
    notificationStore.addNotification({
      type: 'success',
      title: 'Rapport verwijderd',
      message: 'Het rapport is succesvol verwijderd.'
    });
    
    // Navigate back to case detail
    if (caseStore.currentCase) {
      router.push(`/cases/${caseStore.currentCase.id}`);
    } else {
      router.push('/cases');
    }
  } catch (err) {
    notificationStore.addNotification({
      type: 'error',
      title: 'Fout bij verwijderen',
      message: 'Er is een fout opgetreden bij het verwijderen van het rapport.'
    });
    console.error(err);
  }
};

// Regenerate a section
const regenerateSection = async (sectionId: string) => {
  if (!reportStore.currentReport) return;
  
  regeneratingSection.value = sectionId;
  
  try {
    await reportStore.regenerateSection({
      report_id: reportId.value,
      section_id: sectionId
    });
    
    // Refresh report data
    await reportStore.fetchReport(reportId.value);
    
    notificationStore.addNotification({
      type: 'success',
      title: 'Sectie geregenereerd',
      message: `De sectie "${getSectionTitle(sectionId)}" is succesvol geregenereerd.`
    });
  } catch (err) {
    notificationStore.addNotification({
      type: 'error',
      title: 'Fout bij regenereren',
      message: 'Er is een fout opgetreden bij het regenereren van de sectie.'
    });
    console.error(err);
  } finally {
    regeneratingSection.value = null;
  }
};

// Format markdown content to HTML
const formatMarkdown = (content: string) => {
  try {
    return marked(content);
  } catch (e) {
    console.error('Error parsing markdown:', e);
    return content.replace(/\n/g, '<br>');
  }
};

// Fetch source chunks for the active section
const fetchSources = async () => {
  if (!reportStore.currentReport || !activeSection.value) return;
  
  const metadata = reportStore.currentReport.metadata;
  if (!metadata || !metadata.sections || !metadata.sections[activeSection.value]) {
    sources.value = [];
    return;
  }
  
  const sectionMetadata = metadata.sections[activeSection.value];
  const chunkIds = sectionMetadata.chunk_ids || [];
  
  if (chunkIds.length === 0) {
    sources.value = [];
    return;
  }
  
  loadingSources.value = true;
  
  try {
    // In a full implementation, we would fetch the chunks from the API
    // For now, we'll just use the chunk IDs as placeholders
    const dummySources = chunkIds.map((id: string, index: number) => ({
      id,
      content: `Bron ${index + 1} inhoud zou hier verschijnen. In een volledige implementatie zou deze opgehaald worden van de API.`,
      metadata: {
        document_name: `Document ${index + 1}`,
        page: index + 1
      }
    }));
    
    sources.value = dummySources;
  } catch (err) {
    console.error('Error fetching sources:', err);
    notificationStore.addNotification({
      type: 'error',
      title: 'Fout bij laden bronnen',
      message: 'Er is een fout opgetreden bij het ophalen van de bronnen.'
    });
  } finally {
    loadingSources.value = false;
  }
};

// Copy section content to clipboard
const copySectionContent = async (content: string) => {
  try {
    await navigator.clipboard.writeText(content);
    notificationStore.addNotification({
      type: 'success',
      title: 'Gekopieerd',
      message: 'Sectie-inhoud is gekopieerd naar het klembord.'
    });
  } catch (err) {
    console.error('Error copying to clipboard:', err);
    notificationStore.addNotification({
      type: 'error',
      title: 'Kopiëren mislukt',
      message: 'Kan niet kopiëren naar klembord.'
    });
  }
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

// Get section title from template
const getSectionTitle = (sectionId: string) => {
  if (
    !reportStore.currentReport || 
    !reportStore.templates[reportStore.currentReport.template_id] ||
    !reportStore.templates[reportStore.currentReport.template_id].sections[sectionId]
  ) {
    return sectionId;
  }
  
  return reportStore.templates[reportStore.currentReport.template_id].sections[sectionId].title;
};

// Get status class for styling
const getStatusClass = (status: string) => {
  const statusMap: Record<string, string> = {
    'processing': 'status-processing',
    'generating': 'status-processing',
    'generated': 'status-success',
    'failed': 'status-error'
  };
  
  return statusMap[status] || 'status-default';
};

// Watch for sources dialog opening
const handleSourcesDialogOpen = async () => {
  if (showSourcesDialog.value) {
    await fetchSources();
  }
};

// Watch for changes to the sources dialog visibility
// This would be better with a watch, but we'll keep it simple
const openSourcesDialog = async () => {
  showSourcesDialog.value = true;
  await handleSourcesDialogOpen();
};

// Selected layout for download
const selectedLayout = ref('standaard');

// Available layout options
const layoutOptions = [
  { id: 'standaard', name: 'Standaard' },
  { id: 'modern', name: 'Modern' },
  { id: 'professioneel', name: 'Professioneel' }
];

// Show download options dialog
const showDownloadDialog = ref(false);

// Store whether preview was open
const wasPreviewOpen = ref(false);

// Open download options dialog
const openDownloadDialog = () => {
  // If preview dialog is open, close it temporarily
  wasPreviewOpen.value = showPreviewDialog.value;
  if (wasPreviewOpen.value) {
    showPreviewDialog.value = false;
  }

  // Show download dialog
  showDownloadDialog.value = true;
};

// Close download options dialog
const closeDownloadDialog = () => {
  showDownloadDialog.value = false;

  // If preview was open before, restore it
  if (wasPreviewOpen.value) {
    showPreviewDialog.value = true;
    wasPreviewOpen.value = false;
  }
};

// Download report as DOCX with selected layout
const downloadReport = async (layout = 'standaard') => {
  if (!reportStore.currentReport) return;

  downloadingReport.value = true;

  try {
    // Close any open dialogs
    showDownloadDialog.value = false;
    showPreviewDialog.value = false;

    // Reset dialog state
    wasPreviewOpen.value = false;

    // Download with selected layout
    await reportStore.downloadReportAsDocx(reportId.value, layout);

    notificationStore.addNotification({
      type: 'success',
      title: 'Download gestart',
      message: 'Het rapport wordt gedownload.'
    });
  } catch (err) {
    notificationStore.addNotification({
      type: 'error',
      title: 'Download mislukt',
      message: 'Er is een fout opgetreden bij het downloaden van het rapport.'
    });
    console.error(err);
  } finally {
    downloadingReport.value = false;
  }
};

// Preview report (all sections)
const previewFullReport = async () => {
  if (!reportStore.currentReport) return;
  
  try {
    // Refresh the current report data
    await reportStore.previewReport(reportId.value);
    // Show the preview modal
    showPreviewDialog.value = true;
  } catch (err) {
    notificationStore.addNotification({
      type: 'error',
      title: 'Preview mislukt',
      message: 'Er is een fout opgetreden bij het voorvertonen van het rapport.'
    });
    console.error(err);
  }
};

// Close the preview dialog
const closePreviewDialog = () => {
  showPreviewDialog.value = false;
};

// Print the preview content
const printPreview = () => {
  window.print();
};

// Get the download URL for the report
const getDownloadUrl = () => {
  if (!reportStore.currentReport) return '';
  
  // Get the API base URL
  let baseUrl = '';
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    baseUrl = `http://${hostname}:8000/api/v1`;
  } else {
    baseUrl = 'http://localhost:8000/api/v1';
  }
  
  // Add the mock JWT token
  const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJleGFtcGxlX3VzZXJfaWQiLCJuYW1lIjoiVGVzdCBVc2VyIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c';
  
  // Build the URL with token as a query parameter for simplicity
  return `${baseUrl}/reports/${reportId.value}/export/docx?token=${token}`;
};

// Get ordered sections for the report preview
const getOrderedSections = () => {
  // Define the correct section order
  const sectionOrder = [
    "persoonsgegevens",
    "werkgever_functie",
    "aanleiding",
    "arbeidsverleden",
    "medische_situatie",
    "belastbaarheid",
    "belasting_huidige_functie",
    "visie_ad",
    "matching",
    "conclusie",
    "samenvatting"
  ];
  
  // If no report, return empty array
  if (!reportStore.currentReport || !reportStore.currentReport.content) {
    console.log("No report content available");
    return [];
  }
  
  console.log("Report content keys:", Object.keys(reportStore.currentReport.content));
  
  // Filter the ordered sections to only include those that exist in the report content
  const availableSections = sectionOrder.filter(sectionId => 
    reportStore.currentReport.content[sectionId] !== undefined
  );
  
  console.log("Available sections:", availableSections);
  
  return availableSections;
};

// Handle comments updated event
const handleCommentsUpdated = (count: number) => {
  console.log(`Comments updated: ${count} comments for section ${activeSection.value}`);
  // Could add UI feedback here, such as showing comment count in section header
};

// Clean up on component unmount
onMounted(() => {
  fetchReport();
  
  return () => {
    stopStatusPolling();
    showSourcesDialog.value = false;
    showPreviewDialog.value = false;
  };
});
</script>

<template>
  <div class="report-view">
    <!-- Loading Skeleton -->
    <div v-if="isLoadingInitial" class="loading-skeleton">
      <div class="skeleton-header">
        <div class="skeleton-title"></div>
        <div class="skeleton-actions">
          <div class="skeleton-button"></div>
          <div class="skeleton-button"></div>
        </div>
      </div>
      <div class="skeleton-content">
        <div class="skeleton-card">
          <div class="skeleton-line"></div>
          <div class="skeleton-line short"></div>
          <div class="skeleton-line"></div>
        </div>
        <div class="skeleton-card">
          <div class="skeleton-line"></div>
          <div class="skeleton-line"></div>
          <div class="skeleton-line short"></div>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="!reportStore.currentReport" class="error-state">
      <div class="error-icon">📄</div>
      <h2>Rapport niet gevonden</h2>
      <p>Het opgevraagde rapport bestaat niet of je hebt geen toegang.</p>
      <button @click="router.push('/cases')" class="btn btn-primary">
        <span class="icon">←</span>
        Terug naar Cases
      </button>
    </div>

    <!-- Report Content -->
    <div v-else class="report-container">
      <!-- Breadcrumb -->
      <nav class="breadcrumb">
        <router-link to="/cases" class="breadcrumb-item">Cases</router-link>
        <span class="breadcrumb-separator">›</span>
        <router-link 
          v-if="caseStore.currentCase"
          :to="`/cases/${caseStore.currentCase.id}`" 
          class="breadcrumb-item"
        >
          {{ caseStore.currentCase.title }}
        </router-link>
        <span v-if="caseStore.currentCase" class="breadcrumb-separator">›</span>
        <span class="breadcrumb-current">{{ reportStore.currentReport.title }}</span>
      </nav>

      <!-- Report Header -->
      <div class="report-header">
        <div class="header-content">
          <div class="title-section">
            <h1>{{ reportStore.currentReport.title }}</h1>
            <div class="status-badge" :class="statusIndicator.class">
              <span class="status-icon">{{ statusIndicator.icon }}</span>
              <span class="status-text">{{ statusIndicator.text }}</span>
            </div>
          </div>
          
          <div class="header-actions">
            <button 
              v-if="isReportComplete"
              @click="previewFullReport" 
              class="btn btn-outline"
            >
              <span class="icon">👁️</span>
              Preview
            </button>
            <button
              v-if="isReportComplete"
              @click="openDownloadDialog"
              class="btn btn-primary"
              :disabled="downloadingReport"
            >
              <div v-if="downloadingReport" class="loading-spinner small"></div>
              <span v-else class="icon">💾</span>
              {{ downloadingReport ? 'Bezig...' : 'Download' }}
            </button>
            <button @click="deleteReport" class="btn btn-danger-outline">
              <span class="icon">🗑️</span>
              Verwijderen
            </button>
          </div>
        </div>
      </div>

      <!-- Processing Status Card -->
      <div v-if="isReportGenerating" class="status-card processing">
        <div class="status-content">
          <div class="loading-spinner"></div>
          <div class="status-info">
            <h3>Rapport wordt gegenereerd</h3>
            <p>Dit kan enkele minuten duren. De pagina wordt automatisch bijgewerkt.</p>
            <div class="progress-bar">
              <div class="progress-fill"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Error Status Card -->
      <div v-if="isReportFailed" class="status-card error">
        <div class="status-content">
          <div class="status-icon error">❌</div>
          <div class="status-info">
            <h3>Rapport generatie mislukt</h3>
            <p v-if="reportStore.currentReport.error" class="error-details">
              {{ reportStore.currentReport.error }}
            </p>
            <p v-else>Er is een fout opgetreden bij het genereren van het rapport.</p>
          </div>
        </div>
      </div>

      <!-- Report Information Cards -->
      <div class="info-grid">
        <div class="info-card">
          <div class="card-header">
            <h3>Rapport Details</h3>
          </div>
          <div class="card-content">
            <div class="info-row">
              <span class="info-label">Template</span>
              <span class="info-value">
                {{ reportStore.templates[reportStore.currentReport.template_id]?.name || reportStore.currentReport.template_id }}
              </span>
            </div>
            <div class="info-row">
              <span class="info-label">Status</span>
              <span class="info-value">
                <span class="status-badge" :class="statusIndicator.class">
                  {{ statusIndicator.text }}
                </span>
              </span>
            </div>
            <div class="info-row">
              <span class="info-label">Aangemaakt</span>
              <span class="info-value">{{ formatDate(reportStore.currentReport.created_at) }}</span>
            </div>
            <div v-if="reportStore.currentReport.updated_at" class="info-row">
              <span class="info-label">Bijgewerkt</span>
              <span class="info-value">{{ formatDate(reportStore.currentReport.updated_at) }}</span>
            </div>
          </div>
        </div>

        <div v-if="caseStore.currentCase" class="info-card">
          <div class="card-header">
            <h3>Case Informatie</h3>
          </div>
          <div class="card-content">
            <div class="info-row">
              <span class="info-label">Case</span>
              <span class="info-value">{{ caseStore.currentCase.title }}</span>
            </div>
            <div v-if="caseStore.currentCase.description" class="info-row">
              <span class="info-label">Beschrijving</span>
              <span class="info-value">{{ caseStore.currentCase.description }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Documenten</span>
              <span class="info-value">{{ caseStore.currentCase.documents?.length || 0 }} documenten</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Report Content Section -->
      <div v-if="isReportComplete && hasReportContent" class="content-section">
        <div class="content-header">
          <h2>Rapport Inhoud</h2>
          <div class="content-controls">
            <span class="section-count">{{ reportSections.length }} secties</span>
          </div>
        </div>
        
        <!-- Sections Navigation -->
        <div class="sections-nav">
          <button 
            v-for="sectionId in reportSections" 
            :key="sectionId"
            class="section-tab"
            :class="{ active: activeSection === sectionId }"
            @click="activeSection = sectionId"
          >
            <span class="tab-title">{{ getSectionTitle(sectionId) }}</span>
            <span v-if="regeneratingSection === sectionId" class="tab-status loading">
              <div class="loading-spinner tiny"></div>
            </span>
          </button>
        </div>
        
        <!-- Active Section Content -->
        <div v-if="activeSection && currentSectionContent" class="section-viewer">
          <div class="viewer-header">
            <div class="section-title">
              <h3>{{ getSectionTitle(activeSection) }}</h3>
              <span class="word-count">{{ currentSectionContent.split(' ').length }} woorden</span>
            </div>
            <div class="viewer-actions">
              <button 
                @click="copySectionContent(currentSectionContent)" 
                class="btn btn-outline btn-sm"
                title="Kopieer sectie-inhoud"
              >
                <span class="icon">📋</span>
              </button>
              <button 
                @click="regenerateSection(activeSection)"
                class="btn btn-outline btn-sm"
                :disabled="regeneratingSection === activeSection"
                title="Regenereer deze sectie"
              >
                <div v-if="regeneratingSection === activeSection" class="loading-spinner tiny"></div>
                <span v-else class="icon">🔄</span>
              </button>
              <button 
                @click="toggleMarkdown = !toggleMarkdown"
                class="btn btn-outline btn-sm"
                :class="{ active: toggleMarkdown }"
                title="Schakel tussen opgemaakt en markdown weergave"
              >
                <span class="icon">{{ toggleMarkdown ? '📝' : '👁️' }}</span>
              </button>
              <button 
                v-if="reportStore.currentReport.metadata?.sections?.[activeSection]?.chunk_ids?.length"
                @click="openSourcesDialog"
                class="btn btn-outline btn-sm"
                title="Bekijk bronnen"
              >
                <span class="icon">📄</span>
                Bronnen
              </button>
            </div>
          </div>
          
          <div class="viewer-content">
            <div v-if="!toggleMarkdown" class="content-formatted">
              <div v-html="formatMarkdown(currentSectionContent)"></div>
            </div>
            <pre v-else class="content-markdown">{{ currentSectionContent }}</pre>
          </div>

          <!-- Comments Section -->
          <div class="comments-section">
            <CommentSystem 
              :report-id="reportStore.currentReport.id"
              :section-id="activeSection"
              :include-internal="true"
              @comments-updated="handleCommentsUpdated"
            />
          </div>
          
          <!-- Sources Dialog -->
          <div v-if="showSourcesDialog" class="sources-dialog">
            <div class="dialog-content">
              <div class="dialog-header">
                <h3>Bronnen voor {{ getSectionTitle(activeSection) }}</h3>
                <button @click="showSourcesDialog = false" class="close-btn">&times;</button>
              </div>
              <div class="dialog-body">
                <div v-if="loadingSources" class="loading-sources">
                  <div class="spinner"></div>
                  <p>Bronnen worden geladen...</p>
                </div>
                <div v-else-if="sources.length === 0" class="no-sources">
                  <p>Geen bronnen beschikbaar voor deze sectie.</p>
                </div>
                <div v-else class="sources-list">
                  <div v-for="(source, index) in sources" :key="index" class="source-item">
                    <div class="source-header">
                      <strong>Bron {{ index + 1 }}</strong>
                      <span class="source-meta">
                        {{ source.metadata?.document_name || 'Onbekend document' }}
                      </span>
                    </div>
                    <div class="source-content">
                      {{ source.content }}
                    </div>
                  </div>
                </div>
              </div>
              <div class="dialog-footer">
                <button @click="showSourcesDialog = false" class="btn btn-primary">Sluiten</button>
              </div>
            </div>
          </div>
        </div>
        
        <!-- No Section Selected -->
        <div v-else class="no-section-selected">
          <div class="empty-state">
            <div class="empty-icon">📖</div>
            <h3>Selecteer een sectie</h3>
            <p>Kies een sectie uit de navigatie om de inhoud te bekijken.</p>
          </div>
        </div>
      </div>

      <!-- Empty Content State -->
      <div v-else-if="isReportComplete && !hasReportContent" class="empty-content">
        <div class="empty-state">
          <div class="empty-icon">📄</div>
          <h3>Geen inhoud beschikbaar</h3>
          <p>Dit rapport heeft nog geen gegenereerde inhoud.</p>
        </div>
      </div>
    </div>

    <!-- Preview Report Dialog -->
    <div v-if="showPreviewDialog" class="preview-dialog">
      <div class="dialog-content preview-content">
        <div class="dialog-header">
          <h3>Rapport Preview: {{ reportStore.currentReport.title }}</h3>
          <div class="dialog-header-actions">
            <button @click="printPreview" class="btn btn-outline">
              <span class="icon">🖨️</span> Afdrukken
            </button>
            <button @click="openDownloadDialog" class="btn btn-primary">
              <span class="icon">📥</span> Downloaden
            </button>
            <button @click="closePreviewDialog" class="close-btn" style="font-size: 1.5rem; cursor: pointer;">&times;</button>
          </div>
        </div>
        <div class="dialog-body">
          <!-- Report Content Preview -->
          <div class="preview-report">
            <!-- Title Page -->
            <div class="preview-title-page">
              <h1>Arbeidsdeskundig Rapport</h1>
              <h2>{{ reportStore.currentReport.title }}</h2>
              <p class="preview-date">{{ formatDate(reportStore.currentReport.created_at) }}</p>

              <!-- Profile Information (if available) -->
              <div v-if="reportStore.currentReport.metadata?.user_profile" class="preview-profile-info">
                <div class="preview-profile-header">
                  <div v-if="reportStore.currentReport.metadata.user_profile.logo_url" class="preview-logo">
                    <img :src="reportStore.currentReport.metadata.user_profile.logo_url" alt="Logo" />
                  </div>
                  <div class="preview-profile-details">
                    <p v-if="reportStore.currentReport.metadata.user_profile.display_name" class="preview-profile-name">
                      {{ reportStore.currentReport.metadata.user_profile.display_name }}
                    </p>
                    <p v-else-if="reportStore.currentReport.metadata.user_profile.first_name && reportStore.currentReport.metadata.user_profile.last_name" class="preview-profile-name">
                      {{ reportStore.currentReport.metadata.user_profile.first_name }} {{ reportStore.currentReport.metadata.user_profile.last_name }}
                    </p>
                    <p v-if="reportStore.currentReport.metadata.user_profile.job_title" class="preview-profile-jobtitle">
                      {{ reportStore.currentReport.metadata.user_profile.job_title }}
                    </p>
                    <p v-if="reportStore.currentReport.metadata.user_profile.certification" class="preview-profile-certification">
                      {{ reportStore.currentReport.metadata.user_profile.certification }}
                      <span v-if="reportStore.currentReport.metadata.user_profile.registration_number">
                        - {{ reportStore.currentReport.metadata.user_profile.registration_number }}
                      </span>
                    </p>
                  </div>
                </div>

                <div v-if="reportStore.currentReport.metadata.user_profile.company_name" class="preview-company-info">
                  <p class="preview-company-name">{{ reportStore.currentReport.metadata.user_profile.company_name }}</p>

                  <div v-if="reportStore.currentReport.metadata.user_profile.company_address ||
                             reportStore.currentReport.metadata.user_profile.company_postal_code ||
                             reportStore.currentReport.metadata.user_profile.company_city"
                       class="preview-company-address">
                    <p>
                      {{ reportStore.currentReport.metadata.user_profile.company_address }}<br v-if="reportStore.currentReport.metadata.user_profile.company_address">
                      {{ reportStore.currentReport.metadata.user_profile.company_postal_code }} {{ reportStore.currentReport.metadata.user_profile.company_city }}
                    </p>
                  </div>

                  <div class="preview-company-contact">
                    <p v-if="reportStore.currentReport.metadata.user_profile.company_phone">
                      Tel: {{ reportStore.currentReport.metadata.user_profile.company_phone }}
                    </p>
                    <p v-if="reportStore.currentReport.metadata.user_profile.company_email">
                      Email: {{ reportStore.currentReport.metadata.user_profile.company_email }}
                    </p>
                    <p v-if="reportStore.currentReport.metadata.user_profile.company_website">
                      Website: {{ reportStore.currentReport.metadata.user_profile.company_website }}
                    </p>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Table of Contents -->
            <div class="preview-toc">
              <h2>Inhoudsopgave</h2>
              <ol class="toc-list">
                <li v-for="sectionId in getOrderedSections()" :key="sectionId">
                  {{ getSectionTitle(sectionId) }}
                </li>
              </ol>
            </div>
            
            <!-- Report Sections -->
            <!-- Use proper section order -->
            <template v-if="getOrderedSections().length > 0">
              <div 
                v-for="sectionId in getOrderedSections()" 
                :key="sectionId" 
                class="preview-section"
              >
                <h2>{{ getSectionTitle(sectionId) }}</h2>
                <div class="preview-section-content">
                  <div v-html="formatMarkdown(reportStore.currentReport.content[sectionId])"></div>
                </div>
              </div>
            </template>
            <div v-else class="no-content">
              <p>Er is nog geen inhoud beschikbaar in dit rapport.</p>
            </div>
          </div>
        </div>
        <div class="dialog-footer">
          <button @click="closePreviewDialog" class="btn btn-primary">
            Sluiten
          </button>
        </div>
      </div>
    </div>

    <!-- Download Options Dialog -->
    <div v-if="showDownloadDialog" class="download-dialog sources-dialog">
      <div class="dialog-content">
        <div class="dialog-header">
          <h3>Download Rapportage</h3>
          <button @click="closeDownloadDialog" class="close-btn">&times;</button>
        </div>
        <div class="dialog-body">
          <p>Kies een layout voor je rapport:</p>
          <div class="layout-options">
            <div
              v-for="option in layoutOptions"
              :key="option.id"
              class="layout-option"
              :class="{ 'selected': selectedLayout === option.id }"
              @click="selectedLayout = option.id"
            >
              <div class="layout-preview">
                <!-- Verbeterde visuele weergave van de layout -->
                <div class="layout-preview-image" :class="option.id">
                  <!-- Standaard layout -->
                  <div v-if="option.id === 'standaard'" class="preview-standard">
                    <div class="preview-page">
                      <div class="preview-title"></div>
                      <div class="preview-header">
                        <div class="preview-logo-small"></div>
                        <div class="preview-header-text"></div>
                      </div>
                      <div class="preview-body">
                        <div class="preview-line"></div>
                        <div class="preview-line"></div>
                        <div class="preview-line short"></div>
                        <div class="preview-section-header"></div>
                        <div class="preview-line"></div>
                        <div class="preview-line"></div>
                      </div>
                    </div>
                  </div>

                  <!-- Modern layout -->
                  <div v-else-if="option.id === 'modern'" class="preview-modern">
                    <div class="preview-page">
                      <div class="preview-title-modern"></div>
                      <div class="preview-header modern">
                        <div class="preview-logo-right"></div>
                      </div>
                      <div class="preview-body">
                        <div class="preview-line modern"></div>
                        <div class="preview-line modern"></div>
                        <div class="preview-line modern short"></div>
                        <div class="preview-section-header modern"></div>
                        <div class="preview-line modern"></div>
                      </div>
                    </div>
                  </div>

                  <!-- Professioneel layout -->
                  <div v-else-if="option.id === 'professioneel'" class="preview-professional">
                    <div class="preview-page">
                      <div class="preview-title-professional"></div>
                      <div class="preview-header professional">
                        <div class="preview-logo-large"></div>
                        <div class="preview-company-info"></div>
                      </div>
                      <div class="preview-body professional">
                        <div class="preview-section-header professional"></div>
                        <div class="preview-line professional"></div>
                        <div class="preview-line professional"></div>
                        <div class="preview-line professional short"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="layout-details">
                <h4>{{ option.name }}</h4>
                <p v-if="option.id === 'standaard'">
                  Eenvoudige, overzichtelijke layout met standaard opmaak. Logo links bovenaan met bedrijfsgegevens ernaast.
                </p>
                <p v-else-if="option.id === 'modern'">
                  Moderne en frisse layout met accentkleuren en betere visuele hiërarchie. Logo rechts bovenaan met minimalistisch design.
                </p>
                <p v-else-if="option.id === 'professioneel'">
                  Professionele layout met bedrijfslogo prominent aanwezig bovenaan en formele structuur voor officiële documenten.
                </p>
              </div>
            </div>
          </div>
        </div>
        <div class="dialog-footer">
          <button @click="closeDownloadDialog" class="btn btn-secondary">Annuleren</button>
          <button @click="downloadReport(selectedLayout)" class="btn btn-primary">
            <span v-if="downloadingReport" class="spinner small"></span>
            <span v-else class="icon">📥</span>
            Download
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Modern Design System Variables */
:root {
  --primary-color: #2563eb;
  --primary-hover: #1d4ed8;
  --primary-light: #eff6ff;
  --success-color: #10b981;
  --success-light: #ecfdf5;
  --error-color: #ef4444;
  --error-light: #fef2f2;
  --warning-color: #f59e0b;
  --warning-light: #fffbeb;
  --text-color: #374151;
  --text-light: #6b7280;
  --text-lighter: #9ca3af;
  --border-color: #e5e7eb;
  --border-light: #f3f4f6;
  --bg-color: #ffffff;
  --bg-secondary: #f9fafb;
  --bg-tertiary: #f3f4f6;
  --shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  --radius: 8px;
  --radius-sm: 4px;
  --radius-lg: 12px;
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
  --spacing-2xl: 3rem;
}

/* Base Layout */
.report-view {
  min-height: 100vh;
  background-color: var(--bg-secondary);
  padding: var(--spacing-lg);
}

/* Loading Skeleton */
.loading-skeleton {
  max-width: 1200px;
  margin: 0 auto;
  background-color: var(--bg-color);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl);
  box-shadow: var(--shadow);
}

.skeleton-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xl);
}

.skeleton-title {
  height: 32px;
  width: 300px;
  background: linear-gradient(90deg, var(--bg-tertiary) 25%, var(--border-light) 50%, var(--bg-tertiary) 75%);
  background-size: 200% 100%;
  animation: shimmer 2s infinite;
  border-radius: var(--radius-sm);
}

.skeleton-actions {
  display: flex;
  gap: var(--spacing-md);
}

.skeleton-button {
  height: 40px;
  width: 120px;
  background: linear-gradient(90deg, var(--bg-tertiary) 25%, var(--border-light) 50%, var(--bg-tertiary) 75%);
  background-size: 200% 100%;
  animation: shimmer 2s infinite;
  border-radius: var(--radius-sm);
}

.skeleton-content {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--spacing-lg);
}

.skeleton-card {
  padding: var(--spacing-lg);
  background-color: var(--bg-secondary);
  border-radius: var(--radius);
  border: 1px solid var(--border-color);
}

.skeleton-line {
  height: 16px;
  background: linear-gradient(90deg, var(--bg-tertiary) 25%, var(--border-light) 50%, var(--bg-tertiary) 75%);
  background-size: 200% 100%;
  animation: shimmer 2s infinite;
  border-radius: var(--radius-sm);
  margin-bottom: var(--spacing-md);
}

.skeleton-line.short {
  width: 60%;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* Error State */
.error-state {
  max-width: 600px;
  margin: var(--spacing-2xl) auto;
  text-align: center;
  padding: var(--spacing-2xl);
  background-color: var(--bg-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
}

.error-icon {
  font-size: 4rem;
  margin-bottom: var(--spacing-lg);
}

.error-state h2 {
  color: var(--text-color);
  margin-bottom: var(--spacing-md);
  font-size: 1.5rem;
  font-weight: 600;
}

.error-state p {
  color: var(--text-light);
  margin-bottom: var(--spacing-xl);
}

/* Main Container */
.report-container {
  max-width: 1200px;
  margin: 0 auto;
}

/* Breadcrumb */
.breadcrumb {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
  font-size: 0.875rem;
}

.breadcrumb-item {
  color: var(--text-light);
  text-decoration: none;
  transition: color 0.2s;
}

.breadcrumb-item:hover {
  color: var(--primary-color);
}

.breadcrumb-separator {
  color: var(--text-lighter);
}

.breadcrumb-current {
  color: var(--text-color);
  font-weight: 500;
}

/* Report Header */
.report-header {
  background-color: var(--bg-color);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl);
  box-shadow: var(--shadow);
  margin-bottom: var(--spacing-xl);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-lg);
}

.title-section {
  flex: 1;
}

.title-section h1 {
  margin: 0 0 var(--spacing-md) 0;
  color: var(--text-color);
  font-size: 1.875rem;
  font-weight: 700;
  line-height: 1.25;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-badge.status-processing {
  background-color: var(--warning-light);
  color: var(--warning-color);
}

.status-badge.status-success {
  background-color: var(--success-light);
  color: var(--success-color);
}

.status-badge.status-error {
  background-color: var(--error-light);
  color: var(--error-color);
}

.status-badge.status-default {
  background-color: var(--bg-tertiary);
  color: var(--text-light);
}

.header-actions {
  display: flex;
  gap: var(--spacing-md);
  flex-shrink: 0;
}

/* Status Cards */
.status-card {
  background-color: var(--bg-color);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
  box-shadow: var(--shadow);
  border-left: 4px solid;
}

.status-card.processing {
  border-left-color: var(--warning-color);
  background: linear-gradient(135deg, var(--warning-light) 0%, var(--bg-color) 100%);
}

.status-card.error {
  border-left-color: var(--error-color);
  background: linear-gradient(135deg, var(--error-light) 0%, var(--bg-color) 100%);
}

.status-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.status-icon {
  font-size: 2rem;
}

.status-info h3 {
  margin: 0 0 var(--spacing-sm) 0;
  color: var(--text-color);
  font-size: 1.25rem;
  font-weight: 600;
}

.status-info p {
  margin: 0;
  color: var(--text-light);
}

.error-details {
  background-color: var(--error-light);
  padding: var(--spacing-md);
  border-radius: var(--radius-sm);
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
  margin-top: var(--spacing-sm);
}

.progress-bar {
  width: 100%;
  height: 4px;
  background-color: var(--border-light);
  border-radius: 2px;
  overflow: hidden;
  margin-top: var(--spacing-md);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--warning-color), var(--primary-color));
  border-radius: 2px;
  animation: progress 2s ease-in-out infinite;
}

@keyframes progress {
  0% { width: 0%; }
  50% { width: 70%; }
  100% { width: 100%; }
}

/* Info Grid */
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.info-card {
  background-color: var(--bg-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.info-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.card-header {
  background: linear-gradient(135deg, var(--primary-light) 0%, var(--bg-color) 100%);
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
}

.card-header h3 {
  margin: 0;
  color: var(--primary-color);
  font-size: 1.125rem;
  font-weight: 600;
}

.card-content {
  padding: var(--spacing-lg);
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: var(--spacing-md) 0;
  border-bottom: 1px solid var(--border-light);
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-weight: 500;
  color: var(--text-light);
  flex-shrink: 0;
  width: 40%;
}

.info-value {
  color: var(--text-color);
  text-align: right;
  word-break: break-word;
  flex: 1;
}

/* Content Section */
.content-section {
  background-color: var(--bg-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
  overflow: hidden;
  margin-bottom: var(--spacing-xl);
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-xl);
  background: linear-gradient(135deg, var(--primary-light) 0%, var(--bg-color) 100%);
  border-bottom: 1px solid var(--border-color);
}

.content-header h2 {
  margin: 0;
  color: var(--primary-color);
  font-size: 1.5rem;
  font-weight: 600;
}

.content-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.section-count {
  background-color: var(--primary-color);
  color: white;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 600;
}

/* Sections Navigation */
.sections-nav {
  display: flex;
  flex-wrap: wrap;
  background-color: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  overflow-x: auto;
}

.section-tab {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  background: none;
  border: none;
  color: var(--text-light);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  border-bottom: 3px solid transparent;
  white-space: nowrap;
}

.section-tab:hover {
  background-color: var(--border-light);
  color: var(--text-color);
}

.section-tab.active {
  background-color: var(--bg-color);
  color: var(--primary-color);
  border-bottom-color: var(--primary-color);
}

.tab-title {
  font-size: 0.875rem;
}

.tab-status.loading {
  display: flex;
  align-items: center;
}

/* Section Viewer */
.section-viewer {
  padding: var(--spacing-xl);
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xl);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
}

.section-title h3 {
  margin: 0 0 var(--spacing-xs) 0;
  color: var(--text-color);
  font-size: 1.25rem;
  font-weight: 600;
}

.word-count {
  color: var(--text-lighter);
  font-size: 0.75rem;
  font-weight: 500;
}

.viewer-actions {
  display: flex;
  gap: var(--spacing-sm);
}

.viewer-content {
  margin-bottom: var(--spacing-xl);
}

.content-formatted {
  line-height: 1.7;
  color: var(--text-color);
  font-size: 1rem;
}

.content-formatted h1,
.content-formatted h2,
.content-formatted h3,
.content-formatted h4,
.content-formatted h5,
.content-formatted h6 {
  color: var(--primary-color);
  margin-top: var(--spacing-xl);
  margin-bottom: var(--spacing-md);
  font-weight: 600;
}

.content-formatted p {
  margin-bottom: var(--spacing-md);
}

.content-formatted ul,
.content-formatted ol {
  margin-bottom: var(--spacing-md);
  padding-left: var(--spacing-xl);
}

.content-formatted li {
  margin-bottom: var(--spacing-sm);
}

.content-markdown {
  background-color: var(--bg-secondary);
  padding: var(--spacing-lg);
  border-radius: var(--radius);
  color: var(--text-color);
  font-family: 'Courier New', monospace;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-x: auto;
  margin: 0;
  border: 1px solid var(--border-color);
}

/* Comments Section */
.comments-section {
  border-top: 1px solid var(--border-color);
  padding-top: var(--spacing-xl);
}

/* Empty States */
.empty-state {
  text-align: center;
  padding: var(--spacing-2xl) var(--spacing-lg);
  color: var(--text-light);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: var(--spacing-lg);
  opacity: 0.5;
}

.empty-state h3 {
  margin: 0 0 var(--spacing-md) 0;
  color: var(--text-color);
  font-size: 1.125rem;
  font-weight: 600;
}

.empty-state p {
  margin: 0;
  color: var(--text-light);
}

.no-section-selected,
.empty-content {
  background-color: var(--bg-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
  margin-bottom: var(--spacing-xl);
}

/* Button System */
.btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s ease;
  text-decoration: none;
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-sm {
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: 0.75rem;
}

.btn-primary {
  background-color: var(--primary-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: var(--primary-hover);
  transform: translateY(-1px);
}

.btn-outline {
  background-color: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-color);
}

.btn-outline:hover:not(:disabled) {
  background-color: var(--bg-secondary);
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.btn-outline.active {
  background-color: var(--primary-light);
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.btn-danger-outline {
  background-color: transparent;
  border: 1px solid var(--error-color);
  color: var(--error-color);
}

.btn-danger-outline:hover:not(:disabled) {
  background-color: var(--error-color);
  color: white;
}

.icon {
  font-size: 0.875em;
}

/* Loading Spinners */
.loading-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid var(--border-light);
  border-radius: 50%;
  border-top-color: var(--primary-color);
  animation: spin 1s linear infinite;
}

.loading-spinner.small {
  width: 16px;
  height: 16px;
  border-width: 2px;
}

.loading-spinner.tiny {
  width: 12px;
  height: 12px;
  border-width: 2px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Dialogs */
.sources-dialog,
.preview-dialog {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.dialog-content {
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  background-color: white;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.preview-content {
  max-width: 1000px;
  max-height: 95vh;
}

.preview-report {
  background: white;
  color: var(--text-primary);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.preview-title-page {
  text-align: center;
  padding: var(--spacing-2xl);
  border-bottom: 2px solid var(--border-color);
  margin-bottom: var(--spacing-xl);
  background: linear-gradient(135deg, var(--bg-secondary) 0%, white 100%);
}

.preview-title-page h1 {
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--primary-color);
  margin-bottom: var(--spacing-lg);
  line-height: 1.2;
}

.preview-date {
  font-size: 1.125rem;
  color: var(--text-secondary);
  margin-bottom: var(--spacing-xl);
}

.preview-profile-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
  margin-top: var(--spacing-xl);
}

.preview-profile-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  justify-content: center;
}

.preview-logo img {
  max-height: 80px;
  max-width: 200px;
  object-fit: contain;
}

.preview-profile-details {
  text-align: left;
}

.preview-profile-name {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--spacing-xs);
}

.preview-profile-jobtitle,
.preview-profile-certification {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-xs);
}

.preview-company-info {
  text-align: center;
  padding: var(--spacing-lg);
  background: var(--bg-secondary);
  border-radius: var(--radius);
}

.preview-company-name {
  font-weight: 600;
  font-size: 1.125rem;
  color: var(--text-primary);
  margin-bottom: var(--spacing-sm);
}

.preview-company-address,
.preview-company-contact p {
  color: var(--text-secondary);
  font-size: 0.9rem;
  margin-bottom: var(--spacing-xs);
}

.preview-toc {
  margin: var(--spacing-xl) 0;
  padding: var(--spacing-lg);
  background: var(--bg-secondary);
  border-radius: var(--radius);
}

.preview-toc h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--spacing-lg);
  text-align: center;
}

.preview-section {
  margin-bottom: var(--spacing-xl);
  padding: var(--spacing-lg);
  background: white;
  border-radius: var(--radius);
  border: 1px solid var(--border-color);
}

.preview-section h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: var(--spacing-md);
  padding-bottom: var(--spacing-sm);
  border-bottom: 2px solid var(--primary-light);
}

.preview-section-content {
  color: var(--text-primary);
  line-height: 1.6;
}

.preview-section-content p {
  margin-bottom: var(--spacing-md);
}

.preview-section-content h4 {
  font-weight: 600;
  color: var(--text-primary);
  margin: var(--spacing-lg) 0 var(--spacing-sm) 0;
}

.preview-section-content ul,
.preview-section-content ol {
  margin-left: var(--spacing-lg);
  margin-bottom: var(--spacing-md);
}

.preview-section-content li {
  margin-bottom: var(--spacing-xs);
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--border-color);
  background: linear-gradient(135deg, var(--primary-light) 0%, var(--bg-color) 100%);
}

.dialog-header h3 {
  margin: 0;
  color: var(--primary-color);
  font-size: 1.25rem;
  font-weight: 600;
}

.dialog-body {
  flex: 1;
  padding: var(--spacing-xl);
  overflow-y: auto;
}

.dialog-footer {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
  background-color: var(--bg-secondary);
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--text-light);
  padding: var(--spacing-xs);
  border-radius: var(--radius-sm);
  transition: all 0.2s ease;
}

.close-btn:hover {
  background-color: var(--error-light);
  color: var(--error-color);
}

/* Layout Preview Styling */
.layout-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.layout-option {
  border: 2px solid var(--border-color);
  border-radius: var(--radius);
  padding: var(--spacing-md);
  cursor: pointer;
  transition: all 0.2s ease;
  background: white;
}

.layout-option:hover {
  border-color: var(--primary-color);
  box-shadow: var(--shadow);
}

.layout-option.selected {
  border-color: var(--primary-color);
  background: var(--primary-light);
}

.layout-preview {
  margin-bottom: var(--spacing-md);
}

.layout-preview-image {
  width: 100%;
  height: 120px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: white;
  position: relative;
  overflow: hidden;
}

.preview-page {
  width: 100%;
  height: 100%;
  padding: 8px;
  background: white;
  position: relative;
}

/* Standard Layout */
.preview-standard .preview-title {
  height: 12px;
  background: var(--primary-color);
  margin-bottom: 6px;
  width: 60%;
}

.preview-standard .preview-header {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 8px;
}

.preview-logo-small {
  width: 16px;
  height: 16px;
  background: var(--gray-300);
  border-radius: 2px;
}

.preview-header-text {
  height: 3px;
  background: var(--gray-300);
  flex: 1;
}

.preview-line {
  height: 2px;
  background: var(--gray-200);
  margin-bottom: 3px;
}

.preview-line.short {
  width: 70%;
}

.preview-section-header {
  height: 4px;
  background: var(--primary-light);
  margin: 6px 0 3px 0;
  width: 40%;
}

/* Modern Layout */
.preview-modern .preview-title-modern {
  height: 10px;
  background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
  margin-bottom: 4px;
  width: 70%;
}

.preview-modern .preview-header.modern {
  justify-content: flex-end;
  margin-bottom: 6px;
}

.preview-logo-right {
  width: 12px;
  height: 12px;
  background: var(--primary-color);
  border-radius: 50%;
}

.preview-line.modern {
  height: 2px;
  background: var(--gray-300);
  margin-bottom: 2px;
}

.preview-section-header.modern {
  height: 3px;
  background: var(--primary-color);
  margin: 4px 0 2px 0;
  width: 35%;
}

/* Professional Layout */
.preview-professional .preview-title-professional {
  height: 14px;
  background: var(--gray-800);
  margin-bottom: 8px;
  width: 80%;
}

.preview-professional .preview-header.professional {
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  margin-bottom: 8px;
}

.preview-logo-large {
  width: 20px;
  height: 8px;
  background: var(--primary-color);
}

.preview-company-info {
  height: 4px;
  background: var(--gray-300);
  width: 50%;
}

.preview-body.professional {
  border-top: 1px solid var(--border-color);
  padding-top: 6px;
}

.preview-section-header.professional {
  height: 5px;
  background: var(--gray-800);
  margin-bottom: 4px;
  width: 45%;
}

.preview-line.professional {
  height: 2px;
  background: var(--gray-200);
  margin-bottom: 2px;
}

/* Responsive Design */
@media (max-width: 768px) {
  .report-view {
    padding: var(--spacing-md);
  }

  .header-content {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    justify-content: stretch;
    flex-wrap: wrap;
  }

  .btn {
    flex: 1;
    justify-content: center;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

  .sections-nav {
    flex-direction: column;
  }

  .section-tab {
    justify-content: flex-start;
  }

  .viewer-header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-md);
  }

  .viewer-actions {
    justify-content: stretch;
    flex-wrap: wrap;
  }

  .dialog-content {
    width: 95%;
    max-height: 95vh;
  }
}

@media (max-width: 480px) {
  .title-section h1 {
    font-size: 1.5rem;
  }

  .status-badge {
    font-size: 0.625rem;
  }

  .viewer-actions {
    flex-direction: column;
  }
}
</style>