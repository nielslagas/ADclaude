<template>
  <div class="ad-rapport-template">
    <div class="rapport-container">
      
      <!-- Title Page -->
      <div class="titel-pagina">
        <h1 class="hoofdtitel">Arbeidsdeskundig rapport</h1>
        <div class="persoon-info">
          <h2>{{ reportData.werknemer?.naam || '[Naam werknemer]' }}</h2>
        </div>
        <div class="adviseur-info">
          <p>{{ reportData.adviseur?.naam || 'P.R.J. Peters' }}</p>
          <p>Gecertificeerd Register Arbeidsdeskundige</p>
          <p>Vector Arbeidsdeskundig Advies</p>
        </div>
      </div>

      <!-- Re-integratie onderzoek header -->
      <div class="sectie-header">
        <h1>Arbeidsdeskundig re-integratieonderzoek</h1>
      </div>

      <!-- Gegevens Opdrachtgever -->
      <div class="gegevens-sectie">
        <h2>Gegevens opdrachtgever</h2>
        <table class="gegevens-tabel">
          <tr>
            <td class="label">Naam bedrijf</td>
            <td class="waarde">{{ reportData.opdrachtgever?.naam_bedrijf || '[Bedrijfsnaam]' }}</td>
          </tr>
          <tr>
            <td class="label">Contactpersoon</td>
            <td class="waarde">{{ reportData.opdrachtgever?.contactpersoon || '[Contactpersoon]' }}</td>
          </tr>
          <tr>
            <td class="label">Functie</td>
            <td class="waarde">{{ reportData.opdrachtgever?.functie_contactpersoon || '[Functie]' }}</td>
          </tr>
          <tr>
            <td class="label">Adres (postbus)</td>
            <td class="waarde">{{ reportData.opdrachtgever?.adres || '[Adres]' }}</td>
          </tr>
          <tr>
            <td class="label">PC/Woonplaats</td>
            <td class="waarde">{{ formatPcWoonplaats(reportData.opdrachtgever) }}</td>
          </tr>
          <tr>
            <td class="label">Telefoonnummer</td>
            <td class="waarde">{{ reportData.opdrachtgever?.telefoonnummer || '[Telefoonnummer]' }}</td>
          </tr>
          <tr>
            <td class="label">E-mailadres</td>
            <td class="waarde">
              <a v-if="reportData.opdrachtgever?.email" :href="`mailto:${reportData.opdrachtgever.email}`">
                {{ reportData.opdrachtgever.email }}
              </a>
              <span v-else>[E-mailadres]</span>
            </td>
          </tr>
        </table>
      </div>

      <!-- Gegevens Werknemer -->
      <div class="gegevens-sectie">
        <h2>Gegevens werknemer</h2>
        <table class="gegevens-tabel">
          <tr>
            <td class="label">Naam</td>
            <td class="waarde">{{ reportData.werknemer?.naam || '[Naam werknemer]' }}</td>
          </tr>
          <tr>
            <td class="label">Geboortedatum</td>
            <td class="waarde">{{ reportData.werknemer?.geboortedatum || '[Geboortedatum]' }}</td>
          </tr>
          <tr>
            <td class="label">Adres</td>
            <td class="waarde">{{ reportData.werknemer?.adres || '[Adres]' }}</td>
          </tr>
          <tr>
            <td class="label">PC/Woonplaats</td>
            <td class="waarde">{{ formatPcWoonplaats(reportData.werknemer) }}</td>
          </tr>
          <tr>
            <td class="label">Telefoonnummer</td>
            <td class="waarde">{{ reportData.werknemer?.telefoonnummer || '[Telefoonnummer]' }}</td>
          </tr>
          <tr>
            <td class="label">E-mailadres</td>
            <td class="waarde">
              <a v-if="reportData.werknemer?.email" :href="`mailto:${reportData.werknemer.email}`">
                {{ reportData.werknemer.email }}
              </a>
              <span v-else>[E-mailadres]</span>
            </td>
          </tr>
        </table>
      </div>

      <!-- Gegevens Adviseur -->
      <div class="gegevens-sectie">
        <h2>Gegevens adviseur</h2>
        <table class="gegevens-tabel">
          <tr>
            <td class="label">Naam arbeidsdeskundige</td>
            <td class="waarde">{{ reportData.adviseur?.naam || 'P.R.J. Peters' }}</td>
          </tr>
          <tr>
            <td class="label">Telefoonnummer bedrijf</td>
            <td class="waarde">{{ reportData.adviseur?.telefoonnummer || '06-81034165' }}</td>
          </tr>
        </table>
      </div>

      <!-- Gegevens Onderzoek -->
      <div class="gegevens-sectie">
        <h2>Gegevens onderzoek</h2>
        <table class="gegevens-tabel">
          <tr>
            <td class="label">Datum onderzoek</td>
            <td class="waarde">{{ reportData.onderzoek?.datum_onderzoek || '[Datum onderzoek]' }}</td>
          </tr>
          <tr>
            <td class="label">Datum rapportage</td>
            <td class="waarde">{{ reportData.onderzoek?.datum_rapportage || '[Datum rapportage]' }}</td>
          </tr>
        </table>
      </div>

      <!-- Samenvatting -->
      <div class="hoofdsectie">
        <h1 class="samenvatting-titel"><em>Samenvatting</em></h1>
        
        <h2>Vraagstelling</h2>
        <ul class="vraagstelling-lijst">
          <li v-for="vraag in reportData.samenvatting_vraagstelling" :key="vraag">
            {{ vraag }}
          </li>
          <li v-if="!reportData.samenvatting_vraagstelling?.length">
            Kan werknemer het eigen werk nog uitvoeren?
          </li>
          <li v-if="!reportData.samenvatting_vraagstelling?.length">
            Is het eigen werk met aanpassingen passend te maken?
          </li>
          <li v-if="!reportData.samenvatting_vraagstelling?.length">
            Kan werknemer ander werk bij eigen werkgever uitvoeren?
          </li>
          <li v-if="!reportData.samenvatting_vraagstelling?.length">
            Zijn er mogelijkheden voor externe re-integratie?
          </li>
        </ul>

        <h2>Conclusie</h2>
        <ul class="conclusie-lijst">
          <li v-for="conclusie in reportData.samenvatting_conclusie" :key="conclusie">
            {{ conclusie }}
          </li>
          <li v-if="!reportData.samenvatting_conclusie?.length">
            [Hoofdconclusie 1 - wordt ingevuld op basis van analyse]
          </li>
          <li v-if="!reportData.samenvatting_conclusie?.length">
            [Hoofdconclusie 2 - wordt ingevuld op basis van analyse]
          </li>
        </ul>
      </div>

      <!-- Rapportage -->
      <div class="hoofdsectie">
        <h1 class="rapportage-titel"><em>Rapportage</em></h1>

        <!-- 1. Vraagstelling -->
        <h2>1. Vraagstelling</h2>
        <ul class="vraagstelling-detail">
          <li v-for="item in reportData.vraagstelling" :key="item.vraag">
            {{ item.vraag }}
          </li>
          <li v-if="!reportData.vraagstelling?.length">
            Kan werknemer het eigen werk nog uitvoeren?
          </li>
          <li v-if="!reportData.vraagstelling?.length">
            Is het eigen werk met aanpassingen passend te maken?
          </li>
          <li v-if="!reportData.vraagstelling?.length">
            Kan werknemer ander werk bij eigen werkgever uitvoeren?
          </li>
          <li v-if="!reportData.vraagstelling?.length">
            Zijn er mogelijkheden voor externe re-integratie?
          </li>
        </ul>

        <!-- 2. Ondernomen activiteiten -->
        <h2>2. Ondernomen activiteiten</h2>
        <ul class="activiteiten-lijst">
          <li v-for="activiteit in reportData.ondernomen_activiteiten" :key="activiteit">
            {{ activiteit }}
          </li>
          <li v-if="!reportData.ondernomen_activiteiten?.length">
            [Activiteit 1 - wordt ingevuld op basis van uitgevoerde acties]
          </li>
          <li v-if="!reportData.ondernomen_activiteiten?.length">
            [Activiteit 2 - wordt ingevuld op basis van uitgevoerde acties]
          </li>
        </ul>

        <!-- 3. Gegevensverzameling -->
        <h2>3. Gegevensverzameling</h2>

        <!-- 3.1 Voorgeschiedenis -->
        <h3>3.1 Voorgeschiedenis</h3>
        <p class="voorgeschiedenis-tekst">
          {{ reportData.voorgeschiedenis || '[Voorgeschiedenis wordt ingevuld op basis van documenten en gesprekken]' }}
        </p>

        <h4>Verzuimhistorie</h4>
        <p class="verzuimhistorie-tekst">
          {{ reportData.verzuimhistorie || '[Verzuimhistorie wordt ingevuld op basis van medische informatie]' }}
        </p>

        <!-- 3.2 Gegevens werkgever -->
        <h3>3.2 Gegevens werkgever</h3>
        <table class="bedrijfsinfo-tabel">
          <tr>
            <td class="label">Aard bedrijf</td>
            <td class="waarde">{{ reportData.opdrachtgever?.aard_bedrijf || '[Beschrijving bedrijfsactiviteiten]' }}</td>
          </tr>
          <tr>
            <td class="label">Omvang bedrijf</td>
            <td class="waarde">{{ reportData.opdrachtgever?.omvang_bedrijf || '[Informatie over bedrijfsomvang]' }}</td>
          </tr>
          <tr>
            <td class="label">Aantal werknemers</td>
            <td class="waarde">{{ reportData.opdrachtgever?.aantal_werknemers || '[Aantal medewerkers]' }}</td>
          </tr>
          <tr>
            <td class="label">Functies, aantal werknemers per functie</td>
            <td class="waarde">{{ reportData.opdrachtgever?.functies_expertises || '[Beschrijving functies en expertises]' }}</td>
          </tr>
          <tr>
            <td class="label">Overige informatie</td>
            <td class="waarde">
              <a v-if="reportData.opdrachtgever?.website" :href="reportData.opdrachtgever.website" target="_blank">
                {{ reportData.opdrachtgever.website }}
              </a>
              <span v-else>[Website en overige informatie]</span>
            </td>
          </tr>
        </table>

        <!-- 3.3 Gegevens werknemer -->
        <h3>3.3 Gegevens werknemer</h3>
        
        <!-- Opleidingen tabel -->
        <table v-if="reportData.opleidingen?.length" class="opleidingen-tabel">
          <thead>
            <tr>
              <th>Opleidingen / cursussen</th>
              <th>Richting</th>
              <th>Diploma / certificaat / jaar</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="opl in reportData.opleidingen" :key="opl.naam">
              <td>{{ opl.naam }}</td>
              <td>{{ opl.richting || '-' }}</td>
              <td>{{ opl.diploma_certificaat || '' }} {{ opl.jaar || '' }}</td>
            </tr>
          </tbody>
        </table>

        <!-- Default opleidingen tabel -->
        <table v-else class="opleidingen-tabel">
          <thead>
            <tr>
              <th>Opleidingen / cursussen</th>
              <th>Richting</th>
              <th>Diploma / certificaat / jaar</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>[Opleiding 1]</td>
              <td>[Richting]</td>
              <td>[Diploma/Jaar]</td>
            </tr>
            <tr>
              <td>[Opleiding 2]</td>
              <td>[Richting]</td>
              <td>[Diploma/Jaar]</td>
            </tr>
          </tbody>
        </table>

        <!-- Arbeidsverleden tabel -->
        <table v-if="reportData.arbeidsverleden_lijst?.length" class="arbeidsverleden-tabel">
          <thead>
            <tr>
              <th>Arbeidsverleden van / tot</th>
              <th>Werkgever</th>
              <th>Functie</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="av in reportData.arbeidsverleden_lijst" :key="`${av.werkgever}-${av.periode}`">
              <td>{{ av.periode }}</td>
              <td>{{ av.werkgever }}</td>
              <td>{{ av.functie }}</td>
            </tr>
          </tbody>
        </table>

        <!-- Default arbeidsverleden -->
        <table v-else class="arbeidsverleden-tabel">
          <thead>
            <tr>
              <th>Arbeidsverleden van / tot</th>
              <th>Werkgever</th>
              <th>Functie</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>[Periode]</td>
              <td>[Werkgever]</td>
              <td>[Functie]</td>
            </tr>
          </tbody>
        </table>

        <!-- Bekwaamheden -->
        <h4>Bekwaamheden</h4>
        <table class="bekwaamheden-tabel">
          <tr>
            <td class="label">Computervaardigheden</td>
            <td class="waarde">{{ reportData.bekwaamheden?.computervaardigheden || '[Niveau computervaardigheden]' }}</td>
          </tr>
          <tr>
            <td class="label">Taalvaardigheid</td>
            <td class="waarde">{{ reportData.bekwaamheden?.taalvaardigheid || '[Taalvaardigheden]' }}</td>
          </tr>
          <tr>
            <td class="label">Rijbewijs / categorie</td>
            <td class="waarde">{{ reportData.bekwaamheden?.rijbewijs || '[Rijbewijs informatie]' }}</td>
          </tr>
        </table>

        <!-- 3.4 Belastbaarheid van werknemer -->
        <h3>3.4 Belastbaarheid van werknemer</h3>
        <p v-if="reportData.belastbaarheid">
          De belastbaarheid is op {{ reportData.belastbaarheid.datum_beoordeling }} 
          door {{ reportData.belastbaarheid.beoordelaar }} weergegeven in een 
          functionelemogelijkhedenlijst (FML). Uit de FML van werknemer blijkt dat de 
          belastbaarheid in vergelijking met een gezond persoon tussen 16 en 65 jaar 
          beperkt is op de volgende aspecten:
        </p>
        <p v-else>
          De belastbaarheid is op [datum] door [bedrijfsarts] weergegeven in een 
          functionelemogelijkhedenlijst (FML). Uit de FML van werknemer blijkt dat de 
          belastbaarheid beperkt is op de volgende aspecten:
        </p>

        <!-- FML Tabel -->
        <table class="fml-tabel">
          <thead>
            <tr>
              <th colspan="3">Rubriek</th>
              <th>Mate van beperking</th>
            </tr>
          </thead>
          <tbody>
            <template v-if="reportData.belastbaarheid?.fml_rubrieken?.length">
              <template v-for="rubriek in reportData.belastbaarheid.fml_rubrieken" :key="rubriek.rubriek_nummer">
                <tr v-if="rubriek.mate_beperking !== 'Niet beperkt' || rubriek.items?.length">
                  <td colspan="3">
                    <strong>Rubriek {{ rubriek.rubriek_nummer }}: {{ rubriek.rubriek_naam }}</strong>
                  </td>
                  <td><strong>{{ rubriek.mate_beperking }}</strong></td>
                </tr>
                <tr v-for="item in rubriek.items" :key="item.beschrijving">
                  <td>{{ item.nummer || '' }}</td>
                  <td colspan="2">{{ item.beschrijving }}</td>
                  <td>{{ rubriek.mate_beperking }}</td>
                </tr>
              </template>
            </template>
            <!-- Default FML content -->
            <template v-else>
              <tr>
                <td colspan="3"><strong>Rubriek I: Persoonlijk functioneren</strong></td>
                <td><strong>[Mate van beperking]</strong></td>
              </tr>
              <tr>
                <td>2.</td>
                <td colspan="2">[Beschrijving beperkingen]</td>
                <td>[Mate van beperking]</td>
              </tr>
              <tr>
                <td colspan="3"><strong>Rubriek VI: Werktijden</strong></td>
                <td><strong>[Mate van beperking]</strong></td>
              </tr>
              <tr>
                <td></td>
                <td colspan="2">[Werktijd beperkingen]</td>
                <td>[Mate van beperking]</td>
              </tr>
            </template>
          </tbody>
        </table>

        <p v-if="reportData.belastbaarheid?.prognose" class="prognose">
          <strong>Prognose:</strong> {{ reportData.belastbaarheid.prognose }}
        </p>

        <!-- Meer secties kunnen hier worden toegevoegd... -->
        <!-- Voor nu stoppen we hier om de lengte beheersbaar te houden -->
        
        <div class="meer-secties">
          <p><em>Verdere secties (3.5-7) worden hier toegevoegd...</em></p>
        </div>

      </div>

      <!-- Signature -->
      <div class="ondertekening">
        <p>{{ reportData.adviseur?.naam || 'P.R.J. Peters' }}<br/>
        Gecertificeerd registerarbeidsdeskundige<br/>
        Vector Arbeidsdeskundig Advies</p>
        
        <div class="disclaimer">
          <p><small>
            * Dit rapport is tot stand gekomen na gesprekken met werkgever en werknemer en is gebaseerd op de huidige situatie. 
            Werkgever en werknemer kunnen aan de inhoud van dit rapport geen rechten ontlenen.<br/>
            * Voor actuele informatie over regelingen en voorzieningen verwijzen wij naar de sites van UWV (www.uwv.nl), 
            UWV WERKbedrijf (www.werk.nl) en de Belastingdienst (www.belastingdienst.nl).<br/>
            * Aan digitale versies van het rapport kunnen geen rechten worden ontleend en deze mogen niet aan derden worden verstuurd.
          </small></p>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

// Props
interface Props {
  reportData: any // ADReport structured data
}

const props = defineProps<Props>()

// Helper methods
const formatPcWoonplaats = (contact: any) => {
  if (!contact) return '[Postcode Woonplaats]'
  const pc = contact.postcode || ''
  const plaats = contact.woonplaats || ''
  return `${pc}  ${plaats}`.trim() || '[Postcode Woonplaats]'
}
</script>

<style scoped>
/* Professional Dutch AD Report Styling */
.ad-rapport-template {
  font-family: 'Times New Roman', 'Liberation Serif', serif;
  font-size: 11pt;
  line-height: 1.4;
  color: #1f2937;
  background: white;
  padding: 40px;
  max-width: 800px;
  margin: 0 auto;
}

.rapport-container {
  background: white;
  min-height: 100vh;
}

/* Title page */
.titel-pagina {
  text-align: center;
  margin-bottom: 60px;
  padding: 60px 0;
  border-bottom: 2px solid #1e40af;
}

.hoofdtitel {
  font-size: 24pt;
  font-weight: bold;
  color: #1e40af;
  text-transform: uppercase;
  letter-spacing: 2px;
  margin-bottom: 40px;
}

.persoon-info h2 {
  font-size: 18pt;
  color: #1f2937;
  margin: 30px 0;
}

.adviseur-info {
  margin-top: 60px;
  font-size: 12pt;
  color: #374151;
}

.adviseur-info p {
  margin: 8px 0;
}

/* Section headers */
.sectie-header h1 {
  font-size: 18pt;
  font-weight: bold;
  color: #1e40af;
  text-transform: uppercase;
  text-align: center;
  margin: 40px 0 30px 0;
  letter-spacing: 1px;
}

.hoofdsectie h1 {
  font-size: 16pt;
  font-weight: bold;
  color: #1e40af;
  text-align: center;
  margin: 40px 0 25px 0;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.hoofdsectie h2 {
  font-size: 14pt;
  font-weight: bold;
  color: #1e40af;
  margin: 30px 0 15px 0;
  border-bottom: 2px solid #1e40af;
  padding-bottom: 5px;
}

.hoofdsectie h3 {
  font-size: 12pt;
  font-weight: bold;
  color: #2563eb;
  margin: 25px 0 12px 0;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 3px;
}

.hoofdsectie h4 {
  font-size: 11pt;
  font-weight: bold;
  font-style: italic;
  color: #3b82f6;
  margin: 20px 0 8px 0;
}

/* Gegevens sections */
.gegevens-sectie {
  margin-bottom: 30px;
}

.gegevens-sectie h2 {
  font-size: 14pt;
  font-weight: bold;
  color: #1e40af;
  margin-bottom: 15px;
  border-bottom: 2px solid #1e40af;
  padding-bottom: 5px;
}

/* Table styling */
table {
  width: 100%;
  border-collapse: collapse;
  margin: 15px 0 25px 0;
  border: 2px solid #1e40af;
}

.gegevens-tabel td,
.bekwaamheden-tabel td,
.bedrijfsinfo-tabel td {
  padding: 12px 15px;
  border: 1px solid #1e40af;
  vertical-align: top;
}

.gegevens-tabel td.label,
.bekwaamheden-tabel td.label,
.bedrijfsinfo-tabel td.label {
  background-color: #eff6ff;
  font-weight: bold;
  color: #1e40af;
  width: 40%;
}

.gegevens-tabel td.waarde,
.bekwaamheden-tabel td.waarde,
.bedrijfsinfo-tabel td.waarde {
  background-color: white;
}

/* Data tables */
.opleidingen-tabel,
.arbeidsverleden-tabel,
.fml-tabel {
  margin: 20px 0;
  border: 2px solid #1e40af;
}

.opleidingen-tabel th,
.arbeidsverleden-tabel th,
.fml-tabel th {
  background-color: #1e40af;
  color: white;
  font-weight: bold;
  text-align: left;
  padding: 12px 15px;
  border: 1px solid #1e40af;
}

.opleidingen-tabel td,
.arbeidsverleden-tabel td,
.fml-tabel td {
  padding: 10px 15px;
  border: 1px solid #1e40af;
  vertical-align: top;
  background-color: white;
}

.fml-tabel tr:nth-child(even) td {
  background-color: #f8fafc;
}

/* Lists */
.vraagstelling-lijst,
.conclusie-lijst,
.vraagstelling-detail,
.activiteiten-lijst {
  margin: 15px 0;
  padding-left: 25px;
}

.vraagstelling-lijst li,
.conclusie-lijst li,
.vraagstelling-detail li,
.activiteiten-lijst li {
  margin: 8px 0;
  line-height: 1.5;
}

/* Text content */
.voorgeschiedenis-tekst,
.verzuimhistorie-tekst {
  margin: 15px 0;
  text-align: justify;
  line-height: 1.5;
}

.prognose {
  margin: 20px 0;
  font-style: italic;
}

/* Footer */
.ondertekening {
  margin-top: 60px;
  padding-top: 30px;
  border-top: 1px solid #e5e7eb;
}

.ondertekening p {
  margin-bottom: 40px;
  line-height: 1.6;
}

.disclaimer {
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid #e5e7eb;
  font-size: 9pt;
  color: #6b7280;
  font-style: italic;
}

/* Temporary styling for incomplete sections */
.meer-secties {
  background-color: #fef3c7;
  border: 1px solid #f59e0b;
  border-radius: 4px;
  padding: 20px;
  margin: 40px 0;
  text-align: center;
  color: #92400e;
  font-style: italic;
}

/* Links */
a {
  color: #1e40af;
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

/* Print styles */
@media print {
  .ad-rapport-template {
    padding: 0;
    font-size: 10pt;
  }
  
  .titel-pagina {
    page-break-after: always;
  }
  
  .hoofdsectie {
    page-break-inside: avoid;
  }
  
  table {
    page-break-inside: avoid;
  }
}
</style>