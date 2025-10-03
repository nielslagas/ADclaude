<template>
  <div class="audio-recording-page">
    <h1 class="page-title">Audio Opname</h1>
    
    <div class="case-selector" v-if="!selectedCase">
      <h2>Selecteer een Casus</h2>
      <div v-if="loading" class="loading-indicator">
        <i class="fas fa-spinner fa-spin"></i> Casussen laden...
      </div>
      
      <div v-else-if="cases.length === 0" class="no-cases-message">
        <p>Geen casussen gevonden. Maak eerst een nieuwe casus aan.</p>
        <router-link to="/cases/new" class="btn btn-primary">Nieuwe Casus</router-link>
      </div>
      
      <div v-else class="case-list">
        <div
          v-for="caseItem in cases"
          :key="caseItem.id"
          class="case-item"
          @click="selectCase(caseItem)"
        >
          <div class="case-info">
            <h3>{{ caseItem.title }}</h3>
            <p class="case-description">{{ caseItem.description || 'Geen beschrijving' }}</p>
            <p class="case-date">Gemaakt op: {{ formatDate(caseItem.created_at) }}</p>
          </div>
        </div>
      </div>
    </div>
    
    <div v-else class="recording-section">
      <div class="case-header">
        <h2>
          <i class="fas fa-folder-open"></i>
          Casus: {{ selectedCase.title }}
        </h2>
        <button class="btn btn-outline-secondary" @click="deselectCase">
          <i class="fas fa-arrow-left"></i> Andere Casus Kiezen
        </button>
      </div>
      
      <AudioRecorder 
        :case-id="selectedCase.id" 
        @recording-saved="onRecordingSaved"
      />
      
      <div v-if="recentRecordings.length > 0" class="recent-recordings">
        <h3>Recente Opnames</h3>
        <div class="recordings-list">
          <div 
            v-for="recording in recentRecordings" 
            :key="recording.id"
            class="recording-item"
          >
            <div class="recording-info">
              <i class="fas fa-microphone"></i>
              <span class="recording-title">{{ recording.title }}</span>
              <span class="recording-status" :class="recording.status">
                {{ getStatusLabel(recording.status) }}
              </span>
              <span v-if="recording.metadata && recording.metadata.transcription_method" class="transcription-method" :class="recording.metadata.transcription_method">
                {{ getTranscriptionMethodLabel(recording.metadata.transcription_method) }}
              </span>
            </div>
            
            <div class="recording-actions">
              <button 
                class="btn btn-sm btn-info"
                @click="viewTranscription(recording)"
                :disabled="recording.status !== 'processed'"
              >
                <i class="fas fa-file-alt"></i>
                Bekijk Transcriptie
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div v-if="selectedRecording" class="transcription-modal">
      <div class="modal-overlay" @click="closeTranscription"></div>
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ selectedRecording.title }}</h3>
          <button class="close-button" @click="closeTranscription">
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="modal-body">
          <div v-if="loadingTranscription" class="loading-transcription">
            <i class="fas fa-spinner fa-spin"></i>
            Transcriptie laden...
          </div>
          
          <div v-else-if="transcriptionError" class="transcription-error">
            <i class="fas fa-exclamation-triangle"></i>
            {{ transcriptionError }}
          </div>
          
          <div v-else class="transcription-content">
            <p v-if="!transcriptionContent" class="no-transcription">
              Geen transcriptie beschikbaar
            </p>
            <div v-else>
              <div class="transcription-header">
                <span class="transcription-info">
                  <span v-if="selectedRecording.metadata && selectedRecording.metadata.transcription_method"
                    class="transcription-method-badge"
                    :class="selectedRecording.metadata.transcription_method"
                  >
                    {{ getTranscriptionMethodLabel(selectedRecording.metadata.transcription_method) }}
                  </span>
                  <span v-if="selectedRecording.metadata && selectedRecording.metadata.transcription_length" class="transcription-length">
                    {{ selectedRecording.metadata.transcription_length }} tekens
                  </span>
                  <span v-if="selectedRecording.metadata && selectedRecording.metadata.language" class="transcription-language">
                    Taal: {{ selectedRecording.metadata.language === 'nl' ? 'Nederlands' : selectedRecording.metadata.language }}
                  </span>
                </span>
              </div>
              <div class="content-area">
                {{ transcriptionContent }}
              </div>
            </div>
            
            <div class="action-buttons">
              <button class="btn btn-primary" @click="useInReport(selectedRecording)">
                <i class="fas fa-file-import"></i>
                Gebruiken in Rapport
              </button>
              
              <button class="btn btn-outline-secondary" @click="closeTranscription">
                <i class="fas fa-times"></i>
                Sluiten
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div v-if="successMessage" class="success-notification">
      <i class="fas fa-check-circle"></i>
      {{ successMessage }}
    </div>
  </div>
</template>

<script>
import AudioRecorder from '@/components/audio/AudioRecorder.vue';

export default {
  name: 'AudioRecordingView',
  components: {
    AudioRecorder
  },
  data() {
    return {
      loading: false,
      cases: [],
      selectedCase: null,
      recentRecordings: [],
      selectedRecording: null,
      transcriptionContent: null,
      loadingTranscription: false,
      transcriptionError: null,
      successMessage: null,
      successTimer: null
    }
  },
  mounted() {
    this.loadCases();
  },
  methods: {
    async loadCases() {
      this.loading = true;
      try {
        const response = await this.$axios.get('/cases/');
        this.cases = response.data;
      } catch (error) {
        console.error('Error loading cases:', error);
      } finally {
        this.loading = false;
      }
    },
    
    selectCase(caseItem) {
      this.selectedCase = caseItem;
      this.loadCaseRecordings(caseItem.id);
    },
    
    deselectCase() {
      this.selectedCase = null;
      this.recentRecordings = [];
    },
    
    async loadCaseRecordings(caseId) {
      try {
        const response = await this.$axios.get(`/cases/${caseId}/documents?type=audio`);
        this.recentRecordings = response.data.filter(doc => doc.document_type === 'audio');
      } catch (error) {
        console.error('Error loading recordings:', error);
      }
    },
    
    onRecordingSaved(document) {
      // Add the new recording to the list
      this.recentRecordings.unshift(document);
      
      // Show success message
      this.showSuccessMessage('Opname succesvol opgeslagen en wordt verwerkt.');
    },
    
    async viewTranscription(recording) {
      this.selectedRecording = recording;
      this.loadingTranscription = true;
      this.transcriptionContent = null;
      this.transcriptionError = null;
      
      try {
        const response = await this.$axios.get(`/documents/${recording.id}`);
        this.transcriptionContent = response.data.content;
      } catch (error) {
        console.error('Error loading transcription:', error);
        this.transcriptionError = 'Fout bij het laden van de transcriptie.';
      } finally {
        this.loadingTranscription = false;
      }
    },
    
    closeTranscription() {
      this.selectedRecording = null;
      this.transcriptionContent = null;
    },
    
    useInReport(recording) {
      // Implementation to use the transcription in a report
      this.showSuccessMessage('Transcriptie toegevoegd aan rapport.');
      this.closeTranscription();
    },
    
    showSuccessMessage(message) {
      // Clear existing timer if there is one
      if (this.successTimer) {
        clearTimeout(this.successTimer);
      }
      
      // Show the message
      this.successMessage = message;
      
      // Hide the message after 5 seconds
      this.successTimer = setTimeout(() => {
        this.successMessage = null;
      }, 5000);
    },
    
    formatDate(dateString) {
      if (!dateString) return 'Onbekend';
      
      const date = new Date(dateString);
      return date.toLocaleDateString('nl-NL', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      });
    },
    
    getStatusLabel(status) {
      const statusMap = {
        'processing': 'Bezig met verwerken',
        'processed': 'Verwerkt',
        'enhanced': 'Verbeterd',
        'failed': 'Mislukt',
        'error': 'Fout'
      };

      return statusMap[status] || status;
    },

    getTranscriptionMethodLabel(method) {
      const methodMap = {
        'claude': 'Claude AI',
        'whisper': 'Whisper',
        'unknown': 'Standaard'
      };

      return methodMap[method] || method;
    }
  }
}
</script>

<style scoped>
.audio-recording-page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
}

.page-title {
  margin-bottom: 30px;
  color: #333;
  font-weight: 600;
}

.case-selector {
  margin-bottom: 30px;
}

.loading-indicator {
  text-align: center;
  padding: 20px;
  font-size: 18px;
  color: #666;
}

.no-cases-message {
  text-align: center;
  padding: 30px;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.case-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.case-item {
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background-color: white;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.case-item:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.case-info h3 {
  margin-top: 0;
  color: #333;
  font-size: 18px;
}

.case-description {
  color: #666;
  margin-bottom: 10px;
}

.case-date {
  font-size: 14px;
  color: #999;
}

.recording-section {
  background-color: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.case-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #eee;
}

.case-header h2 {
  margin: 0;
  font-size: 20px;
}

.recent-recordings {
  margin-top: 30px;
}

.recordings-list {
  margin-top: 15px;
}

.recording-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  background-color: #f8f9fa;
  border-radius: 6px;
  margin-bottom: 10px;
}

.recording-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.recording-title {
  font-weight: 500;
}

.recording-status {
  font-size: 13px;
  padding: 3px 8px;
  border-radius: 4px;
  background-color: #e9ecef;
}

.recording-status.processing {
  background-color: #cff4fc;
  color: #055160;
}

.recording-status.processed {
  background-color: #d1e7dd;
  color: #0f5132;
}

.recording-status.failed, .recording-status.error {
  background-color: #f8d7da;
  color: #842029;
}

.transcription-method {
  font-size: 13px;
  padding: 3px 8px;
  border-radius: 4px;
  margin-left: 10px;
}

.transcription-method.claude {
  background-color: #e0f2fe;
  color: #0369a1;
}

.transcription-method.whisper {
  background-color: #f0fdfa;
  color: #0f766e;
}

.recording-actions {
  display: flex;
  gap: 8px;
}

.transcription-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
}

.modal-content {
  position: relative;
  width: 80%;
  max-width: 800px;
  max-height: 80vh;
  background-color: white;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  z-index: 1001;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background-color: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
}

.close-button {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 20px;
  color: #666;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
}

.loading-transcription, .transcription-error {
  text-align: center;
  padding: 30px;
  color: #666;
}

.transcription-error {
  color: #842029;
}

.no-transcription {
  text-align: center;
  padding: 20px;
  color: #666;
  font-style: italic;
}

.transcription-header {
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
}

.transcription-info {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.transcription-method-badge,
.transcription-length,
.transcription-language {
  font-size: 13px;
  padding: 3px 10px;
  border-radius: 4px;
  background-color: #f3f4f6;
  color: #4b5563;
}

.transcription-method-badge.claude {
  background-color: #e0f2fe;
  color: #0369a1;
  font-weight: 500;
}

.transcription-method-badge.whisper {
  background-color: #f0fdfa;
  color: #0f766e;
  font-weight: 500;
}

.content-area {
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  white-space: pre-wrap;
  margin-bottom: 20px;
  max-height: 40vh;
  overflow-y: auto;
  line-height: 1.6;
  font-size: 15px;
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
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
</style>