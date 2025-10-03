<template>
  <div class="static-ad-report" v-if="reportData">
    <!-- Report Header - Professional Dutch Style -->
    <div class="report-header">
      <h1>Arbeidsdeskundig rapport</h1>
      <h2>{{ reportData.werknemer?.naam || '[Naam werknemer]' }}</h2>
      
      <div class="advisor-info">
        <p class="advisor-name"><strong>{{ reportData.adviseur?.naam || 'Patrick Peters' }}</strong></p>
        <p class="advisor-title">{{ reportData.adviseur?.titel || 'Gecertificeerd Register Arbeidsdeskundige' }}</p>
        <p class="advisor-company">{{ reportData.adviseur?.bedrijf || 'Vector Arbeidsdeskundig Advies' }}</p>
      </div>
    </div>

    <!-- Title Section -->
    <div class="title-section">
      <h2 class="section-title">Arbeidsdeskundig re-integratieonderzoek</h2>
    </div>

    <!-- Gegevens Opdrachtgever -->
    <div class="section">
      <h3>Gegevens opdrachtgever</h3>
      <table class="data-table">
        <tbody>
          <tr>
            <th>Naam bedrijf</th>
            <td>{{ reportData.werkgever?.naam || '[Bedrijfsnaam]' }}</td>
          </tr>
          <tr>
            <th>Contactpersoon</th>
            <td>{{ reportData.werkgever?.contactpersoon || '[Contactpersoon]' }}</td>
          </tr>
          <tr>
            <th>Functie</th>
            <td>{{ reportData.werkgever?.functie_contactpersoon || '[Functie contactpersoon]' }}</td>
          </tr>
          <tr>
            <th>Adres (postbus)</th>
            <td>{{ reportData.werkgever?.adres || '[Adres]' }}</td>
          </tr>
          <tr>
            <th>PC/Woonplaats</th>
            <td>{{ reportData.werkgever?.postcode_plaats || '[Postcode Plaats]' }}</td>
          </tr>
          <tr>
            <th>Telefoonnummer</th>
            <td>{{ reportData.werkgever?.telefoonnummer || '[Telefoonnummer]' }}</td>
          </tr>
          <tr>
            <th>E-mailadres</th>
            <td>{{ reportData.werkgever?.email || '[E-mailadres]' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Gegevens Werknemer -->
    <div class="section">
      <h3>Gegevens werknemer</h3>
      <table class="data-table">
        <tbody>
          <tr>
            <th>Naam</th>
            <td>{{ reportData.werknemer?.naam || '[Naam werknemer]' }}</td>
          </tr>
          <tr>
            <th>Geboortedatum</th>
            <td>{{ reportData.werknemer?.geboortedatum || '[Geboortedatum]' }}</td>
          </tr>
          <tr>
            <th>Adres</th>
            <td>{{ reportData.werknemer?.adres || '[Adres]' }}</td>
          </tr>
          <tr>
            <th>PC/Woonplaats</th>
            <td>{{ reportData.werknemer?.postcode_plaats || '[Postcode Plaats]' }}</td>
          </tr>
          <tr>
            <th>Telefoonnummer</th>
            <td>{{ reportData.werknemer?.telefoonnummer || '[Telefoonnummer]' }}</td>
          </tr>
          <tr>
            <th>E-mailadres</th>
            <td>{{ reportData.werknemer?.email || '[E-mailadres]' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Gegevens Adviseur -->
    <div class="section">
      <h3>Gegevens adviseur</h3>
      <table class="data-table">
        <tbody>
          <tr>
            <th>Naam arbeidsdeskundige</th>
            <td>{{ reportData.adviseur?.naam || '[Naam adviseur]' }}</td>
          </tr>
          <tr>
            <th>Telefoonnummer bedrijf</th>
            <td>{{ reportData.adviseur?.telefoonnummer || '[Telefoonnummer]' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Gegevens Onderzoek -->
    <div class="section">
      <h3>Gegevens onderzoek</h3>
      <table class="data-table">
        <tbody>
          <tr>
            <th>Datum onderzoek</th>
            <td>{{ reportData.onderzoek?.datum_onderzoek || '[Datum onderzoek]' }}</td>
          </tr>
          <tr>
            <th>Datum rapportage</th>
            <td>{{ reportData.onderzoek?.datum_rapportage || '[Datum rapportage]' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Samenvatting -->
    <div class="section">
      <h3><em>Samenvatting</em></h3>
      
      <h4>Vraagstelling</h4>
      <ul class="question-list">
        <li>{{ reportData.samenvatting?.vraagstelling?.[0] || 'Kan werknemer het eigen werk bij de eigen werkgever nog uitvoeren?' }}</li>
        <li>{{ reportData.samenvatting?.vraagstelling?.[1] || 'Zo nee, is het eigen werk met behulp van aanpassingen passend te maken?' }}</li>
        <li>{{ reportData.samenvatting?.vraagstelling?.[2] || 'Zo nee, kan werknemer ander werk bij de eigen werkgever uitvoeren?' }}</li>
        <li>{{ reportData.samenvatting?.vraagstelling?.[3] || 'Zo nee, zijn er mogelijkheden om werknemer naar ander werk te begeleiden en is een vervolgtraject gewenst?' }}</li>
      </ul>

      <h4>Conclusie</h4>
      <ul class="conclusion-list">
        <li>{{ reportData.samenvatting?.conclusie?.[0] || 'Werknemer is op dit moment nog ongeschikt voor het eigen werk bij de eigen werkgever.' }}</li>
        <li>{{ reportData.samenvatting?.conclusie?.[1] || 'Het eigen werk is mogelijk passend te maken door voorzieningen of aanpassingen.' }}</li>
        <li>{{ reportData.samenvatting?.conclusie?.[2] || 'Werknemer is niet geschikt voor ander werk bij de eigen werkgever.' }}</li>
        <li>{{ reportData.samenvatting?.conclusie?.[3] || 'Werknemer is geschikt voor passende arbeid op de arbeidsmarkt.' }}</li>
      </ul>
    </div>

    <!-- Rapportage -->
    <div class="section">
      <h3><em>Rapportage</em></h3>
      
      <!-- 1. Vraagstelling -->
      <div class="subsection">
        <h4>1. Vraagstelling</h4>
        <ul class="question-list">
          <li>{{ reportData.rapportage?.vraagstelling?.[0] || 'Kan werknemer het eigen werk bij de eigen werkgever nog uitvoeren?' }}</li>
          <li>{{ reportData.rapportage?.vraagstelling?.[1] || 'Zo nee, is het eigen werk met behulp van aanpassingen passend te maken?' }}</li>
          <li>{{ reportData.rapportage?.vraagstelling?.[2] || 'Zo nee, kan werknemer ander werk bij de eigen werkgever uitvoeren?' }}</li>
          <li>{{ reportData.rapportage?.vraagstelling?.[3] || 'Zo nee, zijn er mogelijkheden om werknemer naar ander werk te begeleiden en is een vervolgtraject gewenst?' }}</li>
        </ul>
      </div>

      <!-- 2. Ondernomen activiteiten -->
      <div class="subsection">
        <h4>2. Ondernomen activiteiten</h4>
        <ul class="activity-list">
          <li v-for="(activiteit, index) in reportData.rapportage?.activiteiten || defaultActiviteiten" :key="index">
            {{ activiteit }}
          </li>
        </ul>
      </div>

      <!-- 3. Gegevensverzameling -->
      <div class="subsection">
        <h4>3. Gegevensverzameling</h4>
        
        <!-- 3.1 Voorgeschiedenis -->
        <div class="subsubsection">
          <h5>3.1 Voorgeschiedenis</h5>
          <p>{{ reportData.gegevensverzameling?.voorgeschiedenis || '[Voorgeschiedenis tekst]' }}</p>
          
          <h6>Verzuimhistorie</h6>
          <p>{{ reportData.gegevensverzameling?.verzuimhistorie || '[Verzuimhistorie tekst]' }}</p>
        </div>

        <!-- 3.2 Gegevens werkgever -->
        <div class="subsubsection">
          <h5>3.2 Gegevens werkgever</h5>
          <table class="data-table">
            <tbody>
              <tr>
                <th>Aard bedrijf</th>
                <td>{{ reportData.gegevensverzameling?.werkgever?.aard_bedrijf || '[Aard bedrijf]' }}</td>
              </tr>
              <tr>
                <th>Omvang bedrijf</th>
                <td>{{ reportData.gegevensverzameling?.werkgever?.omvang_bedrijf || '[Omvang bedrijf]' }}</td>
              </tr>
              <tr>
                <th>Aantal werknemers</th>
                <td>{{ reportData.gegevensverzameling?.werkgever?.aantal_werknemers || '[Aantal werknemers]' }}</td>
              </tr>
              <tr>
                <th>Functies, aantal werknemers per functie</th>
                <td>{{ reportData.gegevensverzameling?.werkgever?.functies_beschrijving || '[Functies beschrijving]' }}</td>
              </tr>
              <tr>
                <th>Overige informatie</th>
                <td>{{ reportData.gegevensverzameling?.werkgever?.overige_informatie || '[Website/overige info]' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 3.3 Gegevens werknemer -->
        <div class="subsubsection">
          <h5>3.3 Gegevens werknemer</h5>
          
          <!-- Opleidingen tabel -->
          <table class="education-table">
            <thead>
              <tr>
                <th>Opleidingen / cursussen</th>
                <th>Richting</th>
                <th>Diploma / certificaat / jaar</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(opleiding, index) in reportData.gegevensverzameling?.werknemer?.opleidingen || defaultOpleidingen" :key="index">
                <td>{{ opleiding.naam }}</td>
                <td>{{ opleiding.richting }}</td>
                <td>{{ opleiding.diploma_jaar }}</td>
              </tr>
            </tbody>
          </table>

          <!-- Arbeidsverleden tabel -->
          <table class="work-history-table">
            <thead>
              <tr>
                <th>Arbeidsverleden van / tot</th>
                <th>Werkgever</th>
                <th>Functie</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(werk, index) in reportData.gegevensverzameling?.werknemer?.arbeidsverleden || defaultArbeidsverleden" :key="index">
                <td>{{ werk.periode }}</td>
                <td>{{ werk.werkgever }}</td>
                <td>{{ werk.functie }}</td>
              </tr>
            </tbody>
          </table>

          <!-- Bekwaamheden tabel -->
          <table class="skills-table">
            <thead>
              <tr>
                <th>Bekwaamheden</th>
                <th></th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Computervaardigheden</td>
                <td>{{ reportData.gegevensverzameling?.werknemer?.computervaardigheden || 'Goed' }}</td>
                <td></td>
              </tr>
              <tr>
                <td>Taalvaardigheid</td>
                <td>{{ reportData.gegevensverzameling?.werknemer?.taalvaardigheid || 'Goed' }}</td>
                <td></td>
              </tr>
              <tr>
                <td>Rijbewijs / categorie</td>
                <td>{{ reportData.gegevensverzameling?.werknemer?.rijbewijs || '[Rijbewijs informatie]' }}</td>
                <td></td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 3.4 Belastbaarheid werknemer -->
        <div class="subsubsection">
          <h5>3.4 Belastbaarheid van werknemer</h5>
          <p>{{ reportData.gegevensverzameling?.belastbaarheid?.beschrijving || '[Belastbaarheid beschrijving van bedrijfsarts]' }}</p>

          <!-- FML Tabel -->
          <table class="fml-table">
            <thead>
              <tr>
                <th></th>
                <th></th>
                <th></th>
                <th>Mate van beperking</th>
              </tr>
            </thead>
            <tbody>
              <!-- Rubriek I -->
              <tr class="section-header">
                <td><strong>Rubriek I: Persoonlijk functioneren</strong></td>
                <td></td>
                <td></td>
                <td><strong>Mate van beperking</strong></td>
              </tr>
              <tr v-for="(item, index) in reportData.gegevensverzameling?.belastbaarheid?.persoonlijk_functioneren || defaultPersoonlijkFunctioneren" :key="index">
                <td>{{ item.nummer }}</td>
                <td>{{ item.beschrijving }}</td>
                <td></td>
                <td>{{ item.mate_beperking }}</td>
              </tr>

              <!-- Rubriek II -->
              <tr class="section-header">
                <td><strong>Rubriek II: Sociaal functioneren</strong></td>
                <td></td>
                <td></td>
                <td><strong>Mate van beperking</strong></td>
              </tr>
              <tr v-for="(item, index) in reportData.gegevensverzameling?.belastbaarheid?.sociaal_functioneren || defaultSociaalFunctioneren" :key="index">
                <td>{{ item.nummer }}</td>
                <td>{{ item.beschrijving }}</td>
                <td></td>
                <td>{{ item.mate_beperking }}</td>
              </tr>

              <!-- Overige rubrieken -->
              <tr class="section-header">
                <td><strong>Rubriek III: Aanpassing aan fysieke omgevingseisen</strong></td>
                <td></td>
                <td></td>
                <td>{{ reportData.gegevensverzameling?.belastbaarheid?.fysieke_omgeving || 'Niet beperkt' }}</td>
              </tr>
              <tr class="section-header">
                <td><strong>Rubriek IV: Dynamische handelingen</strong></td>
                <td></td>
                <td></td>
                <td>{{ reportData.gegevensverzameling?.belastbaarheid?.dynamische_handelingen || 'Niet beperkt' }}</td>
              </tr>
              <tr class="section-header">
                <td><strong>Rubriek V: Statische houdingen</strong></td>
                <td></td>
                <td></td>
                <td>{{ reportData.gegevensverzameling?.belastbaarheid?.statische_houdingen || 'Niet beperkt' }}</td>
              </tr>
              <tr class="section-header">
                <td><strong>Rubriek VI: Werktijden</strong></td>
                <td>{{ reportData.gegevensverzameling?.belastbaarheid?.werktijden || 'Er zijn beperkingen in werktijden...' }}</td>
                <td></td>
                <td></td>
              </tr>
            </tbody>
          </table>

          <p>{{ reportData.gegevensverzameling?.belastbaarheid?.prognose || '[Prognose tekst van bedrijfsarts]' }}</p>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="report-footer">
      <div class="signature-section">
        <p><strong>{{ reportData.adviseur?.naam || '[Naam arbeidsdeskundige]' }}</strong></p>
        <p>{{ reportData.adviseur?.titel || 'Gecertificeerd registerarbeidsdeskundige' }}</p>
        <p>{{ reportData.adviseur?.bedrijf || '[Bedrijfsnaam]' }}</p>
      </div>
      
      <div class="disclaimer">
        <ul>
          <li>Dit rapport is tot stand gekomen na gesprekken met werkgever en werknemer en is gebaseerd op de huidige situatie. Werkgever en werknemer kunnen aan de inhoud van dit rapport geen rechten ontlenen.</li>
          <li>Voor actuele informatie over regelingen en voorzieningen verwijzen wij naar de sites van UWV (www.uwv.nl), UWV WERKbedrijf (www.werk.nl) en de Belastingdienst (www.belastingdienst.nl).</li>
          <li>Aan digitale versies van het rapport kunnen geen rechten worden ontleend en deze mogen niet aan derden worden verstuurd.</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

// Props
interface Props {
  reportData: any
}

const props = defineProps<Props>()

// Default data voor lege velden
const defaultActiviteiten = [
  'Voorbereiding (dossieronderzoek) op [datum].',
  'Bestuderen informatie van de bedrijfsarts op [datum].',
  'Overleg met bedrijfsarts op [datum].',
  'Gesprek met werknemer op [datum] op de werklocatie.',
  'Gesprek met werkgever op [datum] op de werklocatie.',
  'Overleg met werknemer en werkgever gezamenlijk op [datum].',
  'Rapportage opstellen op [datum].'
]

const defaultOpleidingen = [
  { naam: '[Opleiding]', richting: '[Richting]', diploma_jaar: '[Jaar]' },
  { naam: '[Aanvullende cursussen]', richting: '[Richting]', diploma_jaar: '[Jaar]' }
]

const defaultArbeidsverleden = [
  { periode: '[Van/tot datum]', werkgever: '[Werkgever]', functie: '[Functie]' }
]

const defaultPersoonlijkFunctioneren = [
  {
    nummer: '2.',
    beschrijving: 'Verdelen van de aandacht: [beschrijving van beperkingen]',
    mate_beperking: 'Beperkt'
  }
]

const defaultSociaalFunctioneren = [
  {
    nummer: '6.',
    beschrijving: 'Emotionele problemen van anderen hanteren: [beschrijving van beperkingen]',
    mate_beperking: 'Beperkt'
  }
]
</script>

<style scoped>
.static-ad-report {
  max-width: 210mm;
  margin: 0 auto;
  padding: 25mm 20mm 20mm 20mm;
  font-family: 'Times New Roman', serif;
  font-size: 11pt;
  line-height: 1.4;
  color: #000;
  background: white;
}

.report-header {
  text-align: left;
  margin-bottom: 30px;
  padding-bottom: 0;
  page-break-after: always;
}

.report-header h1 {
  font-size: 14pt;
  font-weight: bold;
  margin-bottom: 8px;
  color: #000;
  text-align: left;
}

.report-header h2 {
  font-size: 13pt;
  font-weight: normal;
  margin-bottom: 40px;
  color: #000;
  text-align: left;
}

.advisor-info {
  margin: 80px 0 40px 0;
  text-align: left;
}

.advisor-name {
  font-size: 11pt;
  margin-bottom: 4px;
  color: #000;
}

.advisor-title {
  font-size: 11pt;
  margin-bottom: 4px;
  color: #000;
}

.advisor-company {
  font-size: 11pt;
  margin-bottom: 20px;
  color: #000;
}

.title-section {
  margin: 40px 0 30px 0;
}

.section-title {
  font-size: 14pt;
  font-weight: bold;
  color: #000;
  text-align: left;
  margin-bottom: 30px;
}

.section {
  margin-bottom: 32px;
  page-break-inside: avoid;
}

.section h3 {
  font-size: 12pt;
  font-weight: bold;
  margin-bottom: 12px;
  color: #000;
  text-align: left;
}

.subsection {
  margin-bottom: 24px;
  margin-left: 0;
}

.subsection h4 {
  font-size: 12pt;
  font-weight: bold;
  margin-bottom: 12px;
  margin-top: 20px;
  color: #000;
}

.subsubsection {
  margin-bottom: 20px;
  margin-left: 0;
}

.subsubsection h5 {
  font-size: 11pt;
  font-weight: bold;
  margin-bottom: 10px;
  margin-top: 16px;
  color: #000;
  text-decoration: underline;
}

.subsubsection h6 {
  font-size: 11pt;
  font-weight: bold;
  margin-bottom: 8px;
  margin-top: 12px;
  color: #000;
  font-style: italic;
}

/* Tables - Exact PDF Style */
.data-table,
.education-table,
.work-history-table,
.skills-table,
.fml-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 20px;
  font-size: 11pt;
}

.data-table th,
.data-table td {
  border: 1px solid #000;
  padding: 6px 8px;
  text-align: left;
  vertical-align: top;
  line-height: 1.3;
}

.data-table th {
  background-color: white;
  font-weight: normal;
  width: 30%;
  text-align: left;
}

.data-table td {
  background-color: white;
  width: 70%;
}

/* Education and Work History Tables */
.education-table th,
.education-table td,
.work-history-table th,
.work-history-table td,
.skills-table th,
.skills-table td {
  border: 1px solid #000;
  padding: 6px 8px;
  text-align: left;
  vertical-align: top;
  line-height: 1.3;
  background-color: white;
}

.education-table th,
.work-history-table th,
.skills-table th {
  font-weight: bold;
  background-color: white;
}

/* FML Table - Special Formatting */
.fml-table th,
.fml-table td {
  border: 1px solid #000;
  padding: 6px 8px;
  text-align: left;
  vertical-align: top;
  line-height: 1.3;
  background-color: white;
}

.fml-table .section-header td {
  background-color: #f0f0f0;
  font-weight: bold;
  text-align: left;
  font-size: 11pt;
}

/* Lists */
.question-list,
.conclusion-list,
.activity-list {
  padding-left: 0;
  list-style: none;
}

.question-list li,
.conclusion-list li,
.activity-list li {
  margin-bottom: 4px;
  padding-left: 0;
}

.question-list li::before,
.conclusion-list li::before,
.activity-list li::before {
  content: "• ";
  font-weight: bold;
  margin-right: 4px;
}

/* Footer */
.report-footer {
  margin-top: 40px;
  border-top: 1px solid #ccc;
  padding-top: 20px;
}

.signature-section {
  margin-bottom: 20px;
}

.signature-section p {
  margin: 2px 0;
}

.disclaimer ul {
  font-size: 10pt;
  line-height: 1.3;
  padding-left: 0;
  list-style: none;
}

.disclaimer li {
  margin-bottom: 8px;
  padding-left: 0;
}

.disclaimer li::before {
  content: "• ";
  font-weight: bold;
  margin-right: 4px;
}

/* Print styles */
@media print {
  .static-ad-report {
    margin: 0;
    padding: 15mm;
    box-shadow: none;
  }
  
  .section {
    page-break-inside: avoid;
  }
}
</style>