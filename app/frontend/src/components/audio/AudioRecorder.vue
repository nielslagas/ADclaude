<template>
  <div class="audio-recorder">
    <div class="recorder-controls">
      <div class="status-indicator" :class="{ 'recording': isRecording }">
        <span v-if="isRecording">Opname: {{ formattedDuration }}</span>
        <span v-else>Klaar om op te nemen</span>
      </div>
      
      <div class="button-group">
        <button 
          class="btn" 
          :class="isRecording ? 'btn-danger' : 'btn-primary'" 
          @click="toggleRecording" 
          :disabled="isProcessing"
        >
          <i class="fas" :class="isRecording ? 'fa-stop' : 'fa-microphone'"></i>
          {{ isRecording ? 'Stop Opname' : 'Start Opname' }}
        </button>
        
        <button 
          v-if="audioUrl" 
          class="btn btn-secondary" 
          @click="playRecording" 
          :disabled="isPlaying || isRecording || isProcessing"
        >
          <i class="fas" :class="isPlaying ? 'fa-pause' : 'fa-play'"></i>
          {{ isPlaying ? 'Pauzeren' : 'Afspelen' }}
        </button>
        
        <button 
          v-if="audioUrl && !isRecording" 
          class="btn btn-success" 
          @click="saveRecording"
          :disabled="isProcessing"
        >
          <i class="fas" :class="isProcessing ? 'fa-spinner fa-spin' : 'fa-save'"></i>
          {{ isProcessing ? 'Bezig met verwerken...' : 'Opname Opslaan' }}
        </button>
      </div>
    </div>
    
    <div v-if="audioUrl && !isRecording" class="audio-preview">
      <div class="waveform" ref="waveformContainer"></div>
      
      <audio ref="audioPlayer" :src="audioUrl" controls class="audio-player" @ended="isPlaying = false"></audio>
    </div>
    
    <div v-if="audioUrl && !isRecording" class="recording-info">
      <div class="form-group">
        <label for="recordingTitle">Titel</label>
        <input 
          type="text" 
          id="recordingTitle" 
          v-model="recordingTitle" 
          class="form-control" 
          placeholder="Geef een titel aan de opname"
          :disabled="isProcessing"
        />
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
        ></textarea>
      </div>
    </div>
    
    <div v-if="errorMessage" class="alert alert-danger">
      {{ errorMessage }}
    </div>
  </div>
</template>

<script>
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
      waveform: null
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
        // Create form data for the API
        const formData = new FormData();
        formData.append('case_id', this.caseId);
        formData.append('title', this.recordingTitle);
        formData.append('description', this.recordingDescription || '');
        formData.append('audio_data', this.audioBlob, 'recording.webm');
        
        // Send to API
        const response = await this.$axios.post('/audio/record/', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        
        // Emit success event with document info
        this.$emit('recording-saved', response.data.document);
        
        // Reset the recorder
        this.resetRecorder();
        
      } catch (error) {
        console.error('Error saving recording:', error);
        this.errorMessage = error.response?.data?.detail || 'Fout bij het opslaan van de opname.';
      } finally {
        this.isProcessing = false;
      }
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