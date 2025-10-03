<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useDocumentStore } from '@/stores/document';
import { useCaseStore } from '@/stores/case';
import DocumentProcessingStatus from '@/components/DocumentProcessingStatus.vue';
import HybridRagVisualizer from '@/components/HybridRagVisualizer.vue';

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
    // Check if this is a local audio recording (starting with 'local-audio-')
    if (documentId.value.startsWith('local-audio-')) {
      console.log('Loading local audio document from localStorage');
      const loadedDocument = loadLocalAudioDocument(documentId.value);

      if (loadedDocument) {
        // Set the document in the store manually
        documentStore.currentDocument = loadedDocument;
        console.log('Loaded local audio document:', loadedDocument);

        // Get case ID from the document and fetch case details if needed
        if (loadedDocument.case_id && (!caseStore.currentCase || caseStore.currentCase.id !== loadedDocument.case_id)) {
          await caseStore.fetchCase(loadedDocument.case_id);
        }
      } else {
        throw new Error('Local audio document not found');
      }
    } else {
      // Normal API document fetch
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
    }
  } catch (err) {
    error.value = 'Er is een fout opgetreden bij het ophalen van het document.';
    console.error(err);
  } finally {
    loading.value = false;
  }
};

// Load a local audio document from localStorage
const loadLocalAudioDocument = (documentId: string) => {
  try {
    // Get recordings from localStorage
    const recordings = JSON.parse(localStorage.getItem('audioRecordings') || '[]');

    // Find the recording with the matching ID
    const recording = recordings.find((rec: any) => rec.id === documentId);

    if (recording) {
      return recording;
    }

    return null;
  } catch (err) {
    console.error('Error loading local audio document:', err);
    return null;
  }
};

// Poll for document status updates if it's processing
const startStatusPolling = () => {
  // Clear any existing timer
  if (processingStatusTimer.value) {
    clearInterval(processingStatusTimer.value);
  }

  // Start with 0% progress
  processingProgress.value = 0;

  // Poll every 2 seconds
  processingStatusTimer.value = window.setInterval(async () => {
    try {
      console.log('Polling document status...');
      // Force a fresh fetch without caching
      const document = await documentStore.fetchDocument(documentId.value);
      console.log('Poll response, document status:', document.status);

      // Update progress based on metadata
      if (document.metadata) {
        let parsedMetadata;
        if (typeof document.metadata === 'string') {
          try {
            parsedMetadata = JSON.parse(document.metadata);
          } catch (e) {
            parsedMetadata = {};
          }
        } else {
          parsedMetadata = document.metadata;
        }

        // Update progress if available
        if (parsedMetadata.processing_progress) {
          processingProgress.value = parseFloat(parsedMetadata.processing_progress);
        } else if (document.status === 'processing') {
          // Increment progress artificially if not provided
          processingProgress.value = Math.min(processingProgress.value + 5, 90);
        } else if (document.status === 'processed' || document.status === 'enhanced') {
          processingProgress.value = 100;
        }
      }

      // If document is no longer processing, stop polling
      if (document.status !== 'processing') {
        console.log('Document status is now complete, stopping polling');
        // Set progress to 100% if completed
        processingProgress.value = 100;
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

// Document processing metadata
const processingProgress = ref(0);
const isHybridMode = computed(() => {
  if (!documentStore.currentDocument?.metadata) return false;

  // Check if metadata contains hybrid processing information
  const metadata = documentStore.currentDocument.metadata;
  if (typeof metadata === 'string') {
    try {
      const parsed = JSON.parse(metadata);
      return parsed.processing_strategy !== undefined;
    } catch (e) {
      return false;
    }
  } else if (typeof metadata === 'object') {
    return metadata.processing_strategy !== undefined;
  }

  return false;
});

const processingStrategy = computed(() => {
  if (!documentStore.currentDocument?.metadata) return '';

  // Extract processing strategy from metadata
  const metadata = documentStore.currentDocument.metadata;
  if (typeof metadata === 'string') {
    try {
      const parsed = JSON.parse(metadata);
      return parsed.processing_strategy || '';
    } catch (e) {
      return '';
    }
  } else if (typeof metadata === 'object') {
    return metadata.processing_strategy || '';
  }

  return '';
});

const processingStats = computed(() => {
  if (!documentStore.currentDocument?.metadata) return null;

  // Extract processing stats from metadata
  const metadata = documentStore.currentDocument.metadata;
  let parsedMetadata;

  if (typeof metadata === 'string') {
    try {
      parsedMetadata = JSON.parse(metadata);
    } catch (e) {
      return null;
    }
  } else if (typeof metadata === 'object') {
    parsedMetadata = metadata;
  } else {
    return null;
  }

  // Return processing stats if available
  if (parsedMetadata.chunk_stats || parsedMetadata.strategy_counts) {
    // Convert to expected format
    return {
      total_chunks: parsedMetadata.total_chunks || parsedMetadata.chunk_stats?.total_chunks || 0,
      direct_llm: parsedMetadata.strategy_counts?.direct_llm || 0,
      hybrid: parsedMetadata.strategy_counts?.hybrid || 0,
      full_rag: parsedMetadata.strategy_counts?.full_rag || 0
    };
  }

  return null;
});

// Get document type icon/name based on mimetype or document_type
const getDocumentTypeName = (document: any) => {
  // First check document_type - this is more reliable
  if (document.document_type === 'audio') {
    return 'Audio Opname';
  }

  // Then check mimetype if document_type not available or not specific
  const mimetype = document.mimetype || '';
  if (mimetype === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
    return 'Word Document';
  } else if (mimetype === 'text/plain') {
    return 'Text Document';
  } else if (mimetype.includes('audio')) {
    return 'Audio Opname';
  }

  // Check filename extension as last resort
  if (document.filename) {
    const ext = document.filename.split('.').pop()?.toLowerCase();
    if (['mp3', 'wav', 'ogg', 'webm', 'm4a'].includes(ext)) {
      return 'Audio Opname';
    }
  }

  return 'Document';
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

// Compute distribution for the visualizer
const searchDistribution = computed(() => {
  if (!processingStats.value) {
    return { direct: 33, hybrid: 33, full: 34 };
  }

  const total = processingStats.value.direct_llm +
                processingStats.value.hybrid +
                processingStats.value.full_rag;

  if (total === 0) {
    return { direct: 33, hybrid: 33, full: 34 };
  }

  return {
    direct: Math.round((processingStats.value.direct_llm / total) * 100),
    hybrid: Math.round((processingStats.value.hybrid / total) * 100),
    full: Math.round((processingStats.value.full_rag / total) * 100)
  };
});

// Check if document is an audio recording
const isAudioDocument = computed(() => {
  if (!documentStore.currentDocument) return false;

  // Check document_type field first
  if (documentStore.currentDocument.document_type === 'audio') return true;

  // Check mimetype
  const mimetype = documentStore.currentDocument.mimetype || '';
  if (mimetype.includes('audio')) return true;

  // Check file extension as last resort
  if (documentStore.currentDocument.filename) {
    const ext = documentStore.currentDocument.filename.split('.').pop()?.toLowerCase();
    if (['mp3', 'wav', 'ogg', 'webm', 'm4a'].includes(ext)) return true;
  }

  // Check if this is a local mock audio document
  if (documentStore.currentDocument.id?.startsWith('local-audio-')) return true;

  return false;
});

// Audio player controls
const audioPlayer = ref<HTMLAudioElement | null>(null);
const isPlaying = ref(false);
const audioDuration = ref(0);
const audioCurrentTime = ref(0);
const audioProgress = ref(0);
const audioVolume = ref(1.0);

// Transcription editing
const editTranscription = ref(false);
const editedTranscription = ref('');
const originalTranscription = ref('');

// Initialize transcription editing
const initTranscriptionEdit = () => {
  if (!documentStore.currentDocument?.content) return;

  // Store original content for cancellation
  originalTranscription.value = documentStore.currentDocument.content;
  // Initialize edit field with current content
  editedTranscription.value = documentStore.currentDocument.content;
};

// Save edited transcription
const saveTranscription = async () => {
  if (!documentStore.currentDocument?.id) return;

  try {
    // For mock local documents, update in localStorage
    if (documentStore.currentDocument.id.startsWith('local-audio-')) {
      updateLocalAudioTranscription(documentStore.currentDocument.id, editedTranscription.value);

      // Update document in current view
      if (documentStore.currentDocument) {
        documentStore.currentDocument.content = editedTranscription.value;
      }

      // Exit edit mode
      editTranscription.value = false;

      // Show success message (implement if needed)
      console.log('Transcriptie opgeslagen (lokaal)');
    } else {
      // For real documents, call an API (Mock API call for now)
      console.log('Updating transcription via API for document:', documentStore.currentDocument.id);
      console.log('New transcription:', editedTranscription.value);

      // TODO: Implement actual API call when backend is ready
      // For now, just update the current document in memory
      if (documentStore.currentDocument) {
        documentStore.currentDocument.content = editedTranscription.value;
      }

      // Exit edit mode
      editTranscription.value = false;

      // Show success message (implement if needed)
      console.log('Transcriptie opgeslagen');
    }
  } catch (err) {
    console.error('Error saving transcription:', err);
    // Show error message (implement if needed)
  }
};

// Cancel transcription editing
const cancelTranscriptionEdit = () => {
  // Reset to original content
  if (documentStore.currentDocument) {
    editedTranscription.value = originalTranscription.value;
  }

  // Exit edit mode
  editTranscription.value = false;
};

// Helper to update transcription in localStorage for mock documents
const updateLocalAudioTranscription = (documentId: string, newTranscription: string) => {
  try {
    // Get existing recordings
    const existingRecordings = JSON.parse(localStorage.getItem('audioRecordings') || '[]');

    // Find and update the specific recording
    const updatedRecordings = existingRecordings.map((recording: any) => {
      if (recording.id === documentId) {
        return {
          ...recording,
          content: newTranscription,
          updated_at: new Date().toISOString()
        };
      }
      return recording;
    });

    // Save back to localStorage
    localStorage.setItem('audioRecordings', JSON.stringify(updatedRecordings));
    console.log('Updated transcription in localStorage');
  } catch (err) {
    console.error('Error updating localStorage transcription:', err);
  }
};

// Toggle audio playback
const toggleAudioPlayback = () => {
  if (!audioPlayer.value) return;

  if (isPlaying.value) {
    audioPlayer.value.pause();
  } else {
    audioPlayer.value.play();
  }

  isPlaying.value = !isPlaying.value;
};

// Update audio progress
const updateAudioProgress = () => {
  if (!audioPlayer.value) return;

  audioCurrentTime.value = audioPlayer.value.currentTime;
  audioDuration.value = audioPlayer.value.duration || 0;
  audioProgress.value = audioDuration.value > 0
    ? (audioCurrentTime.value / audioDuration.value) * 100
    : 0;
};

// Format audio time (seconds to MM:SS)
const formatAudioTime = (time: number) => {
  if (isNaN(time)) return '00:00';

  const minutes = Math.floor(time / 60);
  const seconds = Math.floor(time % 60);

  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
};

// Set audio position when user clicks progress bar
const setAudioPosition = (event: MouseEvent) => {
  if (!audioPlayer.value || !event.currentTarget) return;

  const progressBar = event.currentTarget as HTMLElement;
  const rect = progressBar.getBoundingClientRect();
  const position = (event.clientX - rect.left) / rect.width;

  audioPlayer.value.currentTime = position * audioDuration.value;
  updateAudioProgress();
};

// Set audio volume
const setAudioVolume = (event: Event) => {
  if (!audioPlayer.value) return;

  const input = event.target as HTMLInputElement;
  const volume = parseFloat(input.value);

  audioPlayer.value.volume = volume;
  audioVolume.value = volume;
};

// Get audio source URL
const getAudioSourceUrl = computed(() => {
  if (!documentStore.currentDocument) return '';

  // For mock local audio documents (AudioRecorder component), use the file_path directly
  if (documentStore.currentDocument.id?.startsWith('local-audio-')) {
    return documentStore.currentDocument.file_path || '';
  }

  // For real audio documents, construct URL from base API URL
  const fileUrl = documentStore.currentDocument.file_path || documentStore.currentDocument.storage_path;
  if (fileUrl) {
    return `/api/files/${fileUrl}`;
  }

  return '';
});

// Initialize component and set up cleanup
onMounted(() => {
  fetchDocument();

  // Use a watcher to initialize transcription editing once document is loaded
  watch(() => documentStore.currentDocument, (newDoc) => {
    if (newDoc?.content) {
      initTranscriptionEdit();
    }
  }, { immediate: true });
});

// Clean up on component unmount
onUnmounted(() => {
  stopStatusPolling();

  // Clean up audio player
  if (audioPlayer.value) {
    audioPlayer.value.pause();
    audioPlayer.value.src = '';
  }
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

      <!-- Processing Status with Enhanced UI -->
      <DocumentProcessingStatus
        v-if="documentStore.currentDocument"
        :status="documentStore.currentDocument.status"
        :document="documentStore.currentDocument"
        :progress="processingProgress"
        :statusMessage="documentStore.currentDocument.error || ''"
        :processingStrategy="processingStrategy"
        :processingStats="processingStats"
        :isHybridMode="isHybridMode"
      />

      <!-- Document Details -->
      <!-- Hybrid RAG Architecture Visualizer -->
      <HybridRagVisualizer
        v-if="isHybridMode && processingStats"
        :activeSize="processingStrategy === 'direct_llm' ? 'small' :
                    processingStrategy === 'hybrid' ? 'medium' : 'large'"
        :showSearchFlow="true"
        :searchDistribution="searchDistribution"
        :totalResults="processingStats?.total_chunks || 0"
        :avgSimilarity="0.78"
      />

      <div class="document-details">
        <!-- Audio Player for Audio Documents -->
        <div v-if="isAudioDocument" class="detail-card audio-player-container">
          <h3>Audio Opname</h3>
          <div class="audio-player-controls">
            <audio
              ref="audioPlayer"
              :src="getAudioSourceUrl"
              style="display: none;"
              @play="isPlaying = true"
              @pause="isPlaying = false"
              @timeupdate="updateAudioProgress"
              @ended="isPlaying = false"
              @loadedmetadata="updateAudioProgress"
            ></audio>

            <div class="audio-controls">
              <button @click="toggleAudioPlayback" class="play-button">
                <i class="fas" :class="isPlaying ? 'fa-pause' : 'fa-play'"></i>
              </button>

              <div class="audio-progress">
                <div class="progress-time">{{ formatAudioTime(audioCurrentTime) }}</div>
                <div class="progress-bar-container" @click="setAudioPosition">
                  <div class="progress-bar" :style="{ width: `${audioProgress}%` }"></div>
                </div>
                <div class="progress-time">{{ formatAudioTime(audioDuration) }}</div>
              </div>

              <div class="volume-control">
                <i class="fas fa-volume-up"></i>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  v-model="audioVolume"
                  @input="setAudioVolume"
                />
              </div>
            </div>
          </div>
        </div>

        <div class="detail-card">
          <h3>Document Informatie</h3>
          <div class="detail-item">
            <div class="detail-label">Bestandsnaam</div>
            <div class="detail-value">{{ documentStore.currentDocument.filename }}</div>
          </div>
          <div class="detail-item">
            <div class="detail-label">Type</div>
            <div class="detail-value">{{ getDocumentTypeName(documentStore.currentDocument) }}</div>
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
          v-if="(documentStore.currentDocument.status === 'processed' || documentStore.currentDocument.status === 'enhanced') && !isAudioDocument && documentStore.currentDocument.chunks && documentStore.currentDocument.chunks.length > 0"
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

        <!-- Audio Transcription for audio documents -->
        <div
          v-if="isAudioDocument && (documentStore.currentDocument.status === 'processed' || documentStore.currentDocument.status === 'enhanced')"
          class="document-preview transcription-container"
        >
          <div class="transcription-header">
            <h3>Transcriptie</h3>
            <div class="transcription-actions">
              <button class="btn btn-outline" @click="editTranscription = !editTranscription">
                <i class="fas" :class="editTranscription ? 'fa-eye' : 'fa-edit'"></i>
                {{ editTranscription ? 'Bekijken' : 'Bewerken' }}
              </button>
            </div>
          </div>

          <!-- View mode -->
          <div v-if="!editTranscription" class="transcription-content">
            <p v-if="!documentStore.currentDocument.content" class="no-content">
              Geen transcriptie beschikbaar voor deze audio opname.
            </p>
            <div v-else class="transcription-text">
              {{ documentStore.currentDocument.content }}
            </div>
          </div>

          <!-- Edit mode -->
          <div v-else class="transcription-edit">
            <textarea
              v-model="editedTranscription"
              class="transcription-textarea"
              placeholder="Bewerk de transcriptie hier..."
              rows="10"
            ></textarea>
            <div class="transcription-edit-actions">
              <button class="btn btn-primary" @click="saveTranscription">
                <i class="fas fa-save"></i> Opslaan
              </button>
              <button class="btn btn-secondary" @click="cancelTranscriptionEdit">
                <i class="fas fa-times"></i> Annuleren
              </button>
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

/* Audio Player Styles */
.audio-player-container {
  grid-column: 1 / -1;
  margin-bottom: 1.5rem;
}

.audio-player-controls {
  margin-top: 1rem;
}

.audio-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
  background-color: #f8f9fa;
  padding: 0.75rem;
  border-radius: 8px;
}

.play-button {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: none;
  background-color: #3b82f6;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.1s;
}

.play-button:hover {
  transform: scale(1.05);
  background-color: #2563eb;
}

.play-button:active {
  transform: scale(0.95);
}

.audio-progress {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.progress-time {
  font-family: monospace;
  font-size: 0.9rem;
  color: #6b7280;
  min-width: 40px;
  text-align: center;
}

.progress-bar-container {
  flex: 1;
  height: 8px;
  background-color: #e5e7eb;
  border-radius: 4px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background-color: #3b82f6;
  border-radius: 4px;
  transition: width 0.1s;
}

.volume-control {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #6b7280;
}

.volume-control input[type="range"] {
  width: 80px;
  cursor: pointer;
}

/* Transcription Styles */
.transcription-container {
  grid-column: 1 / -1;
}

.transcription-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.transcription-header h3 {
  margin: 0;
}

.transcription-actions {
  display: flex;
  gap: 0.5rem;
}

.transcription-content {
  background-color: white;
  border-radius: 8px;
  padding: 1.5rem;
  border: 1px solid #e5e7eb;
}

.transcription-text {
  white-space: pre-wrap;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  font-size: 1rem;
  line-height: 1.6;
  color: var(--text-color);
}

.no-content {
  color: var(--text-light);
  font-style: italic;
  text-align: center;
  padding: 2rem;
}

.transcription-edit {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.transcription-textarea {
  width: 100%;
  padding: 1rem;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  font-size: 1rem;
  line-height: 1.6;
  resize: vertical;
  min-height: 200px;
}

.transcription-textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}

.transcription-edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
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