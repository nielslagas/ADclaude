# RAG en Spraakfunctionaliteit Implementatie

Dit document beschrijft de implementatie van de hybride RAG-aanpak en spraakfunctionaliteit voor het AI-Arbeidsdeskundige project.

## 1. Hybride RAG Implementatie

### Overzicht

De hybride RAG-implementatie combineert directe LLM-benadering voor kleine documenten met asynchrone vector embeddings voor grotere documenten. Dit zorgt voor een optimale balans tussen gebruikerservaring en intelligente document verwerking.

### Componenten

1. **Document Classifier (`document_classifier.py`)**
   - Classificeert documenten op basis van grootte
   - Bepaalt optimale verwerkingsstrategie (direct_llm, hybrid, full_rag)
   - Prioriteert verwerking op basis van documentgrootte

2. **Hybrid Processor (`hybrid_processor.py`)**
   - Centrale component voor document verwerking
   - Markeert documenten direct als "processed" voor snelle gebruikersfeedback
   - Creëert eenvoudige chunks zonder embeddings
   - Dispatcht asynchrone taken voor embeddings generatie

### Verwerkingsstrategieën

1. **Direct LLM** (kleine documenten < 20K tekens)
   - Document wordt direct naar het LLM gestuurd
   - Geen vector embeddings nodig
   - Hoge prioriteit voor snelle verwerking

2. **Hybrid** (middelgrote documenten < 60K tekens)
   - Document is direct beschikbaar voor gebruik
   - Vectorisatie gebeurt asynchroon op de achtergrond
   - Medium prioriteit voor embeddings generatie

3. **Full RAG** (grote documenten > 60K tekens)
   - Document is direct beschikbaar voor basis gebruik
   - Volledige RAG-pipeline wordt op de achtergrond uitgevoerd
   - Lage prioriteit voor embeddings generatie

### Voordelen

- Gebruikers kunnen direct met documenten werken (geen wachttijd)
- Systeem wordt geleidelijk slimmer door asynchrone embeddings
- Automatische selectie van optimale strategie per document
- Schaalbaarheid voor documenten van elke grootte

## 2. Spraakfunctionaliteit

### Overzicht

De spraakfunctionaliteit stelt gebruikers in staat om audio op te nemen of te uploaden, die vervolgens wordt getranscribeerd en geïntegreerd in het document verwerkingssysteem.

### Componenten

1. **Audio Transcriber (`audio_transcriber.py`)**
   - Verwerkt audio-opnames met OpenAI Whisper
   - Ondersteunt meerdere audio-formaten
   - Asynchroon verwerking via Celery

2. **Audio API Endpoints (`audio.py`)**
   - `/audio/upload/`: Upload audio bestand
   - `/audio/record/`: Sla browser-opgenomen audio op
   - `/audio/{document_id}/status`: Controleer transcriptie status

3. **Frontend Componenten**
   - `AudioRecorder.vue`: Component voor audio-opname in de browser
   - `AudioRecordingView.vue`: Pagina voor opname en beheer van audio

### Proces

1. Gebruiker neemt audio op via de browser of uploadt een bestaand audio bestand
2. Audio wordt opgeslagen in het systeem en gemarkeerd als "processing"
3. Een Celery-taak transcribeert de audio met Whisper
4. Na voltooiing wordt het document gemarkeerd als "processed"
5. De transcriptie is beschikbaar voor gebruik in rapporten

### Voordelen

- Flexibele invoermethode voor arbeidsdeskundigen
- Mogelijkheid om verslagen onderweg op te nemen
- Integratie met bestaande RAG-pipeline
- Ondersteuning voor meerdere audio-formaten

## 3. Database Wijzigingen

Het documentmodel is uitgebreid met de volgende velden:

- `document_type`: Type document (document, audio, image)
- `content`: Inhoud van het document (bijv. transcriptie)
- `processing_strategy`: Verwerkingsstrategie (direct_llm, hybrid, full_rag)

## 4. Uitrol Instructies

### Vereisten

Voor de nieuwe functionaliteit zijn de volgende packages nodig:
- OpenAI Whisper (`openai-whisper>=20240930`)
- NumPy en Numba voor audio verwerking
- FFmpeg voor audio-bestandsconversie
- PyTorch voor Whisper model

### Database Migratie

Voer de volgende commando's uit om de database bij te werken:

```bash
cd app/backend
alembic upgrade head
```

### Omgevingsvariabelen

Geen nieuwe omgevingsvariabelen nodig. De bestaande configuratie voor LLM's werkt ook voor de nieuwe functionaliteit.

### Docker Opnieuw Bouwen

Bouw de Docker-images opnieuw om de nieuwe afhankelijkheden te installeren:

```bash
docker-compose build backend-api backend-worker
docker-compose up -d
```

## 5. Volgende Stappen

1. **Uitbreiding van Audio Processing**
   - Ondersteuning voor sprekerherkenning (diarization)
   - Automatische sectie-indeling in transcripties
   - Verfijnen van transcripties met Claude

2. **RAG Optimalisaties**
   - Implementeren van geavanceerde chunking-strategieën met paragraafbehoud
   - Vectorstore optimalisaties voor betere zoekresultaten
   - Intelligente selectie van relevante chunks

3. **Gebruikerstesten**
   - Valideer de hybride RAG-aanpak met echte gebruikers
   - Test de spraakfunctionaliteit in praktijksituaties
   - Verzamel feedback voor verdere verbeteringen