<template>
  <div class="audio-recorder" role="region" aria-label="Audio opname functionaliteit">
    <div class="recorder-controls">
      <div 
        class="status-indicator" 
        :class="{ 'recording': isRecording }"
        role="status"
        aria-live="polite"
        :aria-label="isRecording ? `Bezig met opnemen: ${formattedDuration}` : 'Gereed voor opname'"
      >
        <span v-if="isRecording">Opname: {{ formattedDuration }}</span>
        <span v-else>Klaar om op te nemen</span>
      </div>
      
      <div class="button-group" role="group" aria-label="Opname bedieningsknoppen">
        <button 
          class="btn" 
          :class="isRecording ? 'btn-danger' : 'btn-primary'" 
          @click="toggleRecording" 
          :disabled="isProcessing"
          :aria-label="isRecording ? 'Stop audio opname' : 'Start audio opname'"
          :aria-pressed="isRecording"
        >
          <i class="fas" :class="isRecording ? 'fa-stop' : 'fa-microphone'" aria-hidden="true"></i>
          {{ isRecording ? 'Stop Opname' : 'Start Opname' }}
        </button>
        
        <button 
          v-if="audioUrl" 
          class="btn btn-secondary" 
          @click="playRecording" 
          :disabled="isPlaying || isRecording || isProcessing"
          :aria-label="isPlaying ? 'Pauzeer audio afspelen' : 'Speel audio opname af'"
          :aria-pressed="isPlaying"
        >
          <i class="fas" :class="isPlaying ? 'fa-pause' : 'fa-play'" aria-hidden="true"></i>
          {{ isPlaying ? 'Pauzeren' : 'Afspelen' }}
        </button>
        
        <button 
          v-if="audioUrl && !isRecording" 
          class="btn btn-success" 
          @click="saveRecording"
          :disabled="isProcessing"
          :aria-label="isProcessing ? 'Bezig met opslaan van opname' : 'Sla audio opname op'"
        >
          <i class="fas" :class="isProcessing ? 'fa-spinner fa-spin' : 'fa-save'" aria-hidden="true"></i>
          {{ isProcessing ? 'Bezig met verwerken...' : 'Opname Opslaan' }}
        </button>
      </div>
    </div>
    
    <div v-if="audioUrl && !isRecording" class="audio-preview" role="region" aria-label="Audio voorvertoning">
      <div 
        class="waveform" 
        ref="waveformContainer"
        aria-label="Audio golfvorm visualisatie"
        role="img"
      ></div>
      
      <audio 
        ref="audioPlayer" 
        :src="audioUrl" 
        controls 
        class="audio-player" 
        @ended="isPlaying = false"
        aria-label="Audio opname afspelen"
      ></audio>
    </div>
    
    <div v-if="audioUrl && !isRecording" class="recording-info" role="region" aria-label="Opname informatie">
      <div class="form-group">
        <label for="recordingTitle">Titel</label>
        <input 
          type="text" 
          id="recordingTitle" 
          v-model="recordingTitle" 
          class="form-control" 
          placeholder="Geef een titel aan de opname"
          :disabled="isProcessing"
          required
          aria-describedby="recordingTitle-help"
        />
        <div id="recordingTitle-help" class="form-help">
          Geef uw opname een duidelijke titel voor eenvoudige herkenning
        </div>
      </div>
      
      <div class="form-group">
        <label for="recordingDescription">Omschrijving (optioneel)</label>
        <textarea 
          id="recordingDescription" 
          v-model="recordingDescription" 
          class="form-control" 
          rows="3" 
          placeholder="Omschrijf kort wat er in deze opname wordt besproken"
          :disabled="isProcessing"
          aria-describedby="recordingDescription-help"
        ></textarea>
        <div id="recordingDescription-help" class="form-help">
          Optionele beschrijving om context te geven aan uw opname
        </div>
      </div>
    </div>
    
    <div 
      v-if="errorMessage" 
      class="alert alert-danger"
      role="alert"
      aria-live="assertive"
    >
      <span class="sr-only">Fout:</span>
      {{ errorMessage }}
    </div>
  </div>
</template>

<script>
import { apiClient } from '@/services/api';

export default {
  name: 'AudioRecorder',
  props: {
    caseId: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      mediaRecorder: null,
      audioChunks: [],
      audioUrl: null,
      isRecording: false,
      isPlaying: false,
      isProcessing: false,
      recordingTitle: '',
      recordingDescription: '',
      recordingDuration: 0,
      recordingTimer: null,
      audioBlob: null,
      errorMessage: '',
      audioContext: null,
      audioAnalyser: null,
      audioSource: null,
      waveform: null,
      api: apiClient // Store the API client as a component property
    }
  },
  computed: {
    formattedDuration() {
      const minutes = Math.floor(this.recordingDuration / 60);
      const seconds = this.recordingDuration % 60;
      return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
  },
  methods: {
    async toggleRecording() {
      if (this.isRecording) {
        this.stopRecording();
      } else {
        await this.startRecording();
      }
    },
    async startRecording() {
      try {
        this.errorMessage = '';
        this.audioChunks = [];
        this.audioUrl = null;
        
        // Request microphone access
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // Set up audio context for visualization
        this.setupAudioContext(stream);
        
        // Set up media recorder
        this.mediaRecorder = new MediaRecorder(stream);
        
        this.mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            this.audioChunks.push(event.data);
          }
        };
        
        this.mediaRecorder.onstop = () => {
          this.audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
          this.audioUrl = URL.createObjectURL(this.audioBlob);
          this.isRecording = false;
          
          // Stop the recording timer
          clearInterval(this.recordingTimer);
          
          // Generate default title if empty
          if (!this.recordingTitle) {
            const now = new Date();
            this.recordingTitle = `Opname ${now.toLocaleDateString()} ${now.toLocaleTimeString()}`;
          }
          
          // Set up waveform visualizer
          this.$nextTick(() => {
            this.setupWaveform();
          });
        };
        
        // Start recording
        this.mediaRecorder.start();
        this.isRecording = true;
        this.recordingDuration = 0;
        
        // Start recording timer
        this.recordingTimer = setInterval(() => {
          this.recordingDuration++;
        }, 1000);
        
      } catch (error) {
        console.error('Error starting recording:', error);
        this.errorMessage = 'Toegang tot microfoon was niet mogelijk. Controleer de browser instellingen.';
      }
    },
    stopRecording() {
      if (this.mediaRecorder && this.isRecording) {
        this.mediaRecorder.stop();
        this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
      }
    },
    playRecording() {
      const audioPlayer = this.$refs.audioPlayer;
      
      if (audioPlayer) {
        if (this.isPlaying) {
          audioPlayer.pause();
        } else {
          audioPlayer.play();
        }
        
        this.isPlaying = !this.isPlaying;
      }
    },
    async saveRecording() {
      // Validate input
      if (!this.recordingTitle.trim()) {
        this.errorMessage = 'Geef uw opname een titel';
        return;
      }

      // Set processing state
      this.isProcessing = true;
      this.errorMessage = '';

      try {
        console.log("Starting saveRecording process");

        // Log debug information
        console.log("Audio blob type:", this.audioBlob.type);
        console.log("Audio blob size:", this.audioBlob.size);
        console.log("Case ID:", this.caseId);
        console.log("Title:", this.recordingTitle);

        // Create a FormData object to send the audio file and metadata
        const formData = new FormData();
        formData.append('case_id', this.caseId);
        formData.append('title', this.recordingTitle);

        if (this.recordingDescription) {
          formData.append('description', this.recordingDescription);
        }

        // Create a file from the blob with appropriate name
        const audioFileName = `recording_${Date.now()}.${this.getFileExtension(this.audioBlob.type)}`;
        const audioFile = new File([this.audioBlob], audioFileName, { type: this.audioBlob.type });

        // Add the file to the form data
        formData.append('audio_file', audioFile);

        console.log("Sending audio to server for processing...");

        // Send the audio to the server
        const response = await this.api.post('/audio/upload/', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });

        console.log("Server response:", response.data);

        if (response.data && response.data.status === 'success') {
          console.log("Audio uploaded successfully. Document ID:", response.data.document.id);

          // Create a temporary document object while waiting for the server to process
          const document = {
            id: response.data.document.id,
            title: this.recordingTitle,
            description: this.recordingDescription || '',
            document_type: 'audio',
            status: 'processing',
            case_id: this.caseId,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            content: "Transcriptie wordt verwerkt...",
            file_path: URL.createObjectURL(this.audioBlob) // Local URL for playback until server processes
          };

          // Also save a copy to localStorage for immediate playback
          this.saveRecordingToLocalStorage(document);

          // Emit success event with the document
          this.$emit('recording-saved', document);

          // Reset the recorder
          this.resetRecorder();
        } else {
          throw new Error('Server returned an error: ' + JSON.stringify(response.data));
        }
      } catch (error) {
        console.error('Error saving recording:', error);
        this.errorMessage = 'Fout bij het opslaan van de opname: ' + (error.response?.data?.message || error.message);
      } finally {
        this.isProcessing = false;
      }
    },

    // Helper method to get file extension from MIME type
    getFileExtension(mimeType) {
      const extensions = {
        'audio/webm': 'webm',
        'audio/mp3': 'mp3',
        'audio/mp4': 'mp4',
        'audio/wav': 'wav',
        'audio/ogg': 'ogg',
        'audio/mpeg': 'mp3'
      };

      return extensions[mimeType] || 'webm'; // Default to webm if unknown
    },

    // Helper method to save recording to localStorage
    saveRecordingToLocalStorage(document) {
      // Get existing recordings or initialize empty array
      const existingRecordings = JSON.parse(localStorage.getItem('audioRecordings') || '[]');

      // Add new recording
      existingRecordings.push({
        ...document,
        audioBlob: this.audioUrl // Store the data URL
      });

      // Save back to localStorage
      localStorage.setItem('audioRecordings', JSON.stringify(existingRecordings));
      console.log("Saved recording to localStorage");
    },
    resetRecorder() {
      this.audioChunks = [];
      this.audioUrl = null;
      this.recordingTitle = '';
      this.recordingDescription = '';
      this.recordingDuration = 0;
      this.audioBlob = null;
      this.errorMessage = '';
      
      if (this.audioAnalyser) {
        this.audioAnalyser.disconnect();
        this.audioAnalyser = null;
      }
      
      if (this.audioSource) {
        this.audioSource.disconnect();
        this.audioSource = null;
      }
      
      if (this.audioContext && this.audioContext.state !== 'closed') {
        this.audioContext.close();
        this.audioContext = null;
      }
    },
    setupAudioContext(stream) {
      // Create audio context for visualization
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      this.audioAnalyser = this.audioContext.createAnalyser();
      this.audioSource = this.audioContext.createMediaStreamSource(stream);
      this.audioSource.connect(this.audioAnalyser);
    },
    setupWaveform() {
      // Load audio file for waveform visualization
      if (!this.audioUrl || !this.$refs.waveformContainer) return;
      
      // Implementation will depend on if you want to use a library like wavesurfer.js
      // or implement a simple canvas-based visualization
      console.log('Setting up waveform visualization');
      
      // Basic implementation might be:
      // 1. Create an audio element
      // 2. Load the blob URL
      // 3. Draw waveform using canvas and AudioContext.createAnalyser()
    }
  },
  beforeUnmount() {
    // Clean up resources
    if (this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop();
      this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
    
    if (this.audioUrl) {
      URL.revokeObjectURL(this.audioUrl);
    }
    
    clearInterval(this.recordingTimer);
    
    if (this.audioAnalyser) {
      this.audioAnalyser.disconnect();
    }
    
    if (this.audioSource) {
      this.audioSource.disconnect();
    }
    
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
    }
  }
}
</script>

<style scoped>
.audio-recorder {
  margin: 20px 0;
  padding: 20px;
  border-radius: 8px;
  background-color: #f8f9fa;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.recorder-controls {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 20px;
}

.status-indicator {
  font-weight: bold;
  padding: 10px;
  text-align: center;
  border-radius: 4px;
  background-color: #e9ecef;
}

.status-indicator.recording {
  background-color: #dc3545;
  color: white;
  animation: pulse 1.5s infinite;
}

.button-group {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.audio-preview {
  margin: 20px 0;
}

.waveform {
  height: 120px;
  background-color: #e9ecef;
  border-radius: 4px;
  margin-bottom: 10px;
}

.audio-player {
  width: 100%;
}

.recording-info {
  margin-top: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-control {
  width: 100%;
  padding: 8px;
  border: 1px solid #ced4da;
  border-radius: 4px;
}

.alert {
  margin-top: 20px;
  padding: 10px;
  border-radius: 4px;
}

.alert-danger {
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
}

@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
  100% {
    opacity: 1;
  }
}
</style>