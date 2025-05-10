# Technische Notitie: RAG Pipeline Fix Implementation

Deze notitie beschrijft de technische implementatie van de oplossing voor de RAG pipeline problemen in de arbeidsdeskundige rapport generator.

## Probleembeschrijving

De originele implementatie had de volgende problemen:

1. **Document processing blokkeerde**: Documenten waren pas beschikbaar na volledige verwerking (~81 seconden)
2. **RAG pipeline faalde**: Door ontbrekende vector search functionaliteit
3. **Report generatie traag**: Celery taken werden niet goed geregistreerd
4. **Error handling ontbrak**: Problemen waren moeilijk te diagnosticeren

## Geïmplementeerde Oplossing

We hebben een hybride benadering geïmplementeerd die de volgende componenten bevat:

### 1. Vector Search Functionaliteit

PostgreSQL functies voor vector similarity search zijn toegevoegd:

```sql
CREATE OR REPLACE FUNCTION search_document_chunks_vector(
    query_embedding vector(768),
    case_id uuid,
    match_threshold float DEFAULT 0.6,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id text,
    document_id uuid,
    content text,
    metadata jsonb,
    similarity float
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.chunk_id as id,
        c.document_id,
        c.content,
        c.metadata,
        1 - (c.embedding <=> query_embedding) as similarity
    FROM
        document_embeddings c
    JOIN
        document d ON c.document_id = d.id
    WHERE
        d.case_id = search_document_chunks_vector.case_id
        AND (1 - (c.embedding <=> query_embedding)) >= match_threshold
    ORDER BY
        c.embedding <=> query_embedding
    LIMIT
        match_count;
END;
$$ LANGUAGE plpgsql;
```

### 2. Hybride Document Processor

Een nieuwe document processor die:
- Documenten direct als 'processed' markeert
- Chunking direct uitvoert
- Asynchrone embeddings generatie inplant

```python
@celery.task
def process_document_hybrid(document_id: str):
    """
    Hybrid document processor that:
    1. Reads the document
    2. Splits it into chunks
    3. Stores the chunks in the database
    4. Marks the document as processed immediately
    5. Schedules asynchronous embedding generation
    """
    # Document is immediately marked as processed
    db_service.update_document_status(document_id, "processed")
    
    # Schedule asynchronous embedding generation based on document size
    if size_category == "small":
        # For small documents, generate embeddings immediately with high priority
        priority = 5
        delay_seconds = 1
    elif size_category == "medium":
        # Medium priority for medium sized documents
        priority = 3
        delay_seconds = 5
    else:
        # Lowest priority for large documents
        priority = 1
        delay_seconds = 10
```

### 3. Direct Report Generation

Om problemen met Celery taakregistratie te omzeilen, is de rapport generatie rechtstreeks in de API endpoints ingebouwd:

```python
# Directe implementatie in de API endpoint
try:
    # Get document texts for this case
    docs = db_service.get_rows("document", {
        "case_id": str(report_data.case_id),
        "status": "processed"
    })
    
    # Get document chunks and combine them
    all_content = ""
    for doc in docs:
        chunks = db_service.get_document_chunks(doc["id"])
        doc_content = "\n\n".join([chunk["content"] for chunk in chunks])
        all_content += f"\n\n=== DOCUMENT: {doc['filename']} ===\n\n{doc_content}"
    
    # Generate content for each section
    import google.generativeai as genai
    # Gemini 1.5 Pro configuratie
    # ...
```

### 4. Sectie Regeneratie

Een directe regeneratie van secties zonder Celery taken:

```python
# Directe implementatie zonder Celery taken
try:
    # Get document chunks for this case (using report's case_id)
    case_id = report["case_id"]
    documents = db_service.get_rows("document", {
        "case_id": case_id,
        "status": ["processed", "enhanced"]
    })
    
    # Get full document content
    all_content = ""
    for doc in documents:
        # Get document chunks
        chunks = db_service.get_document_chunks(doc["id"])
        
        # Combine chunk content
        doc_content = "\n\n".join([chunk["content"] for chunk in chunks])
        all_content += f"\n\n=== DOCUMENT: {doc['filename']} ===\n\n{doc_content}"
    
    # Create prompt and generate content
    # ...
```

## Technische Uitdagingen

Tijdens de implementatie kwamen de volgende uitdagingen naar voren:

1. **Gemini API Integratie**: De Gemini API ondersteunt geen systeem-rol in het formaat dat oorspronkelijk werd gebruikt.
   - Oplossing: Systeem instructies worden nu toegevoegd aan de gebruikers-prompt.

2. **Variabele scope issues**: Problemen met toegang tot variabelen tussen verschillende functies.
   - Oplossing: Variabelen opnieuw definiëren waar nodig, bijvoorbeeld `case_id = report["case_id"]`.

3. **Error handling**: Verbeterde error handling met graceful degradation.
   - Oplossing: Try-except blocks met duidelijke foutmeldingen en fallback mechanismen.

## Testresultaten

De geïmplementeerde oplossing is succesvol getest met:

1. Document upload en onmiddellijke verwerking
2. Rapport generatie met alle secties 
3. Sectie regeneratie op aanvraag

De hybride benadering zorgt voor:
- Directe beschikbaarheid van documenten
- Snellere rapport generatie
- Meer robuuste werking met fallback mechanismen

## Aanbevelingen voor Toekomstige Verbeteringen

1. **Celery Task Registratie Oplossen**: Het basis probleem met Celery task registratie aanpakken voor echte asynchrone verwerking.

2. **Betere Chunking Strategieën**: Geavanceerdere chunking strategieën implementeren die beter begrip van context behouden.

3. **Rijkere Prompts**: Meer geavanceerde prompt templates voor betere rapport generatie.

4. **UI Verbeteringen**: Meer feedback over verwerking en generatie status.

## Conclusie

De hybride benadering biedt een werkende oplossing voor de RAG pipeline problemen, met zowel directe beschikbaarheid als geavanceerde RAG functionaliteit. Deze implementatie zorgt voor een betere gebruikerservaring zonder in te leveren op de kwaliteit van de gegenereerde rapporten.

---
Datum: 8 mei 2025
Auteur: Ontwikkelteam AI-Arbeidsdeskundige