# Getting Started met AD-Rapport Generator

Deze gids helpt je om de AD-Rapport Generator lokaal op te zetten en te testen.

## Vereisten

- **Python 3.10+** voor de backend
- **Node.js 16+** voor de frontend
- **Docker en Docker Compose** voor de lokale ontwikkelomgeving
- **Google API Key** voor toegang tot Gemini AI
- **Supabase Account** voor database, auth en storage

## 1. Project Klonen

```bash
git clone <repository-url>
cd ai-arbeidsdeskundige_claude
```

## 2. Supabase Setup

Volg de instructies in `supabase_setup.md` om je Supabase project te configureren en de benodigde tabellen aan te maken.

## 3. Backend Setup

```bash
# Navigeer naar de backend directory
cd app/backend

# Maak .env bestand (kopieer van example en pas aan)
cp .env.example .env

# Vul in je .env bestand:
# - SUPABASE_URL
# - SUPABASE_KEY (service_role key)
# - GOOGLE_API_KEY

# Start de backend services met Docker Compose
docker-compose up -d
```

De API zal beschikbaar zijn op `http://localhost:8000`. Test dit met:
```bash
curl http://localhost:8000/
# Je zou een JSON response moeten krijgen: {"message":"AD-Rapport Generator API"}
```

## 4. Frontend Setup

```bash
# Navigeer naar de frontend directory
cd app/frontend

# Installeer dependencies
npm install

# Maak .env.local bestand (kopieer van example en pas aan)
cp .env.example .env.local

# Vul in je .env.local bestand:
# - VITE_SUPABASE_URL
# - VITE_SUPABASE_KEY (anon key)
# - VITE_API_BASE_URL (http://localhost:8000/api/v1)

# Start de development server
npm run dev
```

De frontend zal beschikbaar zijn op `http://localhost:5173`.

## 5. Gebruikersregistratie

1. Open de app in je browser: http://localhost:5173
2. Klik op "Registreren" om een account aan te maken
3. Vul een e-mailadres en wachtwoord in

## 6. Je Eerste Rapport Genereren

1. **Case aanmaken**:
   - Klik op "Nieuwe Case" na inloggen
   - Vul een titel en optionele beschrijving in
   - Klik op "Aanmaken"

2. **Document uploaden**:
   - Ga naar de case details pagina
   - Klik op "Document Uploaden"
   - Selecteer een Word (.docx) of tekstbestand (.txt) met relevante informatie
   - Wacht tot het bestand is verwerkt (status verandert naar "processed")

3. **Rapport genereren**:
   - Klik op "Nieuw Rapport"
   - Kies het template "Staatvandienst Format"
   - Vul een titel in en klik op "Genereren"
   - Wacht tot het rapport is gegenereerd (dit kan enkele minuten duren)

4. **Resultaat bekijken**:
   - Klik op het gegenereerde rapport om het te openen
   - Bekijk de verschillende secties
   - Kopieer de inhoud naar je eigen document indien gewenst

## 7. Debugging

### Backend logs bekijken:
```bash
docker-compose logs -f
```

### Frontend logs:
Deze zijn zichtbaar in je browser console (F12)

## 8. Stoppen

Om de lokale ontwikkelomgeving te stoppen:

```bash
# Stop de frontend met Ctrl+C in de terminal
# Stop de backend containers:
cd app/backend
docker-compose down
```

## 9. Next Steps

Na het testen van de MVP, overweeg:

1. Het toevoegen van meer templates
2. Het verbeteren van de zoekfunctionaliteit  
3. Het toevoegen van editing mogelijkheden voor rapporten
4. Het implementeren van een volledige deployment pipeline