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
    <!-- Hero Section -->
    <section class="hero">
      <div class="hero-content">
        <div class="hero-badge">
          <span class="badge badge-primary">
            <svg class="badge-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 0a8 8 0 100 16A8 8 0 008 0zM3.732 5.732a.5.5 0 01.707-.707L8 8.586l3.561-3.561a.5.5 0 11.707.707l-3.914 3.915a.5.5 0 01-.708 0L3.732 5.732z"/>
            </svg>
            AI-Powered
          </span>
        </div>
        
        <h1 class="hero-title">
          Arbeidsdeskundige
          <span class="title-highlight">AI Assistant</span>
        </h1>
        
        <p class="hero-subtitle">
          Professionele arbeidsdeskundig rapporten, intelligent geoptimaliseerd.
          Bespaar tijd zonder in te leveren op kwaliteit.
        </p>
        
        <div class="hero-stats">
          <div class="stat">
            <span class="stat-number">75%</span>
            <span class="stat-label">Tijdsbesparing</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-number">100%</span>
            <span class="stat-label">AVG Compliant</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-number">24/7</span>
            <span class="stat-label">Beschikbaar</span>
          </div>
        </div>
        
        <div class="hero-actions">
          <button v-if="!authStore.isLoggedIn" @click="goToLogin" class="btn btn-primary btn-lg">
            <svg class="btn-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M3 3a1 1 0 011 1v12a1 1 0 11-2 0V4a1 1 0 011-1zm7.707 3.293a1 1 0 010 1.414L9.414 9H17a1 1 0 110 2H9.414l1.293 1.293a1 1 0 01-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0z" clip-rule="evenodd"/>
            </svg>
            Aan de slag
          </button>
          <button v-else @click="goToCases" class="btn btn-primary btn-lg">
            <svg class="btn-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2H4z"/>
            </svg>
            Mijn Cases
          </button>
          <a href="#features" class="btn btn-outline btn-lg">
            <svg class="btn-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
            </svg>
            Meer info
          </a>
        </div>
      </div>
      
      <div class="hero-visual">
        <div class="visual-card">
          <div class="visual-header">
            <div class="visual-dots">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
            <span class="visual-title">Rapport Preview</span>
          </div>
          <div class="visual-content">
            <div class="visual-line long"></div>
            <div class="visual-line medium"></div>
            <div class="visual-line short"></div>
            <div class="visual-line medium"></div>
          </div>
        </div>
      </div>
    </section>

    <!-- Features Section -->
    <section id="features" class="features">
      <div class="section-header">
        <h2>Waarom kiezen voor AI Assistant?</h2>
        <p>Moderne technologie voor professionele arbeidsdeskundigen</p>
      </div>
      
      <div class="features-grid">
        <div class="feature-card">
          <div class="feature-icon">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="16" cy="16" r="14"/>
              <path d="M8 16l4 4 12-12"/>
            </svg>
          </div>
          <h3>Bespaar Tijd</h3>
          <p>Automatische generatie van rapportsecties op basis van uw documenten. Bespaar tot 75% van uw tijd.</p>
        </div>
        
        <div class="feature-card">
          <div class="feature-icon">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M16 2L3 14v16h26V14L16 2z"/>
              <path d="M12 30v-8h8v8"/>
            </svg>
          </div>
          <h3>Behoud Controle</h3>
          <p>U blijft volledig in controle. Bewerk, verfijn en pas alle content aan naar uw wensen.</p>
        </div>
        
        <div class="feature-card">
          <div class="feature-icon">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="4" y="4" width="24" height="24" rx="4"/>
              <path d="M9 12l6 6 8-8"/>
            </svg>
          </div>
          <h3>AVG Compliant</h3>
          <p>Veilige verwerking volgens Nederlandse privacy-wetgeving. Uw data blijft altijd beschermd.</p>
        </div>
      </div>
    </section>

    <!-- Workflow Section -->
    <section class="workflow">
      <div class="section-header">
        <h2>Hoe het werkt</h2>
        <p>Van document naar professioneel rapport in 4 eenvoudige stappen</p>
      </div>
      
      <div class="workflow-steps">
        <div class="step">
          <div class="step-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="4" width="18" height="16" rx="2"/>
              <path d="M7 2v4M17 2v4M3 10h18"/>
            </svg>
          </div>
          <div class="step-number">01</div>
          <h4>Maak een Case</h4>
          <p>Start een nieuwe case en organiseer uw documenten overzichtelijk</p>
        </div>
        
        <div class="step-connector"></div>
        
        <div class="step">
          <div class="step-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
              <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/>
            </svg>
          </div>
          <div class="step-number">02</div>
          <h4>Upload Documenten</h4>
          <p>Voeg FML, gespreksverslagen en andere relevante documenten toe</p>
        </div>
        
        <div class="step-connector"></div>
        
        <div class="step">
          <div class="step-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>
            </svg>
          </div>
          <div class="step-number">03</div>
          <h4>AI Generatie</h4>
          <p>Laat AI intelligente rapportsecties genereren op basis van uw input</p>
        </div>
        
        <div class="step-connector"></div>
        
        <div class="step">
          <div class="step-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 12l2 2 4-4"/>
              <path d="M21 12c-1 0-3-1-3-3s2-3 3-3 3 1 3 3-2 3-3 3"/>
              <path d="M3 12c1 0 3-1 3-3s-2-3-3-3-3 1-3 3 2 3 3 3"/>
              <path d="M18.5 21c0-1.5-1-3-3-3s-3 1.5-3 3 1 3 3 3 3-1.5 3-3"/>
              <path d="M5.5 21c0-1.5 1-3 3-3s3 1.5 3 3-1 3-3 3-3-1.5-3-3"/>
            </svg>
          </div>
          <div class="step-number">04</div>
          <h4>Finaliseer & Export</h4>
          <p>Controleer, bewerk en exporteer uw professionele rapport</p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* Base Layout */
.home {
  min-height: 100vh;
}

/* Hero Section */
.hero {
  position: relative;
  padding: 4rem 0 6rem;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  border-radius: 0 0 2rem 2rem;
  margin-bottom: 4rem;
  overflow: hidden;
}

.hero::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%236366f1' fill-opacity='0.03'%3E%3Ccircle cx='30' cy='30' r='2'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E") repeat;
}

.hero-content {
  position: relative;
  z-index: 1;
  max-width: 800px;
  margin: 0 auto;
  text-align: center;
}

.hero-badge {
  margin-bottom: 1.5rem;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 2rem;
  font-size: 0.875rem;
  font-weight: 500;
}

.badge-primary {
  background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
  color: white;
}

.badge-icon {
  opacity: 0.8;
}

.hero-title {
  font-size: 3.5rem;
  font-weight: 800;
  line-height: 1.1;
  margin-bottom: 1.5rem;
  color: var(--text-primary);
}

.title-highlight {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  display: block;
}

.hero-subtitle {
  font-size: 1.25rem;
  color: var(--text-secondary);
  margin-bottom: 2rem;
  line-height: 1.6;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.hero-stats {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 2rem;
  margin: 3rem 0;
  flex-wrap: wrap;
}

.stat {
  text-align: center;
}

.stat-number {
  display: block;
  font-size: 2rem;
  font-weight: 700;
  color: var(--primary-color);
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 0.875rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-divider {
  width: 1px;
  height: 2rem;
  background: var(--gray-300);
}

.hero-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
  margin-top: 2rem;
}

.btn-icon {
  margin-right: 0.5rem;
}

/* Hero Visual */
.hero-visual {
  margin-top: 3rem;
  display: flex;
  justify-content: center;
}

.visual-card {
  max-width: 500px;
  width: 100%;
  background: white;
  border-radius: 12px;
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  transform: perspective(1000px) rotateX(5deg);
  transition: transform var(--transition-duration);
}

.visual-card:hover {
  transform: perspective(1000px) rotateX(0deg) translateY(-5px);
}

.visual-header {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  color: white;
  padding: 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.visual-dots {
  display: flex;
  gap: 0.5rem;
}

.dot {
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
}

.visual-title {
  font-weight: 600;
}

.visual-content {
  padding: 2rem;
}

.visual-line {
  height: 0.75rem;
  background: var(--gray-200);
  border-radius: 0.375rem;
  margin-bottom: 1rem;
}

.visual-line.long { width: 100%; }
.visual-line.medium { width: 75%; }
.visual-line.short { width: 50%; }

/* Features Section */
.features {
  margin: 4rem 0;
}

.section-header {
  text-align: center;
  margin-bottom: 3rem;
}

.section-header h2 {
  font-size: 2.5rem;
  font-weight: 700;
  margin-bottom: 1rem;
  color: var(--text-primary);
}

.section-header p {
  font-size: 1.125rem;
  color: var(--text-secondary);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 2rem;
}

.feature-card {
  background: white;
  padding: 2.5rem;
  border-radius: 12px;
  box-shadow: var(--shadow);
  text-align: center;
  transition: transform var(--transition-duration), box-shadow var(--transition-duration);
  border: 1px solid var(--gray-200);
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: var(--shadow-lg);
}

.feature-icon {
  width: 4rem;
  height: 4rem;
  margin: 0 auto 1.5rem;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.feature-card h3 {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: var(--text-primary);
}

.feature-card p {
  color: var(--text-secondary);
  line-height: 1.6;
}

/* Workflow Section */
.workflow {
  margin: 4rem 0;
  background: var(--gray-50);
  padding: 4rem 2rem;
  border-radius: 2rem;
}

.workflow-steps {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
  position: relative;
}

.step {
  background: white;
  padding: 2rem;
  border-radius: 12px;
  box-shadow: var(--shadow);
  text-align: center;
  transition: transform var(--transition-duration);
  border: 1px solid var(--gray-200);
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.step:hover {
  transform: translateY(-3px);
}

.step-icon {
  width: 3rem;
  height: 3rem;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1rem;
}

.step-number {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--primary-color);
  background: var(--primary-light);
  padding: 0.25rem 0.75rem;
  border-radius: 1rem;
  margin-bottom: 1rem;
}

.step h4 {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 1rem;
  color: var(--text-primary);
}

.step p {
  color: var(--text-secondary);
  line-height: 1.5;
  font-size: 0.9rem;
}

.step-connector {
  display: none;
}

/* Responsive Design */
@media (max-width: 768px) {
  .hero-title {
    font-size: 2.5rem;
  }
  
  .hero-stats {
    gap: 1.5rem;
  }
  
  .stat-divider {
    display: none;
  }
  
  .hero-actions {
    flex-direction: column;
    align-items: center;
  }
  
  .hero-actions .btn {
    width: 100%;
    max-width: 300px;
  }
  
  .features-grid,
  .workflow-steps {
    grid-template-columns: 1fr;
  }
  
  .visual-card {
    transform: none;
  }
  
  .visual-card:hover {
    transform: translateY(-5px);
  }
  
  .workflow {
    padding: 3rem 1rem;
  }
}

@media (min-width: 1024px) {
  .workflow-steps {
    grid-template-columns: repeat(4, 1fr);
  }
  
  .step-connector {
    display: block;
    position: absolute;
    top: 50%;
    right: -1rem;
    width: 2rem;
    height: 2px;
    background: linear-gradient(90deg, var(--primary-color), transparent);
    transform: translateY(-50%);
  }
  
  .step:last-child .step-connector {
    display: none;
  }
}
</style>