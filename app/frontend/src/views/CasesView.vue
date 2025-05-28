<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useCaseStore } from '@/stores/case';
import { useNotificationStore } from '@/stores/notification';
import type { Case, CaseCreate } from '@/types';

const caseStore = useCaseStore();
const router = useRouter();
const notificationStore = useNotificationStore();
const loading = ref(false);
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
    // Error handling is done by the store notification system
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
    notificationStore.warning('Validatiefout', 'Titel is verplicht');
    return;
  }

  loading.value = true;

  try {
    const createdCase = await caseStore.createCase(newCase.value);
    showCreateForm.value = false;
    newCase.value = { title: '', description: '' };
    
    // Navigate to the new case
    router.push(`/cases/${createdCase.id}`);
  } catch (err) {
    // Error handling is done by the store notification system
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

const getStatusLabel = (status: string): string => {
  const statusLabels: Record<string, string> = {
    'active': 'Actief',
    'completed': 'Voltooid',
    'archived': 'Gearchiveerd',
    'draft': 'Concept'
  };
  return statusLabels[status] || status;
};
</script>

<template>
  <div class="cases-container">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-text">
          <h1>Mijn Cases</h1>
          <p class="header-subtitle">Beheer uw arbeidsdeskundig onderzoek cases</p>
        </div>
        <div class="header-actions">
          <button 
            @click="toggleCreateForm" 
            class="btn btn-primary"
            :class="{ 'btn-outline': showCreateForm }"
            :disabled="loading"
          >
            <svg v-if="!showCreateForm" class="btn-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd"/>
            </svg>
            <svg v-else class="btn-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
            </svg>
            {{ showCreateForm ? 'Annuleren' : 'Nieuwe Case' }}
          </button>
        </div>
      </div>
    </div>


    <!-- Create Case Form -->
    <Transition name="slide-down">
      <div v-if="showCreateForm" class="create-form-container">
        <div class="card">
          <div class="card-header">
            <h2 class="card-title">Nieuwe Case Aanmaken</h2>
            <p class="card-subtitle">Voer de basisgegevens in voor uw nieuwe case</p>
          </div>
          <div class="card-body">
            <form @submit.prevent="createCase">
              <div class="form-group">
                <label for="title" class="form-label">Titel *</label>
                <input 
                  type="text" 
                  id="title" 
                  v-model="newCase.title" 
                  placeholder="Bijvoorbeeld: Onderzoek Jan Janssen"
                  required
                  class="form-input"
                  :disabled="loading"
                />
              </div>

              <div class="form-group">
                <label for="description" class="form-label">Beschrijving (optioneel)</label>
                <textarea 
                  id="description" 
                  v-model="newCase.description" 
                  placeholder="Korte beschrijving van de case..."
                  class="form-textarea"
                  rows="3"
                  :disabled="loading"
                ></textarea>
              </div>

              <div class="form-actions">
                <button type="submit" class="btn btn-primary" :disabled="loading">
                  <svg v-if="loading" class="btn-icon animate-spin" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M10 3a7 7 0 100 14 7 7 0 000-14zm0 2a5 5 0 110 10 5 5 0 010-10z" opacity="0.25"/>
                    <path d="M10 3a7 7 0 017 7h-2a5 5 0 00-5-5V3z"/>
                  </svg>
                  <svg v-else class="btn-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                  </svg>
                  {{ loading ? 'Bezig met aanmaken...' : 'Case Aanmaken' }}
                </button>
                <button type="button" class="btn btn-outline" @click="toggleCreateForm" :disabled="loading">
                  Annuleren
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Cases List -->
    <div class="cases-section">
      <!-- Loading Skeleton -->
      <div v-if="loading && !caseStore.cases.length" class="cases-grid">
        <div v-for="n in 3" :key="n" class="case-skeleton">
          <div class="skeleton skeleton-header"></div>
          <div class="skeleton skeleton-text"></div>
          <div class="skeleton skeleton-text short"></div>
          <div class="skeleton skeleton-footer"></div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else-if="!caseStore.cases.length" class="empty-state">
        <div class="empty-icon">
          <svg width="64" height="64" viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="8" y="16" width="48" height="32" rx="4"/>
            <path d="M8 20h48M16 12v8M48 12v8"/>
          </svg>
        </div>
        <h3>Nog geen cases</h3>
        <p>Begin met het aanmaken van uw eerste arbeidsdeskundige case.</p>
        <button @click="toggleCreateForm" class="btn btn-primary">
          <svg class="btn-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd"/>
          </svg>
          Eerste Case Aanmaken
        </button>
      </div>

      <!-- Cases Grid -->
      <div v-else class="cases-grid">
        <TransitionGroup name="fade" appear tag="div" class="cases-grid-inner">
          <div 
            v-for="caseItem in caseStore.cases" 
            :key="caseItem.id" 
            class="case-card"
            @click="viewCase(caseItem.id)"
            role="button"
            tabindex="0"
            @keydown.enter="viewCase(caseItem.id)"
            @keydown.space.prevent="viewCase(caseItem.id)"
          >
            <div class="case-header">
              <h3 class="case-title">{{ caseItem.title }}</h3>
              <span class="case-status" :class="`status-${caseItem.status}`">
                {{ getStatusLabel(caseItem.status) }}
              </span>
            </div>
            
            <div class="case-body">
              <p v-if="caseItem.description" class="case-description">
                {{ caseItem.description }}
              </p>
              <p v-else class="case-description empty">
                Geen beschrijving toegevoegd
              </p>
            </div>
            
            <div class="case-footer">
              <div class="case-meta">
                <svg class="meta-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path fill-rule="evenodd" d="M4 2a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2V4a2 2 0 00-2-2H4zm0 2h8v8H4V4z" clip-rule="evenodd"/>
                </svg>
                <span class="case-date">{{ formatDate(caseItem.created_at) }}</span>
              </div>
              <div class="case-arrow">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path fill-rule="evenodd" d="M6.22 3.22a.75.75 0 011.06 0l4.25 4.25a.75.75 0 010 1.06l-4.25 4.25a.75.75 0 11-1.06-1.06L9.94 8 6.22 4.28a.75.75 0 010-1.06z" clip-rule="evenodd"/>
                </svg>
              </div>
            </div>
          </div>
        </TransitionGroup>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Container */
.cases-container {
  max-width: 1280px;
  margin: 0 auto;
}

/* Page Header */
.page-header {
  margin-bottom: var(--spacing-2xl);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-lg);
}

.header-text h1 {
  margin: 0 0 var(--spacing-sm) 0;
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
}

.header-subtitle {
  margin: 0;
  font-size: var(--font-size-lg);
  color: var(--text-secondary);
}

.header-actions {
  flex-shrink: 0;
}

.btn-icon {
  margin-right: var(--spacing-sm);
}

/* Alerts */
.alert {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: var(--spacing-lg);
  border-radius: var(--radius);
  margin-bottom: var(--spacing-lg);
  border: 1px solid transparent;
}

.alert-danger {
  background-color: var(--error-light);
  border-color: var(--error-color);
  color: var(--error-color);
}

.alert-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.alert-icon {
  flex-shrink: 0;
}

.alert-close {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: var(--spacing-xs);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

/* Form Container */
.create-form-container {
  margin-bottom: var(--spacing-2xl);
}

.form-actions {
  display: flex;
  gap: var(--spacing-md);
  margin-top: var(--spacing-lg);
}

/* Cases Section */
.cases-section {
  margin-top: var(--spacing-2xl);
}

.cases-grid {
  width: 100%;
}

.cases-grid-inner {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--spacing-lg);
}

/* Loading Skeletons */
.case-skeleton {
  background-color: var(--bg-primary);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  border: 1px solid var(--border-color);
}

.skeleton {
  border-radius: var(--radius-sm);
  background-color: var(--gray-200);
  animation: skeleton 1.5s infinite;
}

.skeleton-header {
  height: 24px;
  margin-bottom: var(--spacing-md);
  width: 70%;
}

.skeleton-text {
  height: 16px;
  margin-bottom: var(--spacing-sm);
}

.skeleton-text.short {
  width: 60%;
}

.skeleton-footer {
  height: 14px;
  width: 40%;
  margin-top: var(--spacing-md);
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: var(--spacing-2xl);
  grid-column: 1 / -1;
}

.empty-icon {
  color: var(--gray-400);
  margin-bottom: var(--spacing-lg);
}

.empty-state h3 {
  margin: 0 0 var(--spacing-md) 0;
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.empty-state p {
  margin: 0 0 var(--spacing-lg) 0;
  color: var(--text-secondary);
  font-size: var(--font-size-lg);
}

/* Case Cards */
.case-card {
  background-color: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  cursor: pointer;
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
}

.case-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
  border-color: var(--border-hover);
}

.case-card:focus {
  outline: none;
  box-shadow: var(--shadow-lg), 0 0 0 2px var(--primary-color);
}

.case-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-md);
  gap: var(--spacing-md);
}

.case-title {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  line-height: var(--line-height-tight);
}

.case-status {
  flex-shrink: 0;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-active {
  background-color: var(--success-light);
  color: var(--success-color);
}

.status-completed {
  background-color: var(--primary-light);
  color: var(--primary-color);
}

.status-archived {
  background-color: var(--gray-100);
  color: var(--gray-600);
}

.status-draft {
  background-color: var(--warning-light);
  color: var(--warning-color);
}

.case-body {
  margin-bottom: var(--spacing-lg);
}

.case-description {
  margin: 0;
  font-size: var(--font-size-sm);
  line-height: var(--line-height-relaxed);
  color: var(--text-secondary);
}

.case-description.empty {
  color: var(--text-muted);
  font-style: italic;
}

.case-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--border-color);
}

.case-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.meta-icon {
  color: var(--text-muted);
}

.case-date {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
}

.case-arrow {
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

/* Animations */
@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes slide-down {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.animate-spin {
  animation: spin 1s linear infinite;
}

/* Transitions */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all var(--transition-normal);
}

.slide-down-enter-from {
  opacity: 0;
  transform: translateY(-20px);
}

.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Fade transitions for TransitionGroup */
.fade-enter-active,
.fade-leave-active {
  transition: all var(--transition-normal);
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-20px) scale(0.95);
}

.fade-move {
  transition: transform var(--transition-normal);
}

/* Responsive Design */
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-md);
  }
  
  .header-text {
    text-align: center;
  }
  
  .header-text h1 {
    font-size: var(--font-size-3xl);
  }
  
  .cases-grid-inner {
    grid-template-columns: 1fr;
    gap: var(--spacing-md);
  }
  
  .case-card {
    padding: var(--spacing-md);
  }
  
  .form-actions {
    flex-direction: column;
  }
}

@media (max-width: 480px) {
  .case-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-sm);
  }
  
  .case-status {
    align-self: flex-start;
  }
  
  .case-footer {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-sm);
  }
  
  .case-arrow {
    align-self: flex-end;
  }
}
</style>