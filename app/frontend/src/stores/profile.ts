import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import api from '@/services/api';

interface ProfileLogo {
  id: string;
  profile_id: string;
  file_name: string;
  storage_path: string;
  mime_type: string;
  size: number;
  created_at: string;
  updated_at: string;
}

export interface UserProfile {
  id: string;
  user_id: string;
  first_name: string | null;
  last_name: string | null;
  display_name: string | null;
  job_title: string | null;
  company_name: string | null;
  company_description: string | null;
  company_address: string | null;
  company_postal_code: string | null;
  company_city: string | null;
  company_country: string | null;
  company_phone: string | null;
  company_email: string | null;
  company_website: string | null;
  certification: string | null;
  registration_number: string | null;
  specializations: string[] | null;
  bio: string | null;
  created_at: string;
  updated_at: string;
  logo: ProfileLogo | null;
  logo_url: string | null;
}

interface ProfileWizardStep {
  step_number: number;
  title: string;
  completed: boolean;
  fields: string[];
}

interface ProfileCompletionStatus {
  progress_percentage: number;
  steps_completed: number;
  total_steps: number;
  steps: ProfileWizardStep[];
  required_fields_missing: string[];
}

export const useProfileStore = defineStore('profile', () => {
  // State
  const profile = ref<UserProfile | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const completionStatus = ref<ProfileCompletionStatus | null>(null);

  // Getters
  const hasProfile = computed(() => !!profile.value);
  const fullName = computed(() => {
    if (!profile.value) return null;
    if (profile.value.display_name) return profile.value.display_name;
    if (profile.value.first_name && profile.value.last_name) {
      return `${profile.value.first_name} ${profile.value.last_name}`;
    }
    return null;
  });
  const completionPercentage = computed(() => completionStatus.value?.progress_percentage || 0);
  const isProfileComplete = computed(() => completionPercentage.value === 100);

  // Actions
  const fetchProfile = async () => {
    loading.value = true;
    error.value = null;

    try {
      const { data } = await api.get('/profiles/me');
      profile.value = data;
      return data;
    } catch (err: any) {
      console.error('Error fetching profile:', err);
      error.value = err.message || 'Failed to fetch profile';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const updateProfile = async (profileData: Partial<UserProfile>) => {
    loading.value = true;
    error.value = null;

    try {
      const { data } = await api.put('/profiles/me', profileData);
      profile.value = data;
      return data;
    } catch (err: any) {
      console.error('Error updating profile:', err);
      error.value = err.message || 'Failed to update profile';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const uploadLogo = async (file: File) => {
    loading.value = true;
    error.value = null;

    try {
      const formData = new FormData();
      formData.append('file', file);

      const { data } = await api.post('/profiles/me/logo', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      // Refresh profile to get updated logo
      await fetchProfile();
      return data;
    } catch (err: any) {
      console.error('Error uploading logo:', err);
      error.value = err.message || 'Failed to upload logo';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const deleteLogo = async () => {
    loading.value = true;
    error.value = null;

    try {
      await api.delete('/profiles/me/logo');
      // Refresh profile to reflect logo deletion
      await fetchProfile();
    } catch (err: any) {
      console.error('Error deleting logo:', err);
      error.value = err.message || 'Failed to delete logo';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const fetchCompletionStatus = async () => {
    loading.value = true;
    error.value = null;

    try {
      const { data } = await api.get('/profiles/me/completion');
      completionStatus.value = data;
      return data;
    } catch (err: any) {
      console.error('Error fetching completion status:', err);
      error.value = err.message || 'Failed to fetch completion status';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  // Initialize store by fetching profile
  const initialize = async () => {
    try {
      await fetchProfile();
      await fetchCompletionStatus();
    } catch (err) {
      console.error('Error initializing profile store:', err);
    }
  };

  // Return store
  return {
    // State
    profile,
    loading,
    error,
    completionStatus,

    // Getters
    hasProfile,
    fullName,
    completionPercentage,
    isProfileComplete,

    // Actions
    fetchProfile,
    updateProfile,
    uploadLogo,
    deleteLogo,
    fetchCompletionStatus,
    initialize
  };
});