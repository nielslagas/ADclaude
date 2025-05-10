<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useDocumentStore } from '@/stores/document';
import { useCaseStore } from '@/stores/case';

const route = useRoute();
const router = useRouter();
const documentStore = useDocumentStore();
const caseStore = useCaseStore();

const loading = ref(false);
const error = ref<string | null>(null);
const processingStatusTimer = ref<number | null>(null);
const documentId = ref(route.params.id as string);

// Fetch document details
const fetchDocument = async () => {
  if (!documentId.value) return;
  
  loading.value = true;
  try {
    const document = await documentStore.fetchDocument(documentId.value);
    
    // If document is still processing, start polling
    if (document.status === 'processing') {
      console.log('Document is in processing state, starting polling');
      startStatusPolling();
    } else {
      console.log('Document is in final state:', document.status);
    }
    
    // Fetch case details if we don't have them already
    if (!caseStore.currentCase || caseStore.currentCase.id !== document.case_id) {
      await caseStore.fetchCase(document.case_id);
    }
  } catch (err) {
    error.value = 'Er is een fout opgetreden bij het ophalen van het document.';
    console.error(err);
  } finally {
    loading.value = false;
  }
};

// Poll for document status updates if it's processing
const startStatusPolling = () => {
  // Clear any existing timer
  if (processingStatusTimer.value) {
    clearInterval(processingStatusTimer.value);
  }
  
  // Poll every 2 seconds
  processingStatusTimer.value = window.setInterval(async () => {
    try {
      console.log('Polling document status...');
      // Force a fresh fetch without caching
      const document = await documentStore.fetchDocument(documentId.value);
      console.log('Poll response, document status:', document.status);
      
      // If document is no longer processing, stop polling
      if (document.status !== 'processing') {
        console.log('Document status is now complete, stopping polling');
        stopStatusPolling();
        
        // Force an immediate UI refresh if needed
        if (document.status === 'processed' || document.status === 'enhanced') {
          console.log('Document is processed or enhanced, refreshing UI');
        }
      }
    } catch (err) {
      console.error('Error polling document status:', err);
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

// Delete document
const deleteDocument = async () => {
  if (!confirm('Weet je zeker dat je dit document wilt verwijderen?')) {
    return;
  }
  
  try {
    await documentStore.deleteDocument(documentId.value);
    
    // Navigate back to case detail
    if (caseStore.currentCase) {
      router.push(`/cases/${caseStore.currentCase.id}`);
    } else {
      router.push('/cases');
    }
  } catch (err) {
    error.value = 'Er is een fout opgetreden bij het verwijderen van het document.';
    console.error(err);
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

// Format file size
const formatFileSize = (bytes: number) => {
  if (bytes < 1024) {
    return `${bytes} B`;
  } else if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  } else {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
};

// Get document type icon/name based on mimetype
const getDocumentTypeName = (mimetype: string) => {
  if (mimetype === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
    return 'Word Document';
  } else if (mimetype === 'text/plain') {
    return 'Text Document';
  } else {
    return 'Document';
  }
};

// Get status class for styling
const getStatusClass = (status: string) => {
  const statusMap: Record<string, string> = {
    'processing': 'status-processing',
    'processed': 'status-success',
    'enhanced': 'status-success',  // Added 'enhanced' status for documents with embeddings
    'failed': 'status-error'
  };
  
  return statusMap[status] || 'status-default';
};

// Initialize component and set up cleanup
onMounted(() => {
  fetchDocument();
});

// Clean up on component unmount
onUnmounted(() => {
  stopStatusPolling();
});
</script>

<template>
  <div class="document-detail-container">
    <div v-if="loading && !documentStore.currentDocument" class="loading">
      <p>Document wordt geladen...</p>
    </div>

    <div v-else-if="!documentStore.currentDocument" class="error-state">
      <h2>Document niet gevonden</h2>
      <p>Het opgevraagde document bestaat niet of je hebt geen toegang.</p>
      <button @click="router.push('/cases')" class="btn btn-primary">Terug naar Cases</button>
    </div>

    <div v-else class="document-content">
      <!-- Document Header -->
      <div class="document-header">
        <div class="document-title-section">
          <h1>{{ documentStore.currentDocument.filename }}</h1>
          <span 
            class="document-status" 
            :class="getStatusClass(documentStore.currentDocument.status)"
          >
            {{ documentStore.currentDocument.status }}
          </span>
        </div>
        
        <div class="document-actions">
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
            <button @click="deleteDocument" class="btn btn-danger">
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
        v-if="documentStore.currentDocument.status === 'processing'" 
        class="processing-status"
      >
        <div class="spinner"></div>
        <p>Document wordt verwerkt. Dit kan enkele minuten duren.</p>
      </div>

      <!-- Error Status -->
      <div 
        v-if="documentStore.currentDocument.status === 'failed'" 
        class="error-status"
      >
        <p>Document verwerking is mislukt.</p>
        <p v-if="documentStore.currentDocument.error" class="error-message">
          {{ documentStore.currentDocument.error }}
        </p>
      </div>

      <!-- Document Details -->
      <div class="document-details">
        <div class="detail-card">
          <h3>Document Informatie</h3>
          <div class="detail-item">
            <div class="detail-label">Bestandsnaam</div>
            <div class="detail-value">{{ documentStore.currentDocument.filename }}</div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Type</div>
            <div class="detail-value">{{ getDocumentTypeName(documentStore.currentDocument.mimetype) }}</div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Grootte</div>
            <div class="detail-value">{{ formatFileSize(documentStore.currentDocument.size) }}</div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Status</div>
            <div class="detail-value" :class="getStatusClass(documentStore.currentDocument.status)">
              {{ documentStore.currentDocument.status }}
            </div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Geüpload</div>
            <div class="detail-value">{{ formatDate(documentStore.currentDocument.created_at) }}</div>
          </div>
          <div class="detail-item" v-if="documentStore.currentDocument.updated_at">
            <div class="detail-label">Laatst bijgewerkt</div>
            <div class="detail-value">{{ formatDate(documentStore.currentDocument.updated_at) }}</div>
          </div>
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

        <!-- Document Content Preview (For processed documents) -->
        <div 
          v-if="(documentStore.currentDocument.status === 'processed' || documentStore.currentDocument.status === 'enhanced') && documentStore.currentDocument.chunks && documentStore.currentDocument.chunks.length > 0" 
          class="document-preview"
        >
          <h3>Document Preview</h3>
          <div 
            v-for="(chunk, index) in documentStore.currentDocument.chunks" 
            :key="index"
            class="document-chunk"
          >
            <div class="chunk-header">
              <span>Segment {{ index + 1 }}</span>
            </div>
            <div class="chunk-content">
              {{ chunk.content }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.document-detail-container {
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

.document-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.document-title-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.document-title-section h1 {
  margin: 0;
  color: var(--primary-color);
  font-size: 1.75rem;
  word-break: break-word;
}

.document-status {
  font-size: 0.75rem;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-weight: 500;
  white-space: nowrap;
}

.document-actions {
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

.document-details {
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

.document-preview {
  grid-column: 1 / -1;
  background-color: white;
  border-radius: 8px;
  box-shadow: var(--shadow);
  padding: 1.5rem;
}

.document-preview h3 {
  margin-top: 0;
  margin-bottom: 1.25rem;
  color: var(--primary-color);
  font-size: 1.25rem;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 0.75rem;
}

.document-chunk {
  margin-bottom: 1.5rem;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
}

.chunk-header {
  background-color: #f8f9fa;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid #e5e7eb;
  font-weight: 500;
  color: var(--text-light);
  font-size: 0.9rem;
}

.chunk-content {
  padding: 1rem;
  white-space: pre-wrap;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--text-color);
  overflow-x: auto;
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
  .document-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .document-actions {
    width: 100%;
    flex-direction: column;
    gap: 1rem;
  }

  .action-group {
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
}
</style>