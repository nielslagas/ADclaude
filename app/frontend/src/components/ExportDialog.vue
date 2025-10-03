<template>
  <div v-if="isOpen" class="export-dialog modal-overlay">
    <div class="modal-container">
      <div class="modal-header">
        <h2 class="modal-title">
          <span class="icon">📄</span>
          Rapport Exporteren
        </h2>
        <button @click="close" class="close-btn" aria-label="Sluiten">
          <span class="icon">✕</span>
        </button>
      </div>

      <div class="modal-body">
        <!-- Format Selection -->
        <div class="export-section">
          <h3 class="section-title">Bestandsformaat</h3>
          <div class="format-grid">
            <div
              v-for="format in availableFormats"
              :key="format.id"
              @click="selectedFormat = format.id"
              :class="['format-card', { active: selectedFormat === format.id }]"
              tabindex="0"
              @keydown.enter="selectedFormat = format.id"
            >
              <div class="format-icon">{{ format.icon }}</div>
              <div class="format-name">{{ format.name }}</div>
              <div class="format-description">{{ format.description }}</div>
              <div v-if="selectedFormat === format.id" class="format-selected">
                <span class="icon">✓</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Template Selection -->
        <div class="export-section">
          <h3 class="section-title">Template Stijl</h3>
          <div class="template-grid">
            <div
              v-for="template in availableTemplates"
              :key="template.id"
              @click="selectedTemplate = template.id"
              :class="['template-card', { active: selectedTemplate === template.id }]"
              tabindex="0"
              @keydown.enter="selectedTemplate = template.id"
            >
              <div class="template-preview">
                <div :class="['preview-header', `preview-${template.id}`]">
                  <div class="preview-line long"></div>
                  <div class="preview-line medium"></div>
                </div>
                <div class="preview-content">
                  <div class="preview-line short"></div>
                  <div class="preview-line long"></div>
                  <div class="preview-line medium"></div>
                </div>
              </div>
              <div class="template-info">
                <div class="template-name">{{ template.name }}</div>
                <div class="template-description">{{ template.description }}</div>
                <div class="template-features">
                  <span
                    v-for="feature in template.features"
                    :key="feature"
                    class="feature-tag"
                  >
                    {{ feature }}
                  </span>
                </div>
              </div>
              <div v-if="selectedTemplate === template.id" class="template-selected">
                <span class="icon">✓</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Export Options -->
        <div class="export-section">
          <h3 class="section-title">Export Opties</h3>
          <div class="options-grid">
            <label class="option-item">
              <input
                type="checkbox"
                v-model="includeStructuredContent"
                :disabled="!supportsStructuredContent"
              />
              <span class="checkbox-custom"></span>
              <span class="option-label">
                Gestructureerde inhoud gebruiken
                <small v-if="!supportsStructuredContent">(Niet beschikbaar voor dit rapport)</small>
              </span>
            </label>
            
            <label class="option-item">
              <input
                type="checkbox"
                v-model="includeMetadata"
              />
              <span class="checkbox-custom"></span>
              <span class="option-label">
                Metadata en bronverwijzingen includeren
              </span>
            </label>
            
            <label class="option-item" v-if="selectedFormat === 'pdf'">
              <input
                type="checkbox"
                v-model="enableWatermark"
              />
              <span class="checkbox-custom"></span>
              <span class="option-label">
                Watermerk toevoegen
              </span>
            </label>
          </div>
        </div>

        <!-- Preview Section -->
        <div v-if="previewUrl" class="export-section">
          <h3 class="section-title">Voorbeeld</h3>
          <div class="preview-container">
            <button @click="generatePreview" class="btn btn-secondary" :disabled="generatingPreview">
              <span v-if="generatingPreview" class="loading-spinner small"></span>
              <span v-else class="icon">👁️</span>
              {{ generatingPreview ? 'Voorbeeld wordt geladen...' : 'Voorbeeld genereren' }}
            </button>
          </div>
        </div>

        <!-- Export Progress -->
        <div v-if="exportProgress.show" class="export-section">
          <div class="progress-container">
            <div class="progress-header">
              <span class="progress-title">{{ exportProgress.title }}</span>
              <span class="progress-percentage">{{ exportProgress.percentage }}%</span>
            </div>
            <div class="progress-bar">
              <div 
                class="progress-fill" 
                :style="{ width: `${exportProgress.percentage}%` }"
              ></div>
            </div>
            <div class="progress-message">{{ exportProgress.message }}</div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button @click="close" class="btn btn-secondary" :disabled="isExporting">
          Annuleren
        </button>
        <button
          @click="startExport"
          class="btn btn-primary"
          :disabled="isExporting || !canExport"
        >
          <span v-if="isExporting" class="loading-spinner small"></span>
          <span v-else class="icon">📥</span>
          {{ isExporting ? 'Bezig met exporteren...' : 'Exporteren' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useReportStore } from '@/stores/report';
import { useNotificationStore } from '@/stores/notification';
import { apiClient } from '@/services/api';
import { useAuthenticatedDownload } from '@/composables/useAuthenticatedDownload';

// Props
interface Props {
  isOpen: boolean;
  reportId: string;
}

const props = defineProps<Props>();

// Emits
const emit = defineEmits<{
  close: [];
  exported: [{ format: string; template: string; filename: string }];
}>();

// Stores
const reportStore = useReportStore();
const notificationStore = useNotificationStore();
const { downloadFile, buildAuthenticatedUrl } = useAuthenticatedDownload();

// Reactive state
const selectedFormat = ref('docx');
const selectedTemplate = ref('standaard');
const includeStructuredContent = ref(true);
const includeMetadata = ref(false);
const enableWatermark = ref(false);
const isExporting = ref(false);
const generatingPreview = ref(false);
const previewUrl = ref('');

// Available formats
const availableFormats = ref([
  {
    id: 'docx',
    name: 'Microsoft Word',
    description: 'Volledig bewerkbaar document met alle opmaak',
    icon: '📄',
    mime: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  },
  {
    id: 'pdf',
    name: 'PDF Document',
    description: 'Universeel leesbaar, klaar om te delen',
    icon: '📋',
    mime: 'application/pdf'
  },
  {
    id: 'html',
    name: 'Webpagina',
    description: 'Voor online weergave of verdere bewerking',
    icon: '🌐',
    mime: 'text/html'
  }
]);

// Available templates (loaded from API)
const availableTemplates = ref([
  {
    id: 'standaard',
    name: 'Standaard',
    description: 'Traditioneel Nederlandse zakelijke indeling',
    features: ['Klassieke layout', 'Professionele typografie']
  },
  {
    id: 'modern',
    name: 'Modern',
    description: 'Hedendaagse lay-out met blauwe headers',
    features: ['Twee-kolommen titelpagina', 'Headers en footers']
  },
  {
    id: 'professioneel',
    name: 'Professioneel',
    description: 'Minimalistische professionele vormgeving',
    features: ['Clean design', 'Gestructureerde subsecties']
  },
  {
    id: 'compact',
    name: 'Compact',
    description: 'Ruimte-efficiënt formaat voor korte rapporten',
    features: ['Kleinere fonts', 'Verminderde marges']
  }
]);

// Export progress tracking
const exportProgress = ref({
  show: false,
  title: '',
  message: '',
  percentage: 0
});

// Computed properties
const canExport = computed(() => {
  return props.reportId && selectedFormat.value && selectedTemplate.value && !isExporting.value;
});

const supportsStructuredContent = computed(() => {
  // Check if the current report has structured content available
  const report = reportStore.currentReport;
  if (!report || !report.metadata) return false;
  return !!report.metadata.structured_content;
});

const currentFormat = computed(() => {
  return availableFormats.value.find(f => f.id === selectedFormat.value);
});

const currentTemplate = computed(() => {
  return availableTemplates.value.find(t => t.id === selectedTemplate.value);
});

// Methods
const close = () => {
  if (!isExporting.value) {
    emit('close');
  }
};

const loadTemplates = async () => {
  try {
    const response = await apiClient.get('/reports/export/templates');
    if (response.data?.templates) {
      availableTemplates.value = Object.values(response.data.templates);
    }
  } catch (error) {
    console.warn('Could not load export templates:', error);
    // Keep default templates
  }
};

const generatePreview = async () => {
  if (!canExport.value) return;

  generatingPreview.value = true;
  try {
    // For HTML format, we can generate a preview
    if (selectedFormat.value === 'html') {
      const queryParams: Record<string, string> = {
        layout: selectedTemplate.value
      };
      
      // Add additional parameters based on options
      if (includeStructuredContent.value && supportsStructuredContent.value) {
        queryParams.structured = 'true';
      }
      if (includeMetadata.value) {
        queryParams.metadata = 'true';
      }
      
      const url = await buildAuthenticatedUrl(`/reports/${props.reportId}/export/html`, queryParams);
      previewUrl.value = url;
    } else {
      // For other formats, show a message
      notificationStore.addNotification({
        type: 'info',
        title: 'Voorbeeld niet beschikbaar',
        message: `Voorbeeld is alleen beschikbaar voor HTML formaat. Het ${currentFormat.value?.name} bestand wordt direct gedownload.`
      });
    }
  } catch (error) {
    console.error('Preview generation failed:', error);
    notificationStore.addNotification({
      type: 'error',
      title: 'Voorbeeld mislukt',
      message: 'Er is een fout opgetreden bij het genereren van het voorbeeld.'
    });
  } finally {
    generatingPreview.value = false;
  }
};

const buildExportParams = (format: string): Record<string, string> => {
  const params: Record<string, string> = {
    layout: selectedTemplate.value
  };

  // Add additional parameters based on options
  if (includeStructuredContent.value && supportsStructuredContent.value) {
    params.structured = 'true';
  }
  if (includeMetadata.value) {
    params.metadata = 'true';
  }
  if (enableWatermark.value && format === 'pdf') {
    params.watermark = 'true';
  }

  return params;
};

const updateProgress = (title: string, message: string, percentage: number) => {
  exportProgress.value = {
    show: true,
    title,
    message,
    percentage: Math.min(100, Math.max(0, percentage))
  };
};

const startExport = async () => {
  if (!canExport.value) {
    return;
  }

  isExporting.value = true;
  
  try {
    updateProgress('Exporteren gestart', 'Bestand wordt voorbereid...', 10);

    // Generate filename
    const timestamp = new Date().toISOString().slice(0, 10);
    const reportTitle = reportStore.currentReport?.title?.replace(/[^a-zA-Z0-9]/g, '_') || 'rapport';
    const extension = currentFormat.value?.id || 'docx';
    const filename = `${reportTitle}_${selectedTemplate.value}_${timestamp}.${extension}`;
    
    updateProgress('Download wordt voorbereid', 'Verbinding maken met server...', 30);

    // Build export parameters
    const exportParams = buildExportParams(selectedFormat.value);
    const exportPath = `/reports/${props.reportId}/export/${selectedFormat.value}`;
    
    updateProgress('Download starten', 'Bestand wordt gedownload...', 70);

    // Use authenticated download
    await downloadFile(exportPath, filename, exportParams);

    updateProgress('Voltooid', 'Export succesvol voltooid', 100);

    // Show success notification
    notificationStore.addNotification({
      type: 'success',
      title: 'Export succesvol',
      message: `Het rapport is geëxporteerd als ${currentFormat.value?.name} bestand.`
    });

    // Emit success event
    emit('exported', {
      format: selectedFormat.value,
      template: selectedTemplate.value,
      filename: filename
    });

    // Close dialog after short delay
    setTimeout(() => {
      close();
    }, 1500);

  } catch (error) {
    console.error('Export failed:', error);
    
    exportProgress.value.show = false;
    
    const errorMessage = error instanceof Error ? error.message : 'Onbekende fout';
    notificationStore.addNotification({
      type: 'error',
      title: 'Export mislukt',
      message: `Er is een fout opgetreden bij het exporteren van het rapport: ${errorMessage}`
    });
  } finally {
    isExporting.value = false;
    // Hide progress after delay
    setTimeout(() => {
      exportProgress.value.show = false;
    }, 3000);
  }
};

// Watch for format changes to update options
watch(selectedFormat, (newFormat) => {
  // Reset format-specific options
  if (newFormat !== 'pdf') {
    enableWatermark.value = false;
  }
});

// Load templates on mount
onMounted(() => {
  loadTemplates();
});
</script>

<style scoped>
.export-dialog {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  max-width: 800px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: between;
  align-items: center;
  padding: 24px 32px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #6b7280;
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: #f3f4f6;
  color: #374151;
}

.modal-body {
  padding: 32px;
  max-height: 60vh;
  overflow-y: auto;
}

.export-section {
  margin-bottom: 32px;
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.format-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.format-card {
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  background: white;
}

.format-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.format-card.active {
  border-color: #3b82f6;
  background: #eff6ff;
}

.format-icon {
  font-size: 2rem;
  margin-bottom: 8px;
}

.format-name {
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.format-description {
  color: #6b7280;
  font-size: 0.875rem;
}

.format-selected {
  position: absolute;
  top: 12px;
  right: 12px;
  background: #3b82f6;
  color: white;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.template-card {
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  background: white;
}

.template-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.template-card.active {
  border-color: #3b82f6;
  background: #eff6ff;
}

.template-preview {
  height: 80px;
  background: #f9fafb;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
  border: 1px solid #e5e7eb;
}

.preview-header {
  margin-bottom: 8px;
}

.preview-line {
  height: 3px;
  background: #d1d5db;
  border-radius: 2px;
  margin-bottom: 4px;
}

.preview-line.long { width: 80%; }
.preview-line.medium { width: 60%; }
.preview-line.short { width: 40%; }

/* Template-specific preview colors */
.preview-standaard .preview-line { background: #374151; }
.preview-modern .preview-line { background: #3b82f6; }
.preview-professioneel .preview-line { background: #1e40af; }
.preview-compact .preview-line { background: #2563eb; height: 2px; }

.template-info {
  margin-bottom: 8px;
}

.template-name {
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.template-description {
  color: #6b7280;
  font-size: 0.875rem;
  margin-bottom: 8px;
}

.template-features {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.feature-tag {
  background: #f3f4f6;
  color: #6b7280;
  font-size: 0.75rem;
  padding: 2px 6px;
  border-radius: 4px;
}

.template-selected {
  position: absolute;
  top: 12px;
  right: 12px;
  background: #3b82f6;
  color: white;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
}

.options-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.option-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  cursor: pointer;
}

.option-item input[type="checkbox"] {
  display: none;
}

.checkbox-custom {
  width: 20px;
  height: 20px;
  border: 2px solid #d1d5db;
  border-radius: 4px;
  position: relative;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.option-item input[type="checkbox"]:checked + .checkbox-custom {
  background: #3b82f6;
  border-color: #3b82f6;
}

.option-item input[type="checkbox"]:checked + .checkbox-custom::after {
  content: '✓';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  font-size: 0.75rem;
  font-weight: bold;
}

.option-item input[type="checkbox"]:disabled + .checkbox-custom {
  background: #f3f4f6;
  border-color: #d1d5db;
}

.option-label {
  color: #374151;
  font-size: 0.875rem;
  line-height: 1.4;
}

.option-label small {
  display: block;
  color: #9ca3af;
  margin-top: 2px;
}

.progress-container {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 20px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.progress-title {
  font-weight: 600;
  color: #1f2937;
}

.progress-percentage {
  font-weight: 500;
  color: #3b82f6;
}

.progress-bar {
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #1d4ed8);
  transition: width 0.3s ease;
}

.progress-message {
  color: #6b7280;
  font-size: 0.875rem;
}

.preview-container {
  padding: 16px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  text-align: center;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 24px 32px;
  border-top: 1px solid #e5e7eb;
  background: #f9fafb;
}

.btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.875rem;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s ease;
  text-decoration: none;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}

.btn-secondary:hover:not(:disabled) {
  background: #e5e7eb;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top: 2px solid currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loading-spinner.small {
  width: 14px;
  height: 14px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.icon {
  font-style: normal;
}
</style>