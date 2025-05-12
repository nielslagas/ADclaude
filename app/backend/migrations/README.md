# Database Migrations

Dit document beschrijft de database migraties voor het AI-Arbeidsdeskundige project.

## Nieuwe schema wijzigingen

De volgende wijzigingen zijn toegevoegd:

### Document model
- `document_type`: Type van het document (document, audio, image)
- `content`: Inhoud van het document (bijv. transcriptie)
- `processing_strategy`: Verwerking strategie (direct_llm, hybrid, full_rag)

### Nieuwe endpoints
- `/audio/upload/`: Upload audio bestand en start transcriptie
- `/audio/record/`: Sla opgenomen audio op en start transcriptie
- `/audio/{document_id}/status`: Controleer transcriptie status

## Uitvoeren van migraties

Migraties worden automatisch uitgevoerd bij het starten van de Docker containers.

Om migraties handmatig uit te voeren:

```bash
# In de backend container
alembic upgrade head
```

Om een nieuwe migratie te maken:

```bash
# In de backend container
alembic revision --autogenerate -m "Beschrijving van wijzigingen"
```

## Nieuwe vereisten

Voor de spraakfunctionaliteit moeten de volgende pakketten worden geïnstalleerd:

```
openai-whisper==20240930
numba
numpy
torch
ffmpeg-python
```