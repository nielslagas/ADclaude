<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useProfileStore, UserProfile } from '@/stores/profile';
import { useRouter } from 'vue-router';
import { getFullApiUrl } from '@/services/api';

const profileStore = useProfileStore();
const router = useRouter();

// Form state
const isEditing = ref(false);
const activeStep = ref(1);
const formData = ref<Partial<UserProfile>>({});
const logoFile = ref<File | null>(null);
const logoPreview = ref<string | null>(null);
const isSaving = ref(false);
const formError = ref<string | null>(null);
const successMessage = ref<string | null>(null);
const newSpecialization = ref('');

// Computed properties
const isProfileComplete = computed(() => profileStore.isProfileComplete);
const currentStepFields = computed(() => {
  if (!profileStore.completionStatus) return [];
  const step = profileStore.completionStatus.steps.find(s => s.step_number === activeStep.value);
  return step ? step.fields : [];
});

// Methods
const startEditing = () => {
  formData.value = { ...profileStore.profile };
  isEditing.value = true;
};

const cancelEditing = () => {
  formData.value = {};
  isEditing.value = false;
  logoFile.value = null;
  logoPreview.value = null;
};

const saveProfile = async () => {
  formError.value = null;
  successMessage.value = null;
  isSaving.value = true;

  try {
    // Save profile data
    await profileStore.updateProfile(formData.value);

    // Upload logo if selected
    if (logoFile.value) {
      await profileStore.uploadLogo(logoFile.value);
    }

    // Refresh completion status
    await profileStore.fetchCompletionStatus();

    // Success!
    successMessage.value = 'Profiel succesvol bijgewerkt!';
    isEditing.value = false;
    formData.value = {};
    logoFile.value = null;
    logoPreview.value = null;
  } catch (err: any) {
    // Set a more specific error message if available
    if (err.response && err.response.data && err.response.data.detail) {
      formError.value = `Fout bij opslaan: ${err.response.data.detail}`;
    } else if (err.message) {
      formError.value = `Fout bij opslaan: ${err.message}`;
    } else {
      formError.value = 'Er is een fout opgetreden bij het opslaan van het profiel.';
    }

    // Log detailed error information
    console.error('Error saving profile:', err);
    console.error('Error details:', {
      status: err.response?.status,
      statusText: err.response?.statusText,
      data: err.response?.data,
      message: err.message
    });
  } finally {
    isSaving.value = false;
  }
};

const handleLogoChange = (event: Event) => {
  const input = event.target as HTMLInputElement;
  if (input.files && input.files.length > 0) {
    const file = input.files[0];
    
    // Validate file size (max 2MB)
    if (file.size > 2 * 1024 * 1024) {
      formError.value = "Het logo is te groot. Maximale bestandsgrootte is 2MB.";
      // Reset the file input
      input.value = '';
      return;
    }
    
    // Validate file type
    const allowedTypes = ["image/jpeg", "image/png", "image/gif", "image/svg+xml"];
    if (!allowedTypes.includes(file.type)) {
      formError.value = "Ongeldig bestandsformaat. Ondersteunde formaten: JPG, PNG, GIF, SVG.";
      // Reset the file input
      input.value = '';
      return;
    }
    
    // Clear any previous errors
    formError.value = null;
    
    // Set the file and create preview
    logoFile.value = file;
    logoPreview.value = URL.createObjectURL(file);
  }
};

const deleteLogo = async () => {
  try {
    await profileStore.deleteLogo();
    logoPreview.value = null;
    logoFile.value = null;
  } catch (err) {
    console.error('Error deleting logo:', err);
  }
};

const goToStep = (step: number) => {
  activeStep.value = step;
};

const goToNextStep = () => {
  if (activeStep.value < 4) {
    activeStep.value++;
  }
};

const goToPreviousStep = () => {
  if (activeStep.value > 1) {
    activeStep.value--;
  }
};

const addSpecialization = () => {
  if (!newSpecialization.value.trim()) return;

  if (!formData.value.specializations) {
    formData.value.specializations = [];
  }

  formData.value.specializations.push(newSpecialization.value.trim());
  newSpecialization.value = '';
};

const removeSpecialization = (index: number) => {
  if (formData.value.specializations) {
    formData.value.specializations.splice(index, 1);
  }
};

// Initialize
onMounted(async () => {
  try {
    console.log("ProfileView mounted, initializing...");
    console.log("Store state:", profileStore.profile ? "has profile" : "no profile");
    
    // Always fetch fresh profile data
    try {
      console.log("Fetching profile...");
      await profileStore.fetchProfile();
      console.log("Profile fetched:", profileStore.profile);
    } catch (profileErr) {
      console.error("Error fetching profile:", profileErr);
      formError.value = "Kon profiel niet laden. Probeer het later opnieuw.";
    }
    
    // Try to fetch completion status, but continue if it fails
    try {
      console.log("Fetching completion status...");
      await profileStore.fetchCompletionStatus();
      console.log("Completion status fetched:", profileStore.completionStatus);
      
      // Start with the first incomplete step
      if (profileStore.completionStatus) {
        for (const step of profileStore.completionStatus.steps) {
          if (!step.completed) {
            activeStep.value = step.step_number;
            break;
          }
        }
      }
    } catch (statusErr) {
      console.error("Error fetching completion status:", statusErr);
      // Continue anyway
    }
  } catch (err) {
    console.error("Error in profile initialization:", err);
    formError.value = "Er is een fout opgetreden bij het laden van het profiel.";
  }
});
</script>

<template>
  <div class="profile-page">
    <div class="page-header">
      <h1>Mijn Profiel</h1>
      <div class="completion-indicator" v-if="profileStore.completionStatus">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: `${profileStore.completionPercentage}%` }"></div>
        </div>
        <div class="progress-text">
          {{ profileStore.completionPercentage }}% compleet
        </div>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="profileStore.loading" class="loading-container">
      <div class="spinner"></div>
      <p>Profiel laden...</p>
    </div>

    <!-- Error state -->
    <div v-else-if="profileStore.error" class="error-container">
      <p>Er is een fout opgetreden bij het laden van uw profiel.</p>
      <button class="btn btn-primary" @click="profileStore.fetchProfile">Opnieuw proberen</button>
    </div>

    <!-- Profile View Mode -->
    <div v-else-if="!isEditing && profileStore.profile" class="profile-container">
      <div class="profile-header">
        <div class="profile-avatar">
          <img v-if="profileStore.profile.logo_url" :src="getFullApiUrl(profileStore.profile.logo_url)" alt="Logo" class="profile-logo">
          <div v-else class="profile-logo-placeholder">
            <i class="fas fa-building"></i>
          </div>
        </div>

        <div class="profile-info">
          <h2>{{ profileStore.fullName || 'Geen naam ingesteld' }}</h2>
          <p v-if="profileStore.profile.job_title" class="profile-job-title">{{ profileStore.profile.job_title }}</p>
          <p v-if="profileStore.profile.company_name" class="profile-company">{{ profileStore.profile.company_name }}</p>
          
          <div class="profile-actions">
            <button class="btn btn-primary" @click="startEditing">
              <i class="fas fa-edit"></i> Profiel bewerken
            </button>
          </div>
        </div>
      </div>

      <!-- Profile details cards -->
      <div class="profile-sections">
        <!-- Personal information -->
        <div class="profile-section">
          <h3>Persoonlijke informatie</h3>
          <div class="profile-details">
            <div class="profile-detail" v-if="profileStore.profile.first_name || profileStore.profile.last_name">
              <span class="detail-label">Naam:</span>
              <span class="detail-value">{{ profileStore.profile.first_name }} {{ profileStore.profile.last_name }}</span>
            </div>
            <div class="profile-detail" v-if="profileStore.profile.job_title">
              <span class="detail-label">Functie:</span>
              <span class="detail-value">{{ profileStore.profile.job_title }}</span>
            </div>
            <div class="profile-detail" v-if="profileStore.profile.bio">
              <span class="detail-label">Biografie:</span>
              <span class="detail-value">{{ profileStore.profile.bio }}</span>
            </div>
          </div>
        </div>

        <!-- Company information -->
        <div class="profile-section">
          <h3>Bedrijfsinformatie</h3>
          <div class="profile-details">
            <div class="profile-detail" v-if="profileStore.profile.company_name">
              <span class="detail-label">Bedrijfsnaam:</span>
              <span class="detail-value">{{ profileStore.profile.company_name }}</span>
            </div>
            <div class="profile-detail" v-if="profileStore.profile.company_description">
              <span class="detail-label">Beschrijving:</span>
              <span class="detail-value">{{ profileStore.profile.company_description }}</span>
            </div>
            <div class="profile-detail" v-if="profileStore.profile.company_address">
              <span class="detail-label">Adres:</span>
              <span class="detail-value">
                {{ profileStore.profile.company_address }}<br>
                {{ profileStore.profile.company_postal_code }} {{ profileStore.profile.company_city }}<br>
                {{ profileStore.profile.company_country }}
              </span>
            </div>
            <div class="profile-detail" v-if="profileStore.profile.company_phone">
              <span class="detail-label">Telefoon:</span>
              <span class="detail-value">{{ profileStore.profile.company_phone }}</span>
            </div>
            <div class="profile-detail" v-if="profileStore.profile.company_email">
              <span class="detail-label">Email:</span>
              <span class="detail-value">{{ profileStore.profile.company_email }}</span>
            </div>
            <div class="profile-detail" v-if="profileStore.profile.company_website">
              <span class="detail-label">Website:</span>
              <span class="detail-value">
                <a :href="profileStore.profile.company_website" target="_blank">
                  {{ profileStore.profile.company_website }}
                </a>
              </span>
            </div>
          </div>
        </div>

        <!-- Professional information -->
        <div class="profile-section">
          <h3>Professionele informatie</h3>
          <div class="profile-details">
            <div class="profile-detail" v-if="profileStore.profile.certification">
              <span class="detail-label">Certificering:</span>
              <span class="detail-value">{{ profileStore.profile.certification }}</span>
            </div>
            <div class="profile-detail" v-if="profileStore.profile.registration_number">
              <span class="detail-label">Registratienummer:</span>
              <span class="detail-value">{{ profileStore.profile.registration_number }}</span>
            </div>
            <div class="profile-detail" v-if="profileStore.profile.specializations && profileStore.profile.specializations.length > 0">
              <span class="detail-label">Specialisaties:</span>
              <span class="detail-value">
                <ul class="specializations-list">
                  <li v-for="spec in profileStore.profile.specializations" :key="spec">{{ spec }}</li>
                </ul>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Profile completion notice -->
      <div v-if="!isProfileComplete" class="profile-completion-notice">
        <div class="notice-icon">
          <i class="fas fa-info-circle"></i>
        </div>
        <div class="notice-content">
          <h4>Maak uw profiel compleet</h4>
          <p>Uw profielinformatie zal worden gebruikt in het genereren van rapporten. 
             Een volledig profiel zorgt voor professionele rapportages met uw bedrijfsgegevens.</p>
          <button class="btn btn-secondary" @click="startEditing">Profiel voltooien</button>
        </div>
      </div>
    </div>

    <!-- Profile Edit Mode -->
    <div v-else-if="isEditing" class="profile-edit-container">
      <!-- Form messages -->
      <div v-if="formError" class="alert alert-danger">
        {{ formError }}
      </div>
      <div v-if="successMessage" class="alert alert-success">
        {{ successMessage }}
      </div>

      <!-- Wizard steps -->
      <div class="wizard-steps">
        <div class="step" 
             v-for="step in profileStore.completionStatus?.steps" 
             :key="step.step_number"
             :class="{ 'active': activeStep === step.step_number, 'completed': step.completed }"
             @click="goToStep(step.step_number)">
          <div class="step-number">{{ step.step_number }}</div>
          <div class="step-title">{{ step.title }}</div>
        </div>
      </div>

      <!-- Step 1: Personal Information -->
      <div v-if="activeStep === 1" class="form-step">
        <h3>Persoonlijke informatie</h3>
        <div class="form-row">
          <div class="form-group">
            <label for="first_name">Voornaam</label>
            <input type="text" id="first_name" v-model="formData.first_name" class="form-control">
          </div>
          <div class="form-group">
            <label for="last_name">Achternaam</label>
            <input type="text" id="last_name" v-model="formData.last_name" class="form-control">
          </div>
        </div>
        <div class="form-group">
          <label for="display_name">Weergavenaam (optioneel)</label>
          <input type="text" id="display_name" v-model="formData.display_name" class="form-control">
          <small class="form-text text-muted">Laat leeg om automatisch te genereren uit voor- en achternaam</small>
        </div>
        <div class="form-group">
          <label for="job_title">Functietitel</label>
          <input type="text" id="job_title" v-model="formData.job_title" class="form-control">
        </div>
        <div class="form-group">
          <label for="bio">Biografie (optioneel)</label>
          <textarea id="bio" v-model="formData.bio" class="form-control" rows="4"></textarea>
          <small class="form-text text-muted">Een korte introductie over uzelf als arbeidsdeskundige</small>
        </div>
      </div>

      <!-- Step 2: Company Information -->
      <div v-if="activeStep === 2" class="form-step">
        <h3>Bedrijfsgegevens</h3>
        <div class="form-group">
          <label for="company_name">Bedrijfsnaam</label>
          <input type="text" id="company_name" v-model="formData.company_name" class="form-control">
        </div>
        <div class="form-group">
          <label for="company_description">Bedrijfsbeschrijving (optioneel)</label>
          <textarea id="company_description" v-model="formData.company_description" class="form-control" rows="3"></textarea>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label for="company_address">Adres</label>
            <input type="text" id="company_address" v-model="formData.company_address" class="form-control">
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label for="company_postal_code">Postcode</label>
            <input type="text" id="company_postal_code" v-model="formData.company_postal_code" class="form-control">
          </div>
          <div class="form-group">
            <label for="company_city">Plaats</label>
            <input type="text" id="company_city" v-model="formData.company_city" class="form-control">
          </div>
        </div>
        <div class="form-group">
          <label for="company_country">Land</label>
          <input type="text" id="company_country" v-model="formData.company_country" class="form-control">
        </div>
        <div class="form-row">
          <div class="form-group">
            <label for="company_email">E-mail</label>
            <input type="email" id="company_email" v-model="formData.company_email" class="form-control">
          </div>
          <div class="form-group">
            <label for="company_phone">Telefoon</label>
            <input type="tel" id="company_phone" v-model="formData.company_phone" class="form-control">
          </div>
        </div>
        <div class="form-group">
          <label for="company_website">Website (optioneel)</label>
          <input type="url" id="company_website" v-model="formData.company_website" class="form-control">
        </div>
      </div>

      <!-- Step 3: Professional Information -->
      <div v-if="activeStep === 3" class="form-step">
        <h3>Professionele informatie</h3>
        <div class="form-group">
          <label for="certification">Certificering</label>
          <input type="text" id="certification" v-model="formData.certification" class="form-control">
          <small class="form-text text-muted">Bijv. Register Arbeidsdeskundige, SRA, etc.</small>
        </div>
        <div class="form-group">
          <label for="registration_number">Registratienummer</label>
          <input type="text" id="registration_number" v-model="formData.registration_number" class="form-control">
        </div>
        <div class="form-group">
          <label>Specialisaties</label>
          <div class="specializations-editor">
            <input type="text" v-model="newSpecialization" class="form-control" placeholder="Voeg een specialisatie toe">
            <button type="button" class="btn btn-primary btn-sm" @click="addSpecialization">
              <i class="fas fa-plus"></i>
            </button>
          </div>
          <div v-if="formData.specializations && formData.specializations.length > 0" class="specializations-list">
            <div v-for="(spec, index) in formData.specializations" :key="index" class="specialization-item">
              <span>{{ spec }}</span>
              <button type="button" class="btn btn-danger btn-sm" @click="removeSpecialization(index)">
                <i class="fas fa-times"></i>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 4: Logo Upload -->
      <div v-if="activeStep === 4" class="form-step">
        <h3>Logo en afbeeldingen</h3>
        <div class="logo-upload-container">
          <div class="logo-preview">
            <img v-if="logoPreview" :src="logoPreview" alt="Logo preview" class="preview-image">
            <img v-else-if="profileStore.profile?.logo_url" :src="getFullApiUrl(profileStore.profile.logo_url)" alt="Current logo" class="preview-image">
            <div v-else class="preview-placeholder">
              <i class="fas fa-building"></i>
              <p>Geen logo</p>
            </div>
          </div>
          <div class="logo-actions">
            <label class="btn btn-primary">
              <i class="fas fa-upload"></i> Logo uploaden
              <input 
                type="file" 
                accept="image/*" 
                @change="handleLogoChange" 
                style="display: none"
              >
            </label>
            <button 
              v-if="logoPreview || profileStore.profile?.logo_url" 
              class="btn btn-danger" 
              @click="deleteLogo"
            >
              <i class="fas fa-trash"></i> Logo verwijderen
            </button>
          </div>
          <div class="logo-info">
            <p>Upload een bedrijfslogo dat in uw rapporten zal worden gebruikt. Aanbevolen formaat is 200x200 pixels.</p>
            <p>Ondersteunde formaten: JPG, PNG, GIF, SVG</p>
          </div>
        </div>
      </div>

      <!-- Form actions -->
      <div class="form-actions">
        <button type="button" class="btn btn-secondary" @click="cancelEditing">Annuleren</button>
        <div class="step-navigation">
          <button 
            type="button" 
            class="btn btn-outline-primary" 
            @click="goToPreviousStep"
            :disabled="activeStep === 1"
          >
            <i class="fas fa-arrow-left"></i> Vorige
          </button>
          <button 
            v-if="activeStep < 4"
            type="button" 
            class="btn btn-outline-primary" 
            @click="goToNextStep"
          >
            Volgende <i class="fas fa-arrow-right"></i>
          </button>
          <button 
            v-else
            type="button" 
            class="btn btn-primary" 
            @click="saveProfile"
            :disabled="isSaving"
          >
            <i v-if="isSaving" class="fas fa-spinner fa-spin"></i>
            <i v-else class="fas fa-save"></i> 
            Profiel opslaan
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-page {
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.page-header h1 {
  margin: 0;
  color: var(--primary-color);
}

.completion-indicator {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.progress-bar {
  width: 200px;
  height: 8px;
  background-color: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: var(--primary-color);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.8rem;
  margin-top: 0.25rem;
  color: var(--text-light);
}

/* Loading and error states */
.loading-container, .error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  border-top-color: var(--primary-color);
  animation: spin 1s ease-in-out infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Profile view */
.profile-container {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: var(--shadow);
  overflow: hidden;
}

.profile-header {
  display: flex;
  padding: 2rem;
  background-color: #f8f9fa;
  border-bottom: 1px solid #e0e0e0;
}

.profile-avatar {
  width: 200px;
  height: 200px;
  margin-right: 2rem;
  flex-shrink: 0;
  display: flex;
  justify-content: center;
  align-items: center;
}

.profile-logo {
  width: 100%;
  height: 100%;
  object-fit: cover; /* Changed from contain to cover */
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  background-color: white;
  display: block; /* Ensure it's displayed as a block */
}

.profile-logo-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f1f1f1;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  color: #999;
  font-size: 3rem;
}

.profile-info {
  flex-grow: 1;
}

.profile-info h2 {
  margin-top: 0;
  margin-bottom: 0.5rem;
  color: var(--primary-color);
}

.profile-job-title {
  font-size: 1.1rem;
  color: var(--text-color);
  margin-bottom: 0.25rem;
}

.profile-company {
  font-size: 1rem;
  color: var(--text-light);
  margin-bottom: 1rem;
}

.profile-actions {
  margin-top: 1rem;
}

/* Profile sections */
.profile-sections {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
  padding: 1.5rem;
}

.profile-section {
  background-color: #fff;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  overflow: hidden;
}

.profile-section h3 {
  margin: 0;
  padding: 1rem;
  background-color: #f8f9fa;
  border-bottom: 1px solid #e0e0e0;
  font-size: 1.1rem;
  color: var(--primary-color);
}

.profile-details {
  padding: 1rem;
}

.profile-detail {
  margin-bottom: 1rem;
}

.profile-detail:last-child {
  margin-bottom: 0;
}

.detail-label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.25rem;
  color: var(--text-color);
}

.detail-value {
  color: var(--text-dark);
}

.specializations-list {
  list-style-type: none;
  padding-left: 0;
  margin: 0;
}

.specializations-list li {
  margin-bottom: 0.25rem;
}

/* Profile completion notice */
.profile-completion-notice {
  margin-top: 2rem;
  display: flex;
  align-items: flex-start;
  background-color: #e8f4fd;
  border-radius: 8px;
  padding: 1.5rem;
  border-left: 4px solid #2196f3;
}

.notice-icon {
  font-size: 1.5rem;
  color: #2196f3;
  margin-right: 1rem;
}

.notice-content h4 {
  margin-top: 0;
  margin-bottom: 0.5rem;
  color: #0d47a1;
}

.notice-content p {
  margin-bottom: 1rem;
  color: #546e7a;
}

/* Edit form */
.profile-edit-container {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: var(--shadow);
  padding: 2rem;
}

.wizard-steps {
  display: flex;
  margin-bottom: 2rem;
  border-bottom: 1px solid #e0e0e0;
  padding-bottom: 1rem;
}

.step {
  display: flex;
  align-items: center;
  margin-right: 1.5rem;
  cursor: pointer;
  opacity: 0.6;
  transition: opacity 0.2s ease;
}

.step:hover {
  opacity: 0.8;
}

.step.active {
  opacity: 1;
}

.step.completed {
  opacity: 0.8;
}

.step-number {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background-color: #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 0.5rem;
  font-weight: 600;
}

.step.active .step-number {
  background-color: var(--primary-color);
  color: white;
}

.step.completed .step-number {
  background-color: #4caf50;
  color: white;
}

.form-step {
  margin-bottom: 2rem;
}

.form-step h3 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: var(--primary-color);
}

.form-row {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.form-row .form-group {
  flex: 1;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.form-control {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 1rem;
}

.form-text {
  font-size: 0.8rem;
  margin-top: 0.25rem;
}

/* Logo upload */
.logo-upload-container {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.logo-preview {
  width: 200px;
  height: 200px;
  border: 2px dashed #ccc;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1rem;
  background-color: #f8f9fa;
  overflow: hidden;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover; /* Fill the container while maintaining aspect ratio */
  object-position: center; /* Center the image */
  display: block; /* Ensure it's displayed as a block */
}

.preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #999;
}

.preview-placeholder i {
  font-size: 3rem;
  margin-bottom: 0.5rem;
}

.logo-actions {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.logo-info {
  text-align: center;
  color: var(--text-light);
  font-size: 0.9rem;
  max-width: 400px;
}

/* Form actions */
.form-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e0e0e0;
}

.step-navigation {
  display: flex;
  gap: 1rem;
}

/* Specializations editor */
.specializations-editor {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.specializations-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.specialization-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background-color: #e8f4fd;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

.alert {
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1.5rem;
}

.alert-danger {
  background-color: #ffebee;
  color: #c62828;
  border: 1px solid #ffcdd2;
}

.alert-success {
  background-color: #e8f5e9;
  color: #2e7d32;
  border: 1px solid #c8e6c9;
}

/* Mobile responsiveness */
@media (max-width: 768px) {
  .profile-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
  
  .profile-avatar {
    margin-right: 0;
    margin-bottom: 1.5rem;
  }
  
  .profile-sections {
    grid-template-columns: 1fr;
  }
  
  .form-row {
    flex-direction: column;
    gap: 0;
  }
  
  .wizard-steps {
    overflow-x: auto;
    padding-bottom: 1.5rem;
  }
  
  .step {
    flex-shrink: 0;
  }
  
  .form-actions {
    flex-direction: column;
    gap: 1rem;
  }
  
  .step-navigation {
    width: 100%;
    justify-content: space-between;
  }
}
</style>