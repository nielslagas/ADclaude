<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useReportStore } from '@/stores/report';
import { useCaseStore } from '@/stores/case';
import { marked } from 'marked'; // Dit moet geïnstalleerd worden via npm install marked
import CommentSystem from '@/components/CommentSystem.vue';

const route = useRoute();
const router = useRouter();
const reportStore = useReportStore();
const caseStore = useCaseStore();

const loading = ref(false);
const error = ref<string | null>(null);
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
    error.value = 'Er is een fout opgetreden bij het ophalen van het rapport.';
    console.error(err);
  } finally {
    loading.value = false;
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
    
    // Navigate back to case detail
    if (caseStore.currentCase) {
      router.push(`/cases/${caseStore.currentCase.id}`);
    } else {
      router.push('/cases');
    }
  } catch (err) {
    error.value = 'Er is een fout opgetreden bij het verwijderen van het rapport.';
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
  } catch (err) {
    error.value = 'Er is een fout opgetreden bij het regenereren van de sectie.';
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
    error.value = 'Er is een fout opgetreden bij het ophalen van de bronnen.';
  } finally {
    loadingSources.value = false;
  }
};

// Copy section content to clipboard
const copySectionContent = async (content: string) => {
  try {
    await navigator.clipboard.writeText(content);
    alert('Inhoud gekopieerd naar klembord');
  } catch (err) {
    console.error('Error copying to clipboard:', err);
    error.value = 'Kan niet kopiëren naar klembord';
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

    // Show a brief success message
    alert('Het rapport wordt gedownload.');
  } catch (err) {
    error.value = 'Er is een fout opgetreden bij het downloaden van het rapport.';
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
    error.value = 'Er is een fout opgetreden bij het voorvertonen van het rapport.';
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
  <div class="report-detail-container">
    <div v-if="loading && !reportStore.currentReport" class="loading">
      <p>Rapport wordt geladen...</p>
    </div>

    <div v-else-if="!reportStore.currentReport" class="error-state">
      <h2>Rapport niet gevonden</h2>
      <p>Het opgevraagde rapport bestaat niet of je hebt geen toegang.</p>
      <button @click="router.push('/cases')" class="btn btn-primary">Terug naar Cases</button>
    </div>

    <div v-else class="report-content">
      <!-- Report Header -->
      <div class="report-header">
        <div class="report-title-section">
          <h1>{{ reportStore.currentReport.title }}</h1>
          <span 
            class="report-status" 
            :class="getStatusClass(reportStore.currentReport.status)"
          >
            {{ reportStore.currentReport.status }}
          </span>
        </div>
        
        <div class="report-actions">
          <!-- Document actions -->
          <div class="action-group">
            <button
              v-if="reportStore.currentReport.status === 'generated'"
              @click="openDownloadDialog"
              class="btn btn-primary"
              :disabled="downloadingReport"
            >
              <span class="icon">📥</span>
              <span v-if="downloadingReport">Bezig...</span>
              <span v-else>Downloaden als DOCX</span>
            </button>
            <button 
              v-if="reportStore.currentReport.status === 'generated'"
              @click="previewFullReport" 
              class="btn btn-secondary"
            >
              <span class="icon">👁️</span> Preview Rapport
            </button>
          </div>
          
          <!-- Navigation and destructive actions -->
          <div class="action-group">
            <button 
              v-if="caseStore.currentCase"
              @click="router.push(`/cases/${caseStore.currentCase.id}`)" 
              class="btn btn-outline"
            >
              <span class="icon">🔙</span> Terug naar Case
            </button>
            <button 
              v-else
              @click="router.push('/cases')" 
              class="btn btn-outline"
            >
              <span class="icon">🔙</span> Terug naar Cases
            </button>
            <button @click="deleteReport" class="btn btn-danger">
              <span class="icon">🗑️</span> Verwijderen
            </button>
          </div>
        </div>
      </div>

      <!-- Alert for errors -->
      <div v-if="error" class="alert alert-danger">
        {{ error }}
        <button @click="error = null" class="close-btn">&times;</button>
      </div>

      <!-- Processing Status -->
      <div 
        v-if="reportStore.currentReport.status === 'processing' || reportStore.currentReport.status === 'generating'" 
        class="processing-status"
      >
        <div class="spinner"></div>
        <p>Rapport wordt gegenereerd. Dit kan enkele minuten duren.</p>
      </div>

      <!-- Error Status -->
      <div 
        v-if="reportStore.currentReport.status === 'failed'" 
        class="error-status"
      >
        <p>Rapport generatie is mislukt.</p>
        <p v-if="reportStore.currentReport.error" class="error-message">
          {{ reportStore.currentReport.error }}
        </p>
      </div>

      <!-- Report Details -->
      <div class="report-details">
        <div class="detail-card">
          <h3>Rapport Informatie</h3>
          <div class="detail-item">
            <div class="detail-label">Titel</div>
            <div class="detail-value">{{ reportStore.currentReport.title }}</div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Template</div>
            <div class="detail-value">
              {{ reportStore.templates[reportStore.currentReport.template_id]?.name || reportStore.currentReport.template_id }}
            </div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Status</div>
            <div class="detail-value" :class="getStatusClass(reportStore.currentReport.status)">
              {{ reportStore.currentReport.status }}
            </div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Aangemaakt</div>
            <div class="detail-value">{{ formatDate(reportStore.currentReport.created_at) }}</div>
          </div>
          <div class="detail-item" v-if="reportStore.currentReport.updated_at">
            <div class="detail-label">Laatst bijgewerkt</div>
            <div class="detail-value">{{ formatDate(reportStore.currentReport.updated_at) }}</div>
          </div>
          
          <!-- No buttons needed here as we have them in the header -->
        </div>

        <div class="detail-card" v-if="caseStore.currentCase">
          <h3>Case Informatie</h3>
          <div class="detail-item">
            <div class="detail-label">Case</div>
            <div class="detail-value">{{ caseStore.currentCase.title }}</div>
          </div>
          <div class="detail-item" v-if="caseStore.currentCase.description">
            <div class="detail-label">Beschrijving</div>
            <div class="detail-value">{{ caseStore.currentCase.description }}</div>
          </div>
        </div>
      </div>

      <!-- Report Content (For generated reports) -->

      <div 
        v-if="reportStore.currentReport.status === 'generated' && reportStore.currentReport.content && Object.keys(reportStore.currentReport.content).length > 0" 
        class="report-sections"
      >
        <h2>Rapport Inhoud</h2>
        
        <!-- Sections Navigation -->
        <div class="sections-nav">
          <button 
            v-for="(content, sectionId) in reportStore.currentReport.content" 
            :key="sectionId"
            class="section-nav-btn"
            :class="{ active: activeSection === sectionId }"
            @click="activeSection = sectionId"
          >
            {{ getSectionTitle(sectionId) }}
          </button>
        </div>
        
        <!-- Active Section Content -->
        <div v-if="activeSection && reportStore.currentReport.content[activeSection]" class="section-content">
          <div class="section-header">
            <h3>{{ getSectionTitle(activeSection) }}</h3>
            <div class="section-actions">
              <button 
                @click="copySectionContent(reportStore.currentReport.content[activeSection])" 
                class="btn btn-primary"
              >
                <span class="icon">📋</span> Kopiëren
              </button>
              <button 
                @click="regenerateSection(activeSection)"
                class="btn btn-secondary"
                :disabled="regeneratingSection === activeSection"
              >
                <span class="icon">🔄</span>
                <span v-if="regeneratingSection === activeSection">Bezig...</span>
                <span v-else>Regenereren</span>
              </button>
              <button 
                @click="toggleMarkdown = !toggleMarkdown"
                class="btn btn-outline"
              >
                <span class="icon">🔍</span> {{ toggleMarkdown ? 'Gewone weergave' : 'Markdown weergave' }}
              </button>
              <button 
                v-if="reportStore.currentReport.metadata?.sections?.[activeSection]?.chunk_ids?.length"
                @click="openSourcesDialog"
                class="btn btn-outline"
              >
                <span class="icon">📄</span> Bronnen
              </button>
            </div>
          </div>
          
          <div class="section-text">
            <!-- Toggle between formatted and raw markdown view -->
            <div v-if="!toggleMarkdown" class="formatted-content">
              <div v-html="formatMarkdown(reportStore.currentReport.content[activeSection])"></div>
            </div>
            <pre v-else class="markdown-content">{{ reportStore.currentReport.content[activeSection] }}</pre>
          </div>

          <!-- Comment System -->
          <CommentSystem 
            v-if="reportStore.currentReport.status === 'generated'"
            :report-id="reportStore.currentReport.id"
            :section-id="activeSection"
            :include-internal="true"
            @comments-updated="handleCommentsUpdated"
          />
          
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
        </div>
        
        <div v-else class="no-section-selected">
          <p>Selecteer een sectie om de inhoud te bekijken.</p>
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
.report-detail-container {
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

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.report-title-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.report-title-section h1 {
  margin: 0;
  color: var(--primary-color);
  font-size: 1.75rem;
  word-break: break-word;
}

.report-status {
  font-size: 0.75rem;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-weight: 500;
  white-space: nowrap;
}

.report-actions {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.action-group {
  display: flex;
  gap: 0.75rem;
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

.processing-status {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem;
  background-color: #eff6ff;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #dbeafe;
  border-radius: 50%;
  border-top-color: #3b82f6;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.processing-status p {
  margin: 0;
  color: #3b82f6;
  font-weight: 500;
}

.error-status {
  padding: 1.5rem;
  background-color: #fef2f2;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.error-status p {
  margin: 0 0 0.5rem 0;
  color: #dc2626;
  font-weight: 500;
}

.error-status .error-message {
  font-weight: normal;
  font-family: monospace;
  background-color: #fee2e2;
  padding: 0.75rem;
  border-radius: 4px;
  white-space: pre-wrap;
  overflow-x: auto;
}

.report-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.detail-card {
  background-color: white;
  border-radius: 8px;
  box-shadow: var(--shadow);
  padding: 1.5rem;
  height: fit-content;
}

.detail-card h3 {
  margin-top: 0;
  margin-bottom: 1.25rem;
  color: var(--primary-color);
  font-size: 1.25rem;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 0.75rem;
}

.detail-item {
  display: flex;
  margin-bottom: 1rem;
}

.detail-label {
  width: 40%;
  font-weight: 500;
  color: var(--text-color);
}

.detail-value {
  width: 60%;
  color: var(--text-color);
  word-break: break-word;
}

.detail-actions {
  margin-top: 1.5rem;
  display: flex;
  justify-content: flex-end;
}

.detail-hint {
  margin-top: 1.5rem;
  text-align: center;
  color: var(--primary-color);
  font-size: 0.9rem;
  font-style: italic;
}

.clickable {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

.back-to-case {
  display: inline-block;
  background-color: #f3f4f6;
  color: var(--primary-color);
  padding: 0.5rem 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  font-weight: 500;
}

.report-sections {
  margin-top: 2rem;
}

.report-sections h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: var(--primary-color);
  font-size: 1.5rem;
}

.sections-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.section-nav-btn {
  padding: 0.75rem 1.25rem;
  background-color: #f3f4f6;
  border: none;
  border-radius: 4px;
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--text-color);
  cursor: pointer;
  transition: all 0.2s;
}

.section-nav-btn:hover {
  background-color: #e5e7eb;
}

.section-nav-btn.active {
  background-color: #dbeafe;
  color: #1d4ed8;
}

.section-content {
  background-color: white;
  border-radius: 8px;
  box-shadow: var(--shadow);
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.section-header h3 {
  margin: 0;
  color: var(--primary-color);
  font-size: 1.25rem;
}

.section-actions {
  display: flex;
  gap: 0.75rem;
}

.section-text {
  line-height: 1.7;
  color: var(--text-color);
  font-size: 1rem;
}

.no-section-selected {
  text-align: center;
  padding: 3rem 1rem;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.no-section-selected p {
  margin: 0;
  color: var(--text-light);
}

.status-processing {
  color: #f59e0b;
}

.status-success {
  color: #10b981;
}

.status-error {
  color: #ef4444;
}

.status-default {
  color: #6b7280;
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: background-color 0.2s;
  white-space: nowrap;
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

.btn-secondary:disabled {
  background-color: #f3f4f6;
  color: #9ca3af;
  cursor: not-allowed;
}

.btn-danger {
  background-color: #ef4444;
  color: white;
}

.btn-danger:hover {
  background-color: #dc2626;
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

.formatted-content {
  line-height: 1.7;
  color: var(--text-color);
}

.formatted-content h1,
.formatted-content h2,
.formatted-content h3,
.formatted-content h4,
.formatted-content h5,
.formatted-content h6 {
  color: var(--primary-color);
  margin-top: 1.5rem;
  margin-bottom: 1rem;
  font-weight: 600;
}

.formatted-content h1 { font-size: 1.5rem; }
.formatted-content h2 { font-size: 1.35rem; }
.formatted-content h3 { font-size: 1.25rem; }
.formatted-content h4 { font-size: 1.15rem; }
.formatted-content h5 { font-size: 1.05rem; }
.formatted-content h6 { font-size: 1rem; }

.formatted-content p {
  margin-bottom: 1rem;
}

.formatted-content ul,
.formatted-content ol {
  margin-bottom: 1rem;
  padding-left: 1.5rem;
}

.formatted-content li {
  margin-bottom: 0.5rem;
}

.formatted-content table {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 1rem;
}

.formatted-content th,
.formatted-content td {
  border: 1px solid #e5e7eb;
  padding: 0.75rem;
  text-align: left;
}

.formatted-content th {
  background-color: #f3f4f6;
  font-weight: 600;
}

.formatted-content blockquote {
  border-left: 4px solid #d1d5db;
  padding-left: 1rem;
  margin-left: 0;
  margin-bottom: 1rem;
  color: #6b7280;
  font-style: italic;
}

.markdown-content {
  background-color: #f8f9fa;
  padding: 1rem;
  border-radius: 4px;
  color: #374151;
  font-family: monospace;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-x: auto;
  margin: 0;
}

.sources-dialog, .preview-dialog {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 100;
}

.dialog-content {
  width: 90%;
  max-width: 800px;
  max-height: 90%;
  background-color: white;
  border-radius: 8px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
}

.preview-content {
  max-width: 900px;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.dialog-header h3 {
  margin: 0;
  color: var(--primary-color);
  font-size: 1.25rem;
}

.dialog-header-actions {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.dialog-body {
  flex: 1;
  padding: 1.5rem;
  overflow-y: auto;
}

.dialog-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: flex-end;
}

/* Preview styles */
.preview-report {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.preview-title-page {
  text-align: center;
  padding: 3rem 1rem;
  border-bottom: 1px solid #e5e7eb;
}

.preview-title-page h1 {
  font-size: 1.75rem;
  color: var(--primary-color);
  margin-bottom: 1rem;
}

.preview-title-page h2 {
  font-size: 1.5rem;
  margin-bottom: 2rem;
}

.preview-date {
  font-style: italic;
  color: #6b7280;
}

.preview-toc {
  padding: 1rem 0;
  border-bottom: 1px solid #e5e7eb;
}

.preview-toc h2 {
  font-size: 1.5rem;
  margin-bottom: 1rem;
  color: var(--primary-color);
}

.toc-list {
  padding-left: 2rem;
}

.toc-list li {
  margin-bottom: 0.5rem;
  color: var(--text-color);
  font-weight: 500;
}

.preview-section {
  padding: 1rem 0;
  border-bottom: 1px solid #e5e7eb;
}

.preview-section h2 {
  font-size: 1.5rem;
  margin-bottom: 1rem;
  color: var(--primary-color);
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 0.5rem;
}

.preview-section-content {
  line-height: 1.7;
}

.no-content {
  padding: 2rem;
  text-align: center;
  color: #6b7280;
  font-style: italic;
}

.loading-sources {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 2rem 0;
}

.no-sources {
  text-align: center;
  padding: 2rem 0;
  color: var(--text-light);
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.source-item {
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
}

.source-header {
  background-color: #f3f4f6;
  padding: 0.75rem 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.source-meta {
  font-size: 0.875rem;
  color: #6b7280;
}

.source-content {
  padding: 1rem;
  background-color: white;
  color: var(--text-color);
  font-size: 0.95rem;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .report-header, .section-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .report-actions {
    width: 100%;
    flex-direction: column;
    gap: 1rem;
  }

  .action-group {
    width: 100%;
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .section-actions {
    width: 100%;
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .detail-item {
    flex-direction: column;
  }
  
  .detail-label, .detail-value {
    width: 100%;
  }
  
  .detail-label {
    margin-bottom: 0.25rem;
  }
  
  .btn {
    width: 100%;
  }
  
  .sections-nav {
    flex-direction: column;
  }
  
  .section-nav-btn {
    width: 100%;
    text-align: left;
  }
  
  .dialog-content {
    width: 95%;
    max-height: 95%;
  }
}

/* Profile styling for report preview */
.preview-title-page {
  padding: 2rem;
  text-align: center;
  margin-bottom: 2rem;
  border-bottom: 1px solid #e0e0e0;
}

.preview-title-page h1 {
  color: var(--primary-color);
  margin-bottom: 1rem;
}

.preview-title-page h2 {
  color: var(--text-color);
  margin-bottom: 1.5rem;
}

.preview-date {
  color: var(--text-light);
  margin-bottom: 2rem;
}

.preview-profile-info {
  margin-top: 3rem;
  text-align: left;
  border-top: 1px solid #e0e0e0;
  padding-top: 2rem;
}

.preview-profile-header {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.preview-logo {
  width: 150px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-logo img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.preview-profile-details {
  flex: 1;
}

.preview-profile-name {
  font-weight: 600;
  font-size: 1.1rem;
  color: var(--text-dark);
  margin: 0 0 0.25rem 0;
}

.preview-profile-jobtitle {
  color: var(--text-color);
  margin: 0 0 0.25rem 0;
}

.preview-profile-certification {
  color: var(--text-color);
  font-style: italic;
  margin: 0;
}

.preview-company-info {
  border-top: 1px solid #e5e7eb;
  padding-top: 1rem;
}

.preview-company-name {
  font-weight: 600;
  color: var(--text-dark);
  margin: 0 0 0.5rem 0;
}

.preview-company-address p {
  margin: 0 0 0.5rem 0;
  color: var(--text-color);
}

.preview-company-contact p {
  margin: 0 0 0.25rem 0;
  color: var(--text-color);
  font-size: 0.9rem;
}

/* Download dialog styling */
.download-dialog .dialog-content {
  max-width: 650px;
}

.layout-options {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-top: 1rem;
}

.layout-option {
  display: flex;
  gap: 1.5rem;
  padding: 1rem;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.layout-option:hover {
  background-color: #f8fafc;
}

.layout-option.selected {
  border-color: #3b82f6;
  background-color: #f0f7ff;
}

.layout-preview {
  width: 180px;
  height: 120px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: white;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
}

.layout-preview-image {
  width: 85%;
  height: 85%;
  background-color: white;
  display: flex;
  flex-direction: column;
}

.layout-details {
  flex: 1;
}

.layout-details h4 {
  margin: 0 0 0.5rem 0;
  color: var(--text-dark);
}

.layout-details p {
  margin: 0;
  color: var(--text-color);
  font-size: 0.9rem;
}

/* Layout previews */
.preview-page {
  width: 100%;
  height: 100%;
  background-color: white;
  border: 1px solid #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.preview-title, .preview-title-modern, .preview-title-professional {
  height: 10%;
  background-color: #f8f9fa;
  margin: 4px;
  border-radius: 2px;
}

.preview-title-modern {
  background-color: #dbeafe;
  height: 12%;
}

.preview-title-professional {
  background-color: #1e40af;
  height: 15%;
}

.preview-header {
  height: 15%;
  background-color: #f9fafb;
  margin: 0 4px 8px 4px;
  border-radius: 2px;
  display: flex;
  align-items: center;
}

.preview-header.modern {
  background-color: #eff6ff;
  display: flex;
  justify-content: flex-end;
}

.preview-header.professional {
  background-color: #f1f5f9;
  height: 20%;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.preview-logo-small {
  width: 20%;
  height: 80%;
  background-color: #e5e7eb;
  margin-left: 5px;
  border-radius: 2px;
}

.preview-logo-right {
  width: 20%;
  height: 80%;
  background-color: #3b82f6;
  margin-right: 5px;
  border-radius: 2px;
}

.preview-logo-large {
  width: 30%;
  height: 80%;
  background-color: #334155;
  margin: 5px;
  border-radius: 2px;
}

.preview-company-info {
  width: 50%;
  height: 80%;
  margin: 5px;
  background-color: #e2e8f0;
  border-radius: 2px;
}

.preview-header-text {
  width: 60%;
  height: 60%;
  background-color: #f3f4f6;
  margin-left: 10px;
  border-radius: 2px;
}

.preview-body {
  height: 75%;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 4px;
}

.preview-body.professional {
  height: 65%;
}

.preview-section-header {
  height: 8px;
  background-color: #f3f4f6;
  width: 40%;
  margin: 4px 0;
  border-radius: 1px;
}

.preview-section-header.modern {
  background-color: #3b82f6;
  height: 6px;
}

.preview-section-header.professional {
  background-color: #1e293b;
  width: 50%;
  height: 10px;
}

.preview-line {
  height: 5px;
  background-color: #e5e7eb;
  width: 100%;
  border-radius: 1px;
}

.preview-line.modern {
  height: 4px;
  background-color: #dbeafe;
}

.preview-line.professional {
  height: 6px;
  background-color: #cbd5e1;
}

.preview-line.short {
  width: 70%;
}

.spinner.small {
  width: 16px;
  height: 16px;
  border-width: 2px;
  margin-right: 0.25rem;
}
</style>