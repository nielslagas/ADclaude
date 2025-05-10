# Probleem: 'Dangerous_Content' Error bij Rapport Generatie

## Probleem Analyse

Bij het genereren van rapporten treedt er een error op met de melding:
```
Er kon geen inhoud worden gegenereerd voor deze sectie: Error generating content with direct LLM: 'dangerous_content'
```

Deze error wordt veroorzaakt door Gemini's inhoudsbeleid dat bepaalde soorten inhoud blokkeert. In dit geval:

1. Het veiligheidsfilter van het model (BLOCK_MEDIUM_AND_ABOVE voor DANGEROUS_CONTENT) blokkeert de gegenereerde inhoud
2. Dit gebeurt waarschijnlijk omdat medische of persoonlijke gegevens worden gedetecteerd in combinatie met arbeidsadviezen
3. Gemini's veiligheidsfilters zijn strenger dan sommige andere modellen, vooral bij het geven van adviezen op basis van medische gegevens

## Voorgestelde Oplossing

### 1. Aanpassen van de Safety Settings in de RAG Pipeline

Verlaag de veiligheidsniveaus voor de "DANGEROUS_CONTENT" parameter, maar behoud stricte controles voor de andere parameters.

Pas de volgende bestanden aan:

#### 1. `/app/backend/app/tasks/generate_report_tasks/report_generator_hybrid.py`

Wijzig de safety_settings in de `generate_content_with_direct_llm` functie (rond regel 118-125):

```python
# Aangepaste safety settings om professionele content toe te staan
safety_settings = {
    "HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE",
    "HATE_SPEECH": "BLOCK_MEDIUM_AND_ABOVE",
    "SEXUALLY_EXPLICIT": "BLOCK_MEDIUM_AND_ABOVE",
    "DANGEROUS_CONTENT": "BLOCK_ONLY_HIGH",  # Gewijzigd van BLOCK_MEDIUM_AND_ABOVE naar BLOCK_ONLY_HIGH
}
```

#### 2. `/app/backend/app/tasks/generate_report_tasks/rag_pipeline.py`

Wijzig de safety_settings in de `generate_content_with_llm` functie (rond regel 423-429):

```python
# Aangepaste safety settings om professionele content toe te staan
safety_settings = {
    "HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE",
    "HATE_SPEECH": "BLOCK_MEDIUM_AND_ABOVE",
    "SEXUALLY_EXPLICIT": "BLOCK_MEDIUM_AND_ABOVE",
    "DANGEROUS_CONTENT": "BLOCK_ONLY_HIGH",  # Gewijzigd van BLOCK_MEDIUM_AND_ABOVE naar BLOCK_ONLY_HIGH
}
```

### 2. Verbeter de System Prompts

Pas de system instructions aan om duidelijker te maken dat dit gaat om professionele arbeidsdeskundige rapporten en niet om medisch advies.

#### 1. In `/app/backend/app/tasks/generate_report_tasks/report_generator_hybrid.py`

Wijzig de system_instruction (rond regel 142-149):

```python
# System instruction for professional tone
system_instruction = (
    "Je bent een ervaren arbeidsdeskundige die professionele rapporten opstelt "
    "volgens de Nederlandse standaarden. Schrijf in de stijl van een officieel arbeidsdeskundig rapport. "
    "Gebruik formele, zakelijke taal en zorg voor een objectieve, feitelijke weergave op basis van de aangeleverde "
    "informatie. Je biedt geen medisch advies, maar beschrijft alleen de situatie zoals die in de documenten "
    "is vastgesteld door medische professionals. Vermijd aannames of speculaties die niet onderbouwd zijn door "
    "de beschikbare gegevens."
)
```

#### 2. In `/app/backend/app/tasks/generate_report_tasks/rag_pipeline.py`

Wijzig de system_instruction (rond regel 452-459):

```python
# Add system instruction for professional tone
system_instruction = (
    "Je bent een ervaren arbeidsdeskundige die professionele rapporten opstelt "
    "volgens de Nederlandse standaarden. Schrijf in de stijl van een officieel arbeidsdeskundig rapport. "
    "Gebruik formele, zakelijke taal en zorg voor een objectieve, feitelijke weergave op basis van de aangeleverde "
    "informatie. Je biedt geen medisch advies, maar beschrijft alleen de situatie zoals die in de documenten "
    "is vastgesteld door medische professionals. Vermijd aannames of speculaties die niet onderbouwd zijn door "
    "de beschikbare gegevens."
)
```

### 3. Verbeterde Error Handling en Fallback Mechanismen

#### 1. In `/app/backend/app/tasks/generate_report_tasks/report_generator_hybrid.py`

Verbeter de error handling rond regel 163-167:

```python
# Enhanced error handling
if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
    block_reason = response.prompt_feedback.block_reason
    error_message = f"Content generation blocked: {block_reason}"
    logger.error(error_message)
    
    # Probeer opnieuw met een meer neutrale prompt als het gaat om dangerous_content
    if 'dangerous_content' in str(block_reason).lower():
        # Probeer een meer neutrale prompt te maken zonder contentfilters te triggeren
        try:
            simple_prompt = "Genereer een objectieve beschrijving op basis van de gegeven informatie, " + \
                            "waarbij je alleen feitelijke informatie uit de documenten gebruikt."
            simple_response = model.generate_content(
                [
                    {"role": "system", "parts": [system_instruction]},
                    {"role": "user", "parts": [simple_prompt + "\n\n" + context]}
                ]
            )
            if simple_response.text and len(simple_response.text.strip()) > 50:
                logger.info("Generated content using simplified neutral prompt")
                return simple_response.text
        except Exception as fallback_error:
            logger.error(f"Fallback prompt also failed: {str(fallback_error)}")
    
    return "Er kon geen inhoud worden gegenereerd. Mogelijk bevat de aangeleverde informatie gevoelige gegevens. " + \
           "Probeer een nieuw rapport aan te maken met aangepaste documenten."
```

#### 2. Vergelijkbare wijziging in `/app/backend/app/tasks/generate_report_tasks/rag_pipeline.py` rond regel 469-472

### 4. Implementeer Claude als Fallback Model

Als Gemini blijft blokkeren op 'dangerous_content', zou je kunnen overwegen Anthropic's Claude API als fallback model te implementeren. Claude heeft doorgaans minder problemen met professionele rapporten over arbeidsgeschiktheid.

Dit vereist extra implementatie en aanpassingen aan de code.

## Test Plan

1. Implementeer de voorgestelde wijzigingen in de safety settings en system prompts
2. Upload een test document met professionele arbeidskundige inhoud
3. Genereer een rapport en controleer of de secties nu correct worden ingevuld
4. Als de error blijft optreden, implementeer de verbeterde error handling
5. Indien nodig, implementeer het fallback model (Claude) als laatste optie

## Impact

De voorgestelde wijzigingen:

1. Laten het Gemini-model toe om professionele inhoud te genereren die eerder als potentieel 'gevaarlijk' werd gemarkeerd
2. Behouden de overige veiligheidsfilters voor ongewenste inhoud
3. Maken de prompts duidelijker en meer gericht op professionele rapportage
4. Bieden fallback mechanismen als de primary generatie mislukt
5. Lossen het probleem op met lege rapportsecties