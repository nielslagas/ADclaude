# RAG Pipeline: Volgende Stappen

Dit document beschrijft de roadmap voor het herstellen van de RAG (Retrieval-Augmented Generation) functionaliteit in de AI-Arbeidsdeskundige applicatie.

## Huidige Situatie

Momenteel is de RAG pipeline vereenvoudigd om stabiliteit te waarborgen:
- Documenten worden direct als "processed" gemarkeerd in de API endpoint
- Er worden geen vector embeddings gegenereerd
- Documenten worden wel opgeslagen en in chunks verdeeld, maar zonder vectorisatie

Deze aanpak heeft het probleem van vastlopende document verwerking succesvol opgelost, maar met als trade-off dat de semantische zoekfunctionaliteit tijdelijk is uitgeschakeld.

## Opties voor Herstel RAG Functionaliteit

### Optie 1: Asynchrone Verwerking met Verbeterde Stabiliteit

Deze benadering herstelt de oorspronkelijke RAG functionaliteit, maar met substantiële verbeteringen:

1. **Directe Beschikbaarheid + Asynchrone Verwerking**:
   - Documenten worden direct als "processed" gemarkeerd bij upload
   - Een asynchrone, laaggeprioriteerde taak start voor vector embeddings generatie
   - Document status wordt bijgewerkt naar "enhanced" na voltooiing van embeddings

2. **Verbeterde Robuustheid**:
   - Strikte timeouts op alle operaties
   - Automatische retry mechanisme voor gefaalde chunks
   - Batchgewijze verwerking met actieve geheugenmonitoring
   - Circuit breaker patroon voor directe afbouw bij hoge belasting

3. **Incrementele Implementatie**:
   ```python
   @celery.task(priority=1)  # Laagste prioriteit
   def enhance_document_vectors(document_id: str):
       """
       Asynchrone taak die vectorisatie toevoegt aan reeds beschikbare documenten
       """
       # Document is al beschikbaar voor gebruiker
       # Genereer embeddings op achtergrond zonder blokkeren
       # Update status naar "enhanced" wanneer gereed
   ```

### Optie 2: LLM-first Benadering (Zonder Vectorisatie)

Deze benadering vermijdt de complexiteit van RAG volledig:

1. **Document Direct naar LLM**:
   - Stuur het volledige document (of grote delen) direct naar het LLM
   - Elimineer de noodzaak voor vectorisatie en retrieval
   - Vertrouw op het contextvenster van modernere LLMs (bijv. Gemini 1.5 Pro)

2. **Voordelen**:
   - Eenvoudiger implementatie
   - Geen complexe indexering en vectorisatie
   - Minder resource-intensief

3. **Implementatie Voorbeeld**:
   ```python
   def generate_report_with_full_context(document_id: str, report_template: str):
       """
       Genereer rapport met volledige document context
       """
       document = db_service.get_document_with_chunks(document_id)
       full_text = "\n\n".join([chunk["content"] for chunk in document["chunks"]])
       
       # Stuur volledige tekst naar LLM
       llm_response = gemini_service.generate_with_context(
           template=report_template,
           context=full_text
       )
       
       return llm_response
   ```

### Optie 3: Hybride Benadering

Een combinatie van beide benaderingen:

1. **Directe Verwerking voor Kleine Documenten**:
   - Voor documenten onder een bepaalde grootte (bijv. <20 pagina's), stuur direct naar LLM
   - Voor grotere documenten, gebruik asynchrone RAG met embeddings

2. **Intelligente Chunking**:
   - Verbeterde chunking die semantische eenheden respecteert (paragrafen, secties)
   - Behoud van documentstructuur in chunks

3. **Progressieve Vectorisatie**:
   - Begin met vectorisatie van de meest relevante delen
   - Voeg incrementeel meer vectoren toe in de achtergrond

## Implementatieplan

### Fase 1: Voorbereidende Analyse (Week 1)
- Uitvoeren van uitgebreide tests van LLM met volledige context vs. RAG
- Analyseren van geheugengebruik en performance bij verschillende documentgroottes
- Bepalen van optimale strategie gebaseerd op testresultaten

### Fase 2: Implementatie Basis Functionaliteit (Week 2)
- Ontwikkelen van de gekozen strategie (Asynchrone RAG of LLM-first)
- Implementeren van verbeterde chunking en indexering
- Uitgebreide test harness voor validatie

### Fase 3: Stabiliteit en Schaalbaarheid (Week 3)
- Implementeren van monitoring en observability
- Stress testen met verschillende belastingen
- Finetuning van performance parameters

### Fase 4: Uitrol en Validatie (Week 4)
- Bèta-rollout naar testgebruikers
- Verzamelen van gebruikersfeedback
- Iteratieve verbeteringen

## Metrieken voor Succes

1. **Stabiliteit**: Geen vastlopende verwerking
2. **Performance**: Document verwerking < 5 seconden voor directe beschikbaarheid
3. **Kwaliteit**: Rapporten met hetzelfde of hogere kwaliteitsniveau als huidige implementatie
4. **Schaalbaarheid**: Ondersteuning voor documenten tot 100+ pagina's
5. **Gebruikerservaring**: Direct beschikbare documenten in de interface

## Risico's en Mitigaties

| Risico | Mitigatie |
|--------|-----------|
| LLM contextvenster onvoldoende | Implementeer slimme chunking voor grote documenten |
| Hoog geheugengebruik bij vectorisatie | Batch verwerking met strikt geheugenmanagement |
| Langzame asynchrone verwerking | Implementeer progressieve beschikbaarheid van embeddings |
| API kosten bij grotere documenten | Intelligente selectie van meest relevante delen |

## Conclusie

Het herstellen van de RAG functionaliteit is een kritieke volgende stap, maar moet worden uitgevoerd met stabiliteit en gebruikerservaring als hoogste prioriteit. De hybride benadering lijkt de meest veelbelovende route, waarbij we de voordelen van directe LLM context combineren met de schaalbaarheid van RAG voor grotere documenten.

---

*Laatst bijgewerkt: 8 mei 2025*