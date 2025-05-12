# AD-Rapport Generator

Een AI-ondersteunde applicatie voor het genereren van arbeidsdeskundige rapportages, gebruikmakend van Retrieval-Augmented Generation (RAG) met Google Gemini 1.5 Pro.

## Projectoverzicht

De AD-Rapport Generator helpt arbeidsdeskundigen bij het opstellen van gestructureerde en consistente rapportages door analyse van geüploade documenten. De applicatie combineert moderne AI met domeinkennis om essentiële secties van arbeidsdeskundige rapporten te genereren, waardoor arbeidsdeskundigen zich kunnen concentreren op analyse en beoordeling.

### Belangrijkste Kenmerken

- **Case Management**: Organiseer werk in individuele cases
- **Document Upload**: Upload en verwerk .docx en .txt documenten
- **AI-Ondersteunde Secties**: Genereer concept-secties voor uw rapport
- **Beveiligd & AVG-Compliant**: Veilige verwerking van gevoelige persoonsgegevens

## Technische Stack

### Backend
- **Framework**: Python/FastAPI/Celery
- **Database**: PostgreSQL met pgvector voor vector embeddings
- **AI**: Google Gemini 1.5 Pro API
- **Asynchrone Verwerking**: Celery met Redis broker

### Frontend
- **Framework**: Vue.js 3 met TypeScript
- **State Management**: Pinia
- **Router**: Vue Router
- **API Client**: Axios

## Lokale Ontwikkeling

### Vereisten
- Docker en Docker Compose
- Node.js 16+
- API keys voor een van de volgende LLM providers:
  - Google AI API key
  - OpenAI API key
  - Anthropic API key

### Installatie met Lokale Database

1. Clone de repository:
```bash
git clone <repository-url>
cd ai-arbeidsdeskundige_claude
```

2. Maak een `.env` bestand in de root van het project (zie `docker-compose.example.env` voor een template):
```
# Kies een provider (google, openai of anthropic)
LLM_PROVIDER=anthropic

# API keys voor verschillende providers
GOOGLE_API_KEY=your_google_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Plek voor opslag van documenten
STORAGE_PATH=/app/storage
```

Raadpleeg [SECURITY.md](SECURITY.md) voor richtlijnen over het veilig beheren van API keys en andere gevoelige informatie.

3. Start de applicatie met Docker Compose:
```bash
docker-compose up -d
```

Dit start de volgende services:
- PostgreSQL database met pgvector extensie voor vector zoeken
- Redis voor caching en message queuing
- Backend API server op poort 8000
- Backend worker voor asynchrone taken

4. Start de frontend (voor ontwikkeling):
```bash
cd app/frontend
npm install
npm run dev
```

De frontend is nu beschikbaar op http://localhost:5173

### Belangrijke updates

#### Gebruikersprofielen (mei 2025)
Er is een compleet gebruikersprofielsysteem toegevoegd dat zorgt voor verbeterde rapportage en branding:

- **Profielbeheer**:
  - Arbeidsdeskundigen kunnen persoonlijke informatie toevoegen
  - Bedrijfsgegevens voor in het rapport vastleggen
  - Professionele informatie, certificeringen en specialisaties bijhouden

- **Logo Upload**:
  - Mogelijkheid om bedrijfslogo's toe te voegen
  - Logo's worden automatisch in rapporten opgenomen
  - Professionele uitstraling in alle rapportages

- **Rapportintegratie**:
  - Alle profielgegevens worden automatisch in gegenereerde rapporten gebruikt
  - Contactgegevens, certificeringen en expertise worden correct getoond
  - Consistente branding voor zowel zelfstandigen als organisaties

#### Hybride RAG Implementatie (mei 2025)
De document processing en rapport generatie pipeline is volledig vernieuwd met een hybride aanpak die de volgende voordelen biedt:

- **Directe Beschikbaarheid**: Documenten zijn onmiddellijk beschikbaar na upload
- **Hybride Verwerking**:
  - Kleine documenten worden direct naar het LLM gestuurd voor optimale resultaten
  - Grote documenten gebruiken de RAG-pipeline met vector search
  - Automatische intelligente selectie van de beste methode

- **Asynchrone Vectorisatie**:
  - Embeddings worden op de achtergrond gegenereerd zonder de gebruikersinterface te blokkeren
  - Documenten krijgen geleidelijk verbeterde semantische zoekfunctionaliteit
  - Prioritering van embeddings generatie op basis van documentgrootte

- **Robuuste Foutafhandeling**:
  - Volledige fallback-mechanismen wanneer vector search niet beschikbaar is
  - Verbeterde chunking met paragraafbehoud voor beter begrip van de context
  - Automatische herstelcapaciteit bij onderbroken verwerking

Deze hybride aanpak zorgt voor een optimale balans tussen gebruiksvriendelijkheid (directe beschikbaarheid) en geavanceerde RAG-capaciteiten (verbeterde semantische zoekfunctionaliteit), terwijl de stabiliteit gewaarborgd blijft.

#### Technische Details

1. **Gebruikersprofielen Implementatie**:
   - PostgreSQL schema met user_profile en profile_logo tabellen
   - Automatische creatie van profielen bij eerste login
   - Wizardinterface voor stapsgewijze profilering
   - Volledig responsieve UI voor alle apparaten

2. **Bedrijfslogo Integratie**:
   - Veilige opslag van bedrijfslogo's in geïsoleerde storage
   - Automatische formaat-optimalisatie voor rapporten
   - Streaming file uploads met voortgangsindicatie
   - Ondersteuning voor alle gangbare afbeeldingsformaten

3. **Documentgrootte Classificatie**:
   - Kleine documenten (<20.000 tekens): Direct LLM-benadering met hoge prioriteit embeddings
   - Middelgrote documenten (<60.000 tekens): Hybride aanpak met medium prioriteit embeddings
   - Grote documenten (>60.000 tekens): RAG-pipeline met lage prioriteit embeddings

4. **Intelligent Chunking**:
   - Paragraafgebaseerd chunking behoudt de semantische eenheden
   - Dynamische overlap gebaseerd op documentstructuur
   - Metadata verrijking met document- en chunkinformatie

5. **Asynchrone Verwerking**:
   - Documenten worden direct als 'processed' gemarkeerd
   - Embeddings worden asynchroon gegenereerd met prioriteitsqueue
   - Status-updates naar 'enhanced' wanneer embeddings beschikbaar zijn

6. **Verbeterde Rapportgeneratie**:
   - Intelligente selectie tussen directe LLM- en RAG-aanpak
   - Context-aware prompt engineering voor optimale resultaten
   - Fallback-mechanismen voor robuuste werking
   - Automatische integratie van profielgegevens en branding

### Debugging Tools

Voor het debuggen van API calls en authenticatie issues, bezoek de debug pagina op http://localhost:5173/test. Deze pagina biedt:

- Token inspectie
- API request logging
- Sessie informatie
- Template fetching tester

### Authentication

De applicatie gebruikt een lokale JWT-gebaseerde authenticatie voor ontwikkeling. Elke gebruikersnaam en wachtwoord wordt geaccepteerd in de lokale omgeving.

### Profielbeheer

Na het inloggen kun je je profiel beheren via de "Mijn Profiel" link in de navigatiebalk. Hier kun je:

1. **Persoonlijke gegevens invullen**:
   - Naam, functie, en biografische informatie
   - Deze gegevens worden gebruikt in rapporten

2. **Bedrijfsinformatie toevoegen**:
   - Bedrijfsnaam, contactgegevens, en adres
   - Deze worden gebruikt in de header van rapporten

3. **Professionele informatie beheren**:
   - Certificeringen en registratienummers toevoegen
   - Specialisaties definiëren voor betere rapportgeneratie

4. **Logo uploaden**:
   - Bedrijfslogo's en afbeeldingen voor in rapporten
   - Ondersteunt JPG, PNG, GIF en SVG formaten

Het volledige profiel wordt automatisch gebruikt bij het genereren van arbeidskundige rapporten.

### Foutopsporing

Als je problemen ondervindt met de applicatie:

1. Controleer de console logs in zowel de browser als de backend containers
2. Gebruik de debug pagina op `/test` om API calls te testen
3. Bekijk de document verwerking logs via `docker-compose logs -f backend-worker`

### Zonder Google API Key

De applicatie kan werken zonder Google API key, maar met beperkte functionaliteit:
- Document upload en verwerking werkt
- Document chunking werkt zonder vector embeddings
- Rapport generatie zal beperkt functioneren (alleen directe LLM-aanpak voor kleine documenten)

### Supabase Setup (Alternatief - Deprecated)

De Supabase implementatie is niet langer actief onderhouden, omdat de applicatie is gemigreerd naar een volledig lokale PostgreSQL implementatie. De oude Supabase configuratie scripts blijven beschikbaar voor referentie.

## Projectstructuur

```
app/
├── backend/
│   ├── app/
│   │   ├── api/              # API endpoints
│   │   ├── core/             # Core configuratie
│   │   ├── models/           # Database modellen
│   │   └── tasks/            # Celery taken (processing, RAG)
│   ├── migrations/           # Alembic database migraties
│   └── Dockerfile            # Backend Dockerfile
├── frontend/
│   ├── src/
│   │   ├── assets/           # Statische assets
│   │   ├── components/       # Vue componenten
│   │   ├── router/           # Vue router configuratie
│   │   ├── services/         # API en Supabase services
│   │   ├── stores/           # Pinia state management
│   │   ├── types/            # TypeScript interfaces
│   │   └── views/            # Vue pagina componenten
│   └── index.html            # HTML entry point
└── docker-compose.yml        # Docker Compose configuratie
```

## Licentie

Dit project is beschikbaar onder de [MIT licentie](LICENSE)