<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const goToLogin = () => {
  window.location.href = '/login'
}

const goToCases = () => {
  router.push('/cases') // Now redirects to the Cases view
}
</script>

<template>
  <div class="home">
    <div class="hero">
      <h1>AD-Rapport Generator</h1>
      <p class="subtitle">Ondersteund door AI voor efficiënte en consistente arbeidsdeskundige rapportages</p>
      
      <div class="cta-buttons">
        <button v-if="!authStore.isLoggedIn" @click="goToLogin" class="btn btn-primary btn-lg">Inloggen</button>
        <button v-else @click="goToCases" class="btn btn-primary btn-lg">Mijn Cases</button>
      </div>
    </div>

    <div class="features">
      <div class="feature-card">
        <h3>Bespaar Tijd</h3>
        <p>Genereer concept-secties voor uw rapportages op basis van geüploade documenten.</p>
      </div>
      
      <div class="feature-card">
        <h3>Behoud Controle</h3>
        <p>Bekijk, bewerk en verfijn alle gegenereerde content voordat u het gebruikt.</p>
      </div>
      
      <div class="feature-card">
        <h3>Beveiligde Verwerking</h3>
        <p>Uw gegevens worden veilig verwerkt met moderne AI en beveiligd volgens AVG-standaarden.</p>
      </div>
    </div>

    <div class="workflow">
      <h2>Hoe het werkt</h2>
      
      <div class="workflow-steps">
        <div class="step">
          <div class="step-number">1</div>
          <h4>Maak een Case aan</h4>
          <p>Organiseer uw werk in cases voor eenvoudig beheer</p>
        </div>
        
        <div class="step">
          <div class="step-number">2</div>
          <h4>Upload Documenten</h4>
          <p>Voeg relevante documenten toe zoals FML, gespreksverslagen en dossiers</p>
        </div>
        
        <div class="step">
          <div class="step-number">3</div>
          <h4>Genereer Rapport</h4>
          <p>Laat AI u helpen bij het opstellen van secties voor uw rapportage</p>
        </div>
        
        <div class="step">
          <div class="step-number">4</div>
          <h4>Controleer & Gebruik</h4>
          <p>Beoordeel, wijzig en gebruik de gegenereerde content in uw werk</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 3rem;
}

.hero {
  text-align: center;
  padding: 3rem 1rem;
  background-color: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 2rem;
}

.hero h1 {
  font-size: 2.5rem;
  margin-bottom: 1rem;
  color: var(--primary-color);
}

.subtitle {
  font-size: 1.25rem;
  color: var(--text-light);
  max-width: 700px;
  margin: 0 auto 2rem auto;
}

.cta-buttons {
  margin-top: 2rem;
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
  margin-bottom: 3rem;
}

.feature-card {
  background-color: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: var(--shadow);
  text-align: center;
}

.feature-card h3 {
  color: var(--primary-color);
  margin-bottom: 1rem;
}

.workflow {
  text-align: center;
  margin-bottom: 3rem;
}

.workflow h2 {
  margin-bottom: 2rem;
  position: relative;
}

.workflow h2:after {
  content: '';
  position: absolute;
  bottom: -10px;
  left: 50%;
  transform: translateX(-50%);
  width: 50px;
  height: 3px;
  background-color: var(--primary-color);
}

.workflow-steps {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-top: 2rem;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1.5rem;
  background-color: white;
  border-radius: 8px;
  box-shadow: var(--shadow);
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: var(--primary-color);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-bottom: 1rem;
}

.step h4 {
  margin-bottom: 0.5rem;
  color: var(--text-color);
}

.step p {
  color: var(--text-light);
  text-align: center;
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .features,
  .workflow-steps {
    grid-template-columns: 1fr;
  }
}
</style>