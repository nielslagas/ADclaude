# Supabase Setup Instructies

## Database Setup

1. Log in bij je Supabase dashboard
2. Ga naar de SQL Editor
3. Voer de SQL-scripts in `supabase_schema.sql` uit om de tabellen en functies te maken
4. Voer vervolgens het script in `supabase_storage.sql` uit om storage te configureren

## Auth Configuratie

1. Ga naar het tabblad **Authentication** in het Supabase dashboard
2. Onder **Providers**, zorg ervoor dat **Email** is ingeschakeld
3. Configureer de instellingen voor e-mailverificatie naar wens (voor MVP kun je 'Confirm email' uitschakelen voor eenvoudigere testen)
4. Als je SMTP wilt configureren voor echte e-mails, doe dit onder **Email Templates**

## Storage Configuratie

1. Ga naar het tabblad **Storage** in het Supabase dashboard
2. Controleer of de bucket "documents" is aangemaakt (dit zou moeten gebeuren via het SQL-script)
3. Controleer de policies om te zorgen dat gebruikers alleen toegang hebben tot hun eigen documenten

## API Keys en URL

1. Ga naar **Project Settings** > **API**
2. Kopieer de volgende gegevens voor je `.env` bestanden:
   - **Project URL** (anon, publieke URL)
   - **anon public** API key (voor frontend gebruik)
   - **service_role** key (alleen voor backend gebruik, houd deze geheim!)

## Connect Vanuit Je App

1. Maak een `.env` bestand aan in de `app/backend` directory:
```
SUPABASE_URL=https://jouwprojectid.supabase.co
SUPABASE_KEY=jouw_service_role_key
GOOGLE_API_KEY=jouw_google_api_key
REDIS_URL=redis://localhost:6379/0
```

2. Maak een `.env.local` bestand aan in de `app/frontend` directory:
```
VITE_SUPABASE_URL=https://jouwprojectid.supabase.co
VITE_SUPABASE_KEY=jouw_anon_key
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## Test Je Setup

1. Start je backend met:
```bash
cd app/backend
docker-compose up
```

2. Start je frontend met:
```bash
cd app/frontend
npm install
npm run dev
```

3. Maak een testgebruiker aan door naar je app te gaan (http://localhost:5173) en het registratieproces te doorlopen.

4. Test de applicatie door:
   - Een case aan te maken
   - Een document te uploaden
   - Een rapport te genereren

## Probleemoplossing

### pgvector Issues

Als je problemen ondervindt met de vector functies, controleer:
1. Dat de dimensie van je embeddings overeenkomt met de vector kolom (768 voor Gemini)
2. Dat de SQL-functie `search_document_chunks_vector` correct is aangemaakt
3. Log de input en output van de embedding functies om te controleren of ze werken

### Auth Issues

Als je problemen hebt met authenticatie:
1. Controleer je JWT-configuratie in Supabase
2. Controleer of je de correcte API keys gebruikt (anon voor frontend, service_role voor backend)
3. Check de CORS-instellingen in je backend

### Storage Issues

Als je problemen hebt met bestandsuploads:
1. Controleer de storage policies
2. Controleer de RLS-instellingen voor de Document tabel
3. Kijk naar de logs van zowel frontend als backend voor foutmeldingen