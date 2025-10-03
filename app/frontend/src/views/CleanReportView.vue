<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRoute } from 'vue-router';
import { useReportStore } from '@/stores/report';
import { useProfileStore } from '@/stores/profile';
import { useCaseStore } from '@/stores/case';

const route = useRoute();
const reportStore = useReportStore();
const profileStore = useProfileStore();
const caseStore = useCaseStore();

const reportId = ref(route.params.id as string);
const loading = ref(false);

// Computed properties
const reportData = computed(() => {
  if (!reportStore.currentReport?.content) return null;
  
  // Use structured_data if available, otherwise create full structure from content
  if (reportStore.currentReport.content.structured_data) {
    return reportStore.currentReport.content.structured_data;
  }
  
  // Create complete AD report structure from available content
  const content = reportStore.currentReport.content;
  const sampleData = generateSampleDataFallbacks();
  
  return {
    // Metadata
    titel: content.titel || 'Arbeidsdeskundig rapport',
    
    // Gegevens tabellen met intelligente data mapping
    opdrachtgever: {
      naam_bedrijf: extractFromContent(content, ['werkgever_naam', 'bedrijf_naam', 'opdrachtgever']) || 
                    caseStore.currentCase?.title || 
                    '[Naam bedrijf uit case titel]',
      contactpersoon: extractFromContent(content, ['contactpersoon_werkgever', 'contactpersoon', 'hr_contact']) || '[Te bepalen tijdens intake]',
      functie_contactpersoon: extractFromContent(content, ['functie_contactpersoon', 'functie_contact']) || '[Te bepalen tijdens intake]',
      adres: extractFromContent(content, ['werkgever_adres', 'bedrijf_adres', 'adres_werkgever']) || '[Bedrijfsadres]',
      postcode: extractFromContent(content, ['werkgever_postcode', 'bedrijf_postcode']) || '[Postcode]',
      woonplaats: extractFromContent(content, ['werkgever_plaats', 'bedrijf_plaats', 'werkgever_stad']) || '[Woonplaats]',
      telefoonnummer: extractFromContent(content, ['werkgever_telefoon', 'bedrijf_telefoon', 'telefoon_werkgever']) || '[Telefoonnummer]',
      email: extractFromContent(content, ['werkgever_email', 'bedrijf_email', 'email_werkgever']) || '[Email adres]',
      aard_bedrijf: extractFromContent(content, ['bedrijfstak', 'sector', 'aard_bedrijf', 'branche']) || '[Te bepalen tijdens onderzoek]',
      omvang_bedrijf: extractFromContent(content, ['bedrijfsomvang', 'aantal_werknemers', 'omvang']) || '[Te bepalen tijdens onderzoek]'
    },
    werknemer: {
      naam: extractFromContent(content, ['werknemer_naam', 'naam_werknemer', 'naam', 'medewerker_naam']) ||
            extractNameFromText(extractTextFromContent(content.gegevensverzameling_werknemer)) ||
            '[Naam werknemer - uit gegevensverzameling]',
      geboortedatum: extractFromContent(content, ['geboortedatum', 'geboorte_datum', 'geb_datum']) || '[Te bepalen tijdens intake]',
      adres: extractFromContent(content, ['werknemer_adres', 'adres_werknemer', 'woonadres']) || '[Woonadres]',
      postcode: extractFromContent(content, ['werknemer_postcode', 'postcode_werknemer']) || '[Postcode]',
      woonplaats: extractFromContent(content, ['werknemer_plaats', 'plaats_werknemer', 'woonplaats']) || '[Woonplaats]',
      telefoonnummer: extractFromContent(content, ['werknemer_telefoon', 'telefoon_werknemer', 'mobiel']) || '[Telefoonnummer]',
      email: extractFromContent(content, ['werknemer_email', 'email_werknemer']) || '[Email adres]'
    },
    adviseur: {
      naam: getFullName(profileStore.profile) || '[Naam arbeidsdeskundige]',
      functie: profileStore.profile?.job_title || 
               profileStore.profile?.certification || 
               'Gecertificeerd Register Arbeidsdeskundige',
      adres: profileStore.profile?.company_address || '[Organisatie adres]',
      postcode: profileStore.profile?.company_postal_code || '[Postcode]',
      woonplaats: profileStore.profile?.company_city || '[Woonplaats]',
      telefoonnummer: profileStore.profile?.company_phone || '[Telefoonnummer]',
      email: profileStore.profile?.company_email || '[Email]'
    },
    onderzoek: {
      datum_onderzoek: new Date().toLocaleDateString('nl-NL'),
      datum_rapportage: new Date().toLocaleDateString('nl-NL'),
      locatie_onderzoek: '[Locatie onderzoek]'
    },
    
    // Samenvatting
    samenvatting_vraagstelling: [
      'Kan werknemer het eigen werk bij de eigen werkgever nog uitvoeren?',
      'Zo nee, is het eigen werk met behulp van aanpassingen passend te maken?', 
      'Zo nee, kan werknemer ander werk bij de eigen werkgever uitvoeren?',
      'Zo nee, zijn er mogelijkheden om werknemer naar ander werk te begeleiden en is een vervolgtraject gewenst?'
    ],
    samenvatting_conclusie: [
      extractTextFromContent(content.conclusie) || 'Conclusie wordt gegenereerd op basis van de rapportage...'
    ],
    
    // Hoofdsecties
    vraagstelling: [
      {
        vraag: 'Kan werknemer het eigen werk bij de eigen werkgever nog uitvoeren?',
        antwoord: extractTextFromContent(content.geschiktheid_eigen_werk) || 'Wordt bepaald in de analyse...'
      },
      {
        vraag: 'Zo nee, is het eigen werk met behulp van aanpassingen passend te maken?',
        antwoord: extractTextFromContent(content.aanpassingen_werk) || 'Wordt bepaald in de analyse...'
      }
    ],
    
    ondernomen_activiteiten: [
      extractTextFromContent(content.ondernomen_activiteiten) || 'Voorbereiding (dossieronderzoek)',
      'Gesprek met werknemer op werklocatie', 
      'Analyse functie-eisen en belastbaarheid',
      'Rapportage en aanbevelingen'
    ],
    
    // Gegevensverzameling
    voorgeschiedenis: extractTextFromContent(content.voorgeschiedenis) || 'Voorgeschiedenis en verzuimhistorie worden verzameld...',
    verzuimhistorie: extractTextFromContent(content.verzuimhistorie) || 'Verzuimgegevens worden geanalyseerd...',
    
    gegevens_werknemer: {
      opleidingen: 'Opleidingsachtergrond wordt verzameld...',
      arbeidsverleden: 'Arbeidsverleden wordt geanalyseerd...',
      bekwaamheden: 'Vaardigheden en bekwaamheden worden beoordeeld...'
    },
    
    belastbaarheid: {
      datum_beoordeling: new Date().toLocaleDateString('nl-NL'),
      beoordelaar: profileStore.profile?.full_name || '[Beoordelaar]',
      fml_rubrieken: [
        { rubriek: 'I. Persoonlijk functioneren', mate_beperking: 'Niet beperkt' },
        { rubriek: 'II. Sociaal functioneren', mate_beperking: 'Niet beperkt' },
        { rubriek: 'III. Aanpassing aan fysieke omgevingseisen', mate_beperking: 'Wordt beoordeeld' },
        { rubriek: 'IV. Dynamische handelingen', mate_beperking: 'Wordt beoordeeld' },
        { rubriek: 'V. Statische houdingen', mate_beperking: 'Wordt beoordeeld' },
        { rubriek: 'VI. Werktijden', mate_beperking: 'Wordt beoordeeld' }
      ]
    },
    
    eigen_functie: {
      naam_functie: content.functie_naam || 'Huidige functie',
      arbeidspatroon: 'Voltijd/deeltijd',
      overeenkomst: 'Arbeidsovereenkomst',
      aantal_uren: 'Aantal uren per week',
      functieomschrijving: extractTextFromContent(content.functieomschrijving) || 'Functieomschrijving wordt geanalyseerd...'
    },
    
    gesprekken: {
      werkgever: extractTextFromContent(content.gesprek_werkgever) || 'Gesprek met werkgever wordt samengevat...',
      werknemer: extractTextFromContent(content.gesprek_werknemer) || 'Gesprek met werknemer wordt samengevat...',
      gezamenlijk: 'Gezamenlijk gesprek indien van toepassing...'
    },
    
    // Visie arbeidsdeskundige
    geschiktheid_eigen_werk: extractTextFromContent(content.geschiktheid_eigen_werk) || 'Analyse geschiktheid voor eigen werkzaamheden...',
    aanpassing_eigen_werk: extractTextFromContent(content.aanpassingen_werk) || 'Mogelijke aanpassingen worden onderzocht...',
    geschiktheid_ander_werk_intern: extractTextFromContent(content.ander_werk_intern) || 'Mogelijkheden voor ander werk bij huidige werkgever...',
    geschiktheid_ander_werk_extern: extractTextFromContent(content.ander_werk_extern) || 'Mogelijkheden voor werk bij andere werkgevers...',
    visie_duurzaamheid: extractTextFromContent(content.duurzaamheid) || 'Duurzaamheidsvisie wordt ontwikkeld...',
    
    // Trajectplan
    trajectplan: [
      'Spoor 1: Eigen werk met/zonder aanpassingen',
      'Spoor 2: Ander werk bij eigen/andere werkgever',
      'Concrete actiepunten worden uitgewerkt...'
    ],
    
    // Conclusies en vervolg
    conclusies: [
      extractTextFromContent(content.conclusie) || 'Hoofdconclusie van het onderzoek...'
    ],
    
    vervolg: [
      'Vervolgstappen worden bepaald op basis van de bevindingen...'
    ]
  };
});

// Helper functions for intelligent data extraction
function extractTextFromContent(content: any): string {
  if (typeof content === 'string') return content;
  if (content && typeof content === 'object') {
    if (content.content) return content.content;
    if (content.text) return content.text;
  }
  return String(content || '');
}

// Extract data from content using multiple possible field names
function extractFromContent(content: any, fieldNames: string[]): string | null {
  if (!content) return null;
  
  // Direct field lookup
  for (const fieldName of fieldNames) {
    if (content[fieldName]) {
      return extractTextFromContent(content[fieldName]);
    }
  }
  
  // Search in nested content
  for (const key in content) {
    const value = extractTextFromContent(content[key]);
    if (value) {
      for (const fieldName of fieldNames) {
        // Look for field name in the text content
        const regex = new RegExp(`${fieldName}[:\\s]*([^\\n\\r,]{2,50})`, 'i');
        const match = value.match(regex);
        if (match && match[1]) {
          return match[1].trim();
        }
      }
    }
  }
  
  return null;
}

// Extract name from text content using common patterns
function extractNameFromText(text: string): string | null {
  if (!text) return null;
  
  const patterns = [
    /(?:naam|werknemer)[:\s]*([A-Z][a-zA-Z\s]{2,40})/i,
    /(?:de\s+heer|mevrouw|dhr\.?|mevr\.?)[:\s]*([A-Z][a-zA-Z\s]{2,40})/i,
    /(?:^|\n)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)/m
  ];
  
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match && match[1]) {
      const name = match[1].trim();
      // Validate it looks like a name (not too long, has space)
      if (name.length > 3 && name.length < 50 && name.includes(' ')) {
        return name;
      }
    }
  }
  
  return null;
}

// Get full name from profile
function getFullName(profile: any): string | null {
  if (!profile) return null;
  
  if (profile.display_name) return profile.display_name;
  
  const firstName = profile.first_name || '';
  const lastName = profile.last_name || '';
  
  if (firstName && lastName) {
    return `${firstName} ${lastName}`;
  }
  
  if (firstName) return firstName;
  if (lastName) return lastName;
  
  return null;
}

// Generate some sample data for demonstration if no real data is available
function generateSampleDataFallbacks(): any {
  const currentDate = new Date().toLocaleDateString('nl-NL');
  
  return {
    sample_company: 'ABC Transport BV',
    sample_employee: 'Jan de Vries', 
    sample_contact: 'Mevrouw M. Jansen',
    sample_contact_role: 'HR Manager',
    sample_address: 'Hoofdstraat 123',
    sample_postal: '1234 AB',
    sample_city: 'Amsterdam',
    sample_phone: '020-1234567',
    sample_email: 'info@abctransport.nl',
    sample_birth_date: '15-03-1980',
    current_date: currentDate
  };
}

// Helper functions to format complex data structures
const formatOpleidingen = (opleidingen: any): string => {
  if (!opleidingen || opleidingen.length === 0) return 'Geen opleidingen beschikbaar';
  if (typeof opleidingen === 'string') return opleidingen;
  
  if (Array.isArray(opleidingen)) {
    return opleidingen.map((opl: any) => {
      if (typeof opl === 'string') return `• ${opl}`;
      return `• ${opl.naam || 'Opleiding'} ${opl.richting ? '- ' + opl.richting : ''} ${opl.jaar ? '(' + opl.jaar + ')' : ''}`.trim();
    }).join('\n');
  }
  
  return 'Opleidingsgegevens worden verzameld';
};

const formatArbeidsverleden = (arbeidsverleden: any): string => {
  if (!arbeidsverleden || arbeidsverleden.length === 0) return 'Geen arbeidsverleden beschikbaar';
  if (typeof arbeidsverleden === 'string') return arbeidsverleden;
  
  if (Array.isArray(arbeidsverleden)) {
    return arbeidsverleden.map((werk: any) => {
      if (typeof werk === 'string') return `• ${werk}`;
      return `• ${werk.periode || 'Periode onbekend'}: ${werk.functie || 'Functie'} bij ${werk.werkgever || 'Werkgever'}`;
    }).join('\n');
  }
  
  return 'Arbeidsverleden wordt geanalyseerd';
};

const formatBekwaamheden = (bekwaamheden: any): string => {
  if (!bekwaamheden) return 'Geen bekwaamheden beschikbaar';
  if (typeof bekwaamheden === 'string') return bekwaamheden;
  
  if (typeof bekwaamheden === 'object') {
    const items: string[] = [];
    if (bekwaamheden.computervaardigheden) items.push(`Computer: ${bekwaamheden.computervaardigheden}`);
    if (bekwaamheden.taalvaardigheid) items.push(`Taal: ${bekwaamheden.taalvaardigheid}`);
    if (bekwaamheden.rijbewijs) items.push(`Rijbewijs: ${bekwaamheden.rijbewijs}`);
    if (bekwaamheden.overige) items.push(`Overig: ${bekwaamheden.overige}`);
    
    return items.length > 0 ? items.join('\n') : 'Vaardigheden worden beoordeeld';
  }
  
  return 'Vaardigheden en bekwaamheden worden beoordeeld';
};

const formatGeschiktheidEigenWerk = (geschiktheid: any): string => {
  if (!geschiktheid) return 'Geschiktheid analyse wordt uitgevoerd';
  if (typeof geschiktheid === 'string') return geschiktheid;
  
  if (Array.isArray(geschiktheid) && geschiktheid.length > 0) {
    return geschiktheid.map((item: any) => {
      if (typeof item === 'string') return item;
      return `${item.belastend_aspect || 'Aspect'}: ${item.conclusie || 'Conclusie wordt bepaald'}`;
    }).join('\n\n');
  }
  
  return 'Geschiktheid voor eigen werk wordt geanalyseerd';
};

const formatTrajectplan = (trajectplan: any): string => {
  if (!trajectplan || trajectplan.length === 0) return 'Geen trajectplan beschikbaar';
  if (typeof trajectplan === 'string') return trajectplan;
  
  if (Array.isArray(trajectplan)) {
    return trajectplan.map((item: any, index: number) => {
      if (typeof item === 'string') return `${index + 1}. ${item}`;
      const verantwoordelijke = item.verantwoordelijke ? ` (${item.verantwoordelijke})` : '';
      const termijn = item.termijn ? ` - termijn: ${item.termijn}` : '';
      return `${index + 1}. ${item.actie || 'Actie'}${verantwoordelijke}${termijn}`;
    }).join('\n');
  }
  
  return 'Trajectplan wordt opgesteld';
};

const formatConclusies = (conclusies: any): string => {
  if (!conclusies || conclusies.length === 0) return 'Geen conclusies beschikbaar';
  if (typeof conclusies === 'string') return conclusies;
  
  if (Array.isArray(conclusies)) {
    return conclusies.map((item: any, index: number) => {
      if (typeof item === 'string') return `${index + 1}. ${item}`;
      const toelichting = item.toelichting ? `\n   ${item.toelichting}` : '';
      return `${index + 1}. ${item.conclusie || 'Conclusie'}${toelichting}`;
    }).join('\n\n');
  }
  
  return 'Conclusies worden opgesteld';
};

const formatGesprek = (gesprek: any, type: 'werkgever' | 'werknemer'): string => {
  if (!gesprek) return `Geen gespreksinformatie ${type} beschikbaar`;
  if (typeof gesprek === 'string') return gesprek;
  
  if (typeof gesprek === 'object') {
    const items: string[] = [];
    
    if (type === 'werkgever') {
      if (gesprek.algemeen) items.push(`Algemene informatie: ${gesprek.algemeen}`);
      if (gesprek.visie_functioneren) items.push(`Visie functioneren: ${gesprek.visie_functioneren}`);
      if (gesprek.visie_duurzaamheid) items.push(`Visie duurzaamheid: ${gesprek.visie_duurzaamheid}`);
      if (gesprek.visie_reintegratie) items.push(`Visie reintegratie: ${gesprek.visie_reintegratie}`);
    } else {
      if (gesprek.visie_beperkingen) items.push(`Visie beperkingen: ${gesprek.visie_beperkingen}`);
      if (gesprek.visie_werk) items.push(`Visie werk: ${gesprek.visie_werk}`);
      if (gesprek.visie_reintegratie) items.push(`Visie reintegratie: ${gesprek.visie_reintegratie}`);
    }
    
    return items.length > 0 ? items.join('\n\n') : `Gesprek met ${type} wordt samengevat`;
  }
  
  return `Gesprek met ${type} wordt samengevat`;
};

const downloadReport = async (format: string = 'docx') => {
  if (!reportId.value) return;
  
  loading.value = true;
  try {
    await reportStore.downloadReportAsDocx(reportId.value, 'standaard');
  } catch (error) {
    console.error('Error downloading report:', error);
  } finally {
    loading.value = false;
  }
};

const generateStructuredData = async () => {
  if (!reportId.value) return;
  
  loading.value = true;
  try {
    console.log('Starting AD structure generation...');
    await reportStore.generateADStructure(reportId.value);
    console.log('AD structure generation completed successfully');
  } catch (error) {
    console.error('Error generating structured data:', error);
    alert('Er is een fout opgetreden bij het genereren van de gestructureerde data.');
  } finally {
    loading.value = false;
  }
};

// Load report and related data on mount
onMounted(async () => {
  if (reportId.value) {
    loading.value = true;
    try {
      // Load report first to get case_id
      await reportStore.fetchReport(reportId.value);
      
      // Load profile data for adviseur information
      await profileStore.fetchProfile();
      
      // Load case data if we have case_id from the report
      if (reportStore.currentReport?.case_id) {
        try {
          await caseStore.fetchCase(reportStore.currentReport.case_id);
        } catch (caseError) {
          console.warn('Could not load case data:', caseError);
          // Continue without case data - not critical
        }
      }
      
    } catch (error) {
      console.error('Error loading report data:', error);
    } finally {
      loading.value = false;
    }
  }
});
</script>

<template>
  <div class="clean-report-view">
    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <div class="loading-spinner"></div>
      <p>Rapport wordt geladen...</p>
    </div>

    <!-- Report Content -->
    <div v-else-if="reportData" class="report-container">
      <!-- Header with Action Buttons -->
      <div class="report-header">
        <h1>Arbeidsdeskundig Rapport</h1>
        <div class="header-actions">
          <button 
            @click="generateStructuredData()" 
            :disabled="loading"
            class="action-button generate-button"
            title="Genereer volledige gestructureerde AD rapport data"
          >
            <span class="action-icon">🏗️</span>
            Genereer Structuur
          </button>
          <button 
            @click="downloadReport('docx')" 
            :disabled="loading"
            class="action-button export-button"
          >
            <span class="action-icon">📄</span>
            Exporteren als DOCX
          </button>
        </div>
      </div>

      <!-- Professional AD Report Layout -->
      <div class="report-content">
        <!-- Gegevens Opdrachtgever -->
        <div class="section">
          <h2>Gegevens Opdrachtgever</h2>
          <table class="gegevens-table">
            <tbody>
              <tr>
                <td class="label">Naam bedrijf:</td>
                <td class="value">{{ reportData?.opdrachtgever?.naam_bedrijf || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Contactpersoon:</td>
                <td class="value">{{ reportData?.opdrachtgever?.contactpersoon || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Functie contactpersoon:</td>
                <td class="value">{{ reportData?.opdrachtgever?.functie_contactpersoon || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Adres:</td>
                <td class="value">{{ reportData?.opdrachtgever?.adres || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Postcode:</td>
                <td class="value">{{ reportData?.opdrachtgever?.postcode || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Woonplaats:</td>
                <td class="value">{{ reportData?.opdrachtgever?.woonplaats || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Telefoonnummer:</td>
                <td class="value">{{ reportData?.opdrachtgever?.telefoonnummer || '-' }}</td>
              </tr>
              <tr>
                <td class="label">E-mail:</td>
                <td class="value">{{ reportData?.opdrachtgever?.email || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Aard van het bedrijf:</td>
                <td class="value">{{ reportData?.opdrachtgever?.aard_bedrijf || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Omvang bedrijf:</td>
                <td class="value">{{ reportData?.opdrachtgever?.omvang_bedrijf || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Gegevens Werknemer -->
        <div class="section">
          <h2>Gegevens Werknemer</h2>
          <table class="gegevens-table">
            <tbody>
              <tr>
                <td class="label">Naam:</td>
                <td class="value">{{ reportData?.werknemer?.naam || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Geboortedatum:</td>
                <td class="value">{{ reportData?.werknemer?.geboortedatum || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Adres:</td>
                <td class="value">{{ reportData?.werknemer?.adres || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Postcode:</td>
                <td class="value">{{ reportData?.werknemer?.postcode || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Woonplaats:</td>
                <td class="value">{{ reportData?.werknemer?.woonplaats || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Telefoonnummer:</td>
                <td class="value">{{ reportData?.werknemer?.telefoonnummer || '-' }}</td>
              </tr>
              <tr>
                <td class="label">E-mail:</td>
                <td class="value">{{ reportData?.werknemer?.email || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Gegevens Adviseur -->
        <div class="section">
          <h2>Gegevens Adviseur</h2>
          <table class="gegevens-table">
            <tbody>
              <tr>
                <td class="label">Naam:</td>
                <td class="value">{{ reportData?.adviseur?.naam || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Functie:</td>
                <td class="value">{{ reportData?.adviseur?.functie || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Adres:</td>
                <td class="value">{{ reportData?.adviseur?.adres || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Postcode:</td>
                <td class="value">{{ reportData?.adviseur?.postcode || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Woonplaats:</td>
                <td class="value">{{ reportData?.adviseur?.woonplaats || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Telefoonnummer:</td>
                <td class="value">{{ reportData?.adviseur?.telefoonnummer || '-' }}</td>
              </tr>
              <tr>
                <td class="label">E-mail:</td>
                <td class="value">{{ reportData?.adviseur?.email || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Gegevens Onderzoek -->
        <div class="section">
          <h2>Gegevens Onderzoek</h2>
          <table class="gegevens-table">
            <tbody>
              <tr>
                <td class="label">Datum onderzoek:</td>
                <td class="value">{{ reportData?.onderzoek?.datum_onderzoek || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Datum rapportage:</td>
                <td class="value">{{ reportData?.onderzoek?.datum_rapportage || '-' }}</td>
              </tr>
              <tr>
                <td class="label">Locatie onderzoek:</td>
                <td class="value">{{ reportData?.onderzoek?.locatie_onderzoek || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Samenvatting -->
        <div class="section">
          <h2>Samenvatting</h2>
          
          <div class="subsection">
            <h3>Vraagstelling</h3>
            <ol class="vraagstelling-list">
              <li v-for="(vraag, index) in reportData?.samenvatting_vraagstelling || []" :key="index">
                {{ vraag }}
              </li>
            </ol>
          </div>

          <div class="subsection">
            <h3>Conclusie</h3>
            <div v-for="(conclusie, index) in reportData?.samenvatting_conclusie || []" :key="index" class="content-text">
              {{ conclusie }}
            </div>
          </div>
        </div>

        <!-- 1. Vraagstelling -->
        <div class="section">
          <h2>1. Vraagstelling</h2>
          <div v-for="(item, index) in reportData?.vraagstelling || []" :key="index" class="subsection">
            <h4>{{ item.vraag }}</h4>
            <div class="content-text">{{ item.antwoord }}</div>
          </div>
        </div>

        <!-- 2. Ondernomen activiteiten -->
        <div class="section">
          <h2>2. Ondernomen activiteiten</h2>
          <ul class="activiteiten-list">
            <li v-for="(activiteit, index) in reportData?.ondernomen_activiteiten || []" :key="index">
              {{ activiteit }}
            </li>
          </ul>
        </div>

        <!-- 3. Gegevensverzameling -->
        <div class="section">
          <h2>3. Gegevensverzameling</h2>
          
          <div class="subsection">
            <h3>3.1 Voorgeschiedenis</h3>
            <div class="content-text">{{ reportData?.voorgeschiedenis || 'Geen voorgeschiedenis beschikbaar' }}</div>
          </div>

          <div class="subsection">
            <h3>3.2 Verzuimhistorie</h3>
            <div class="content-text">{{ reportData?.verzuimhistorie || 'Geen verzuimhistorie beschikbaar' }}</div>
          </div>

          <div class="subsection">
            <h3>3.3 Gegevens werknemer</h3>
            <div class="subsubsection">
              <h4>Opleidingen</h4>
              <div class="content-text" style="white-space: pre-line;">{{ formatOpleidingen(reportData?.opleidingen || reportData?.gegevens_werknemer?.opleidingen) }}</div>
            </div>
            <div class="subsubsection">
              <h4>Arbeidsverleden</h4>
              <div class="content-text" style="white-space: pre-line;">{{ formatArbeidsverleden(reportData?.arbeidsverleden_lijst || reportData?.gegevens_werknemer?.arbeidsverleden) }}</div>
            </div>
            <div class="subsubsection">
              <h4>Bekwaamheden</h4>
              <div class="content-text" style="white-space: pre-line;">{{ formatBekwaamheden(reportData?.bekwaamheden || reportData?.gegevens_werknemer?.bekwaamheden) }}</div>
            </div>
          </div>

          <div class="subsection">
            <h3>3.4 Belastbaarheid</h3>
            <div class="content-text">
              <strong>Datum beoordeling:</strong> {{ reportData?.belastbaarheid?.datum_beoordeling || '-' }}<br>
              <strong>Beoordelaar:</strong> {{ reportData?.belastbaarheid?.beoordelaar || '-' }}
            </div>
            
            <h4>FML Rubrieken</h4>
            <table class="fml-table">
              <thead>
                <tr>
                  <th>Rubriek</th>
                  <th>Mate van beperking</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(rubriek, index) in reportData?.belastbaarheid?.fml_rubrieken || []" :key="index">
                  <td>{{ rubriek.rubriek }}</td>
                  <td>{{ rubriek.mate_beperking }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="subsection">
            <h3>3.5 Eigen functie</h3>
            <table class="gegevens-table">
              <tbody>
                <tr>
                  <td class="label">Naam functie:</td>
                  <td class="value">{{ reportData?.eigen_functie?.naam_functie || '-' }}</td>
                </tr>
                <tr>
                  <td class="label">Arbeidspatroon:</td>
                  <td class="value">{{ reportData?.eigen_functie?.arbeidspatroon || '-' }}</td>
                </tr>
                <tr>
                  <td class="label">Overeenkomst:</td>
                  <td class="value">{{ reportData?.eigen_functie?.overeenkomst || '-' }}</td>
                </tr>
                <tr>
                  <td class="label">Aantal uren:</td>
                  <td class="value">{{ reportData?.eigen_functie?.aantal_uren || '-' }}</td>
                </tr>
              </tbody>
            </table>
            <div class="subsubsection">
              <h4>Functieomschrijving</h4>
              <div class="content-text">{{ reportData?.eigen_functie?.functieomschrijving || 'Geen functieomschrijving beschikbaar' }}</div>
            </div>
          </div>

          <div class="subsection">
            <h3>3.6 Gesprek werkgever</h3>
            <div class="content-text" style="white-space: pre-line;">{{ formatGesprek(reportData?.gesprek_werkgever || reportData?.gesprekken?.werkgever, 'werkgever') }}</div>
          </div>

          <div class="subsection">
            <h3>3.7 Gesprek werknemer</h3>
            <div class="content-text" style="white-space: pre-line;">{{ formatGesprek(reportData?.gesprek_werknemer || reportData?.gesprekken?.werknemer, 'werknemer') }}</div>
          </div>

          <div class="subsection" v-if="reportData?.gesprekken?.gezamenlijk">
            <h3>3.8 Gesprek gezamenlijk</h3>
            <div class="content-text">{{ reportData?.gesprekken?.gezamenlijk || 'Geen gezamenlijk gesprek informatie beschikbaar' }}</div>
          </div>
        </div>

        <!-- 4. Visie arbeidsdeskundige -->
        <div class="section">
          <h2>4. Visie arbeidsdeskundige</h2>
          
          <div class="subsection">
            <h3>4.1 Geschiktheid eigen werk</h3>
            <div class="content-text" style="white-space: pre-line;">{{ formatGeschiktheidEigenWerk(reportData?.geschiktheid_eigen_werk) }}</div>
          </div>

          <div class="subsection">
            <h3>4.2 Aanpassing eigen werk</h3>
            <div class="content-text">{{ reportData?.aanpassing_eigen_werk || 'Aanpassingsmogelijkheden worden onderzocht' }}</div>
          </div>

          <div class="subsection">
            <h3>4.3 Geschiktheid ander werk eigen werkgever</h3>
            <div class="content-text">{{ reportData?.geschiktheid_ander_werk_intern || 'Interne alternatieven worden onderzocht' }}</div>
          </div>

          <div class="subsection">
            <h3>4.4 Geschiktheid ander werk andere werkgever</h3>
            <div class="content-text">{{ reportData?.geschiktheid_ander_werk_extern || 'Externe alternatieven worden onderzocht' }}</div>
          </div>

          <div class="subsection">
            <h3>4.5 Visie duurzaamheid</h3>
            <div class="content-text">{{ reportData?.visie_duurzaamheid || 'Duurzaamheidsvisie wordt ontwikkeld' }}</div>
          </div>
        </div>

        <!-- 5. Trajectplan -->
        <div class="section">
          <h2>5. Trajectplan</h2>
          <div class="content-text" style="white-space: pre-line;">{{ formatTrajectplan(reportData?.trajectplan) }}</div>
        </div>

        <!-- 6. Conclusie -->
        <div class="section">
          <h2>6. Conclusie</h2>
          <div class="content-text" style="white-space: pre-line;">{{ formatConclusies(reportData?.conclusies) }}</div>
        </div>

        <!-- 7. Vervolg -->
        <div class="section">
          <h2>7. Vervolg</h2>
          <ul class="vervolg-list">
            <li v-for="(item, index) in reportData?.vervolg || []" :key="index">
              {{ item }}
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-else class="error-container">
      <p>Rapport kon niet worden geladen.</p>
    </div>
  </div>
</template>

<style scoped>
.clean-report-view {
  min-height: 100vh;
  background-color: #f8fafc;
  padding: 2rem 1rem;
}

.loading-container, .error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
  color: #64748b;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e2e8f0;
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.report-container {
  max-width: 210mm; /* A4 width */
  margin: 0 auto;
  background: white;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  border-radius: 8px;
  overflow: hidden;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2rem;
  background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
  color: white;
}

.report-header h1 {
  margin: 0;
  font-size: 1.875rem;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
}

.action-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.875rem;
}

.generate-button {
  background: #10b981;
  color: white;
}

.generate-button:hover:not(:disabled) {
  background: #059669;
  transform: translateY(-1px);
}

.export-button {
  background: white;
  color: #1e40af;
}

.export-button:hover:not(:disabled) {
  background: #f8fafc;
  transform: translateY(-1px);
}

.action-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.action-icon {
  font-size: 1.125rem;
}

.report-content {
  padding: 2rem;
}

.section {
  margin-bottom: 2rem;
}

.section:last-child {
  margin-bottom: 0;
}

.section h2 {
  color: #1e40af;
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #3b82f6;
}

.subsection {
  margin-bottom: 1.5rem;
}

.subsection h3 {
  color: #2563eb;
  font-size: 1.25rem;
  font-weight: 500;
  margin-bottom: 0.75rem;
}

.subsubsection {
  margin-bottom: 1rem;
  padding-left: 1rem;
}

.subsubsection h4 {
  color: #3b82f6;
  font-size: 1.125rem;
  font-weight: 500;
  margin-bottom: 0.5rem;
}

.section h4 {
  color: #3b82f6;
  font-size: 1.125rem;
  font-weight: 500;
  margin-bottom: 0.5rem;
}

.gegevens-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1rem;
}

.gegevens-table td {
  padding: 0.5rem 0.75rem;
  border: 1px solid #e5e7eb;
  vertical-align: top;
}

.gegevens-table .label {
  background-color: #f9fafb;
  font-weight: 500;
  width: 200px;
  color: #374151;
}

.gegevens-table .value {
  background-color: white;
  color: #111827;
}

.vraagstelling-list {
  padding-left: 1.5rem;
  line-height: 1.6;
}

.vraagstelling-list li {
  margin-bottom: 0.5rem;
  color: #374151;
}

.content-text {
  line-height: 1.6;
  color: #374151;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin-bottom: 0.75rem;
}

/* FML Table styling */
.fml-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
  margin-bottom: 1rem;
}

.fml-table th {
  background-color: #1e40af;
  color: white;
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
}

.fml-table td {
  padding: 0.75rem;
  border: 1px solid #e5e7eb;
  vertical-align: top;
}

.fml-table tbody tr:nth-child(even) {
  background-color: #f9fafb;
}

/* List styling */
.activiteiten-list, .trajectplan-list, .vervolg-list {
  padding-left: 1.5rem;
  line-height: 1.6;
}

.activiteiten-list li, .trajectplan-list li, .vervolg-list li {
  margin-bottom: 0.5rem;
  color: #374151;
}

/* Content text styling improvements */
.content-text strong {
  color: #1e40af;
  font-weight: 600;
}

/* Responsive design */
@media (max-width: 768px) {
  .clean-report-view {
    padding: 1rem 0.5rem;
  }
  
  .report-header {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
    padding: 1.5rem;
  }
  
  .header-actions {
    flex-direction: column;
    width: 100%;
  }
  
  .action-button {
    width: 100%;
    justify-content: center;
  }
  
  .report-content {
    padding: 1.5rem;
  }
  
  .gegevens-table .label {
    width: 150px;
  }
  
  .section h2 {
    font-size: 1.25rem;
  }
  
  .subsection h3 {
    font-size: 1.125rem;
  }
}

/* Print styles */
@media print {
  .clean-report-view {
    padding: 0;
    background: white;
  }
  
  .report-container {
    box-shadow: none;
    max-width: none;
    margin: 0;
    border-radius: 0;
  }
  
  .header-actions {
    display: none;
  }
  
  .report-header {
    background: white !important;
    color: #1e40af !important;
    border-bottom: 2px solid #3b82f6;
  }
}
</style>