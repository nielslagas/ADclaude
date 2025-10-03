<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useReportStore } from '@/stores/report';
import { useCaseStore } from '@/stores/case';
import { useNotificationStore } from '@/stores/notification';
import { marked } from 'marked'; // Dit moet geïnstalleerd worden via npm install marked
import CommentSystem from '@/components/CommentSystem.vue';
import ExportDialog from '@/components/ExportDialog.vue';
import StaticADReportTemplate from '@/components/StaticADReportTemplate.vue';
import { getFullApiUrl } from '@/services/api';

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
const generatingStructured = ref(false);

// Structured content variables
const structuredContent = ref<any>(null);
const useStructuredContent = ref(true);
const structuredFormat = ref('html');

// Static template variables
const useStaticTemplate = ref(true); // Default to true for new consistent view
const staticTemplateData = ref<any>(null);

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
// Transform report content to StaticADReportTemplate format
const transformReportToStaticTemplate = (report: any) => {
  // First check if we have structured_data from the backend
  if (report.content?.structured_data) {
    console.log('Using structured_data from backend:', report.content.structured_data)
    return report.content.structured_data
  }
  
  if (!report || !report.content) {
    console.warn('No report content to transform')
    return null
  }
  
  console.log('Transforming report for static template:', Object.keys(report.content))
  
  // Extract text content from report sections
  const extractContent = (sectionContent: any) => {
    if (typeof sectionContent === 'string') return sectionContent
    if (sectionContent && typeof sectionContent === 'object') {
      if (sectionContent.content) return sectionContent.content
      if (sectionContent.text) return sectionContent.text
    }
    return String(sectionContent || '')
  }
  
  // Parse names from content 
  const extractNameFromContent = (content: string) => {
    const matches = content.match(/(?:naam|werknemer)[:\s]*([^\n\r,]{2,50})/i)
    return matches ? matches[1].trim() : null
  }
  
  const extractCompanyFromContent = (content: string) => {
    const matches = content.match(/(?:bedrijf|werkgever|organisatie)[:\s]*([^\n\r,]{2,50})/i)
    return matches ? matches[1].trim() : null
  }
  
  // Get case data if available
  const caseData = caseStore.currentCase || {}
  
  // Create template data structure
  const templateData = {
    werknemer: {
      naam: extractNameFromContent(extractContent(report.content.gegevensverzameling_werknemer || '')) || 
            caseData.werknemer_naam || 
            `Uit case: ${caseData.title || 'Onbekend'}`,
      geboortedatum: caseData.werknemer_geboortedatum || '[Te bepalen]',
      adres: caseData.werknemer_adres || '[Te bepalen]',
      postcode_plaats: caseData.werknemer_postcode_plaats || '[Te bepalen]',
      telefoonnummer: caseData.werknemer_telefoonnummer || '[Te bepalen]',
      email: caseData.werknemer_email || '[Te bepalen]'
    },
    werkgever: {
      naam: extractCompanyFromContent(extractContent(report.content.gegevensverzameling_werkgever || '')) || 
            caseData.werkgever_naam || 
            caseData.title || 
            '[Bedrijf uit case titel]',
      contactpersoon: caseData.werkgever_contactpersoon || '[Te bepalen]',
      functie_contactpersoon: caseData.werkgever_functie_contactpersoon || '[Te bepalen]',
      adres: caseData.werkgever_adres || '[Te bepalen]',
      postcode_plaats: caseData.werkgever_postcode_plaats || '[Te bepalen]',
      telefoonnummer: caseData.werkgever_telefoonnummer || '[Te bepalen]',
      email: caseData.werkgever_email || '[Te bepalen]'
    },
    adviseur: {
      naam: '[Uit gebruikersprofiel]', // Will be filled by StaticADReportTemplate
      titel: 'Gecertificeerd Register Arbeidsdeskundige',
      bedrijf: '[Uit gebruikersprofiel]',
      telefoonnummer: '[Uit gebruikersprofiel]'
    },
    onderzoek: {
      datum_onderzoek: new Date().toLocaleDateString('nl-NL'),
      datum_rapportage: new Date().toLocaleDateString('nl-NL')
    },
    samenvatting: {
      vraagstelling: [
        'Kan werknemer het eigen werk bij de eigen werkgever nog uitvoeren?',
        'Zo nee, is het eigen werk met behulp van aanpassingen passend te maken?',
        'Zo nee, kan werknemer ander werk bij de eigen werkgever uitvoeren?',
        'Zo nee, zijn er mogelijkheden om werknemer naar ander werk te begeleiden en is een vervolgtraject gewenst?'
      ],
      conclusie: report.content.conclusie ? 
                [extractContent(report.content.conclusie)] : 
                ['Conclusie wordt gegenereerd uit rapport inhoud...']
    },
    rapportage: {
      vraagstelling: [
        'Kan werknemer het eigen werk bij de eigen werkgever nog uitvoeren?',
        'Zo nee, is het eigen werk met behulp van aanpassingen passend te maken?',
        'Zo nee, kan werknemer ander werk bij de eigen werkgever uitvoeren?',
        'Zo nee, zijn er mogelijkheden om werknemer naar ander werk te begeleiden en is een vervolgtraject gewenst?'
      ],
      activiteiten: report.content.ondernomen_activiteiten ? 
                   extractContent(report.content.ondernomen_activiteiten).split('\n').filter(line => line.trim().length > 5) :
                   [
                     'Voorbereiding (dossieronderzoek) op [datum].',
                     'Bestuderen informatie van de bedrijfsarts op [datum].',
                     'Overleg met bedrijfsarts op [datum].',
                     'Gesprek met werknemer op [datum] op de werklocatie.',
                     'Gesprek met werkgever op [datum] op de werklocatie.',
                     'Overleg met werknemer en werkgever gezamenlijk op [datum].',
                     'Rapportage opstellen op [datum].'
                   ]
    },
    gegevensverzameling: {
      voorgeschiedenis: extractContent(report.content.gegevensverzameling_voorgeschiedenis) || 
                       'Uit dossieronderzoek blijkt relevante voorgeschiedenis voor dit arbeidsdeskundig onderzoek.',
      verzuimhistorie: extractContent(report.content.belastbaarheid) || 
                      'Verzuimhistorie wordt geanalyseerd op basis van beschikbare gegevens.',
      werkgever: {
        aard_bedrijf: extractContent(report.content.gegevensverzameling_werkgever) || '[Aard bedrijf uit analyse]',
        omvang_bedrijf: '[Omvang bedrijf]',
        aantal_werknemers: '[Aantal werknemers]',
        functies_beschrijving: '[Functies beschrijving uit analyse]',
        overige_informatie: '[Website/overige info]'
      },
      werknemer: {
        opleidingen: [
          { naam: '[Opleiding uit analyse]', richting: '[Richting]', diploma_jaar: '[Jaar]' },
          { naam: '[Aanvullende cursussen]', richting: '[Richting]', diploma_jaar: '[Jaar]' }
        ],
        arbeidsverleden: [
          { periode: '[Van/tot datum]', werkgever: '[Werkgever]', functie: '[Functie uit analyse]' }
        ],
        computervaardigheden: 'Goed',
        taalvaardigheid: 'Goed', 
        rijbewijs: '[Rijbewijs informatie]'
      },
      belastbaarheid: {
        beschrijving: extractContent(report.content.belastbaarheid) || 
                     'Belastbaarheidsanalyse gebaseerd op arbeidsdeskundig onderzoek.',
        persoonlijk_functioneren: [
          {
            nummer: '2.',
            beschrijving: 'Verdelen van de aandacht: [beschrijving van beperkingen]',
            mate_beperking: 'Beperkt'
          }
        ],
        sociaal_functioneren: [
          {
            nummer: '6.',
            beschrijving: 'Emotionele problemen van anderen hanteren: [beschrijving van beperkingen]',
            mate_beperking: 'Beperkt'
          }
        ],
        fysieke_omgeving: 'Niet beperkt',
        dynamische_handelingen: 'Niet beperkt',
        statische_houdingen: 'Niet beperkt',
        werktijden: 'Er zijn beperkingen in werktijden...',
        prognose: extractContent(report.content.visie_ad_duurzaamheid) || 
                 'Prognose gebaseerd op arbeidsdeskundige beoordeling.'
      }
    },
    // Store reference to original content for debugging
    _originalReport: report,
    _availableSections: Object.keys(report.content)
  }
  
  console.log('Transformed template data:', templateData)
  return templateData
}

const fetchReport = async () => {
  if (!reportId.value) return;
  
  loading.value = true;
  try {
    const report = await reportStore.fetchReport(reportId.value);
    
    // If report is complete, prepare content
    if (report.status === 'generated') {
      // Transform report for static template
      if (useStaticTemplate.value) {
        staticTemplateData.value = transformReportToStaticTemplate(report);
        console.log('Static template data prepared:', staticTemplateData.value);
      }
      
      // Try to load structured content if enabled
      if (useStructuredContent.value) {
        try {
          console.log('Loading structured content for report:', reportId.value);
          const structuredData = await reportStore.fetchStructuredReport(reportId.value, structuredFormat.value);
          structuredContent.value = structuredData;
          console.log('Structured content loaded successfully');
        } catch (err) {
          console.warn('Failed to load structured content, falling back to regular content:', err);
          useStructuredContent.value = false;
          structuredContent.value = null;
        }
      }
    }
    
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

// Enhanced markdown formatting for professional reports
const formatMarkdown = (content: string) => {
  if (!content) return '';
  
  try {
    // Configure marked for professional output
    marked.setOptions({
      breaks: true,
      gfm: true,
      headerIds: false,
      mangle: false
    });
    
    // Clean and process content for better presentation
    let processedContent = content
      // Fix common formatting issues
      .replace(/\n\n\n+/g, '\n\n')  // Remove excessive line breaks
      .replace(/^\s+/gm, '')        // Remove leading whitespace
      .replace(/\s+$/gm, '')        // Remove trailing whitespace
      // Improve list formatting
      .replace(/^[-*]\s+/gm, '• ')  // Standardize bullet points
      // Fix paragraph spacing
      .replace(/([.!?])\s*\n([A-Z])/g, '$1\n\n$2');  // Add paragraph breaks after sentences
    
    const html = marked(processedContent);
    
    // Post-process HTML for better styling
    return html
      .replace(/<p>/g, '<p class="report-paragraph">')
      .replace(/<ul>/g, '<ul class="report-list">')
      .replace(/<ol>/g, '<ol class="report-list">')
      .replace(/<li>/g, '<li class="report-list-item">');
      
  } catch (e) {
    console.error('Error parsing markdown:', e);
    // Fallback: simple line break replacement with paragraph structure
    return content
      .split('\n\n')
      .map(paragraph => paragraph.trim())
      .filter(paragraph => paragraph.length > 0)
      .map(paragraph => `<p class="report-paragraph">${paragraph.replace(/\n/g, '<br>')}</p>`)
      .join('');
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
  // Use professional titles first
  const professionalTitles = getProfessionalSectionTitles();
  if (professionalTitles[sectionId]) {
    return professionalTitles[sectionId];
  }
  
  // Legacy section titles for arbeidsdeskundig rapport (fallback)
  const sectionTitles: Record<string, string> = {
    'samenvatting': 'Samenvatting',
    'aanleiding': 'Aanleiding en Onderzoeksvraag',
    'belastbaarheid': 'Analyse Belastbaarheid',
    'visie_ad': 'Arbeidsdeskundige Visie',
    'matching': 'Matching en Aanbevelingen',
    'conclusie': 'Conclusies en Advies'
  };
  
  // Return section title or fallback to template
  if (sectionTitles[sectionId]) {
    return sectionTitles[sectionId];
  }
  
  // Fallback to template if available
  if (
    reportStore.currentReport && 
    reportStore.templates[reportStore.currentReport.template_id] &&
    reportStore.templates[reportStore.currentReport.template_id].sections[sectionId]
  ) {
    return reportStore.templates[reportStore.currentReport.template_id].sections[sectionId].title;
  }
  
  return sectionId;
};

// Get profile logo URL from user profile data
const getProfileLogoUrl = (userProfile: any) => {
  if (!userProfile) return null;
  
  // Check different possible logo path formats
  if (userProfile.logo_path) {
    // Extract filename from full path
    const filename = userProfile.logo_path.split('/').pop() || userProfile.logo_path;
    return getFullApiUrl(`/api/v1/profiles/logo/${filename}`);
  }
  
  // Check if there's a logo object with storage_path
  if (userProfile.logo && userProfile.logo.storage_path) {
    const filename = userProfile.logo.storage_path.split('/').pop() || userProfile.logo.storage_path;
    return getFullApiUrl(`/api/v1/profiles/logo/${filename}`);
  }
  
  // Check if there's a logo_url already available
  if (userProfile.logo_url) {
    return getFullApiUrl(userProfile.logo_url);
  }
  
  return null;
};

// Extract title from markdown content for TOC
const extractContentTitle = (sectionId: string) => {
  // Always use professional section titles for consistency
  return getSectionTitle(sectionId);
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

// Selected layout for preview AND download
const selectedLayout = ref('standaard');
const previewLayout = ref('standaard');

// Available layout options with detailed descriptions
const layoutOptions = [
  { 
    id: 'standaard', 
    name: 'Standaard', 
    description: 'Traditionele Nederlandse rapport opmaak met genummerde secties'
  },
  { 
    id: 'modern', 
    name: 'Modern', 
    description: 'Moderne layout met verbeterde visuele hiërarchie en kleuren'
  },
  { 
    id: 'professioneel', 
    name: 'Professioneel', 
    description: 'Formele layout geschikt voor juridische en officiële documenten'
  },
  { 
    id: 'compact', 
    name: 'Compact', 
    description: 'Ruimtebesparende layout met kleinere marges en tekst'
  }
];

// Enhanced export dialog
const showExportDialog = ref(false);

// Show download options dialog (legacy)
const showDownloadDialog = ref(false);

// Store whether preview was open
const wasPreviewOpen = ref(false);

// Open enhanced export dialog
const openExportDialog = () => {
  // If preview dialog is open, close it temporarily
  wasPreviewOpen.value = showPreviewDialog.value;
  if (wasPreviewOpen.value) {
    showPreviewDialog.value = false;
  }

  // Show enhanced export dialog
  showExportDialog.value = true;
};

// Open download options dialog (legacy - redirect to enhanced dialog)
const openDownloadDialog = () => {
  openExportDialog();
};

// Close enhanced export dialog
const closeExportDialog = () => {
  showExportDialog.value = false;

  // Restore preview dialog if it was open
  if (wasPreviewOpen.value) {
    showPreviewDialog.value = true;
    wasPreviewOpen.value = false;
  }
};

// Handle successful export
const handleExportSuccess = (details: { format: string; template: string; filename: string }) => {
  console.log('Export completed:', details);
  
  notificationStore.addNotification({
    type: 'success',
    title: 'Export voltooid',
    message: `Het rapport is succesvol geëxporteerd als ${details.format.toUpperCase()} bestand met ${details.template} template.`
  });
};

// Close download options dialog (legacy)
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

// Preview report with layout selection
const previewFullReport = async (layout = 'standaard') => {
  if (!reportStore.currentReport) return;
  
  try {
    // Set preview layout
    previewLayout.value = layout;
    
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

// Determine if template should show custom headers
const shouldShowCustomHeader = (layout: string) => {
  return layout === 'modern' || layout === 'professioneel';
};

// Smart Content Parser - converts LLM markdown to structured data
const parseContentToStructuredData = (content: string, sectionType: string) => {
  if (!content) return null;

  // Remove ALL headers first to avoid duplicates
  let cleanContent = content.replace(/^#{1,6}\s+[^\n]*\n?/gm, '');
  
  switch (sectionType) {
    case 'persoonsgegevens':
      return parsePersonalInfo(cleanContent);
    case 'werkgever_functie':
      return parseEmployerInfo(cleanContent);
    case 'belastbaarheid':
      return parseWorkability(cleanContent);
    case 'matching':
      return parseMatchingCriteria(cleanContent);
    case 'medische_situatie':
      return parseMedicalInfo(cleanContent);
    case 'arbeidsverleden':
      return parseWorkHistory(cleanContent);
    case 'samenvatting':
    case 'conclusie':
    case 'visie_ad':
    case 'aanleiding':
      return parseSummaryContent(cleanContent, sectionType);
    default:
      return { type: 'text', content: cleanContent };
  }
};

// Parse personal information into structured data
const parsePersonalInfo = (content: string) => {
  const data = {
    type: 'personal_info',
    name: extractPattern(content, /(?:naam|heer|mevrouw)\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/i),
    birthDate: extractPattern(content, /(?:geboren|geboortedatum)\s*:?\s*(?:op\s+)?(\d{1,2}[-\s]\d{1,2}[-\s]\d{4}|\d{1,2}\s+\w+\s+\d{4})/i),
    address: extractPattern(content, /(?:woonachtig|adres)\s*:?\s*(?:aan\s+)?([^,\n]+)/i),
    postalCode: extractPattern(content, /(\d{4}\s*[A-Z]{2})/),
    city: extractPattern(content, /\d{4}\s*[A-Z]{2}\s*(?:te\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/i),
    phone: extractPattern(content, /(?:telefoon|tel)\s*:?\s*([\d\s\-\+\(\)]+)/i),
    email: extractPattern(content, /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)/),
    content: content
  };
  return data;
};

// Parse employer and job information
const parseEmployerInfo = (content: string) => {
  return {
    type: 'employer_info',
    employer: extractPattern(content, /(?:werkgever|bedrijf|organisatie)\s*:?\s*([^\n,]+)/i),
    position: extractPattern(content, /(?:functie|functietitel|werkzaam als)\s*:?\s*([^\n,]+)/i),
    department: extractPattern(content, /(?:afdeling|team)\s*:?\s*([^\n,]+)/i),
    startDate: extractPattern(content, /(?:sinds|vanaf|dienstverband)\s*:?\s*(\d{1,2}[-\s]\d{1,2}[-\s]\d{4}|\d{1,2}\s+\w+\s+\d{4})/i),
    contract: extractPattern(content, /(?:contract|dienstverband)\s*:?\s*([^\n,]+)/i),
    content: content
  };
};

// Parse workability with percentages and capabilities
const parseWorkability = (content: string) => {
  const percentages = content.match(/(\d{1,3})%/g) || [];
  const capabilities = [];
  const restrictions = [];
  
  // Extract bullet points for capabilities/restrictions
  const lines = content.split('\n');
  for (const line of lines) {
    if (line.trim().startsWith('-') || line.trim().startsWith('•')) {
      const item = line.replace(/^[-•]\s*/, '').trim();
      if (item.toLowerCase().includes('kan') || item.toLowerCase().includes('mogelijk')) {
        capabilities.push(item);
      } else if (item.toLowerCase().includes('niet') || item.toLowerCase().includes('beperkt')) {
        restrictions.push(item);
      }
    }
  }

  return {
    type: 'workability',
    percentages: percentages.map(p => parseInt(p.replace('%', ''))),
    capabilities: capabilities,
    restrictions: restrictions,
    content: content
  };
};

// Parse matching criteria into structured format
const parseMatchingCriteria = (content: string) => {
  const criteria = [];
  const lines = content.split('\n');
  
  for (const line of lines) {
    if (line.trim().startsWith('-') || line.trim().startsWith('•')) {
      const item = line.replace(/^[-•]\s*/, '').trim();
      const priority = item.includes('(E)') ? 'essential' : item.includes('(W)') ? 'desired' : 'normal';
      criteria.push({
        text: item.replace(/\([EW]\)/g, '').trim(),
        priority: priority
      });
    }
  }

  return {
    type: 'matching_criteria',
    criteria: criteria,
    content: content
  };
};

// Parse medical information
const parseMedicalInfo = (content: string) => {
  return {
    type: 'medical_info',
    diagnosis: extractPattern(content, /(?:diagnose|klachten)\s*:?\s*([^\n]+)/i),
    startDate: extractPattern(content, /(?:sinds|vanaf)\s*:?\s*(\d{1,2}[-\s]\d{1,2}[-\s]\d{4}|\d{1,2}\s+\w+\s+\d{4})/i),
    symptoms: extractListItems(content),
    content: content
  };
};

// Parse work history
const parseWorkHistory = (content: string) => {
  return {
    type: 'work_history',
    positions: extractListItems(content),
    content: content
  };
};

// Parse summary/conclusion content with highlights
const parseSummaryContent = (content: string, sectionType: string) => {
  // Extract key points and recommendations
  const keyPoints = [];
  const recommendations = [];
  
  const lines = content.split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('-') || trimmed.startsWith('•')) {
      const item = trimmed.replace(/^[-•]\s*/, '');
      if (item.toLowerCase().includes('aanbeveling') || item.toLowerCase().includes('advies')) {
        recommendations.push(item);
      } else {
        keyPoints.push(item);
      }
    }
  }

  return {
    type: 'summary_content',
    sectionType: sectionType,
    keyPoints: keyPoints,
    recommendations: recommendations,
    content: content
  };
};

// Helper function to extract patterns
const extractPattern = (text: string, pattern: RegExp): string | null => {
  const match = text.match(pattern);
  return match ? match[1].trim() : null;
};

// Helper function to extract list items
const extractListItems = (text: string): string[] => {
  const lines = text.split('\n');
  const items = [];
  for (const line of lines) {
    if (line.trim().startsWith('-') || line.trim().startsWith('•')) {
      items.push(line.replace(/^[-•]\s*/, '').trim());
    }
  }
  return items;
};

// Professional section order based on Dutch AD standards
const getProfessionalSectionOrder = () => {
  return [
    'vraagstelling',
    'ondernomen_activiteiten',
    'gegevensverzameling_voorgeschiedenis',
    'gegevensverzameling_werkgever', 
    'gegevensverzameling_werknemer',
    'belastbaarheid',
    'eigen_functie',
    'gesprek_werkgever',
    'gesprek_werknemer',
    'gesprek_gezamenlijk',
    'visie_ad_eigen_werk',
    'visie_ad_aanpassing',
    'visie_ad_ander_werk_eigen',
    'visie_ad_ander_werk_extern',
    'visie_ad_duurzaamheid',
    'advies',
    'conclusie',
    'vervolg'
  ];
};

// Professional section titles mapping
const getProfessionalSectionTitles = () => {
  return {
    'vraagstelling': '1. Vraagstelling',
    'ondernomen_activiteiten': '2. Ondernomen activiteiten',
    'gegevensverzameling_voorgeschiedenis': '3.1 Voorgeschiedenis',
    'gegevensverzameling_werkgever': '3.2 Gegevens werkgever',
    'gegevensverzameling_werknemer': '3.3 Gegevens werknemer',
    'belastbaarheid': '3.4 Belastbaarheid van werknemer',
    'eigen_functie': '3.5 Eigen functie werknemer',
    'gesprek_werkgever': '3.6 Gesprek met de werkgever',
    'gesprek_werknemer': '3.7 Gesprek met werknemer',
    'gesprek_gezamenlijk': '3.8 Gesprek met werkgever en werknemer gezamenlijk',
    'visie_ad_eigen_werk': '4.1 Geschiktheid voor eigen werk',
    'visie_ad_aanpassing': '4.2 Aanpassing eigen werk',
    'visie_ad_ander_werk_eigen': '4.3 Geschiktheid voor ander werk bij eigen werkgever',
    'visie_ad_ander_werk_extern': '4.4 Geschiktheid voor ander werk bij andere werkgever',
    'visie_ad_duurzaamheid': '4.5 Duurzaamheid van herplaatsing',
    'advies': '5. Advies',
    'conclusie': '6. Conclusie',
    'vervolg': '7. Vervolg'
  };
};

// Removed duplicate - using getOrderedSectionsOld as main function

// Get professional section title or fall back to generated title
const getProfessionalSectionTitle = (sectionId: string): string => {
  const professionalTitles = getProfessionalSectionTitles();
  
  if (professionalTitles[sectionId]) {
    return professionalTitles[sectionId];
  }
  
  // Fallback to existing getSectionTitle function
  return getSectionTitle(sectionId);
};

// Smart content processing - preserve section titles but remove duplicate headers
const processContentForTemplate = (content: string, layout: string) => {
  if (!content) return '';
  
  let processedContent = content;
  
  // Only remove headers if using CSS-generated headers (Standaard & Compact templates)
  if (layout === 'standaard' || layout === 'compact') {
    // Remove ALL markdown headers (H1-H6) to avoid duplicates with CSS section headers
    processedContent = processedContent.replace(/^#{1,6}\s+[^\n]*\n?/gm, '');
    
    // Remove HTML headers that might be generated
    processedContent = processedContent.replace(/<h[1-6][^>]*>.*?<\/h[1-6]>/gi, '');
    
    // Remove bold text that appears as standalone headers
    processedContent = processedContent.replace(/^\*\*([^*]+)\*\*\s*$/gm, '');
  } else {
    // For Modern & Professioneel templates, only remove H1 (section title level)
    processedContent = processedContent.replace(/^#\s+[^\n]*\n?/gm, '');
  }
  
  // Clean up excessive line breaks
  processedContent = processedContent.replace(/\n\n+/g, '\n\n');
  
  return processedContent.trim();
};

// New function to get structured or fallback content
const getSectionContent = (sectionId: string, layout: string) => {
  // If structured content is available, use it
  if (useStructuredContent.value && structuredContent.value && structuredContent.value.content && structuredContent.value.content[sectionId]) {
    const content = structuredContent.value.content[sectionId];
    console.log(`Using structured content for section ${sectionId}:`, typeof content, content.length);
    
    // If it's already HTML (from structured format), return as-is
    if (structuredFormat.value === 'html') {
      return { content: content, isHtml: true };
    }
    
    // If it's markdown, process it
    if (structuredFormat.value === 'markdown') {
      return { content: processContentForTemplate(content, layout), isHtml: false };
    }
    
    // For other formats, return as-is
    return { content: content, isHtml: false };
  }
  
  // Fallback to regular content processing
  const fallbackContent = reportStore.currentReport?.content?.[sectionId] || '';
  console.log(`Using fallback content for section ${sectionId}:`, typeof fallbackContent, fallbackContent.length);
  return { content: processContentForTemplate(fallbackContent, layout), isHtml: false };
};

// Close the preview dialog
const closePreviewDialog = () => {
  showPreviewDialog.value = false;
};

// Print the preview content
const printPreview = () => {
  window.print();
};

// Check if we should use modern renderer or fallback to legacy
const shouldUseModernRenderer = (sectionId: string) => {
  try {
    // Test if we can parse the content
    const content = reportStore.currentReport?.content?.[sectionId];
    if (!content) return false;
    
    const structuredData = parseContentToStructuredData(content, sectionId);
    
    // Use modern renderer for structured content types
    const modernTypes = ['personal_info', 'employer_info', 'workability', 'matching_criteria', 'medical_info', 'work_history', 'samenvatting', 'belastbaarheid', 'visie_ad', 'matching'];
    return structuredData && modernTypes.includes(structuredData.type);
  } catch (error) {
    console.log('Modern renderer fallback for section:', sectionId, error);
    return false;
  }
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

// Get ordered sections for the report preview (replace old implementation)
const getOrderedSections = () => {
  // Professional Dutch AD report structure
  const professionalOrder = getProfessionalSectionOrder();
  
  // If no report, return empty array
  if (!reportStore.currentReport || !reportStore.currentReport.content) {
    console.log("No report content available");
    return [];
  }
  
  const contentKeys = Object.keys(reportStore.currentReport.content);
  console.log("Report content keys:", contentKeys);
  
  // Filter professional order to only include available sections
  const availableSections = professionalOrder.filter(sectionId => 
    reportStore.currentReport.content[sectionId] !== undefined
  );
  
  console.log("Available professional sections:", availableSections);
  
  // Add any remaining sections that aren't in the professional order (legacy sections)
  const remainingSections = contentKeys.filter(sectionId => 
    !professionalOrder.includes(sectionId) && sectionId !== 'rapport_header'
  );
  
  const allOrderedSections = [...availableSections, ...remainingSections];
  
  // Fallback: if no ordered sections found, use all available content keys
  if (allOrderedSections.length === 0 && contentKeys.length > 0) {
    console.log("No ordered sections found, using all available content keys");
    return contentKeys.filter(key => key !== 'rapport_header'); // Skip header
  }
  
  return allOrderedSections;
};

// Handle comments updated event
const handleCommentsUpdated = (count: number) => {
  console.log(`Comments updated: ${count} comments for section ${activeSection.value}`);
  // Could add UI feedback here, such as showing comment count in section header
};

// Keyboard navigation for section tabs (WCAG compliance)
const handleTabKeydown = (event: KeyboardEvent, sectionId: string, currentIndex: number) => {
  const sections = reportSections.value;
  let newIndex = currentIndex;
  
  switch (event.key) {
    case 'ArrowRight':
    case 'ArrowDown':
      event.preventDefault();
      newIndex = currentIndex < sections.length - 1 ? currentIndex + 1 : 0;
      break;
    case 'ArrowLeft':
    case 'ArrowUp':
      event.preventDefault();
      newIndex = currentIndex > 0 ? currentIndex - 1 : sections.length - 1;
      break;
    case 'Home':
      event.preventDefault();
      newIndex = 0;
      break;
    case 'End':
      event.preventDefault();
      newIndex = sections.length - 1;
      break;
    case 'Enter':
    case ' ':
      event.preventDefault();
      activeSection.value = sectionId;
      // Focus the content panel
      nextTick(() => {
        const panel = document.getElementById(`section-panel-${sectionId}`);
        if (panel) panel.focus();
      });
      return;
    default:
      return;
  }
  
  // Focus the new tab
  const newSectionId = sections[newIndex];
  const newTab = document.getElementById(`section-tab-${newSectionId}`);
  if (newTab) {
    newTab.focus();
  }
};

// Skip to main content functionality
const skipToMainContent = () => {
  const mainTitle = document.getElementById('report-title');
  if (mainTitle) {
    mainTitle.focus();
  }
};

// Generate structured data for the report
const generateStructuredData = async () => {
  if (!reportStore.currentReport) return;
  
  generatingStructured.value = true;
  
  try {
    const result = await reportStore.generateStructuredReport(reportId.value);
    
    notificationStore.addNotification({
      type: 'success',
      title: 'Structured data generatie gestart',
      message: 'Het systeem genereert nu gestructureerde data voor het formulier. Dit kan enkele minuten duren.'
    });
    
    // Start polling for status
    startStatusPolling();
  } catch (err) {
    console.error('Error generating structured data:', err);
    notificationStore.addNotification({
      type: 'error',
      title: 'Fout bij genereren structured data',
      message: 'Er is een fout opgetreden bij het genereren van gestructureerde data.'
    });
  } finally {
    generatingStructured.value = false;
  }
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

// Modern Content Renderer Component (inline for now)
const ModernContentRenderer = {
  props: {
    sectionId: String,
    sectionData: Object,
    layout: String
  },
  template: `
    <div class="modern-content">
      <!-- Personal Info Table -->
      <div v-if="sectionData?.type === 'personal_info'" class="personal-info-table">
        <h3 class="section-subtitle">Persoonsgegevens</h3>
        <table class="info-table">
          <tr v-if="sectionData.name">
            <td class="label">Naam:</td>
            <td class="value">{{ sectionData.name }}</td>
          </tr>
          <tr v-if="sectionData.birthDate">
            <td class="label">Geboortedatum:</td>
            <td class="value">{{ sectionData.birthDate }}</td>
          </tr>
          <tr v-if="sectionData.address">
            <td class="label">Adres:</td>
            <td class="value">{{ sectionData.address }}</td>
          </tr>
          <tr v-if="sectionData.postalCode || sectionData.city">
            <td class="label">Postcode/Plaats:</td>
            <td class="value">{{ sectionData.postalCode }} {{ sectionData.city }}</td>
          </tr>
          <tr v-if="sectionData.phone">
            <td class="label">Telefoon:</td>
            <td class="value">{{ sectionData.phone }}</td>
          </tr>
          <tr v-if="sectionData.email">
            <td class="label">E-mail:</td>
            <td class="value">{{ sectionData.email }}</td>
          </tr>
        </table>
      </div>

      <!-- Employer Info Table -->
      <div v-else-if="sectionData?.type === 'employer_info'" class="employer-info-table">
        <h3 class="section-subtitle">Werkgever en Functie</h3>
        <table class="info-table">
          <tr v-if="sectionData.employer">
            <td class="label">Werkgever:</td>
            <td class="value">{{ sectionData.employer }}</td>
          </tr>
          <tr v-if="sectionData.position">
            <td class="label">Functie:</td>
            <td class="value">{{ sectionData.position }}</td>
          </tr>
          <tr v-if="sectionData.department">
            <td class="label">Afdeling:</td>
            <td class="value">{{ sectionData.department }}</td>
          </tr>
          <tr v-if="sectionData.startDate">
            <td class="label">Sinds:</td>
            <td class="value">{{ sectionData.startDate }}</td>
          </tr>
          <tr v-if="sectionData.contract">
            <td class="label">Contract:</td>
            <td class="value">{{ sectionData.contract }}</td>
          </tr>
        </table>
      </div>

      <!-- Workability with Progress Bars -->
      <div v-else-if="sectionData?.type === 'workability'" class="workability-section">
        <h3 class="section-subtitle">Belastbaarheid</h3>
        
        <div v-if="sectionData.percentages?.length" class="progress-section">
          <h4>Werkkapaciteit</h4>
          <div v-for="(percentage, index) in sectionData.percentages" :key="index" class="progress-item">
            <div class="progress-label">Capaciteit {{ index + 1 }}</div>
            <div class="progress-bar-container">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: percentage + '%' }"></div>
              </div>
              <span class="progress-value">{{ percentage }}%</span>
            </div>
          </div>
        </div>

        <div v-if="sectionData.capabilities?.length" class="capabilities-section">
          <h4>Mogelijkheden</h4>
          <ul class="capability-list">
            <li v-for="capability in sectionData.capabilities" :key="capability" class="capability-item positive">
              <i class="fas fa-check-circle"></i>
              {{ capability }}
            </li>
          </ul>
        </div>

        <div v-if="sectionData.restrictions?.length" class="restrictions-section">
          <h4>Beperkingen</h4>
          <ul class="restriction-list">
            <li v-for="restriction in sectionData.restrictions" :key="restriction" class="restriction-item negative">
              <i class="fas fa-exclamation-circle"></i>
              {{ restriction }}
            </li>
          </ul>
        </div>
      </div>

      <!-- Matching Criteria Matrix -->
      <div v-else-if="sectionData?.type === 'matching_criteria'" class="matching-criteria">
        <h3 class="section-subtitle">Matching Criteria</h3>
        <div class="criteria-matrix">
          <div v-for="criterion in sectionData.criteria" :key="criterion.text" 
               :class="['criterion-item', 'priority-' + criterion.priority]">
            <span class="priority-badge" :class="'badge-' + criterion.priority">
              {{ criterion.priority === 'essential' ? 'E' : criterion.priority === 'desired' ? 'W' : 'N' }}
            </span>
            <span class="criterion-text">{{ criterion.text }}</span>
          </div>
        </div>
      </div>

      <!-- Medical Info -->
      <div v-else-if="sectionData?.type === 'medical_info'" class="medical-info">
        <h3 class="section-subtitle">Medische Situatie</h3>
        <table class="info-table">
          <tr v-if="sectionData.diagnosis">
            <td class="label">Diagnose:</td>
            <td class="value">{{ sectionData.diagnosis }}</td>
          </tr>
          <tr v-if="sectionData.startDate">
            <td class="label">Sinds:</td>
            <td class="value">{{ sectionData.startDate }}</td>
          </tr>
        </table>
        <div v-if="sectionData.symptoms?.length" class="symptoms-list">
          <h4>Symptomen/Klachten</h4>
          <ul>
            <li v-for="symptom in sectionData.symptoms" :key="symptom">{{ symptom }}</li>
          </ul>
        </div>
      </div>

      <!-- Work History -->
      <div v-else-if="sectionData?.type === 'work_history'" class="work-history">
        <h3 class="section-subtitle">Arbeidsverleden</h3>
        <div class="timeline">
          <div v-for="position in sectionData.positions" :key="position" class="timeline-item">
            <div class="timeline-marker"></div>
            <div class="timeline-content">{{ position }}</div>
          </div>
        </div>
      </div>

      <!-- Fallback to legacy markdown rendering -->
      <div v-else class="legacy-content">
        <template v-if="getSectionContent(sectionId, layout).isHtml">
          <div v-html="getSectionContent(sectionId, layout).content"></div>
        </template>
        <template v-else>
          <div v-html="formatMarkdown(getSectionContent(sectionId, layout).content)"></div>
        </template>
      </div>
    </div>
  `
};

// Component will be used inline via dynamic component
</script>

<template>
  <!-- Skip Navigation Link for Accessibility -->
  <a href="#report-title" class="skip-link" @click="skipToMainContent">Ga naar hoofdinhoud</a>
  
  <div class="report-view" role="main" aria-label="Rapport weergave">
    <!-- Debug Info (temporary) -->
    <div v-if="false" class="debug-info" style="background: yellow; padding: 10px; margin: 10px 0;">
      <strong>Debug Info:</strong><br>
      isLoadingInitial: {{ isLoadingInitial }}<br>
      currentReport exists: {{ !!reportStore.currentReport }}<br>
      currentReport status: {{ reportStore.currentReport?.status }}<br>
      isReportComplete: {{ isReportComplete }}
    </div>

    <!-- Loading Skeleton with Better UX -->
    <div v-if="isLoadingInitial" class="loading-skeleton" role="status" aria-label="Rapport wordt geladen">
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

    <!-- Enhanced Error State -->
    <div v-else-if="!reportStore.currentReport" class="error-state" role="alert" aria-live="polite">
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
      <!-- Breadcrumb Navigation -->
      <nav class="breadcrumb" role="navigation" aria-label="Navigatiepad">
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
      <header class="report-header" role="banner">
        <div class="header-content">
          <div class="title-section">
            <h1 id="report-title" tabindex="-1">{{ reportStore.currentReport.title }}</h1>
            <div class="status-badge" :class="statusIndicator.class">
              <span class="status-icon">{{ statusIndicator.icon }}</span>
              <span class="status-text">{{ statusIndicator.text }}</span>
            </div>
          </div>
          
          <div class="header-actions">
            <button 
              v-if="!reportStore.currentReport?.content?.structured_data && isReportComplete"
              @click="generateStructuredData" 
              class="btn btn-outline"
              aria-label="Genereer gestructureerde data voor formulier"
              :disabled="generatingStructured"
            >
              <div v-if="generatingStructured" class="loading-spinner small"></div>
              <span v-else class="icon">📋</span>
              {{ generatingStructured ? 'Bezig...' : 'Formulier Data' }}
            </button>
            <button 
              v-if="isReportComplete"
              @click="previewFullReport" 
              class="btn btn-outline"
              aria-label="Bekijk volledig rapport in preview modus"
            >
              <span class="icon">👁️</span>
              Preview
            </button>
            <button
              v-if="isReportComplete"
              @click="openDownloadDialog"
              class="btn btn-primary"
              :disabled="downloadingReport"
              :aria-label="downloadingReport ? 'Download wordt voorbereid...' : 'Download rapport als DOCX bestand'"
            >
              <div v-if="downloadingReport" class="loading-spinner small"></div>
              <span v-else class="icon">💾</span>
              {{ downloadingReport ? 'Bezig...' : 'Download' }}
            </button>
            <button @click="deleteReport" class="btn btn-danger-outline" aria-label="Verwijder dit rapport permanent">
              <span class="icon">🗑️</span>
              Verwijderen
            </button>
          </div>
        </div>
      </header>

      <!-- Enhanced Processing Status Card -->
      <div v-if="isReportGenerating" class="status-card processing" role="status" aria-live="polite">
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

      <!-- Enhanced Error Status Card -->
      <div v-if="isReportFailed" class="status-card error" role="alert" aria-live="assertive">
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
        
        <!-- Sections Navigation (only show when not using static template) -->
        <nav v-if="!useStaticTemplate" class="sections-nav" role="tablist" aria-label="Rapport secties navigatie">
          <button 
            v-for="(sectionId, index) in reportSections" 
            :key="sectionId"
            class="section-tab"
            :class="{ active: activeSection === sectionId }"
            @click="activeSection = sectionId"
            role="tab"
            :aria-selected="activeSection === sectionId"
            :aria-controls="`section-panel-${sectionId}`"
            :id="`section-tab-${sectionId}`"
            :tabindex="activeSection === sectionId ? 0 : -1"
            @keydown="handleTabKeydown($event, sectionId, index)"
          >
            <span class="tab-title">{{ getSectionTitle(sectionId) }}</span>
            <span v-if="regeneratingSection === sectionId" class="tab-status loading">
              <div class="loading-spinner tiny"></div>
            </span>
          </button>
        </nav>
        
        <!-- Active Section Content -->
        <div v-if="activeSection && currentSectionContent" 
             class="section-viewer" 
             role="tabpanel"
             :id="`section-panel-${activeSection}`"
             :aria-labelledby="`section-tab-${activeSection}`"
             tabindex="0">
          <div class="viewer-header">
            <div class="section-title">
              <h3>{{ getSectionTitle(activeSection) }}</h3>
              <span class="word-count">{{ getSectionContent(activeSection, 'standaard').content.split(' ').length }} woorden</span>
            </div>
            <div class="viewer-actions">
              <button 
                @click="copySectionContent(getSectionContent(activeSection, 'standaard').content)" 
                class="btn btn-outline btn-sm"
                aria-label="Kopieer sectie-inhoud naar klembord"
                title="Kopieer sectie-inhoud"
              >
                <span class="icon">📋</span>
              </button>
              <button 
                @click="regenerateSection(activeSection)"
                class="btn btn-outline btn-sm"
                :disabled="regeneratingSection === activeSection"
                :aria-label="regeneratingSection === activeSection ? 'Sectie wordt geregenereerd...' : 'Regenereer deze sectie met AI'"
                title="Regenereer deze sectie"
              >
                <div v-if="regeneratingSection === activeSection" class="loading-spinner tiny"></div>
                <span v-else class="icon">🔄</span>
              </button>
              <button 
                @click="useStaticTemplate = !useStaticTemplate"
                class="btn btn-outline btn-sm"
                :class="{ active: useStaticTemplate }"
                title="Schakel tussen statische template en sectie weergave"
              >
                <span class="icon">{{ useStaticTemplate ? '📋' : '📄' }}</span>
                {{ useStaticTemplate ? 'Sectie View' : 'Template View' }}
              </button>
              <button 
                v-if="!useStaticTemplate"
                @click="toggleMarkdown = !toggleMarkdown"
                class="btn btn-outline btn-sm"
                :class="{ active: toggleMarkdown }"
                :aria-label="toggleMarkdown ? 'Schakel naar opgemaakte weergave' : 'Schakel naar markdown weergave'"
                :aria-pressed="toggleMarkdown"
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
            <!-- Static Template View -->
            <div v-if="useStaticTemplate && staticTemplateData" class="static-template-container">
              <StaticADReportTemplate :report-data="staticTemplateData" />
            </div>
            
            <!-- Original Section View -->
            <div v-else-if="!useStaticTemplate">
              <div v-if="!toggleMarkdown" class="content-formatted section-content">
                <template v-if="getSectionContent(activeSection, 'standaard').isHtml">
                  <div v-html="getSectionContent(activeSection, 'standaard').content"></div>
                </template>
                <template v-else>
                  <div v-html="formatMarkdown(getSectionContent(activeSection, 'standaard').content)"></div>
                </template>
              </div>
              <pre v-else class="content-markdown">{{ getSectionContent(activeSection, 'standaard').content }}</pre>
            </div>
            
            <!-- Loading state for static template -->
            <div v-else-if="useStaticTemplate && !staticTemplateData" class="template-loading">
              <div class="loading-spinner"></div>
              <p>Template data wordt voorbereid...</p>
            </div>
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
            <!-- Layout Selector in Preview -->
            <select 
              v-model="previewLayout" 
              class="layout-selector"
              title="Kies rapport template"
            >
              <option v-for="option in layoutOptions" :key="option.id" :value="option.id">
                {{ option.name }}
              </option>
            </select>
            
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
            <!-- Professional Cover Page -->
            <div class="preview-cover-page">
              <!-- Header with Logo and Company Info -->
              <div class="cover-header">
                <div v-if="reportStore.currentReport.metadata?.user_profile?.logo_path" class="cover-logo">
                  <img :src="getProfileLogoUrl(reportStore.currentReport.metadata.user_profile)" alt="Logo" onerror="this.style.display='none'" />
                </div>
                <div class="cover-company-info">
                  <div v-if="reportStore.currentReport.metadata?.user_profile">
                    <h3 v-if="reportStore.currentReport.metadata.user_profile.company_name" class="company-name">
                      {{ reportStore.currentReport.metadata.user_profile.company_name }}
                    </h3>
                    <div class="company-details">
                      <p v-if="reportStore.currentReport.metadata.user_profile.company_address">
                        {{ reportStore.currentReport.metadata.user_profile.company_address }}
                      </p>
                      <p v-if="reportStore.currentReport.metadata.user_profile.company_postal_code || reportStore.currentReport.metadata.user_profile.company_city">
                        {{ reportStore.currentReport.metadata.user_profile.company_postal_code }} {{ reportStore.currentReport.metadata.user_profile.company_city }}
                      </p>
                      <p v-if="reportStore.currentReport.metadata.user_profile.company_phone">
                        T: {{ reportStore.currentReport.metadata.user_profile.company_phone }}
                      </p>
                      <p v-if="reportStore.currentReport.metadata.user_profile.company_email">
                        E: {{ reportStore.currentReport.metadata.user_profile.company_email }}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Report Title Section -->
              <div class="cover-title-section">
                <h1 class="cover-main-title">ARBEIDSDESKUNDIG RAPPORT</h1>
                <h2 class="cover-case-title">{{ reportStore.currentReport.title }}</h2>
                
                <!-- Report Metadata -->
                <div class="cover-metadata">
                  <table class="metadata-table">
                    <tbody>
                    <tr>
                      <td><strong>Rapportdatum:</strong></td>
                      <td>{{ formatDate(reportStore.currentReport.created_at) }}</td>
                    </tr>
                    <tr v-if="reportStore.currentReport.metadata?.user_profile">
                      <td><strong>Opgesteld door:</strong></td>
                      <td>
                        <span v-if="reportStore.currentReport.metadata.user_profile.display_name">
                          {{ reportStore.currentReport.metadata.user_profile.display_name }}
                        </span>
                        <span v-else-if="reportStore.currentReport.metadata.user_profile.first_name && reportStore.currentReport.metadata.user_profile.last_name">
                          {{ reportStore.currentReport.metadata.user_profile.first_name }} {{ reportStore.currentReport.metadata.user_profile.last_name }}
                        </span>
                      </td>
                    </tr>
                    <tr v-if="reportStore.currentReport.metadata?.user_profile?.job_title">
                      <td><strong>Functie:</strong></td>
                      <td>{{ reportStore.currentReport.metadata.user_profile.job_title }}</td>
                    </tr>
                    <tr v-if="reportStore.currentReport.metadata?.user_profile?.certification">
                      <td><strong>Certificering:</strong></td>
                      <td>
                        {{ reportStore.currentReport.metadata.user_profile.certification }}
                        <span v-if="reportStore.currentReport.metadata.user_profile.registration_number">
                          ({{ reportStore.currentReport.metadata.user_profile.registration_number }})
                        </span>
                      </td>
                    </tr>
                    <tr>
                      <td><strong>Versie:</strong></td>
                      <td>1.0</td>
                    </tr>
                    <tr>
                      <td><strong>Status:</strong></td>
                      <td>Definitief</td>
                    </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- Footer Notice -->
              <div class="cover-footer">
                <p class="confidentiality-notice">
                  <strong>VERTROUWELIJK</strong><br>
                  Dit rapport is opgesteld conform de geldende richtlijnen voor arbeidsdeskundig onderzoek 
                  en bevat vertrouwelijke informatie die uitsluitend bestemd is voor de opdrachtgever.
                </p>
              </div>
            </div>
            
            <!-- Professional Page Header with Logo -->
            <div class="page-header-with-logo">
              <div v-if="reportStore.currentReport.metadata?.user_profile" class="header-logo-section">
                <img 
                  v-if="reportStore.currentReport.metadata.user_profile.logo_path" 
                  :src="getProfileLogoUrl(reportStore.currentReport.metadata.user_profile)" 
                  alt="Bedrijfslogo" 
                  class="header-logo"
                  onerror="this.style.display='none'" 
                />
                <div class="header-company-info">
                  <h4 v-if="reportStore.currentReport.metadata.user_profile.company_name" class="header-company-name">
                    {{ reportStore.currentReport.metadata.user_profile.company_name }}
                  </h4>
                  <p v-if="reportStore.currentReport.metadata.user_profile.display_name" class="header-expert-name">
                    {{ reportStore.currentReport.metadata.user_profile.display_name }}
                  </p>
                </div>
              </div>
              <div class="header-divider"></div>
            </div>

            <!-- Table of Contents with Template Styling -->
            <div :class="['preview-toc', `toc-${previewLayout}`]">
              <h2 class="toc-title">INHOUDSOPGAVE</h2>
              <div class="toc-content">
                <div v-for="(sectionId, index) in getOrderedSections()" :key="sectionId" class="toc-item">
                  <span class="toc-number">{{ index + 1 }}.</span>
                  <span class="toc-text">{{ getSectionTitle(sectionId) }}</span>
                  <span class="toc-dots"></span>
                  <span class="toc-page">{{ index + 2 }}</span>
                </div>
              </div>
            </div>
            
            <!-- Report Sections with Template-based Styling -->
            <template v-if="getOrderedSections().length > 0">
              <div 
                v-for="(sectionId, index) in getOrderedSections()" 
                :key="sectionId" 
                :class="[
                  'report-section',
                  `template-${previewLayout}`,
                  `section-${sectionId}`
                ]"
                :data-section-number="index + 1"
                :data-section-id="sectionId"
              >
                <!-- Template-based Section Rendering -->
                <div class="section-wrapper">
                  <!-- Section Header (only for certain templates) -->
                  <div v-if="shouldShowCustomHeader(previewLayout)" class="custom-section-header">
                    <h2 class="section-title">{{ getSectionTitle(sectionId) }}</h2>
                  </div>
                  
                  <!-- Modern Structured Content -->
                  <div 
                    :class="[
                      'section-content',
                      `content-${previewLayout}`
                    ]"
                    :data-section-number="index + 1"
                    :data-section-title="getSectionTitle(sectionId)"
                  >
                    
                    <!-- Direct content rendering for proper CSS selector matching -->
                    <template v-if="getSectionContent(sectionId, previewLayout).isHtml">
                      <div v-html="getSectionContent(sectionId, previewLayout).content"></div>
                    </template>
                    <template v-else>
                      <div v-html="formatMarkdown(getSectionContent(sectionId, previewLayout).content)"></div>
                    </template>
                  </div>
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

    <!-- Enhanced Export Dialog -->
    <ExportDialog
      :is-open="showExportDialog"
      :report-id="String(reportId)"
      @close="closeExportDialog"
      @exported="handleExportSuccess"
    />

    <!-- Download Options Dialog (Legacy) -->
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
/* Enhanced Design System Variables */
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
  --text-primary: #1f2937;
  --text-secondary: #6b7280;
  --text-light: #6b7280;
  --text-lighter: #9ca3af;
  --gray-200: #e5e7eb;
  --gray-300: #d1d5db;
  --gray-800: #1f2937;
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

.static-template-container {
  width: 100%;
  max-width: none;
  padding: 0;
  margin: 0;
}

.template-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
  color: var(--text-muted);
}

.template-loading .loading-spinner {
  margin-bottom: var(--spacing-md);
}

.content-formatted {
  line-height: 1.4;
  color: var(--text-color);
  font-size: 11pt;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  text-align: justify;
}

/* Main headers - 12pt */
.content-formatted h1 {
  color: var(--primary-color);
  font-size: 12pt;
  font-weight: 700;
  margin-top: var(--spacing-lg);
  margin-bottom: var(--spacing-sm);
  padding-bottom: 3px;
  border-bottom: 1px solid var(--primary-color);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.content-formatted h1:first-child {
  margin-top: 0;
}

/* Subheaders - 11pt */
.content-formatted h2 {
  color: var(--text-color);
  font-size: 11pt;
  font-weight: 600;
  margin-top: var(--spacing-md);
  margin-bottom: var(--spacing-xs);
  padding-bottom: 2px;
  border-bottom: none;
}

.content-formatted h3 {
  color: var(--text-color);
  font-size: 10pt;
  font-weight: 600;
  margin-top: var(--spacing-sm);
  margin-bottom: 2px;
}

.content-formatted h4,
.content-formatted h5,
.content-formatted h6 {
  color: var(--text-color);
  font-size: 12pt;
  font-weight: 600;
  margin-top: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

/* Paragraphs - professional spacing */
.content-formatted p {
  margin-bottom: var(--spacing-sm);
  text-align: justify;
  line-height: 1.5;
}

/* Lists - compact spacing */
.content-formatted ul,
.content-formatted ol {
  margin-bottom: var(--spacing-sm);
  padding-left: var(--spacing-lg);
}

.content-formatted li {
  margin-bottom: var(--spacing-xs);
  line-height: 1.6;
}

/* Strong text */
.content-formatted strong {
  font-weight: 600;
  color: var(--primary-color);
}

/* Emphasis */
.content-formatted em {
  font-style: italic;
  color: var(--text-light);
}

/* Blockquotes */
.content-formatted blockquote {
  border-left: 4px solid var(--primary-light);
  padding-left: var(--spacing-md);
  margin: var(--spacing-md) 0;
  background: var(--bg-secondary);
  padding: var(--spacing-md);
  border-radius: var(--radius-sm);
  font-style: italic;
}

/* Code */
.content-formatted code {
  background: var(--bg-tertiary);
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 0.9em;
}

.content-formatted pre {
  background: var(--bg-tertiary);
  padding: var(--spacing-md);
  border-radius: var(--radius-sm);
  overflow-x: auto;
  margin: var(--spacing-md) 0;
}

.content-markdown {
  background-color: var(--bg-secondary);
  padding: var(--spacing-lg);
  border-radius: var(--radius);
  color: var(--text-color);
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-x: auto;
  margin: 0;
  border: 1px solid var(--border-color);
  max-height: 500px;
  overflow-y: auto;
}

/* Enhanced section content styling */
.section-content {
  background: white;
  padding: var(--spacing-xl);
  border-radius: var(--radius);
  border: 1px solid var(--border-light);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  max-width: 800px;
  margin: 0 auto;
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
  color: #1f2937;
  font-family: 'Times New Roman', 'Liberation Serif', serif;
  line-height: 1.5;
  max-width: 900px;
  margin: 0 auto;
  padding: 48pt;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  position: relative;
  overflow: hidden;
}

/* Better spacing between report elements */
.preview-report > * + * {
  margin-top: 32pt;
}

/* Enhanced Professional Cover Page */
.preview-cover-page {
  padding: 40pt;
  border-bottom: 3px solid #1e40af; /* Professional blue border */
  margin-bottom: 32pt;
  background: linear-gradient(135deg, #ffffff 0%, #fefeff 100%); /* Subtle gradient */
  page-break-after: always;
  min-height: 800px; /* Taller for better proportion */
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border-radius: 8px 8px 0 0; /* Rounded top corners */
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); /* Subtle shadow */
}

/* Enhanced Cover Header with Logo and Company */
.cover-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 2px solid #e5e7eb; /* Stronger separator */
  padding-bottom: 20pt;
  margin-bottom: 32pt;
  background: rgba(255, 255, 255, 0.8); /* Semi-transparent background */
  padding: 16pt 20pt 20pt 20pt; /* All-around padding */
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05); /* Subtle elevation */
}

.cover-logo {
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.cover-logo img {
  max-height: 60px;
  max-width: 200px;
  object-fit: contain;
  border-radius: 4px;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.1));
}

/* Professional Page Header with Logo */
.page-header-with-logo {
  margin: 24pt 0;
  page-break-inside: avoid;
}

.header-logo-section {
  display: flex;
  align-items: center;
  gap: 16pt;
  margin-bottom: 12pt;
}

.header-logo {
  max-height: 40px;
  max-width: 150px;
  object-fit: contain;
  border-radius: 4px;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.1));
}

.header-company-info {
  flex: 1;
}

.header-company-name {
  margin: 0 0 4pt 0;
  font-size: 14pt;
  font-weight: 700;
  color: #1e40af;
  line-height: 1.2;
}

.header-expert-name {
  margin: 0;
  font-size: 11pt;
  color: #64748b;
  font-weight: 500;
}

.header-divider {
  height: 2px;
  background: linear-gradient(to right, #1e40af, #3b82f6, #93c5fd, transparent);
  margin-bottom: 16pt;
}

.cover-company-info {
  text-align: right;
  font-size: 9pt;
  line-height: 1.3;
}

.company-name {
  font-size: 11pt;
  font-weight: 600;
  color: var(--primary-color);
  margin: 0 0 var(--spacing-xs) 0;
}

.company-details p {
  margin: 0;
  color: var(--text-color);
}

/* Cover Title Section */
.cover-title-section {
  text-align: center;
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.cover-main-title {
  font-size: 22pt; /* Larger, more prominent */
  font-weight: 700;
  color: #1e40af; /* Professional blue */
  margin-bottom: var(--spacing-lg);
  letter-spacing: 2px; /* More distinctive */
  border-bottom: 3px solid #1e40af; /* Thicker border for emphasis */
  padding-bottom: var(--spacing-sm);
  display: inline-block;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1); /* Subtle depth */
}

.cover-case-title {
  font-size: 16pt; /* Larger for better hierarchy */
  font-weight: 600;
  color: #374151; /* Professional gray */
  margin-bottom: var(--spacing-xl);
  line-height: 1.4;
  font-style: italic; /* Emphasize as subtitle */
  padding: 0 20pt; /* Side padding for better line breaks */
}

/* Metadata Table */
.cover-metadata {
  display: flex;
  justify-content: center;
  margin-top: var(--spacing-xl);
}

.metadata-table {
  border-collapse: collapse;
  font-size: 11pt; /* Slightly larger for better readability */
  line-height: 1.4;
  background: #f8fafc; /* Light background */
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); /* Subtle shadow */
}

.metadata-table td {
  padding: 8pt 16pt; /* Better padding */
  text-align: left;
  border-bottom: 1px solid #e2e8f0; /* Subtle border */
}

.metadata-table td:first-child {
  text-align: right;
  color: #1e40af; /* Professional blue for labels */
  width: 140px; /* Slightly wider */
  font-weight: 600; /* Bolder labels */
  background: #eff6ff; /* Light blue background */
}

.metadata-table td:last-child {
  color: #374151; /* Professional dark gray */
  width: 220px; /* Slightly wider */
  font-weight: 500;
}

/* Enhanced Cover Footer */
.cover-footer {
  text-align: center;
  padding: 20pt;
  border-top: 2px solid #1e40af; /* Professional blue border */
  background: #f8fafc; /* Light background */
  border-radius: 8px;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.05); /* Subtle inset shadow */
}

.confidentiality-notice {
  font-size: 10pt; /* Slightly larger for better readability */
  color: #374151; /* Professional dark gray */
  line-height: 1.5;
  margin: 0;
  font-style: italic;
  font-weight: 500; /* Slightly bolder for emphasis */
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.05); /* Subtle text shadow */
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


/* ============================================ */
/* TEMPLATE SYSTEM - Multiple Layout Options */
/* ============================================ */

/* Layout Selector in Preview */
.layout-selector {
  padding: var(--spacing-xs) var(--spacing-sm);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: white;
  color: var(--text-color);
  font-size: 0.875rem;
  cursor: pointer;
  margin-right: var(--spacing-sm);
}

/* ================== */
/* STANDAARD TEMPLATE */
/* ================== */

.template-standaard {
  margin-bottom: var(--spacing-md);
  padding: var(--spacing-sm) 0;
  border-bottom: 1px solid var(--border-light);
}

/* Professional Dutch section headers - improved for better readability */
.template-standaard .section-content::before {
  content: attr(data-section-number) ". " attr(data-section-title);
  display: block;
  font-size: 16pt;
  font-weight: 700;
  color: #1e40af;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin: 32pt 0 16pt 0;
  padding: 12pt 0 8pt 0;
  border-bottom: 3px solid #1e40af;
  background: linear-gradient(135deg, #f1f5f9, #e2e8f0);
  margin-left: -12pt;
  margin-right: -12pt;
  padding-left: 12pt;
  padding-right: 12pt;
}

.template-standaard .section-content {
  font-family: 'Times New Roman', 'Liberation Serif', serif; /* Traditional business font */
  line-height: 1.4; /* Improved readability while staying professional */
  font-size: 11pt; /* Based on analysis of real Dutch reports */
  color: #1f2937; /* Slightly softer black for better readability */
  text-align: justify;
  margin: 0;
  padding: 0 8pt 0 0; /* Small right padding for text flow */
}

/* Hide only H1 headers - we use CSS generated section headers */
.template-standaard .section-content h1 {
  display: none;
}

/* Style H2 headers as blue subsection headers */
.template-standaard .section-content h2 {
  font-size: 12pt !important;
  font-weight: 600 !important;
  color: #1e40af !important; /* Professional blue */
  margin: 16pt 0 8pt 0 !important;
  padding: 0 !important;
  text-transform: none !important;
  border: none !important;
  background: none !important;
}

/* Style H3 headers as smaller blue headers */
.template-standaard .section-content h3 {
  font-size: 11pt !important;
  font-weight: 500 !important;
  color: #3b82f6 !important; /* Lighter blue */
  margin: 12pt 0 6pt 0 !important;
  padding: 0 !important;
  text-transform: none !important;
  border: none !important;
  background: none !important;
}

/* Hide H4-H6 headers */
.template-standaard .section-content h4,
.template-standaard .section-content h5,
.template-standaard .section-content h6 {
  display: none;
}

/* Style bold text as blue subsection headers */
.template-standaard .section-content strong {
  display: block !important; /* Force block display */
  font-size: 11pt; /* Same as body or slightly larger */
  font-weight: 600; /* Semi-bold, not excessive */
  color: #1d4ed8; /* Dark blue for strong headers */
  margin: 12pt 0 4pt 0; /* Professional spacing */
  text-transform: none;
  padding: 0;
  width: 100%; /* Ensure full width for block behavior */
}

/* Style italic text as light blue minor headers */
.template-standaard .section-content em {
  display: block !important; /* Force block display */
  font-size: 11pt; /* Same as body text */
  font-weight: 500;
  color: #60a5fa; /* Light blue for em headers */
  margin: 8pt 0 2pt 0; /* Minimal spacing */
  font-style: normal;
  padding: 0;
  width: 100%; /* Ensure full width for block behavior */
}

/* Dutch business document paragraph spacing - improved */
.template-standaard .section-content p {
  margin: 0 0 8pt 0; /* Better paragraph spacing for readability */
  line-height: 1.4; /* Match section content line height */
  padding: 0;
  text-indent: 0;
  text-align: justify;
}

/* First paragraph after section header */
.template-standaard .section-content p:first-child {
  margin-top: 4pt; /* Small space after section header */
}

/* Improved list styling for readability */
.template-standaard .section-content ul,
.template-standaard .section-content ol {
  margin: 8pt 0;
  padding-left: 20pt; /* Better indentation */
}

.template-standaard .section-content li {
  margin-bottom: 4pt; /* Better list item spacing */
  line-height: 1.4; /* Match section content */
  font-size: 11pt; /* Match body text size */
}

/* ============== */
/* MODERN TEMPLATE */
/* ============== */

.template-modern {
  background: white; /* Clean, professional background */
  border: none; /* Remove decorative borders */
  padding: 0;
  margin-bottom: var(--spacing-md);
  box-shadow: none; /* Remove decorative shadows */
}

.template-modern .custom-section-header {
  display: flex;
  align-items: center;
  gap: 12pt;
  margin-bottom: 16pt;
  padding: 12pt 16pt;
  background: linear-gradient(135deg, #1e40af, #2563eb);
  color: white;
  border-radius: 6pt;
  box-shadow: 0 2px 8px rgba(30, 64, 175, 0.2);
}

.template-modern .section-number {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  font-weight: 700;
  font-size: 12pt;
  width: 32pt;
  height: 32pt;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin: 0;
}

.template-modern .section-title {
  font-size: 14pt;
  font-weight: 700;
  color: white;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: inline; /* Inline with number */
}

.template-modern .section-content {
  font-family: 'Times New Roman', 'Liberation Serif', serif;
  font-size: 11pt;
  line-height: 1.4; /* Better readability */
  color: #1f2937; /* Softer black */
  text-align: justify;
  margin: 16pt 0 8pt 0; /* Professional spacing */
  padding: 0 8pt 0 0; /* Small right padding */
}

/* Hide only H1 headers - we use CSS generated section headers */
.template-modern .section-content h1 {
  display: none;
}

/* Style H2 headers as blue subsection headers */
.template-modern .section-content h2 {
  font-size: 11pt;
  font-weight: 600;
  color: #2563eb; /* Blue color */
  margin: 12pt 0 4pt 0;
  padding: 0;
  text-transform: none;
  border: none;
}

/* Style H3 headers as smaller blue headers */
.template-modern .section-content h3 {
  font-size: 10pt;
  font-weight: 500;
  color: #3b82f6; /* Lighter blue */
  margin: 8pt 0 2pt 0;
  padding: 0;
  text-transform: none;
  border: none;
}

/* Hide H4-H6 headers */
.template-modern .section-content h4,
.template-modern .section-content h5,
.template-modern .section-content h6 {
  display: none;
}

/* Style bold text as blue subsection headers */
.template-modern .section-content strong {
  display: block !important;
  font-size: 11pt;
  font-weight: 600;
  color: #1d4ed8; /* Dark blue */
  margin: 12pt 0 4pt 0;
  text-transform: none;
  padding: 0;
  width: 100%;
}

/* Style italic text as light blue minor headers */
.template-modern .section-content em {
  display: block !important;
  font-size: 11pt;
  font-weight: 500;
  color: #60a5fa; /* Light blue */
  margin: 8pt 0 2pt 0;
  font-style: normal;
  padding: 0;
  width: 100%;
}

/* Professional paragraph spacing */
.template-modern .section-content p {
  margin: 0 0 3pt 0;
  line-height: 1.25;
  padding: 0;
  text-indent: 0;
  text-align: justify;
}

/* ===================== */
/* PROFESSIONEEL TEMPLATE */
/* ===================== */

.template-professioneel {
  border: none; /* Clean professional look */
  padding: 0;
  margin-bottom: var(--spacing-md);
  background: white;
}

.template-professioneel .custom-section-header {
  background: linear-gradient(135deg, #f8fafc, #e2e8f0);
  border-left: 4px solid #1e40af;
  color: #1e40af;
  padding: 16pt;
  margin: 24pt 0 16pt 0;
  display: flex;
  align-items: center;
  gap: 12pt;
  border-radius: 0 6pt 6pt 0;
}

.template-professioneel .section-number {
  font-size: 14pt;
  font-weight: 700;
  margin: 0;
  background: #1e40af;
  color: white;
  padding: 6pt 12pt;
  border-radius: 4pt;
  min-width: auto;
  text-align: center;
  display: inline-block;
}

.template-professioneel .section-title {
  font-size: 14pt;
  font-weight: 700;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  flex: 1;
  color: #1e40af;
}

.template-professioneel .section-content {
  font-family: 'Times New Roman', 'Liberation Serif', serif;
  font-size: 11pt; /* Based on real report analysis */
  line-height: 1.25; /* Tight professional spacing */
  color: #000000;
  text-align: justify;
  margin: 16pt 0 8pt 0;
  padding: 0;
}

/* Hide only H1 headers - we use CSS generated section headers */
.template-professioneel .section-content h1 {
  display: none;
}

/* Style H2 headers as blue subsection headers */
.template-professioneel .section-content h2 {
  font-size: 11pt;
  font-weight: 600;
  color: #2563eb; /* Blue color */
  margin: 12pt 0 4pt 0;
  padding: 0;
  text-transform: none;
  border: none;
}

/* Style H3 headers as smaller blue headers */
.template-professioneel .section-content h3 {
  font-size: 10pt;
  font-weight: 500;
  color: #3b82f6; /* Lighter blue */
  margin: 8pt 0 2pt 0;
  padding: 0;
  text-transform: none;
  border: none;
}

/* Hide H4-H6 headers */
.template-professioneel .section-content h4,
.template-professioneel .section-content h5,
.template-professioneel .section-content h6 {
  display: none;
}

/* Style bold text as blue subsection headers */
.template-professioneel .section-content strong {
  display: block !important;
  font-size: 11pt;
  font-weight: 600;
  color: #1d4ed8; /* Dark blue */
  margin: 12pt 0 4pt 0;
  text-transform: none;
  padding: 0;
  width: 100%;
}

/* Style italic text as light blue minor headers */
.template-professioneel .section-content em {
  display: block !important;
  font-size: 11pt;
  font-weight: 500;
  color: #60a5fa; /* Light blue */
  margin: 8pt 0 2pt 0;
  font-style: normal;
  padding: 0;
  width: 100%;
}

/* Professional paragraph spacing */
.template-professioneel .section-content p {
  margin: 0 0 3pt 0;
  line-height: 1.25;
  padding: 0;
  text-indent: 0;
  text-align: justify;
}

/* =============== */
/* COMPACT TEMPLATE */
/* =============== */

.template-compact {
  margin-bottom: var(--spacing-sm);
  padding: var(--spacing-sm) 0;
}

.template-compact .section-content {
  font-family: 'Times New Roman', 'Liberation Serif', serif;
  font-size: 10pt; /* Compact but readable */
  line-height: 1.2; /* Very tight spacing for compact */
  color: #000000;
  text-align: justify;
  margin: 8pt 0 4pt 0;
  padding: 0;
}

/* Hide only H1 headers - we use CSS generated section headers */
.template-compact .section-content h1 {
  display: none;
}

/* Style H2 headers as blue subsection headers */
.template-compact .section-content h2 {
  font-size: 10pt; /* Smaller for compact */
  font-weight: 600;
  color: #2563eb; /* Blue color */
  margin: 8pt 0 3pt 0; /* Tighter spacing for compact */
  padding: 0;
  text-transform: none;
  border: none;
}

/* Style H3 headers as smaller blue headers */
.template-compact .section-content h3 {
  font-size: 9pt; /* Even smaller for compact */
  font-weight: 500;
  color: #3b82f6; /* Lighter blue */
  margin: 6pt 0 2pt 0; /* Very tight spacing */
  padding: 0;
  text-transform: none;
  border: none;
}

/* Hide H4-H6 headers */
.template-compact .section-content h4,
.template-compact .section-content h5,
.template-compact .section-content h6 {
  display: none;
}

/* Compact section headers */
.template-compact .section-content::before {
  content: attr(data-section-number) ". " attr(data-section-title);
  display: block;
  font-size: 12pt;
  font-weight: 700;
  color: #1e40af;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 20pt 0 8pt 0;
  padding: 6pt 0 4pt 0;
  border-bottom: 2px solid #1e40af;
}

/* Style bold text as blue subsection headers */
.template-compact .section-content strong {
  display: block !important;
  font-size: 10pt;
  font-weight: 600;
  color: #1d4ed8; /* Dark blue */
  margin: 6pt 0 2pt 0;
  text-transform: none;
  padding: 0;
  width: 100%;
}

/* Style italic text as light blue minor headers */
.template-compact .section-content em {
  display: block !important;
  font-size: 10pt;
  font-weight: 500;
  color: #60a5fa; /* Light blue */
  margin: 4pt 0 1pt 0;
  font-style: normal;
  padding: 0;
  width: 100%;
}

/* Compact paragraph spacing */
.template-compact .section-content p {
  margin: 0 0 2pt 0;
  line-height: 1.2;
  padding: 0;
  text-indent: 0;
  text-align: justify;
}

.template-compact .section-content h2 {
  font-size: 9pt;
  font-weight: 600;
  margin: var(--spacing-xs) 0 2px 0;
}

.template-compact .section-content p {
  margin-bottom: 2px;
}

/* ========================= */
/* TEMPLATE-SPECIFIC TOC STYLING */
/* ========================= */

.toc-modern {
  background: linear-gradient(135deg, var(--primary-light) 0%, white 100%);
  border: none;
  border-left: 4px solid var(--primary-color);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.toc-professioneel {
  border: 2px solid var(--primary-color);
  background: white;
}

.toc-professioneel .toc-title {
  background: var(--primary-color);
  color: white;
  margin: calc(-1 * var(--spacing-lg)) calc(-1 * var(--spacing-lg)) var(--spacing-md) calc(-1 * var(--spacing-lg));
  padding: var(--spacing-md);
}

.toc-compact {
  padding: var(--spacing-md);
  font-size: 9pt;
}

.toc-compact .toc-title {
  font-size: 10pt;
  margin-bottom: var(--spacing-sm);
}

.toc-compact .toc-item {
  margin-bottom: 2px;
  font-size: 8pt;
}

/* Enhanced Professional Table of Contents */
.preview-toc {
  margin: 32pt 0;
  padding: 0;
  background: white;
  border: 2px solid #1e40af;
  border-radius: 8pt;
  page-break-after: always;
  box-shadow: 0 6px 16px rgba(30, 64, 175, 0.15);
  overflow: hidden;
}

.toc-title {
  font-size: 14pt;
  font-weight: 700;
  color: white;
  background: linear-gradient(135deg, #1e40af, #2563eb);
  margin: 0;
  padding: 18pt 24pt;
  text-align: center;
  text-transform: uppercase;
  letter-spacing: 0.8px;
}

.toc-content {
  font-size: 11pt;
  line-height: 1.6;
  padding: 20pt 24pt;
  background: #fafbfc;
}

.toc-item {
  display: flex;
  align-items: baseline;
  margin-bottom: 12pt; /* More generous spacing between items */
  position: relative;
  padding: 4pt 0;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.toc-item:hover {
  background-color: #f1f5f9; /* Subtle hover effect */
  padding-left: 8pt;
  padding-right: 8pt;
}

.toc-number {
  font-weight: 700; /* Bolder numbers */
  color: #1e40af; /* Professional blue */
  width: 35px; /* Wider for better alignment */
  flex-shrink: 0;
  font-size: 12pt; /* Slightly larger */
}

.toc-text {
  flex: 1;
  color: #374151; /* Professional dark gray */
  font-weight: 500; /* Medium weight for better readability */
  text-transform: capitalize; /* Better formatting */
}

.toc-dots {
  flex: 1;
  border-bottom: 2px dotted #94a3b8; /* Thicker, more visible dots */
  margin: 0 12pt; /* More generous margins */
  height: 1px;
  align-self: flex-end;
  margin-bottom: 4px;
  min-width: 50px; /* Minimum width for dots */
}

.toc-page {
  font-weight: 700; /* Bolder page numbers */
  color: #1e40af; /* Professional blue */
  width: 35px; /* Wider for better alignment */
  text-align: right;
  flex-shrink: 0;
  font-size: 12pt; /* Slightly larger */
  background: #eff6ff; /* Light blue background */
  padding: 2pt 6pt;
  border-radius: 4px;
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

/* Professional Dutch business report styling */
.section-markdown-content {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  line-height: 1.4;
  font-size: 10pt;
  color: var(--text-color);
  max-width: none;
  text-align: justify;
}

/* Legacy support - will be overridden by template styles */
.section-markdown-content h1 {
  display: flex;
  align-items: baseline;
  color: var(--primary-color);
  font-size: 12pt;
  font-weight: 700;
  margin: 0 0 var(--spacing-md) 0;
  padding-bottom: 3px;
  border-bottom: 1px solid var(--primary-color);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Subsection headers (H2) - 10pt */
.section-markdown-content h2 {
  color: var(--text-color);
  font-size: 10pt;
  font-weight: 600;
  margin: var(--spacing-sm) 0 var(--spacing-xs) 0;
  padding-bottom: 2px;
  border-bottom: none;
}

/* Sub-subsection headers (H3) - 9pt */
.section-markdown-content h3 {
  color: var(--text-color);
  font-size: 9pt;
  font-weight: 600;
  margin: var(--spacing-xs) 0 2px 0;
}

/* Minor headers (H4, H5, H6) */
.section-markdown-content h4,
.section-markdown-content h5,
.section-markdown-content h6 {
  color: var(--text-color);
  font-size: 10pt;
  font-weight: 600;
  margin: var(--spacing-xs) 0 2px 0;
}

/* Paragraphs - compact professional spacing */
.section-markdown-content p {
  margin-bottom: var(--spacing-xs);
  text-align: justify;
  line-height: 1.4;
  text-indent: 0;
}

/* Lists with tight spacing */
.section-markdown-content ul,
.section-markdown-content ol {
  margin: var(--spacing-xs) 0;
  padding-left: var(--spacing-md);
}

.section-markdown-content li {
  margin-bottom: 2px;
  line-height: 1.3;
  font-size: 10pt;
}

/* Nested lists */
.section-markdown-content li ul,
.section-markdown-content li ol {
  margin: 2px 0;
  padding-left: var(--spacing-sm);
}

/* Strong and emphasis */
.section-markdown-content strong {
  font-weight: 600;
  color: var(--primary-color);
}

.section-markdown-content em {
  font-style: italic;
  color: var(--text-light);
}

/* Blockquotes */
.section-markdown-content blockquote {
  border-left: 4px solid var(--primary-light);
  padding-left: var(--spacing-md);
  margin: var(--spacing-md) 0;
  background: var(--bg-secondary);
  padding: var(--spacing-md);
  border-radius: var(--radius-sm);
}

/* Code blocks */
.section-markdown-content code {
  background: var(--bg-tertiary);
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 0.85em;
}

.section-markdown-content pre {
  background: var(--bg-tertiary);
  padding: var(--spacing-md);
  border-radius: var(--radius-sm);
  overflow-x: auto;
  margin: var(--spacing-md) 0;
}

/* Professional HTML Tables */
.section-markdown-content table {
  width: 100%;
  border-collapse: collapse;
  margin: 16pt 0;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  font-size: 11pt;
  line-height: 1.4;
}

.section-markdown-content th {
  background-color: #1e40af;
  color: white;
  font-weight: 600;
  padding: 12pt 16pt;
  text-align: left;
  border: none;
}

.section-markdown-content td {
  padding: 10pt 16pt;
  text-align: left;
  border: none;
  border-bottom: 1px solid #e5e7eb;
  vertical-align: top;
}

.section-markdown-content tr:nth-child(even) td {
  background-color: #f9fafb;
}

.section-markdown-content tr:last-child td {
  border-bottom: none;
}

/* Strong styling in tables */
.section-markdown-content td strong {
  color: #1e40af;
  font-weight: 600;
}

/* Horizontal rules */
.section-markdown-content hr {
  border: none;
  border-top: 2px solid var(--border-color);
  margin: var(--spacing-xl) 0;
}

/* Template wrapper styling */
.section-wrapper {
  width: 100%;
}

/* Ensure data attributes work for section numbering */
.report-section[data-section-number] .section-content h1::before {
  content: attr(data-section-number) ". ";
}

/* Enhanced Report Section Layout */
.report-section {
  margin-bottom: 24pt; /* Better section separation */
  padding: 16pt 0;
  background: transparent;
  border: none;
  page-break-inside: avoid;
  position: relative;
}

.report-section:not(:last-child) {
  border-bottom: 2px solid #e5e7eb; /* Stronger visual separator */
  padding-bottom: 20pt;
  margin-bottom: 28pt; /* Extra space after border */
}

/* Add subtle section background for alternating effect */
.report-section:nth-child(even) {
  background: #fafbfc;
  padding-left: 12pt;
  padding-right: 12pt;
  border-radius: 6px;
  margin-left: -12pt;
  margin-right: -12pt;
}

/* Professional Content Styling */
.report-paragraph {
  margin-bottom: 12pt;
  line-height: 1.6;
  text-align: justify;
  hyphens: auto;
  color: #1f2937;
  font-size: 11pt;
}

.report-paragraph:first-child {
  margin-top: 0;
}

.report-paragraph:last-child {
  margin-bottom: 0;
}

.report-list {
  margin: 12pt 0;
  padding-left: 24pt;
}

.report-list-item {
  margin-bottom: 6pt;
  line-height: 1.5;
  color: #1f2937;
}

.report-list-item:last-child {
  margin-bottom: 0;
}

/* Better spacing for nested lists */
.report-list .report-list {
  margin: 6pt 0;
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
  max-height: calc(90vh - 120px);
  font-size: 14px;
  line-height: 1.6;
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

/* Enhanced Responsive Design for Dutch Arbeidsdeskundige Reports */

/* Mobile-first approach for better UX */
@media (max-width: 320px) {
  .report-view {
    padding: var(--spacing-xs);
    margin: 0;
  }

  /* Only apply to templates that use CSS-generated headers */
  .template-standaard .section-content::before,
  .template-compact .section-content::before {
    font-size: 12pt;
    margin: 12pt 0 8pt 0;
    line-height: 1.3;
  }

  .template-standaard .section-content,
  .template-modern .section-content,
  .template-professioneel .section-content {
    font-size: 10pt;
    padding: 0 4pt 0 0;
    line-height: 1.35;
  }

  .template-compact .section-content {
    font-size: 9pt;
    line-height: 1.25;
  }
}

@media (max-width: 480px) {
  .report-view {
    padding: var(--spacing-sm);
  }

  /* Better mobile typography */
  .template-standaard .section-content::before {
    font-size: 13pt;
    margin: 16pt 0 10pt 0;
    padding: 0 0 3pt 0;
  }

  .template-standaard .section-content {
    font-size: 10.5pt;
    line-height: 1.35;
    padding: 0 6pt 0 0;
  }

  /* Mobile-optimized headers */
  .template-standaard .section-content h2 {
    font-size: 11pt !important;
    margin: 12pt 0 6pt 0 !important;
  }

  .template-standaard .section-content h3 {
    font-size: 10pt !important;
    margin: 8pt 0 4pt 0 !important;
  }

  /* Better mobile paragraph spacing */
  .template-standaard .section-content p {
    margin: 0 0 6pt 0;
    line-height: 1.35;
  }

  /* Improved mobile list spacing */
  .template-standaard .section-content ul,
  .template-standaard .section-content ol {
    margin: 6pt 0;
    padding-left: 16pt;
  }

  .template-standaard .section-content li {
    margin-bottom: 3pt;
    line-height: 1.35;
  }
}

@media (max-width: 768px) {
  .report-view {
    padding: var(--spacing-md);
  }

  .header-content {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-md);
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

/* ===================================== */
/* MODERNE CONTENT COMPONENTS STYLING   */
/* ===================================== */

.modern-content {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  color: #1f2937;
  line-height: 1.5;
}

/* Section Subtitles */
.section-subtitle {
  font-size: 14pt;
  font-weight: 600;
  color: #2563eb;
  margin: 0 0 16pt 0;
  padding-bottom: 8pt;
  border-bottom: 2px solid #e5e7eb;
}

/* Info Tables (like staatvandienst examples) */
.info-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 16pt;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.info-table tr:nth-child(even) {
  background-color: #f9fafb;
}

.info-table td {
  padding: 12pt 16pt;
  border-bottom: 1px solid #e5e7eb;
  vertical-align: top;
}

.info-table td.label {
  font-weight: 600;
  color: #374151;
  width: 30%;
  background-color: #f3f4f6;
}

.info-table td.value {
  color: #1f2937;
}

.info-table tr:last-child td {
  border-bottom: none;
}

/* Progress Bars for Workability */
.progress-section {
  margin-bottom: 24pt;
}

.progress-section h4 {
  font-size: 12pt;
  font-weight: 600;
  color: #374151;
  margin: 0 0 12pt 0;
}

.progress-item {
  margin-bottom: 16pt;
}

.progress-label {
  font-size: 10pt;
  font-weight: 500;
  color: #6b7280;
  margin-bottom: 4pt;
}

.progress-bar-container {
  display: flex;
  align-items: center;
  gap: 12pt;
}

.progress-bar {
  flex: 1;
  height: 8pt;
  background-color: #e5e7eb;
  border-radius: 4pt;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981 0%, #3b82f6 100%);
  transition: width 0.3s ease;
}

.progress-value {
  font-size: 10pt;
  font-weight: 600;
  color: #374151;
  min-width: 40pt;
  text-align: right;
}

/* Capabilities and Restrictions Lists */
.capabilities-section, .restrictions-section {
  margin-bottom: 20pt;
}

.capabilities-section h4, .restrictions-section h4 {
  font-size: 12pt;
  font-weight: 600;
  margin: 0 0 12pt 0;
}

.capabilities-section h4 {
  color: #059669;
}

.restrictions-section h4 {
  color: #dc2626;
}

.capability-list, .restriction-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.capability-item, .restriction-item {
  display: flex;
  align-items: center;
  gap: 8pt;
  padding: 8pt 12pt;
  margin-bottom: 4pt;
  border-radius: 6pt;
  font-size: 10pt;
}

.capability-item.positive {
  background-color: #ecfdf5;
  border-left: 4px solid #10b981;
  color: #065f46;
}

.restriction-item.negative {
  background-color: #fef2f2;
  border-left: 4px solid #ef4444;
  color: #991b1b;
}

.capability-item i {
  color: #10b981;
}

.restriction-item i {
  color: #ef4444;
}

/* Matching Criteria Matrix */
.criteria-matrix {
  display: grid;
  gap: 8pt;
  margin-top: 12pt;
}

.criterion-item {
  display: flex;
  align-items: center;
  gap: 12pt;
  padding: 12pt;
  border-radius: 8pt;
  border: 1px solid #e5e7eb;
  background: white;
  transition: all 0.2s ease;
}

.criterion-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.priority-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24pt;
  height: 24pt;
  border-radius: 50%;
  font-size: 9pt;
  font-weight: 700;
  color: white;
}

.badge-essential {
  background-color: #dc2626;
}

.badge-desired {
  background-color: #f59e0b;
}

.badge-normal {
  background-color: #6b7280;
}

.criterion-text {
  flex: 1;
  font-size: 10pt;
  color: #374151;
}

/* Timeline for Work History */
.timeline {
  position: relative;
  padding-left: 24pt;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 8pt;
  top: 0;
  bottom: 0;
  width: 2px;
  background: linear-gradient(180deg, #3b82f6 0%, #8b5cf6 100%);
}

.timeline-item {
  position: relative;
  margin-bottom: 16pt;
}

.timeline-marker {
  position: absolute;
  left: -20pt;
  top: 4pt;
  width: 12pt;
  height: 12pt;
  border-radius: 50%;
  background: #3b82f6;
  border: 3px solid white;
  box-shadow: 0 0 0 2px #3b82f6;
}

.timeline-content {
  padding: 8pt 12pt;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8pt;
  font-size: 10pt;
  color: #374151;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* Symptoms List */
.symptoms-list {
  margin-top: 16pt;
}

.symptoms-list h4 {
  font-size: 12pt;
  font-weight: 600;
  color: #374151;
  margin: 0 0 8pt 0;
}

.symptoms-list ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.symptoms-list li {
  padding: 6pt 0;
  border-bottom: 1px solid #f3f4f6;
  font-size: 10pt;
  color: #6b7280;
}

.symptoms-list li:last-child {
  border-bottom: none;
}

/* Legacy Content Fallback */
.legacy-content {
  /* Inherit existing styles for non-structured content */
}

/* ========================= */
/* ENHANCED UX IMPROVEMENTS */
/* ========================= */

/* Improved Focus Indicators for Better Accessibility */
.section-tab:focus-visible {
  outline: 3px solid var(--primary-color);
  outline-offset: 2px;
  z-index: 10;
  position: relative;
}

.btn:focus-visible {
  outline: 3px solid var(--primary-color);
  outline-offset: 2px;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2);
}

/* Enhanced Loading States */
.loading-spinner {
  animation: spin 1s linear infinite;
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid var(--primary-color);
  border-radius: 50%;
}

.loading-spinner.small {
  width: 12px;
  height: 12px;
  border-width: 1px;
}

.loading-spinner.tiny {
  width: 10px;
  height: 10px;
  border-width: 1px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Better Error States */
.error-state {
  text-align: center;
  padding: var(--spacing-2xl);
  background: var(--error-light);
  border: 1px solid var(--error-color);
  border-radius: var(--radius-lg);
  margin: var(--spacing-lg);
}

.error-state .error-icon {
  font-size: 3rem;
  margin-bottom: var(--spacing-md);
  opacity: 0.7;
}

.error-state h2 {
  color: var(--error-color);
  margin-bottom: var(--spacing-sm);
}

.error-state p {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-lg);
}

/* Enhanced Status Cards */
.status-card {
  padding: var(--spacing-lg);
  border-radius: var(--radius-lg);
  margin-bottom: var(--spacing-lg);
  border: 1px solid transparent;
}

.status-card.processing {
  background: linear-gradient(135deg, var(--info-light) 0%, #f0f9ff 100%);
  border-color: var(--info-color);
}

.status-card.error {
  background: linear-gradient(135deg, var(--error-light) 0%, #fef7f7 100%);
  border-color: var(--error-color);
}

.status-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.status-info h3 {
  margin: 0 0 var(--spacing-sm) 0;
  font-size: var(--font-size-lg);
}

.status-info p {
  margin: 0;
  color: var(--text-secondary);
}

/* Progress Bar Animation */
.progress-bar {
  width: 100%;
  height: 4px;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 2px;
  overflow: hidden;
  margin-top: var(--spacing-sm);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--primary-hover));
  border-radius: 2px;
  animation: progress 2s ease-in-out infinite;
}

@keyframes progress {
  0% { width: 0%; }
  50% { width: 70%; }
  100% { width: 100%; }
}

/* Better Button Hover States */
.btn {
  transition: all 0.2s ease-in-out;
  position: relative;
  overflow: hidden;
}

.btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s;
}

.btn:hover::before {
  left: 100%;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn:disabled::before {
  display: none;
}

/* Enhanced Section Navigation */
.sections-nav {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
  padding: var(--spacing-md);
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  margin-bottom: var(--spacing-lg);
  border: 1px solid var(--border-color);
}

.section-tab {
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--border-color);
  background: var(--bg-primary);
  border-radius: var(--radius);
  transition: all 0.2s ease-in-out;
  cursor: pointer;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  white-space: nowrap;
}

.section-tab:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.section-tab.active {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: var(--text-inverse);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.section-tab .tab-title {
  font-weight: var(--font-weight-medium);
}

.section-tab .tab-status {
  margin-left: var(--spacing-xs);
}

/* Better Mobile Experience */
@media (max-width: 640px) {
  .sections-nav {
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--spacing-xs);
  }
  
  .section-tab {
    text-align: left;
    padding: var(--spacing-md);
  }
  
  .header-actions {
    flex-direction: column;
    gap: var(--spacing-sm);
  }
  
  .viewer-actions {
    flex-wrap: wrap;
    gap: var(--spacing-xs);
  }
  
  .btn {
    width: 100%;
    justify-content: center;
  }
}

/* Enhanced Breadcrumb Navigation */
.breadcrumb {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) 0;
  font-size: var(--font-size-sm);
  color: var(--text-muted);
}

.breadcrumb-item {
  color: var(--primary-color);
  text-decoration: none;
  transition: color 0.2s ease;
}

.breadcrumb-item:hover {
  color: var(--primary-hover);
  text-decoration: underline;
}

.breadcrumb-separator {
  color: var(--text-muted);
  font-weight: var(--font-weight-medium);
}

.breadcrumb-current {
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

/* Print Styles for Professional Reports */
@media print {
  .report-view {
    padding: 0;
    background: white;
  }
  
  .header-actions,
  .sections-nav,
  .viewer-actions,
  .comments-section,
  .sources-dialog {
    display: none !important;
  }
  
  .section-viewer {
    box-shadow: none;
    border: none;
  }
  
  .template-standaard .section-content,
  .template-modern .section-content,
  .template-professioneel .section-content,
  .template-compact .section-content {
    page-break-inside: avoid;
  }
  
  .template-standaard .section-content::before {
    page-break-after: avoid;
  }
}

/* High Contrast Mode Support */
@media (prefers-contrast: high) {
  .section-tab {
    border-width: 2px;
  }
  
  .btn {
    border-width: 2px;
  }
  
  .template-standaard .section-content::before {
    border-bottom-width: 2px;
  }
}

/* Reduced Motion Support */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  
  .btn::before {
    display: none;
  }
}

/* Dark Mode Support (Future Enhancement) */
@media (prefers-color-scheme: dark) {
  /* Placeholder for dark mode styles */
  /* Would require CSS custom properties updates */
}

/* Focus-within for improved keyboard navigation */
.report-view:focus-within {
  /* Enhanced focus styles when any child has focus */
}

.sections-nav:focus-within {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
  border-radius: var(--radius-lg);
}

</style>