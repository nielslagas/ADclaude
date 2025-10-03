# TESTBESTANDEN VOOR AI-ARBEIDSDESKUNDIGE SYSTEEM

## Overzicht Testcase: J. van der Berg

Deze testbestanden vormen een complete, realistische casus van een arbeidsdeskundige beoordeling voor een 46-jarige administratief medewerker met lumbale rugklachten na een werkongeval.

## 📁 Beschikbare Testdocumenten

### Medische Documentatie
1. **`medisch_rapport.txt`** - Uitgebreid medisch rapport van arbeidsgeneeskundige
   - Diagnose: Hernia L4-L5 met radiculopathie
   - Functionele capaciteiten
   - Behandelplan en prognose

2. **`fysiotherapie_rapport.txt`** - Gedetailleerd fysiotherapie evaluatierapport
   - 16 weken behandelhistorie
   - Progressie en huidige status
   - Werkgerichte aanbevelingen

### Werkgever Informatie
3. **`functieomschrijving_werkgever.txt`** - Complete functieomschrijving
   - Werkzaamheden en verantwoordelijkheden
   - Arbeidsomstandigheden
   - Aanpassingsmogelijkheden
   - Werkgever perspectief

### Werknemer Informatie  
4. **`intake_formulier_werknemer.txt`** - Uitgebreide intake werknemer
   - Persoonlijke situatie en klachten
   - Impact op dagelijks leven
   - Wensen en verwachtingen

5. **`eerdere_werkervaring.txt`** - Carrière overzicht
   - 17 jaar werkervaring
   - Competenties en prestaties
   - Toekomstwensen

### Audio Transcripties (voor inspreken)
6. **`gesprek_werkgever_transcriptie.txt`** - 45 minuten gesprek werkgever
7. **`gesprek_werknemer_transcriptie.txt`** - 60 minuten gesprek werknemer  
8. **`gezamenlijk_gesprek_transcriptie.txt`** - 50 minuten driepartijengesprek

## 🎯 Gebruik van de Testbestanden

### Voor Document Upload
1. Upload de .txt bestanden via de frontend interface
2. Systeem zal ze automatisch verwerken en classificeren
3. Documenten worden gekoppeld aan de testcase

### Voor Audio Functionaliteit
1. Lees de transcriptie bestanden hardop in
2. Upload als audio bestand via audio recorder
3. Systeem transcribeert en verwerkt de content
4. Audio wordt geïntegreerd in het rapport

### Voor Rapport Generatie
Na upload van alle documenten kan het Enhanced AD rapport worden gegenereerd met:
- 22 professionele secties
- FML rubrieken (6 categorieën)
- Geïntegreerde medische en functionele informatie
- Gesprekverslagen van alle partijen

## ✅ Verwachte Resultaten

Het systeem zou moeten kunnen genereren:

### 1. Vraagstelling (4 standaardvragen)
- Geschiktheid eigen functie bij eigen werkgever
- Geschiktheid na aanpassing functie/werkplek
- Geschiktheid andere functies eigen werkgever  
- Geschiktheid andere functies andere werkgever

### 2. FML Rubrieken Assessment
- I. Persoonlijk functioneren: Niet beperkt
- II. Sociaal functioneren: Niet beperkt
- III. Aanpassing fysieke omgeving: Beperkt (ergonomie)
- IV. Dynamische handelingen: Beperkt (tillen >8kg)
- V. Statische houdingen: Beperkt (zitten >45 min)
- VI. Werktijden: Niet beperkt

### 3. Concrete Aanbevelingen
- Geleidelijke werkhervatting 4→6→8 uur
- Ergonomische werkplekaanpassingen
- Geen tillen >8-10 kg
- Pauzes elke 45-60 minuten

## 📊 Kwaliteitsvalidatie

De testcase zou moeten resulteren in:
- **Completeness Score**: 100%
- **Sections Generated**: 22/22
- **FML Generated**: Ja (6 rubrieken)
- **Quality Metrics**: Alle checkpoints gehaald

## 🔄 Test Scenario's

### Scenario 1: Basis Workflow
1. Nieuwe case aanmaken: "J. van der Berg - Rugklachten"
2. Upload medische documenten (2 bestanden)
3. Upload werkgever informatie (1 bestand)
4. Upload werknemer informatie (2 bestanden)
5. Genereer Enhanced AD rapport
6. Controleer kwaliteit en volledigheid

### Scenario 2: Met Audio Integration
1. Basis workflow (stappen 1-4)
2. Record audio van gesprek transcripties (3 bestanden)
3. Upload audio bestanden
4. Wacht op transcriptie
5. Genereer Enhanced AD rapport met audio data
6. Vergelijk resultaat met scenario 1

### Scenario 3: Iteratieve Verbetering
1. Genereer eerste rapport
2. Upload aanvullende documenten
3. Regenereer rapport
4. Analyseer verschillen en verbeteringen

## 🎬 Audio Opname Instructies

Voor realistische audio tests:
1. **Spreek rustig en duidelijk**
2. **Imiteer verschillende stemmen** voor werkgever/werknemer
3. **Inclusief pauzes en "eh" geluiden** voor realisme
4. **Varieer tempo** zoals in echte gesprekken
5. **Record in stille omgeving** voor beste kwaliteit

## 📝 Verwachte Rapport Kwaliteit

Het gegenereerde rapport moet professioneel zijn met:
- Nederlandse arbeidsdeskundige terminologie
- Objectieve, feitelijke taal
- Logische onderbouwing conclusies
- Referenties naar medische bevindingen
- Concrete, uitvoerbare aanbevelingen
- Consistentie tussen alle secties

Deze testcase dekt alle aspecten van een realistische arbeidsdeskundige beoordeling en test alle functies van het Enhanced AD systeem.