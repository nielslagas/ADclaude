# RAG Pipeline: Geavanceerde Documentverwerking en Rapportgeneratie

Dit document beschrijft de Retrieval-Augmented Generation (RAG) pipeline die wordt gebruikt voor het verwerken van documenten en het genereren van rapporten in het AI-Arbeidsdeskundige project.

## Overzicht

De RAG pipeline bestaat uit de volgende hoofdcomponenten:

1. **Document Processing** - Het voorbereiden, verwerken en opslaan van documenten
2. **Chunking** - Het opdelen van documenten in bruikbare segmenten
3. **Embedding Generation** - Het genereren van vectorrepresentaties voor documentchunks
4. **Vector Storage** - Het opslaan en indexeren van embeddings met pgvector
5. **Similarity Search** - Het vinden van relevante documentchunks
6. **Prompt Generation** - Het samenstellen van effectieve prompts voor het LLM
7. **Content Generation** - Het genereren van rapportinhoud

## Technische Implementatie

### Document Processing

Het verwerkingsproces voor documenten verloopt als volgt:

1. Bestand wordt geüpload en opgeslagen op de server
2. Document metadata wordt opgeslagen in de `document` tabel
3. Celery worker start de achtergrondtaak `process_document_mvp`
4. Document wordt geparsed op basis van MIME-type (momenteel ondersteuning voor .docx en .txt)
5. Tekst wordt in chunks opgedeeld
6. Elke chunk krijgt een embedding en wordt opgeslagen

```python
# Uploaden document via API endpoint
@router.post("/", response_model=DocumentRead)
async def upload_document(
    case_id: str = Form(...),
    file: UploadFile = File(...)
):
    # Verwerking en opslag van document
    # ...

    # Start asynchrone document processing taak
    process_document_mvp.delay(document.id)
    
    return document
```

### Geavanceerde Chunking

We hebben een geavanceerde chunking-strategie geïmplementeerd die documentstructuur behoudt en context-aware is:

```python
def chunk_document(text, chunk_size, chunk_overlap, preserve_structured_content=True):
    """
    Split a document into chunks with specified size and overlap using advanced
    chunking strategies to preserve document structure and context.
    """
    # Implementatie details...
```

De chunking-strategie:

- Detecteert kopteksten en sectiestructuur
- Breekt tekst op natuurlijke punten (paragrafen, zinnen)
- Voegt contextuele headers toe aan chunks voor betere oriëntatie
- Handhaaft zinstructuur en voorkomt het midden van zinnen af te breken
- Implementeert overlap tussen chunks om context te behouden

### Embedding Generatie

Voor het genereren van embeddings gebruiken we:

1. Primair: Google Gemini API voor embeddings
2. Fallback: Deterministische embedding generatie voor consistentie
3. Laatste redmiddel: Random embeddings voor testen

```python
def generate_embedding(text: str, dimension: int = 768) -> List[float]:
    """
    Generate embeddings using Google's Gemini model.
    """
    # Implementatie details...
```

### Vector Opslag en Zoeken

Voor efficiënte vectoropslag en zoeken gebruiken we:

1. PostgreSQL met pgvector extensie
2. HNSW indexering voor snelle similarity search
3. Een aangepaste stored procedure voor optimale prestaties

```sql
-- Create function to search document chunks by vector similarity
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
    -- Implementatie details...
$$ LANGUAGE plpgsql;
```

### Query Formulering

We gebruiken domeinspecifieke query-expansie voor het vinden van relevante content:

```python
# Enhanced query formulation for Dutch labor expert contexts
query_mapping = {
    "samenvatting": [
        "persoonsgegevens leeftijd geslacht opleiding werkervaring cliënt", 
        "voorgeschiedenis arbeidssituatie ziektegeschiedenis werknemer",
        # ...meer queries...
    ],
    # ...meer secties...
}
```

Deze aanpak:
- Gebruikt meerdere semantisch diverse queries per rapportsectie
- Is geoptimaliseerd voor de Nederlandse arbeidskundige context
- Implementeert domeinspecifieke terminologie
- Past query-diversiteit aan per sectietype
- Bevat fallback strategieën voor kleine documentsets

### Prompt Engineering

Onze prompts zijn zorgvuldig ontworpen voor het genereren van professionele rapportinhoud:

1. Secties bevatten hun eigen geoptimaliseerde prompts
2. Contextuele informatie wordt effectief georganiseerd
3. Documentmetadata wordt opgenomen voor beter begrip
4. Prompts bevatten zowel inhoudelijke als vormgevingsinstructies

```python
def create_prompt_for_section(section_id: str, section_info: Dict, chunks: List[Dict]):
    """
    Create a prompt for generating content for a specific report section
    based on the retrieved chunks with improved context formatting and organization
    """
    # Implementatie details...
```

### Content Generatie

Voor het genereren van content gebruiken we:

1. Google Gemini API met geoptimaliseerde parameters
2. Specifieke safety settings voor professionele content
3. Robuuste error handling en retries
4. Verificatie van output kwaliteit

```python
def generate_content_with_llm(prompt: str):
    """
    Generate content using Google's Gemini model with optimized settings
    for high-quality, factual report generation
    """
    # Implementatie details...
```

## Dataflow Diagram

```
Documentupload → Opslag → Chunking → Embedding Generatie → Vector Opslag
       ↓
Query Formulering → Embedding Generatie → Vector Similarity Search
       ↓
Relevante Chunks → Prompt Generation → LLM Content Generation → Rapport Sectie
```

## Prestatie-optimalisaties

1. **HNSW Indexering**: Gebruikt voor efficiënte nearest-neighbor zoekoperaties
2. **Batch Processing**: Verwerkt documenten asynchroon in batches
3. **Query Expansion**: Verbetert recall door meerdere semantisch diverse queries
4. **Contextbehoud**: Voorkomt verlies van informatie tussen chunks
5. **Fallback Strategieën**: Garandeert operabiliteit zelfs bij API-onderbrekingen

## Ontwerpbeslissingen

1. **pgvector vs. externe vectordatabase**: PostgreSQL met pgvector biedt voldoende prestaties voor deze use-case en vermindert externe afhankelijkheden
2. **Chunking strategie**: Gebalanceerd tussen behoud van context en optimalisatie van embedding-effectiviteit
3. **768-dimensionale vectoren**: Standaardafmeting voor tekstembeddings, balans tussen precisie en opslag
4. **Gebruik van stored procedures**: Optimaliseert databaseprestaties door verwerking naar de database te verplaatsen

## Toekomstige Verbeteringen

1. **Verfijning van chunking strategie**: Implementeren van meer geavanceerde documentstructuuranalyse
2. **Betere embeddings**: Integratie met nieuwere embedding-modellen naarmate deze beschikbaar komen
3. **Optimalisatie van cosine similarity thresholds**: Aanpassingen op basis van praktijkgebruik
4. **Rerank mechanisme**: Implementatie van een tweede ranking-fase voor betere resultaten
5. **Feedback loop**: Systeem voor gebruikersfeedback om zoekresultaten en gegenereerde inhoud te verbeteren

---

*Laatst bijgewerkt: 8 mei 2025*