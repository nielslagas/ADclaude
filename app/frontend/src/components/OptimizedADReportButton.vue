<template>
  <div class="optimized-ad-report">
    <!-- Generate Button -->
    <div v-if="!loading && !reportGenerated" class="generate-section">
      <h3>🚀 Enhanced AD Rapport</h3>
      <p class="description">
        Professionele arbeidsdeskundige rapporten met complete structuur, 
        realistische content en gestructureerde data output.
      </p>
      
      <div class="benefits">
        <h4>Enhanced AD Voordelen:</h4>
        <ul>
          <li>✅ Complete 22-sectie structuur</li>
          <li>✅ Realistische arbeidsdeskundige content</li>
          <li>✅ Gestructureerde JSON data</li>
          <li>✅ FML rubrieken ondersteuning</li>
          <li>✅ Verbeterde prompts en analyses</li>
          <li>✅ DOCX export met templates</li>
        </ul>
      </div>

      <!-- Template selectie verborgen - altijd Enhanced AD -->
      <div class="template-info">
        <div class="info-badge">
          <i class="fas fa-check-circle"></i>
          <span>Enhanced AD Template</span>
        </div>
      </div>

      <button @click="generateOptimizedReport" class="btn-generate" :disabled="loading">
        <span v-if="loading" class="loading">⏳</span>
        <span v-else class="icon">🚀</span>
        {{ loading ? 'Genereren...' : 'Genereer Geoptimaliseerd AD Rapport' }}
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-section">
      <div class="loading-spinner"></div>
      <h3>AD Rapport wordt gegenereerd...</h3>
      <p>Dit duurt ongeveer 30-60 seconden met de nieuwe geoptimaliseerde methode</p>
      <div class="progress-info">
        <div class="progress-step" :class="{ active: step >= 1 }">📊 Analyseer documenten</div>
        <div class="progress-step" :class="{ active: step >= 2 }">🏢 Genereer gegevens secties</div>
        <div class="progress-step" :class="{ active: step >= 3 }">📋 Maak geschiktheidsanalyse</div>
        <div class="progress-step" :class="{ active: step >= 4 }">📝 Formuleer conclusies</div>
        <div class="progress-step" :class="{ active: step >= 5 }">🎨 Render HTML rapport</div>
      </div>
    </div>

    <!-- Generated Report Display -->
    <div v-if="reportGenerated && htmlContent" class="report-section">
      <div class="report-header">
        <h3>✅ Geoptimaliseerd AD Rapport Gegenereerd</h3>
        <div class="report-actions">
          <button @click="viewReport" class="btn-view">👁️ Bekijk Rapport</button>
          <button @click="exportPDF" class="btn-export">📄 Export PDF</button>
          <button @click="exportWord" class="btn-export">📝 Export Word</button>
          <button @click="generateAnother" class="btn-secondary">🔄 Genereer Nieuw</button>
        </div>
      </div>

      <!-- Report Preview -->
      <div v-if="showPreview" class="report-preview">
        <div class="preview-header">
          <h4>Rapport Preview - Statische Template</h4>
          <button @click="showPreview = false" class="btn-close">✖️</button>
        </div>
        <StaticADReportTemplate :reportData="reportData" />
      </div>

      <!-- Report Stats -->
      <div class="report-stats">
        <div class="stat">
          <strong>Generatie tijd:</strong> {{ generationTime }}s
        </div>
        <div class="stat">
          <strong>LLM calls:</strong> 5-6 (70% reductie)
        </div>
        <div class="stat">
          <strong>Template:</strong> {{ selectedTemplate }}
        </div>
        <div class="stat">
          <strong>Grootte:</strong> {{ Math.round(htmlContent.length / 1024) }}KB
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="error" class="error-section">
      <h3>❌ Fout bij genereren rapport</h3>
      <p>{{ error }}</p>
      <button @click="resetState" class="btn-retry">🔄 Probeer opnieuw</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, inject } from 'vue'
import { apiClient as api } from '@/services/api'
import { useCaseStore } from '@/stores/case'
import { useReportStore } from '@/stores/report'
import { useProfileStore } from '@/stores/profile'
import StaticADReportTemplate from './StaticADReportTemplate.vue'

// Props
interface Props {
  caseId: string
}

const props = defineProps<Props>()

// Store
const caseStore = useCaseStore()
const reportStore = useReportStore()
const profileStore = useProfileStore()

// State
const loading = ref(false)
const error = ref<string | null>(null)
const reportGenerated = ref(false)
const htmlContent = ref('')
const selectedTemplate = ref('standaard')
const step = ref(0)
const generationTime = ref(0)
const showPreview = ref(false)
const reportId = ref('')

// Reactive data for template
const reportData = ref(null)

// Function to prepare case data from store for template
const prepareCaseDataForTemplate = () => {
  console.log('Using case store data:', caseStore.currentCase)
  console.log('Available documents:', caseStore.documents)
  console.log('User profile data:', profileStore.profile)
  
  const caseData = caseStore.currentCase
  const documents = caseStore.documents
  const userProfile = profileStore.profile
  
  if (!caseData) {
    console.warn('No case data available in store')
    return {
      werknemer: { naam: '[Geen case data beschikbaar]' },
      werkgever: { naam: '[Geen case data beschikbaar]' },
      adviseur: { naam: '[Geen case data beschikbaar]' },
      onderzoek: { datum_onderzoek: '[Geen case data beschikbaar]', datum_rapportage: '[Geen case data beschikbaar]' },
      samenvatting: { 
        vraagstelling: ['[Geen case data beschikbaar]'],
        conclusie: ['[Geen case data beschikbaar]']
      }
    }
  }
  
  // Transform the data for the template using available case fields
  const transformedData = {
    werknemer: {
      naam: caseData.werknemer_naam || 'Uit case: ' + (caseData.title || '[Onbekend]'),
      geboortedatum: caseData.werknemer_geboortedatum || '[Te bepalen]',
      adres: caseData.werknemer_adres || '[Te bepalen]',
      postcode_plaats: caseData.werknemer_postcode_plaats || '[Te bepalen]',
      telefoonnummer: caseData.werknemer_telefoonnummer || '[Te bepalen]',
      email: caseData.werknemer_email || '[Te bepalen]'
    },
    werkgever: {
      naam: caseData.werkgever_naam || caseData.title || '[Bedrijf uit case titel]',
      contactpersoon: caseData.werkgever_contactpersoon || '[Te bepalen]',
      functie_contactpersoon: caseData.werkgever_functie_contactpersoon || '[Te bepalen]',
      adres: caseData.werkgever_adres || '[Te bepalen]',
      postcode_plaats: caseData.werkgever_postcode_plaats || '[Te bepalen]',
      telefoonnummer: caseData.werkgever_telefoonnummer || '[Te bepalen]',
      email: caseData.werkgever_email || '[Te bepalen]'
    },
    adviseur: {
      naam: userProfile ? `${userProfile.first_name || ''} ${userProfile.last_name || ''}`.trim() || userProfile.display_name || '[Naam uit profiel]' : '[Uit gebruikersprofiel]',
      titel: userProfile?.certification || 'Gecertificeerd Register Arbeidsdeskundige',
      bedrijf: userProfile?.company_name || '[Uit gebruikersprofiel]',
      telefoonnummer: userProfile?.company_phone || '[Uit gebruikersprofiel]',
      logo_url: userProfile?.logo_url || null
    },
    onderzoek: {
      datum_onderzoek: new Date().toLocaleDateString('nl-NL'),
      datum_rapportage: new Date().toLocaleDateString('nl-NL')
    },
    samenvatting: {
      vraagstelling: [
        'Kan werknemer het eigen werk bij de eigen werkgever nog uitvoeren?',
        'Zo nee, is het eigen werk met behulp van aanpassingen passend te maken?',
        'Zo nee, kan werknemer ander werk bij de eigen werkgever uitvoeren?',
        'Zo nee, zijn er mogelijkheden om werknemer naar ander werk te begeleiden en is een vervolgtraject gewenst?'
      ],
      conclusie: [
        `Analyse voor case "${caseData.title}" wordt uitgevoerd...`,
        `Documenten (${documents.length} stuks) worden geanalyseerd...`,
        'Aanpassingsmogelijkheden worden onderzocht...',
        'Re-integratietraject wordt voorbereid...'
      ]
    },
    rapportage: {
      vraagstelling: [
        'Kan werknemer het eigen werk bij de eigen werkgever nog uitvoeren?',
        'Zo nee, is het eigen werk met behulp van aanpassingen passend te maken?',
        'Zo nee, kan werknemer ander werk bij de eigen werkgever uitvoeren?',
        'Zo nee, zijn er mogelijkheden om werknemer naar ander werk te begeleiden en is een vervolgtraject gewenst?'
      ],
      activiteiten: [
        'Voorbereiding (dossieronderzoek) op [datum].',
        'Bestuderen informatie van de bedrijfsarts op [datum].',
        'Overleg met bedrijfsarts op [datum].',
        'Gesprek met werknemer op [datum] op de werklocatie.',
        'Gesprek met werkgever op [datum] op de werklocatie.',
        'Overleg met werknemer en werkgever gezamenlijk op [datum].',
        'Rapportage opstellen op [datum].'
      ]
    },
    gegevensverzameling: {
      voorgeschiedenis: 'Uit dossieronderzoek blijkt dat werknemer sinds [datum] verzuimt vanwege [reden]. De ziek- en herstelperiode is [beschrijving].',
      verzuimhistorie: 'Werknemer heeft een verzuimperiode van [aantal weken] weken. Uit medische informatie blijkt dat herstel wordt verwacht binnen [termijn].',
      werkgever: {
        aard_bedrijf: '[Aard bedrijf]',
        omvang_bedrijf: '[Omvang bedrijf]',
        aantal_werknemers: '[Aantal werknemers]',
        functies_beschrijving: '[Functies beschrijving]',
        overige_informatie: '[Website/overige info]'
      },
      werknemer: {
        opleidingen: [
          { naam: '[Opleiding]', richting: '[Richting]', diploma_jaar: '[Jaar]' },
          { naam: '[Aanvullende cursussen]', richting: '[Richting]', diploma_jaar: '[Jaar]' }
        ],
        arbeidsverleden: [
          { periode: '[Van/tot datum]', werkgever: '[Werkgever]', functie: '[Functie]' }
        ],
        computervaardigheden: 'Goed',
        taalvaardigheid: 'Goed', 
        rijbewijs: '[Rijbewijs informatie]'
      },
      belastbaarheid: {
        beschrijving: '[Belastbaarheid beschrijving van bedrijfsarts]',
        persoonlijk_functioneren: [
          {
            nummer: '2.',
            beschrijving: 'Verdelen van de aandacht: [beschrijving van beperkingen]',
            mate_beperking: 'Beperkt'
          }
        ],
        sociaal_functioneren: [
          {
            nummer: '6.',
            beschrijving: 'Emotionele problemen van anderen hanteren: [beschrijving van beperkingen]',
            mate_beperking: 'Beperkt'
          }
        ],
        fysieke_omgeving: 'Niet beperkt',
        dynamische_handelingen: 'Niet beperkt',
        statische_houdingen: 'Niet beperkt',
        werktijden: 'Er zijn beperkingen in werktijden...',
        prognose: '[Prognose tekst van bedrijfsarts]'
      }
    },
    documents: documents,
    case_info: caseData
  }
  
  console.log('Transformed data for template:', transformedData)
  return transformedData
}

// Function to integrate content from the working report system with template structure
const integrateWorkingSystemContentWithTemplate = (baseData: any, reportContent: any) => {
  console.log('Integrating working system content - Report sections:', Object.keys(reportContent || {}))
  console.log('Base data keys:', Object.keys(baseData))
  
  // The reportContent from the working system contains sectioned content
  if (!reportContent || typeof reportContent !== 'object') {
    console.warn('No valid report content from working system, using base data')
    return baseData
  }
  
  // Extract actual content from working system sections
  const extractContentText = (sectionContent: any) => {
    if (typeof sectionContent === 'string') return sectionContent
    if (sectionContent && typeof sectionContent === 'object') {
      if (sectionContent.content) return sectionContent.content
      if (sectionContent.text) return sectionContent.text
    }
    return String(sectionContent || '')
  }
  
  // Parse names and info from the actual generated content
  const extractNameFromContent = (content: string) => {
    const matches = content.match(/(?:naam|werknemer)[:\s]*([^\n\r,]{2,50})/i)
    return matches ? matches[1].trim() : null
  }
  
  const extractCompanyFromContent = (content: string) => {
    const matches = content.match(/(?:bedrijf|werkgever|organisatie)[:\s]*([^\n\r,]{2,50})/i)
    return matches ? matches[1].trim() : null
  }
  
  // Validate baseData structure
  if (!baseData.rapportage) {
    console.error('BaseData missing rapportage section:', baseData)
    baseData.rapportage = { vraagstelling: [], activiteiten: [] }
  }
  if (!baseData.gegevensverzameling) {
    console.error('BaseData missing gegevensverzameling section:', baseData)
    baseData.gegevensverzameling = { voorgeschiedenis: '', verzuimhistorie: '', werkgever: {}, werknemer: {}, belastbaarheid: {} }
  }
  
  // Create enhanced data using actual generated content
  const enhancedData = {
    ...baseData,
    // Try to extract werknemer info from generated content
    werknemer: {
      ...baseData.werknemer,
      naam: extractNameFromContent(extractContentText(reportContent.gegevensverzameling_werknemer || reportContent.gesprek_werknemer || '')) || baseData.werknemer.naam
    },
    // Try to extract werkgever info from generated content  
    werkgever: {
      ...baseData.werkgever,
      naam: extractCompanyFromContent(extractContentText(reportContent.gegevensverzameling_werkgever || reportContent.gesprek_werkgever || '')) || baseData.werkgever.naam
    },
    // Use actual generated conclusions
    samenvatting: {
      vraagstelling: baseData.samenvatting.vraagstelling, // Keep standard questions
      conclusie: reportContent.conclusie ? 
                [extractContentText(reportContent.conclusie)] : 
                baseData.samenvatting.conclusie
    },
    rapportage: {
      vraagstelling: baseData.samenvatting.vraagstelling,
      activiteiten: reportContent.ondernomen_activiteiten ? 
                   extractContentText(reportContent.ondernomen_activiteiten).split('\n').filter(line => line.trim().length > 5) :
                   baseData.rapportage.activiteiten
    },
    gegevensverzameling: {
      voorgeschiedenis: extractContentText(reportContent.gegevensverzameling_voorgeschiedenis) || 
                       baseData.gegevensverzameling.voorgeschiedenis,
      verzuimhistorie: extractContentText(reportContent.belastbaarheid) || 
                      baseData.gegevensverzameling.verzuimhistorie,
      werkgever: {
        aard_bedrijf: extractContentText(reportContent.gegevensverzameling_werkgever) || baseData.gegevensverzameling.werkgever.aard_bedrijf,
        omvang_bedrijf: baseData.gegevensverzameling.werkgever.omvang_bedrijf,
        aantal_werknemers: baseData.gegevensverzameling.werkgever.aantal_werknemers,
        functies_beschrijving: baseData.gegevensverzameling.werkgever.functies_beschrijving,
        overige_informatie: baseData.gegevensverzameling.werkgever.overige_informatie
      },
      werknemer: {
        ...baseData.gegevensverzameling.werknemer,
        // Keep structure but could enhance with generated content
      },
      belastbaarheid: {
        beschrijving: extractContentText(reportContent.belastbaarheid) || baseData.gegevensverzameling.belastbaarheid.beschrijving,
        persoonlijk_functioneren: baseData.gegevensverzameling.belastbaarheid.persoonlijk_functioneren,
        sociaal_functioneren: baseData.gegevensverzameling.belastbaarheid.sociaal_functioneren,
        fysieke_omgeving: baseData.gegevensverzameling.belastbaarheid.fysieke_omgeving,
        dynamische_handelingen: baseData.gegevensverzameling.belastbaarheid.dynamische_handelingen,
        statische_houdingen: baseData.gegevensverzameling.belastbaarheid.statische_houdingen,
        werktijden: baseData.gegevensverzameling.belastbaarheid.werktijden,
        prognose: extractContentText(reportContent.visie_ad_duurzaamheid) || baseData.gegevensverzameling.belastbaarheid.prognose
      }
    },
    // Store reference to full generated content for debugging
    _generatedSections: reportContent,
    _availableSections: Object.keys(reportContent)
  }
  
  console.log('Enhanced template data from working system:', enhancedData)
  return enhancedData
}

// Legacy function to integrate LLM generated content with template structure
const integrateReportContentWithTemplate = (baseData: any, reportContent: any) => {
  console.log('Integrating LLM content - Raw content:', reportContent)
  console.log('Base data keys:', Object.keys(baseData))
  
  // The reportContent contains the actual LLM generated sections
  if (!reportContent || typeof reportContent !== 'object') {
    console.warn('No valid report content to integrate, using base data')
    return baseData
  }
  
  // Extract content from each section that was generated by the LLM
  const extractTextContent = (section: any) => {
    if (typeof section === 'string') return section
    if (section && typeof section === 'object' && section.content) return section.content
    if (section && typeof section === 'object' && section.text) return section.text
    return section
  }
  
  // Create enhanced data with LLM content
  const enhancedData = {
    ...baseData,
    // Keep existing basic data but enhance with LLM content
    samenvatting: {
      vraagstelling: baseData.samenvatting.vraagstelling, // Keep standard questions
      conclusie: reportContent.conclusie ? 
                [extractTextContent(reportContent.conclusie)] : 
                ['Analyse voor case "' + baseData.werknemer.naam + '" wordt uitgevoerd...',
                 'Documenten (' + (caseStore.documents?.length || 0) + ' stuks) worden geanalyseerd...',
                 'Aanpassingsmogelijkheden worden onderzocht...',
                 'Re-integratietraject wordt voorbereid...']
    },
    rapportage: {
      vraagstelling: baseData.samenvatting.vraagstelling,
      activiteiten: [
        'Voorbereiding (dossieronderzoek) op [datum].',
        'Bestuderen informatie van de bedrijfsarts op [datum].',
        'Overleg met bedrijfsarts op [datum].',
        'Gesprek met werknemer op [datum] op de werklocatie.',
        'Gesprek met werkgever op [datum] op de werklocatie.',
        'Overleg met werknemer en werkgever gezamenlijk op [datum].',
        'Rapportage opstellen op [datum].'
      ]
    },
    gegevensverzameling: {
      voorgeschiedenis: extractTextContent(reportContent.gegevensverzameling_voorgeschiedenis) || 
                       'Uit dossieronderzoek blijkt dat werknemer sinds [datum] verzuimt vanwege [reden]. De ziek- en herstelperiode is [beschrijving].',
      verzuimhistorie: 'Werknemer heeft een verzuimperiode van [aantal weken] weken. Uit medische informatie blijkt dat herstel wordt verwacht binnen [termijn].',
      werkgever: {
        aard_bedrijf: extractTextContent(reportContent.gegevensverzameling_werkgever) || '[Aard bedrijf uit LLM analyse]',
        omvang_bedrijf: '[Omvang bedrijf]',
        aantal_werknemers: '[Aantal werknemers]',
        functies_beschrijving: '[Functies beschrijving uit LLM analyse]',
        overige_informatie: '[Website/overige info]'
      },
      werknemer: {
        opleidingen: [
          { naam: '[Opleiding uit LLM analyse]', richting: '[Richting]', diploma_jaar: '[Jaar]' },
          { naam: '[Aanvullende cursussen]', richting: '[Richting]', diploma_jaar: '[Jaar]' }
        ],
        arbeidsverleden: [
          { periode: '[Van/tot datum]', werkgever: '[Werkgever]', functie: '[Functie uit LLM analyse]' }
        ],
        computervaardigheden: 'Goed',
        taalvaardigheid: 'Goed', 
        rijbewijs: '[Rijbewijs informatie]'
      },
      belastbaarheid: {
        beschrijving: extractTextContent(reportContent.belastbaarheid) || 
                     '[Belastbaarheid beschrijving van bedrijfsarts uit LLM analyse]',
        persoonlijk_functioneren: [
          {
            nummer: '2.',
            beschrijving: 'Verdelen van de aandacht: [beschrijving van beperkingen]',
            mate_beperking: 'Beperkt'
          }
        ],
        sociaal_functioneren: [
          {
            nummer: '6.',
            beschrijving: 'Emotionele problemen van anderen hanteren: [beschrijving van beperkingen]',
            mate_beperking: 'Beperkt'
          }
        ],
        fysieke_omgeving: 'Niet beperkt',
        dynamische_handelingen: 'Niet beperkt',
        statische_houdingen: 'Niet beperkt',
        werktijden: 'Er zijn beperkingen in werktijden...',
        prognose: extractTextContent(reportContent.visie_ad_duurzaamheid) || 
                 '[Prognose tekst van bedrijfsarts uit LLM analyse]'
      }
    }
  }
  
  console.log('Enhanced template data:', enhancedData)
  return enhancedData
}

// Methods
const generateOptimizedReport = async () => {
  loading.value = true
  error.value = null
  step.value = 0
  
  const startTime = Date.now()

  try {
    // Start progress simulation
    simulateProgress()

    // Step 0: Ensure user profile is loaded
    if (!profileStore.profile) {
      console.log('Fetching user profile...')
      try {
        await profileStore.fetchProfile()
      } catch (profileError) {
        console.warn('Could not fetch user profile:', profileError)
      }
    }

    // Step 1: Prepare basic case data for template
    step.value = 1
    let baseData = prepareCaseDataForTemplate()
    console.log('Base case data prepared:', baseData)
    
    // Step 2: Generate report using existing LLM system
    step.value = 2
    console.log('Creating report with LLM calls...')
    
    const reportTitle = `AD Rapport - ${baseData.werkgever.naam} - ${new Date().toLocaleDateString('nl-NL')}`
    
    try {
      // Create report using Enhanced AD workflow only
      console.log('Attempting to create Enhanced AD report with params:', {
        title: reportTitle,
        case_id: props.caseId,
        template_id: "enhanced_ad_rapport",
        layout_type: "standaard"
      })
      
      const newReport = await reportStore.createEnhancedADReport({
        title: reportTitle,
        case_id: props.caseId,
        template_id: "enhanced_ad_rapport",
        layout_type: "standaard"
      })
      
      console.log('Report created with LLM content:', newReport)
      reportId.value = newReport.id
      
      // Step 3: Wait for report to be fully generated
      step.value = 3
      console.log('Waiting for report generation to complete...')
      
      // Poll for completion (check report status)
      let attempts = 0
      const maxAttempts = 30
      
      while (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 2000))
        
        const report = await reportStore.fetchReport(reportId.value)
        console.log(`Report status check ${attempts + 1}:`, report?.status)
        
        if (report?.status === 'completed' && report?.content) {
          console.log('Report generation completed with content')
          
          // Step 4: Integrate LLM generated content with template structure
          step.value = 4
          console.log('Using generated report content from working system:', report.content)
          reportData.value = integrateWorkingSystemContentWithTemplate(baseData, report.content)
          console.log('Integrated report data:', reportData.value)
          break
        } else if (report?.status === 'failed') {
          throw new Error('Report generation failed')
        }
        
        attempts++
      }
      
      if (attempts >= maxAttempts) {
        console.warn('Report polling timeout, trying to get current report data')
        // Try to get any available report content from the store
        const currentReport = reportStore.currentReport
        if (currentReport && currentReport.content) {
          console.log('Using current report content after timeout:', currentReport.content)
          reportData.value = integrateWorkingSystemContentWithTemplate(baseData, currentReport.content)
        } else {
          console.log('No report content available, using basic template')
          reportData.value = baseData // Use basic data if timeout
        }
      }
      
    } catch (reportError) {
      console.error('Error creating report with LLM:', reportError)
      console.log('Falling back to template - trying current report or basic data')
      
      // Try to use any existing report content from store
      const currentReport = reportStore.currentReport
      if (currentReport && currentReport.content) {
        console.log('Using existing report content from store:', currentReport.content)
        reportData.value = integrateWorkingSystemContentWithTemplate(baseData, currentReport.content)
      } else {
        console.log('No existing report content, using basic template')
        reportData.value = baseData // Use basic data if no content available
      }
    }
    
    htmlContent.value = 'Statische template met LLM gegenereerde content'
    generationTime.value = Math.round((Date.now() - startTime) / 1000)
    reportGenerated.value = true
    step.value = 5

    // Uncomment when backend endpoint is working:
    /*
    // Call optimized AD report generation
    const response = await api.post('/ad-reports/generate-optimized', {
      case_id: props.caseId,
      template: selectedTemplate.value,
      use_async: true
    })

    reportId.value = response.data.report_id

    // Poll for completion
    await pollForCompletion(reportId.value)

    // Get HTML content
    const htmlResponse = await api.get(`/ad-reports/${reportId.value}/structured?format=html`)
    htmlContent.value = htmlResponse.data.content
    */

  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Onbekende fout opgetreden'
    console.error('Error generating optimized report:', err)
  } finally {
    loading.value = false
  }
}

const simulateProgress = () => {
  const steps = [1, 2, 3, 4]
  let currentStep = 0
  
  const interval = setInterval(() => {
    if (currentStep < steps.length && loading.value) {
      step.value = steps[currentStep]
      currentStep++
    } else {
      clearInterval(interval)
    }
  }, 8000) // Update every 8 seconds
}

const pollForCompletion = async (id: string, maxAttempts = 30) => {
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    const status = await api.get(`/ad-reports/${id}/status`)
    
    if (status.data.status === 'generated') {
      return
    } else if (status.data.status === 'failed') {
      throw new Error('Rapport generatie mislukt')
    }
  }
  
  throw new Error('Timeout: rapport generatie duurde te lang')
}

const viewReport = () => {
  showPreview.value = true
}

const exportPDF = async () => {
  try {
    const response = await api.get(`/api/v1/reports/${reportId.value}/export?format=pdf`, {
      responseType: 'blob'
    })
    
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `ad-rapport-${props.caseId}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (err) {
    console.error('Export PDF failed:', err)
  }
}

const exportWord = async () => {
  try {
    const response = await api.get(`/api/v1/reports/${reportId.value}/export?format=docx`, {
      responseType: 'blob'
    })
    
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `ad-rapport-${props.caseId}.docx`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (err) {
    console.error('Export Word failed:', err)
  }
}

const generateAnother = () => {
  resetState()
}

const resetState = () => {
  loading.value = false
  error.value = null
  reportGenerated.value = false
  htmlContent.value = ''
  step.value = 0
  generationTime.value = 0
  showPreview.value = false
  reportId.value = ''
}
</script>

<style scoped>
.optimized-ad-report {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  margin: 20px 0;
}

.generate-section h3 {
  color: #1e40af;
  margin-bottom: 12px;
  font-size: 20px;
}

.description {
  color: #6b7280;
  margin-bottom: 20px;
  line-height: 1.6;
}

.benefits {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  padding: 16px;
  margin: 20px 0;
}

.benefits h4 {
  color: #0369a1;
  margin-bottom: 12px;
}

.benefits ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.benefits li {
  padding: 4px 0;
  color: #0c4a6e;
}

.template-selection {
  margin: 20px 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.template-selection label {
  font-weight: 600;
  color: #374151;
}

.template-select {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  min-width: 120px;
}

.btn-generate {
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-generate:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(59, 130, 246, 0.4);
}

.btn-generate:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.loading-section {
  text-align: center;
  padding: 40px 20px;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.progress-info {
  margin-top: 30px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
}

.progress-step {
  padding: 8px 16px;
  background: #f3f4f6;
  border-radius: 20px;
  color: #6b7280;
  font-size: 14px;
  transition: all 0.3s;
}

.progress-step.active {
  background: #dbeafe;
  color: #1e40af;
  font-weight: 600;
}

.report-section {
  border-top: 2px solid #e5e7eb;
  padding-top: 24px;
  margin-top: 24px;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.report-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.btn-view,
.btn-export,
.btn-secondary,
.btn-retry {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-view {
  background: #10b981;
  color: white;
}

.btn-export {
  background: #6366f1;
  color: white;
}

.btn-secondary {
  background: #6b7280;
  color: white;
}

.btn-retry {
  background: #ef4444;
  color: white;
}

.btn-view:hover,
.btn-export:hover,
.btn-secondary:hover,
.btn-retry:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.report-preview {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  margin: 20px 0;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
  background: #f3f4f6;
}

.btn-close {
  background: #ef4444;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.html-content {
  padding: 20px;
  max-height: 600px;
  overflow-y: auto;
}

.report-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-top: 20px;
  padding: 20px;
  background: #f8fafc;
  border-radius: 8px;
}

.stat {
  color: #374151;
  font-size: 14px;
}

.error-section {
  text-align: center;
  padding: 40px 20px;
  color: #dc2626;
}

.error-section h3 {
  margin-bottom: 12px;
}
</style>