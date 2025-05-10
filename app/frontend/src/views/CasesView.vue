<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useCaseStore } from '@/stores/case';
import type { Case, CaseCreate } from '@/types';

const caseStore = useCaseStore();
const router = useRouter();
const loading = ref(false);
const error = ref<string | null>(null);
const showCreateForm = ref(false);
const newCase = ref<CaseCreate>({
  title: '',
  description: ''
});

// Get all cases on component mount
onMounted(async () => {
  loading.value = true;
  try {
    await caseStore.fetchCases();
  } catch (err) {
    error.value = 'Er is een fout opgetreden bij het ophalen van cases.';
    console.error(err);
  } finally {
    loading.value = false;
  }
});

const viewCase = (caseId: string) => {
  router.push(`/cases/${caseId}`);
};

const toggleCreateForm = () => {
  showCreateForm.value = !showCreateForm.value;
  if (!showCreateForm.value) {
    // Reset form when hiding
    newCase.value = { title: '', description: '' };
  }
};

const createCase = async () => {
  if (!newCase.value.title.trim()) {
    error.value = 'Titel is verplicht';
    return;
  }

  loading.value = true;
  error.value = null;

  try {
    const createdCase = await caseStore.createCase(newCase.value);
    showCreateForm.value = false;
    newCase.value = { title: '', description: '' };
    
    // Navigate to the new case
    router.push(`/cases/${createdCase.id}`);
  } catch (err) {
    error.value = 'Er is een fout opgetreden bij het aanmaken van de case.';
    console.error(err);
  } finally {
    loading.value = false;
  }
};

const formatDate = (dateString: string) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('nl-NL', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
};
</script>

<template>
  <div class="cases-container">
    <div class="header">
      <h1>Mijn Cases</h1>
      <button 
        @click="toggleCreateForm" 
        class="btn btn-primary"
        :class="{ 'btn-secondary': showCreateForm }"
      >
        {{ showCreateForm ? 'Annuleren' : 'Nieuwe Case' }}
      </button>
    </div>

    <div v-if="error" class="alert alert-danger">
      {{ error }}
      <button @click="error = null" class="close-btn">&times;</button>
    </div>

    <!-- Create Case Form -->
    <div v-if="showCreateForm" class="create-form">
      <h2>Nieuwe Case Aanmaken</h2>
      <form @submit.prevent="createCase">
        <div class="form-group">
          <label for="title">Titel *</label>
          <input 
            type="text" 
            id="title" 
            v-model="newCase.title" 
            placeholder="Voer een titel in"
            required
            class="form-control"
          />
        </div>

        <div class="form-group">
          <label for="description">Beschrijving (optioneel)</label>
          <textarea 
            id="description" 
            v-model="newCase.description" 
            placeholder="Voer een beschrijving in"
            class="form-control"
            rows="3"
          ></textarea>
        </div>

        <div class="form-actions">
          <button type="submit" class="btn btn-primary" :disabled="loading">
            <span v-if="loading">Bezig met aanmaken...</span>
            <span v-else>Aanmaken</span>
          </button>
          <button type="button" class="btn btn-secondary" @click="toggleCreateForm">Annuleren</button>
        </div>
      </form>
    </div>

    <!-- Cases List -->
    <div class="cases-list">
      <div v-if="loading && !caseStore.cases.length" class="loading">
        <p>Cases worden geladen...</p>
      </div>

      <div v-else-if="!caseStore.cases.length" class="no-cases">
        <p>Je hebt nog geen cases aangemaakt.</p>
        <button @click="toggleCreateForm" class="btn btn-primary">Eerste Case Aanmaken</button>
      </div>

      <div v-else class="case-cards">
        <div 
          v-for="caseItem in caseStore.cases" 
          :key="caseItem.id" 
          class="case-card"
          @click="viewCase(caseItem.id)"
        >
          <div class="case-header">
            <h3>{{ caseItem.title }}</h3>
            <span class="case-status" :class="caseItem.status">{{ caseItem.status }}</span>
          </div>
          <p v-if="caseItem.description" class="case-description">{{ caseItem.description }}</p>
          <p v-else class="case-description empty">Geen beschrijving</p>
          <div class="case-footer">
            <span class="case-date">Aangemaakt: {{ formatDate(caseItem.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cases-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1rem;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.header h1 {
  margin: 0;
  color: var(--primary-color);
}

.alert {
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
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

.create-form {
  background-color: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  box-shadow: var(--shadow);
}

.create-form h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  font-size: 1.5rem;
  color: var(--primary-color);
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-control {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 1rem;
}

.form-control:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(var(--primary-color-rgb), 0.2);
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

.loading, .no-cases {
  text-align: center;
  padding: 3rem 1rem;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.no-cases p {
  margin-bottom: 1.5rem;
  color: var(--text-light);
}

.case-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.case-card {
  background-color: white;
  border-radius: 8px;
  box-shadow: var(--shadow);
  padding: 1.5rem;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.case-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

.case-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.case-header h3 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--primary-color);
}

.case-status {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: 999px;
  font-weight: 500;
}

.case-status.active {
  background-color: #dcfce7;
  color: #16a34a;
}

.case-status.archived {
  background-color: #f3f4f6;
  color: #6b7280;
}

.case-status.deleted {
  background-color: #fee2e2;
  color: #dc2626;
}

.case-description {
  color: var(--text-color);
  margin-bottom: 1.5rem;
  font-size: 0.9rem;
  line-height: 1.5;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.case-description.empty {
  color: var(--text-light);
  font-style: italic;
}

.case-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
  color: var(--text-light);
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: background-color 0.2s;
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

@media (max-width: 768px) {
  .header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }
  
  .case-cards {
    grid-template-columns: 1fr;
  }
  
  .form-actions {
    flex-direction: column;
  }
}
</style>